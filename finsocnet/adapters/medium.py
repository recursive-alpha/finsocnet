"""Medium: RSS for listings, agent browser + trafilatura for articles (docs/spec/05 §2.6). Session optional."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote_plus, urlsplit

import feedparser

from finsocnet.adapters import _browser, rss, web
from finsocnet.core import http
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, profile_record, save_raw
from finsocnet.core.segments import paragraph_segments, refs

POST_RE = re.compile(r"-([0-9a-f]{10,12})(?:\?|$|/)")


def post_hex(url: str) -> str:
    m = POST_RE.search(url if url.endswith("/") else url + "/")
    if not m:
        raise CliError("USAGE", f"cannot read a Medium post id from {url!r}", "article URLs end with a 12-hex id")
    return m.group(1)


def feed_url(source: str) -> tuple[str, str]:
    s = source.strip()
    if s.startswith("http"):
        u = urlsplit(s)
        path = u.path.strip("/")
        if path.startswith("tag/"):
            return f"https://medium.com/feed/{path}", f"medium:tag:{path[4:]}"
        if path.startswith("@"):
            h = path.split("/")[0]
            return f"https://medium.com/feed/{h}", f"medium:user:{h.lstrip('@').lower()}"
        pub = path.split("/")[0]
        return f"https://medium.com/feed/{pub}", f"medium:publication:{pub}"
    if s.startswith("@"):
        return f"https://medium.com/feed/{s}", f"medium:user:{s.lstrip('@').lower()}"
    if s.startswith("tag:"):
        return f"https://medium.com/feed/tag/{s[4:]}", f"medium:tag:{s[4:]}"
    return f"https://medium.com/feed/tag/{s}", f"medium:tag:{s}"


def feed_refs(xml: str) -> list[dict[str, Any]]:
    out = []
    for e in feedparser.parse(xml).entries:
        link = e.get("link", "").split("?")[0]
        try:
            hexid = post_hex(link)
        except CliError:
            continue
        out.append(item_ref(link, f"medium:{hexid}", "article", e.get("title"), e.get("author"), rss.entry_date(e), re.sub(r"<[^>]+>", " ", rss.entry_html(e)),
                            {"categories": [t["term"] for t in e.get("tags", [])]}))
    return out


def article_record(url: str, html: str, raw_path: str | None, final_url: str | None = None) -> dict[str, Any]:
    md, meta = web.extract_markdown(html, final_url or url)
    segs = paragraph_segments(md, min_len=40) or [{"seq": 0, "kind": "paragraph", "locator": {"para": 0}, "text": meta.get("title") or url}]
    for s in segs:
        if re.match(r"^(```|    )", s["text"]):
            s["kind"] = "code"
    member_only = bool(re.search(r"Member-only story|Get unlimited access|Continue reading with a free account|become a member", html, re.I))
    claps = (re.search(r'"clapCount":\s*(\d+)', html) or [None, None])[1]
    minutes = (re.search(r'"readingTime":\s*([\d.]+)', html) or [None, None])[1]
    r = refs(md)
    handle = (re.search(r'medium\.com/(@[\w.]+)', final_url or url) or [None, meta.get("author")])[1]
    return content_record(f"medium:{post_hex(url)}", "medium", "article", segs, url=url.split("?")[0], title=meta.get("title"), description=meta.get("description"), author={"handle": handle, "display_name": meta.get("author")},
                          published_at=meta.get("date"), language="en", metrics={"claps": int(claps) if claps else None}, links=r["links"], mentions=r["mentions"], raw_path=raw_path, fetch_method="browser+trafilatura",
                          extra={"member_only": member_only, "claps": int(claps) if claps else None, "reading_time_min": float(minutes) if minutes else None, "truncated": member_only and len(md) < 2500},
                          source={"id": f"medium:user:{(handle or 'unknown').lstrip('@').lower()}", "kind": "user", "title": meta.get("author")})


class Medium(PlatformAdapter):
    platform = "medium"
    capabilities = frozenset({"search", "profile", "list", "fetch"})
    opts = {"list": [(("--full",), {"action": "store_true", "help": "scroll the profile page for older posts (RSS only has recent ones)"})]}

    def search(self, query, *, limit=20, since=None, **_):
        _final, html = _browser.load_html("medium", f"https://medium.com/search?q={quote_plus(query)}", wait="networkidle", scrolls=2)
        from lxml import html as lhtml
        root = lhtml.fromstring(html)
        out, seen = [], set()
        for a in root.xpath("//article//a[@href]|//div[@role='link']//a[@href]"):
            href = a.get("href", "").split("?")[0]
            if not href.startswith("http"):
                href = "https://medium.com" + href
            try:
                hexid = post_hex(href)
            except CliError:
                continue
            if hexid in seen:
                continue
            seen.add(hexid)
            out.append(item_ref(href, f"medium:{hexid}", "article", " ".join(a.text_content().split())[:160] or None, None, None, None))
        return out[:limit]

    def profile(self, target, **_):
        h = target.rstrip("/").split("/")[-1]
        h = h if h.startswith("@") else "@" + h.lstrip("@")
        _f, html = _browser.load_html("medium", f"https://medium.com/{h}/about", wait="networkidle")
        md, meta = web.extract_markdown(html)
        return profile_record("medium", f"medium:user:{h.lstrip('@').lower()}", h, display_name=meta.get("title"), bio=(meta.get("description") or md[:300]) or None, profile_url=f"https://medium.com/{h}",
                              links=refs(md)["links"][:20])

    def list(self, source, *, limit=20, cursor=None, since=None, full=False, **_):
        url, src = feed_url(source)
        xml = http.get_text(url, platform="medium")
        save_raw("medium", src.replace(":", "_"), xml, "xml")
        items = feed_refs(xml)
        if cursor:
            ids_ = [i["id"] for i in items]
            items = items[:ids_.index(cursor)] if cursor in ids_ else items
        items = [i for i in items if not since or (i["published_at"] or "")[:10] >= since]
        return list_result(items[:limit], items[0]["id"] if items else cursor, {"id": src})

    def fetch(self, item, **_):
        url = item if item.startswith("http") else f"https://medium.com/p/{item.replace('medium:', '')}"
        final, html = _browser.load_html("medium", url, wait="networkidle")
        return article_record(final, html, save_raw("medium", post_hex(final), html, "html"), final)
