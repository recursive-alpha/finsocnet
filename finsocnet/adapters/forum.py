"""Trading forums: Discourse JSON, XenForo HTML, generic pages (docs/spec/05 §3.4). Everything loads through the agent browser."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote_plus, urljoin, urlsplit

import yaml
from lxml import html as lhtml

from finsocnet.adapters import _browser, web
from finsocnet.core import config
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, save_raw
from finsocnet.core.segments import html_to_markdown, refs

MAX_PAGES = 200


def known_forums() -> list[dict[str, Any]]:
    p = config.repo_root() / "config" / "forums.yaml"
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("forums", []) if p.exists() else []


def host_of(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix("www.")


def detect_engine(html: str, url: str = "") -> str:
    h = html[:60000].lower()
    if 'name="generator" content="discourse' in h or "discourse" in h and "data-discourse-setup" in h or "ember-cli" in h and "discourse" in h:
        return "discourse"
    if "data-template=" in h and ("xenforo" in h or "xf" in h) or 'content="xenforo' in h or "xenforo" in h:
        return "xenforo"
    if "vbulletin" in h:
        return "vbulletin"
    if "phpbb" in h:
        return "phpbb"
    for f in known_forums():
        if f["host"] == host_of(url):
            return f["engine"]
    return "generic"


def thread_id_of(url: str) -> str:
    m = re.search(r"/threads/[^/]*?\.?(\d+)|/t/[^/]+/(\d+)|/t/(\d+)|[?&]t=(\d+)|showthread[^\d]*(\d+)|-(\d+)\.html", url)
    if not m:
        raise CliError("USAGE", f"cannot read a thread id from {url!r}")
    return next(g for g in m.groups() if g)


def content_id(host: str, thread_id: str) -> str:
    return f"forum:{host}:{thread_id}"


# --- Discourse ------------------------------------------------------------------------------------------

def parse_discourse_topic(d: dict[str, Any], host: str, extra_posts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    posts = list(d["post_stream"]["posts"]) + (extra_posts or [])
    seen, uniq = set(), []
    for p in sorted(posts, key=lambda p: p["post_number"]):
        if p["id"] not in seen:
            seen.add(p["id"])
            uniq.append(p)
    segs = []
    for p in uniq:
        text = html_to_markdown(p.get("cooked", ""))
        if not text.strip():
            continue
        segs.append({"seq": len(segs), "kind": "post" if p["post_number"] == 1 else "reply", "locator": {"post_id": p["id"], "page": (p["post_number"] - 1) // 20 + 1, "parent_id": p.get("reply_to_post_number")},
                     "author": {"handle": p.get("username"), "display_name": p.get("name"), "platform_user_id": str(p.get("user_id") or "") or None}, "text": text})
    r = refs("\n".join(s["text"] for s in segs))
    return content_record(content_id(host, str(d["id"])), "forum", "thread", segs, url=f"https://{host}/t/{d.get('slug', 'topic')}/{d['id']}", title=d.get("title"),
                          author={"handle": uniq[0].get("username") if uniq else None}, published_at=d.get("created_at"), language="en", metrics={"views": d.get("views"), "replies": d.get("posts_count", 1) - 1, "likes": d.get("like_count")},
                          links=r["links"], mentions=r["mentions"], fetch_method="discourse_json", extra={"engine": "discourse", "tags": d.get("tags", []), "category_id": d.get("category_id")},
                          source={"id": f"forum:board:{host}:{d.get('category_id')}", "kind": "forum", "title": host})


# --- XenForo --------------------------------------------------------------------------------------------

def parse_xenforo_page(html: str, page: int) -> dict[str, Any]:
    root = lhtml.fromstring(html)
    posts = []
    for art in root.xpath("//article[contains(@class,'message') and @data-content]"):
        pid = (art.get("data-content") or "").replace("post-", "")
        body = art.xpath(".//div[contains(@class,'bbWrapper')]")
        if not body:
            continue
        b = body[0]
        quotes = []
        for q in b.xpath(".//blockquote"):
            quotes.append(" ".join(q.text_content().split()))
            q.getparent().remove(q)
        posts.append({"id": pid, "author": art.get("data-author"), "page": page, "text": html_to_markdown(lhtml.tostring(b, encoding="unicode")), "quotes": quotes,
                      "time": (art.xpath(".//time/@datetime") or [None])[0]})
    title = " ".join("".join(root.xpath("//h1[contains(@class,'p-title-value')]//text()")).split()) or " ".join(root.xpath("//title/text()")).split(" | ")[0].strip()
    last = max([int(x) for x in root.xpath("//ul[contains(@class,'pageNav-main')]//a/text()") if x.strip().isdigit()] or [page])
    return {"title": title, "posts": posts, "last_page": last}


def xenforo_record(host: str, tid: str, title: str, pages: list[dict[str, Any]], url: str, warnings: list[str]) -> dict[str, Any]:
    segs, first_time = [], None
    for pg in pages:
        for p in pg["posts"]:
            if not p["text"].strip():
                continue
            first_time = first_time or p["time"]
            segs.append({"seq": len(segs), "kind": "post" if not segs else "reply", "locator": {"post_id": p["id"], "page": p["page"]}, "author": {"handle": p["author"]}, "text": p["text"]})
    r = refs("\n".join(s["text"] for s in segs))
    return content_record(content_id(host, tid), "forum", "thread", segs or [{"seq": 0, "kind": "post", "locator": {}, "text": title}], url=url, title=title, author={"handle": segs[0]["author"]["handle"] if segs else None},
                          published_at=first_time, links=r["links"], mentions=r["mentions"], fetch_method="xenforo_html",
                          extra={"engine": "xenforo", "pages": len(pages), "warnings": warnings, "quotes": {p["id"]: p["quotes"] for pg in pages for p in pg["posts"] if p["quotes"]}},
                          source={"id": f"forum:board:{host}:main", "kind": "forum", "title": host})


class Forum(PlatformAdapter):
    platform = "forum"
    capabilities = frozenset({"search", "list", "fetch", "detect"})
    opts = {"fetch": [(("--max-pages",), {"type": int, "default": MAX_PAGES})], "search": [(("--host",), {"required": True})]}

    def detect(self, url: str) -> dict[str, Any]:
        _f, html = _browser.load_html("forum", url, wait="domcontentloaded")
        return {"url": url, "host": host_of(url), "engine": detect_engine(html, url), "known": next((f for f in known_forums() if f["host"] == host_of(url)), None)}

    def search(self, query, *, limit=20, since=None, host=None, **_):
        base = f"https://{host}"
        engine = next((f["engine"] for f in known_forums() if f["host"] == host), "generic")
        if engine == "discourse":
            d = _browser.load_json("forum", f"{base}/search.json?q={quote_plus(query)}")
            return [item_ref(f"{base}/t/{t['slug']}/{t['id']}", content_id(host, str(t["id"])), "thread", t.get("title"), None, t.get("created_at"), None, {"posts": t.get("posts_count")}) for t in d.get("topics", [])][:limit]
        _f, html = _browser.load_html("forum", f"{base}/search/search?keywords={quote_plus(query)}&type=post" if engine == "xenforo" else f"{base}/search?q={quote_plus(query)}")
        root = lhtml.fromstring(html)
        out, seen = [], set()
        for a in root.xpath("//a[contains(@href,'/threads/') or contains(@href,'/t/') or contains(@href,'showthread')]"):
            href = urljoin(base, a.get("href"))
            try:
                tid = thread_id_of(href)
            except CliError:
                continue
            if tid not in seen:
                seen.add(tid)
                out.append(item_ref(href, content_id(host, tid), "thread", " ".join(a.text_content().split())[:160], None, None, None))
        return out[:limit]

    def list(self, source, *, limit=30, cursor=None, since=None, **_):
        host = host_of(source)
        engine = next((f["engine"] for f in known_forums() if f["host"] == host), "generic")
        html = None
        if engine == "generic":  # host not in forums.yaml: detect the engine from the page itself
            _f, html = _browser.load_html("forum", re.sub(r"/page-\d+$", "", source.rstrip("/")) + (f"/page-{int(cursor)}" if cursor and int(cursor) > 1 else ""))
            engine = detect_engine(html, source)
        if engine == "discourse":
            d = _browser.load_json("forum", source.rstrip("/") + (".json" if not source.endswith(".json") else "") + (f"?page={cursor}" if cursor else ""))
            topics = d.get("topic_list", {}).get("topics", [])
            items = [item_ref(f"https://{host}/t/{t['slug']}/{t['id']}", content_id(host, str(t["id"])), "thread", t.get("title"), None, t.get("created_at"), None, {"posts": t.get("posts_count"), "views": t.get("views")}) for t in topics]
            return list_result(items[:limit], str(int(cursor or 0) + 1) if topics else None, {"id": f"forum:board:{host}:{source.rstrip('/').split('/')[-1]}"})
        page = int(cursor or 1)
        if html is None:
            _f, html = _browser.load_html("forum", re.sub(r"/page-\d+$", "", source.rstrip("/")) + (f"/page-{page}" if page > 1 else ""))
        root = lhtml.fromstring(html)
        items, seen = [], set()
        for a in root.xpath("//a[contains(@href,'/threads/')]"):
            href = urljoin(source, a.get("href").split("/unread")[0])
            try:
                tid = thread_id_of(href)
            except CliError:
                continue
            if tid not in seen and a.text_content().strip():
                seen.add(tid)
                items.append(item_ref(href, content_id(host, tid), "thread", " ".join(a.text_content().split())[:160], None, None, None))
        return list_result(items[:limit], str(page + 1) if items else None, {"id": f"forum:board:{host}:{source.rstrip('/').split('/')[-1]}"})

    def fetch(self, item, *, max_pages=MAX_PAGES, **_):
        host = host_of(item)
        tid = thread_id_of(item)
        final, html = _browser.load_html("forum", item, wait="domcontentloaded")
        engine = detect_engine(html, item)
        if engine == "discourse":
            d = _browser.load_json("forum", f"https://{host}/t/{tid}.json")
            stream = d["post_stream"].get("stream", [])
            have = {p["id"] for p in d["post_stream"]["posts"]}
            missing = [i for i in stream if i not in have]
            extra: list[dict[str, Any]] = []
            for i in range(0, len(missing), 20):
                q = "&".join(f"post_ids[]={x}" for x in missing[i:i + 20])
                extra += _browser.load_json("forum", f"https://{host}/t/{tid}/posts.json?{q}")["post_stream"]["posts"]
            rec = parse_discourse_topic(d, host, extra)
            rec["raw_path"] = save_raw("forum", f"{host}_{tid}", d)
            return rec
        if engine == "xenforo":
            first = parse_xenforo_page(html, 1)
            pages, warnings = [first], []
            base = re.sub(r"/page-\d+.*$", "", final.split("#")[0].rstrip("/"))
            last = min(first["last_page"], max_pages)
            if first["last_page"] > max_pages:
                warnings.append(f"page cap {max_pages} reached; {first['last_page'] - max_pages} pages not fetched")
            for n in range(2, last + 1):
                _f, h2 = _browser.load_html("forum", f"{base}/page-{n}")
                pages.append(parse_xenforo_page(h2, n))
            rec = xenforo_record(host, tid, first["title"], pages, base, warnings)
            rec["raw_path"] = save_raw("forum", f"{host}_{tid}", html, "html")
            return rec
        rec = web.page_record(item, html, save_raw("forum", f"{host}_{tid}", html, "html"), final)
        rec.update({"id": content_id(host, tid), "platform": "forum", "content_type": "thread"})
        rec["extra"]["engine"] = engine
        rec["extra"]["warning"] = "generic engine: only the first page was read; paginate with the agent"
        return rec
