"""Browser-based social platforms with shared helpers: Facebook, Instagram, Threads, LinkedIn, Seeking Alpha, TikTok.

All selectors/endpoints here follow the documented structure of each site and are NOT verified live (they need accounts and the
sites change often); parsing is isolated in `parse_*` functions covered by hand-written fixtures. `references/platform_notes.md`
of each skill lists what to verify."""

from __future__ import annotations

import json
import re
from typing import Any, Iterator
from urllib.parse import urljoin, urlsplit

from lxml import html as lhtml

from finsocnet.adapters import _browser, web
from finsocnet.adapters.x import iter_nodes
from finsocnet.core import config, transcribe
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, profile_record, save_raw
from finsocnet.core.segments import refs, transcript_windows


def text_of(el: Any) -> str:
    for br in el.xpath(".//br"):
        br.tail = "\n" + (br.tail or "")
    return "\n".join(" ".join(l.split()) for l in "".join(el.itertext()).splitlines() if l.strip()).strip()


def json_script_nodes(html: str) -> Iterator[dict[str, Any]]:
    for s in lhtml.fromstring(html).xpath("//script[@type='application/json' or @type='application/ld+json']/text()"):
        try:
            yield from iter_nodes(json.loads(s))
        except ValueError:
            continue


# --- Facebook -------------------------------------------------------------------------------------------

def parse_facebook(bodies: list[Any]) -> dict[str, Any]:
    """Walk GraphQL bodies for a story (`message.text`, `creation_time`, `actors`) and comment nodes (`body.text`, `author.name`)."""
    post, comments, seen = None, [], set()
    for b in bodies:
        for n in iter_nodes(b):
            msg = (n.get("message") or {}).get("text") if isinstance(n.get("message"), dict) else None
            if msg and post is None and (n.get("__typename") == "Story" or n.get("creation_time") or n.get("post_id")):
                actor = (n.get("actors") or [{}])[0] if isinstance(n.get("actors"), list) else (n.get("actor") or {})
                post = {"id": str(n.get("post_id") or n.get("id")), "text": msg, "time": n.get("creation_time"), "author": actor.get("name"), "author_id": actor.get("id")}
            body = (n.get("body") or {}).get("text") if isinstance(n.get("body"), dict) else None
            if body and n.get("__typename") == "Comment" and n.get("id") not in seen:
                seen.add(n.get("id"))
                comments.append({"id": str(n["id"]), "text": body, "author": (n.get("author") or {}).get("name"), "author_id": (n.get("author") or {}).get("id"), "parent": (n.get("parent_feedback") or {}).get("id")})
    if post is None:
        raise CliError("NOT_FOUND", "no post found in the captured Facebook responses", "the post may be private or the layout changed")
    return {"post": post, "comments": comments}


def facebook_record(owner: str, d: dict[str, Any], url: str, max_comments: int, raw_path: str | None) -> dict[str, Any]:
    p = d["post"]
    segs = [{"seq": 0, "kind": "post", "locator": {"comment_id": p["id"]}, "author": {"handle": p["author"], "platform_user_id": p["author_id"]}, "text": p["text"]}]
    for c in d["comments"][:max_comments]:
        segs.append({"seq": len(segs), "kind": "comment", "locator": {"comment_id": c["id"], "parent_id": c["parent"]}, "author": {"handle": c["author"], "platform_user_id": c["author_id"]}, "text": c["text"]})
    r = refs("\n".join(s["text"] for s in segs))
    return content_record(f"facebook:{owner}:{p['id']}", "facebook", "post", segs, url=url, title=p["text"][:100], author={"handle": p["author"], "platform_user_id": p["author_id"]}, links=r["links"], mentions=r["mentions"],
                          raw_path=raw_path, fetch_method="graphql_capture", extra={"private_source": True, "comments_total": len(d["comments"]), "truncated": len(d["comments"]) > max_comments},
                          source={"id": f"facebook:group:{owner}", "kind": "group", "requires_session": True})


class Facebook(PlatformAdapter):
    platform = "facebook"
    requires_session = True
    capabilities = frozenset({"search", "profile", "list", "fetch"})
    opts = {"fetch": [(("--max-comments",), {"type": int, "default": 200})]}

    def search(self, query, *, limit=20, since=None, **_):
        from urllib.parse import quote_plus
        _f, html = _browser.load_html("facebook", f"https://www.facebook.com/search/groups/?q={quote_plus(query)}", wait="networkidle", scrolls=2)
        out, seen = [], set()
        for a in lhtml.fromstring(html).xpath("//a[contains(@href,'/groups/')]"):
            m = re.search(r"/groups/([\w.-]+)", a.get("href", ""))
            if m and m.group(1) not in seen and a.text_content().strip():
                seen.add(m.group(1))
                out.append(item_ref(f"https://www.facebook.com/groups/{m.group(1)}/", f"facebook:group:{m.group(1)}", "group", " ".join(a.text_content().split())[:120], None, None, None))
        return out[:limit]

    def profile(self, target, **_):
        gid = re.search(r"/groups/([\w.-]+)|/([\w.-]+)/?$", target)
        g = (gid.group(1) or gid.group(2)) if gid else target
        _f, html = _browser.load_html("facebook", f"https://www.facebook.com/groups/{g}/about", wait="networkidle")
        md, meta = web.extract_markdown(html)
        return profile_record("facebook", f"facebook:group:{g}", g, display_name=meta.get("title"), avatar_url=meta.get("image"), bio=md[:500] or None, profile_url=f"https://www.facebook.com/groups/{g}/")

    def list(self, source, *, limit=20, cursor=None, since=None, **_):
        g = re.search(r"/groups/([\w.-]+)", source).group(1) if "/groups/" in source else source  # type: ignore[union-attr]
        _f, html = _browser.load_html("facebook", f"https://www.facebook.com/groups/{g}/", wait="networkidle", scrolls=max(2, limit // 4))
        out, seen = [], set()
        for a in lhtml.fromstring(html).xpath("//a[contains(@href,'/posts/') or contains(@href,'/permalink/')]"):
            m = re.search(r"/(?:posts|permalink)/(\d+)", a.get("href", ""))
            if m and m.group(1) not in seen:
                seen.add(m.group(1))
                out.append(item_ref(urljoin("https://www.facebook.com", a.get("href").split("?")[0]), f"facebook:{g}:{m.group(1)}", "post", None, None, None, None))
        return list_result(out[:limit], None, {"id": f"facebook:group:{g}"})

    def fetch(self, item, *, max_comments=200, **_):
        m = re.search(r"/groups/([\w.-]+)/(?:posts|permalink)/(\d+)", item) or re.search(r"facebook:([\w.-]+):(\d+)", item)
        if not m:
            raise CliError("USAGE", "give https://www.facebook.com/groups/<id>/posts/<post_id>/")
        url = item if item.startswith("http") else f"https://www.facebook.com/groups/{m.group(1)}/posts/{m.group(2)}/"
        _u, bodies = _browser.capture("facebook", url, r"/api/graphql/", scrolls=3)
        return facebook_record(m.group(1), parse_facebook(bodies), url, max_comments, save_raw("facebook", f"{m.group(1)}_{m.group(2)}", bodies))


# --- Threads / Instagram (Meta GraphQL-ish payloads) ---------------------------------------------------

def parse_meta_posts(bodies: list[Any], key_text: str = "caption") -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for b in bodies:
        for n in iter_nodes(b):
            cap = n.get(key_text)
            text = cap.get("text") if isinstance(cap, dict) else (cap if isinstance(cap, str) else None)
            code = n.get("code") or n.get("shortcode")
            if text and code and (n.get("pk") or n.get("id")) and code not in out:
                u = n.get("user") or n.get("owner") or {}
                out[code] = {"code": code, "pk": str(n.get("pk") or n.get("id")), "text": text, "user": u.get("username"), "user_id": str(u.get("pk") or u.get("id") or "") or None,
                             "taken_at": n.get("taken_at"), "likes": n.get("like_count"), "reply_count": n.get("text_post_app_info", {}).get("direct_reply_count") if isinstance(n.get("text_post_app_info"), dict) else None,
                             "video": (n.get("video_versions") or [{}])[0].get("url") if n.get("video_versions") else None, "media_type": n.get("media_type")}
    return out


def meta_record(platform: str, content_id: str, p: dict[str, Any], comments: list[dict[str, Any]], url: str, ctype: str, raw_path: str | None, transcript: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    from datetime import datetime, timezone
    segs = [{"seq": 0, "kind": "post", "locator": {"comment_id": p["pk"]}, "author": {"handle": p["user"], "platform_user_id": p["user_id"]}, "text": p["text"]}]
    segs += [{"seq": len(segs) + i, "kind": "comment", "locator": {"comment_id": c["id"]}, "author": {"handle": c.get("user")}, "text": c["text"]} for i, c in enumerate(comments)]
    if transcript:
        for s in transcript_windows(transcript):
            s["seq"] = len(segs)
            segs.append(s)
    r = refs("\n".join(s["text"] for s in segs))
    published = datetime.fromtimestamp(p["taken_at"], timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if p.get("taken_at") else None
    return content_record(content_id, platform, ctype, segs, url=url, title=p["text"][:100], author={"handle": p["user"], "platform_user_id": p["user_id"]}, published_at=published,
                          metrics={"likes": p.get("likes"), "replies": p.get("reply_count")}, links=r["links"], mentions=r["mentions"], media=[{"kind": "video", "url": p["video"]}] if p.get("video") else [],
                          raw_path=raw_path, fetch_method="graphql_capture", extra={"needs_audio": bool(p.get("video")) and not transcript},
                          source={"id": f"{platform}:user:{(p['user'] or 'unknown').lower()}", "kind": "user", "title": p["user"]})


class Threads(PlatformAdapter):
    platform = "threads"
    capabilities = frozenset({"profile", "list", "fetch"})

    def profile(self, target, **_):
        h = target.rstrip("/").split("/")[-1].lstrip("@")
        _f, html = _browser.load_html("threads", f"https://www.threads.net/@{h}", wait="networkidle")
        md, meta = web.extract_markdown(html)
        return profile_record("threads", f"threads:user:{h.lower()}", f"@{h}", display_name=meta.get("title"), avatar_url=meta.get("image"), bio=meta.get("description"), profile_url=f"https://www.threads.net/@{h}")

    def list(self, source, *, limit=20, cursor=None, since=None, **_):
        h = source.rstrip("/").split("/")[-1].lstrip("@")
        _u, bodies = _browser.capture("threads", f"https://www.threads.net/@{h}", r"/(api/graphql|graphql/query)", scrolls=max(2, limit // 5))
        posts = [p for p in parse_meta_posts(bodies, "caption").values() if (p["user"] or "").lower() == h.lower()]
        return list_result([item_ref(f"https://www.threads.net/@{h}/post/{p['code']}", f"threads:{p['pk']}", "post", None, f"@{h}", None, p["text"], {"likes": p["likes"]}) for p in posts][:limit], None, {"id": f"threads:user:{h.lower()}"})

    def fetch(self, item, **_):
        code = re.search(r"/post/([\w-]+)", item).group(1) if "/post/" in item else item  # type: ignore[union-attr]
        url = item if item.startswith("http") else f"https://www.threads.net/t/{code}"
        _u, bodies = _browser.capture("threads", url, r"/(api/graphql|graphql/query)", scrolls=1)
        posts = parse_meta_posts(bodies, "caption")
        p = posts.get(code) or next(iter(posts.values()), None)
        if not p:
            raise CliError("NOT_FOUND", f"threads post {code} not found in captured responses")
        replies = [{"id": q["pk"], "user": q["user"], "text": q["text"]} for c, q in posts.items() if c != p["code"]]
        return meta_record("threads", f"threads:{p['pk']}", p, replies, url, "post", save_raw("threads", code, bodies))


class Instagram(PlatformAdapter):
    platform = "instagram"
    requires_session = True
    capabilities = frozenset({"profile", "list", "fetch"})
    opts = {"fetch": [(("--transcribe-video",), {"action": "store_true"})]}

    def profile(self, target, **_):
        h = target.rstrip("/").split("/")[-1].lstrip("@")
        _f, html = _browser.load_html("instagram", f"https://www.instagram.com/{h}/", wait="networkidle")
        md, meta = web.extract_markdown(html)
        return profile_record("instagram", f"instagram:user:{h.lower()}", f"@{h}", display_name=meta.get("title"), avatar_url=meta.get("image"), bio=meta.get("description"), profile_url=f"https://www.instagram.com/{h}/")

    def list(self, source, *, limit=12, cursor=None, since=None, **_):
        h = source.rstrip("/").split("/")[-1].lstrip("@")
        _f, html = _browser.load_html("instagram", f"https://www.instagram.com/{h}/", wait="networkidle", scrolls=max(1, limit // 12))
        out, seen = [], set()
        for a in lhtml.fromstring(html).xpath("//a[contains(@href,'/p/') or contains(@href,'/reel/')]"):
            m = re.search(r"/(p|reel)/([\w-]+)", a.get("href", ""))
            if m and m.group(2) not in seen:
                seen.add(m.group(2))
                out.append(item_ref(f"https://www.instagram.com/{m.group(1)}/{m.group(2)}/", f"instagram:{m.group(2)}", "reel" if m.group(1) == "reel" else "post", None, f"@{h}", None, None))
        return list_result(out[:limit], None, {"id": f"instagram:user:{h.lower()}"})

    def fetch(self, item, *, transcribe_video=False, **_):
        m = re.search(r"/(?:p|reel)/([\w-]+)|instagram:([\w-]+)", item)
        code = next(g for g in m.groups() if g) if m else item
        url = item if item.startswith("http") else f"https://www.instagram.com/p/{code}/"
        _u, bodies = _browser.capture("instagram", url, r"/(api/graphql|graphql/query|api/v1/)", scrolls=1)
        posts = parse_meta_posts(bodies, "caption")
        p = posts.get(code) or next(iter(posts.values()), None)
        if not p:
            raise CliError("NOT_FOUND", f"instagram post {code} not found in captured responses")
        transcript = None
        if transcribe_video and p.get("video"):
            transcript = transcribe.as_entries(transcribe.transcribe(url))
        comments = [{"id": q["pk"], "user": q["user"], "text": q["text"]} for c, q in posts.items() if c != p["code"]]
        return meta_record("instagram", f"instagram:{p['code']}", p, comments, url, "short" if p.get("video") else "post", save_raw("instagram", code, bodies), transcript)


# --- LinkedIn -------------------------------------------------------------------------------------------

def parse_linkedin_posts(html: str) -> list[dict[str, Any]]:
    root = lhtml.fromstring(html)
    posts = []
    for el in root.xpath("//*[@data-urn and contains(@data-urn,'urn:li:activity:')]"):
        urn = el.get("data-urn")
        txt = el.xpath(".//*[contains(@class,'update-components-text') or contains(@class,'feed-shared-text')]")
        author = el.xpath(".//*[contains(@class,'update-components-actor__name')]//span[@aria-hidden='true']/text()|.//*[contains(@class,'update-components-actor__title')]//span[1]/text()")
        link = el.xpath(".//a[contains(@class,'update-components-actor__meta-link')]/@href")
        posts.append({"urn": urn, "text": text_of(txt[0]) if txt else "", "author": " ".join(author[0].split()) if author else None, "profile": link[0].split("?")[0] if link else None})
    return [p for p in posts if p["text"]]


def linkedin_record(p: dict[str, Any], raw_path: str | None) -> dict[str, Any]:
    r = refs(p["text"])
    handle = (re.search(r"/in/([\w%-]+)", p["profile"] or "") or [None, p["author"]])[1]
    return content_record(f"linkedin:{p['urn']}", "linkedin", "post", [{"seq": 0, "kind": "post", "locator": {"comment_id": p["urn"]}, "author": {"handle": handle, "display_name": p["author"]}, "text": p["text"]}],
                          url=f"https://www.linkedin.com/feed/update/{p['urn']}/", title=p["text"][:100], author={"handle": handle, "display_name": p["author"], "profile_url": p["profile"]}, links=r["links"], mentions=r["mentions"],
                          raw_path=raw_path, fetch_method="browser_dom", source={"id": f"linkedin:user:{(handle or 'unknown').lower()}", "kind": "user", "title": p["author"], "requires_session": True})


class LinkedIn(PlatformAdapter):
    platform = "linkedin"
    requires_session = True
    capabilities = frozenset({"profile", "list", "fetch"})

    def profile(self, target, **_):
        h = target.rstrip("/").split("/")[-1]
        _f, html = _browser.load_html("linkedin", f"https://www.linkedin.com/in/{h}/", wait="networkidle")
        md, meta = web.extract_markdown(html)
        return profile_record("linkedin", f"linkedin:user:{h.lower()}", h, display_name=meta.get("title"), avatar_url=meta.get("image"), bio=meta.get("description") or md[:300], profile_url=f"https://www.linkedin.com/in/{h}/")

    def list(self, source, *, limit=10, cursor=None, since=None, **_):
        h = source.rstrip("/").split("/")[-1]
        _f, html = _browser.load_html("linkedin", f"https://www.linkedin.com/in/{h}/recent-activity/all/", wait="networkidle", scrolls=max(1, limit // 5))
        return list_result([item_ref(f"https://www.linkedin.com/feed/update/{p['urn']}/", f"linkedin:{p['urn']}", "post", None, p["author"], None, p["text"]) for p in parse_linkedin_posts(html)][:limit], None, {"id": f"linkedin:user:{h.lower()}"})

    def fetch(self, item, **_):
        urn = re.search(r"urn:li:activity:\d+", item)
        if not urn:
            raise CliError("USAGE", "give https://www.linkedin.com/feed/update/urn:li:activity:<id>/")
        _f, html = _browser.load_html("linkedin", f"https://www.linkedin.com/feed/update/{urn.group(0)}/", wait="networkidle")
        posts = [p for p in parse_linkedin_posts(html) if p["urn"] == urn.group(0)] or parse_linkedin_posts(html)[:1]
        if not posts:
            raise CliError("NOT_FOUND", "no post text found on the page")
        return linkedin_record(posts[0], save_raw("linkedin", urn.group(0).replace(":", "_"), html, "html"))


# --- Seeking Alpha --------------------------------------------------------------------------------------

def sa_article_id(url: str) -> str:
    m = re.search(r"/(?:article|news)/(\d+)", url) or re.search(r"seekingalpha:(\d+)", url)
    if not m:
        raise CliError("USAGE", f"cannot read an article id from {url!r}")
    return m.group(1)


def parse_seekingalpha(html: str, url: str) -> dict[str, Any]:
    md, meta = web.extract_markdown(html, url)
    root = lhtml.fromstring(html)
    comments = []
    for c in root.xpath("//*[@data-test-id='comment' or contains(@class,'comment-body')]"):
        comments.append({"id": c.get("id") or str(len(comments)), "author": (c.xpath(".//*[@data-test-id='comment-author']//text()") or [None])[0], "text": text_of(c)})
    author = (root.xpath("//a[contains(@href,'/author/')]/text()") or [meta.get("author")])[0]
    slug = (root.xpath("//a[contains(@href,'/author/')]/@href") or [""])[0].split("/author/")[-1].split("/")[0].split("#")[0] if root.xpath("//a[contains(@href,'/author/')]/@href") else None
    return {"md": md, "meta": meta, "comments": [c for c in comments if c["text"]], "author": author, "author_slug": slug}


def sa_record(url: str, d: dict[str, Any], raw_path: str | None) -> dict[str, Any]:
    from finsocnet.core.segments import paragraph_segments
    segs = paragraph_segments(d["md"], min_len=40) or [{"seq": 0, "kind": "paragraph", "locator": {"para": 0}, "text": d["meta"].get("title") or url}]
    segs += [{"seq": len(segs) + i, "kind": "comment", "locator": {"comment_id": c["id"]}, "author": {"handle": c["author"]}, "text": c["text"]} for i, c in enumerate(d["comments"])]
    r = refs(d["md"])
    return content_record(f"seekingalpha:{sa_article_id(url)}", "seekingalpha", "article", segs, url=url, title=d["meta"].get("title"), author={"handle": d["author_slug"] or d["author"], "display_name": d["author"]},
                          published_at=d["meta"].get("date"), links=r["links"], mentions=r["mentions"], raw_path=raw_path, fetch_method="browser+trafilatura", extra={"premium_truncated": len(d["md"]) < 1500},
                          source={"id": f"seekingalpha:author:{(d['author_slug'] or d['author'] or 'unknown').lower()}", "kind": "user", "title": d["author"]})


class SeekingAlpha(PlatformAdapter):
    platform = "seekingalpha"
    capabilities = frozenset({"list", "fetch", "profile"})

    def profile(self, target, **_):
        s = target.rstrip("/").split("/")[-1]
        _f, html = _browser.load_html("seekingalpha", f"https://seekingalpha.com/author/{s}", wait="networkidle")
        md, meta = web.extract_markdown(html)
        return profile_record("seekingalpha", f"seekingalpha:author:{s.lower()}", s, display_name=meta.get("title"), avatar_url=meta.get("image"), bio=meta.get("description"), profile_url=f"https://seekingalpha.com/author/{s}")

    def list(self, source, *, limit=20, cursor=None, since=None, **_):
        s = source.rstrip("/").split("/")[-1]
        _f, html = _browser.load_html("seekingalpha", f"https://seekingalpha.com/author/{s}/articles", wait="networkidle", scrolls=1)
        out, seen = [], set()
        for a in lhtml.fromstring(html).xpath("//a[contains(@href,'/article/')]"):
            m = re.search(r"/article/(\d+)", a.get("href", ""))
            if m and m.group(1) not in seen and a.text_content().strip():
                seen.add(m.group(1))
                out.append(item_ref(urljoin("https://seekingalpha.com", a.get("href").split("?")[0]), f"seekingalpha:{m.group(1)}", "article", " ".join(a.text_content().split())[:160], s, None, None))
        return list_result(out[:limit], None, {"id": f"seekingalpha:author:{s.lower()}"})

    def fetch(self, item, **_):
        aid = sa_article_id(item)
        url = item if item.startswith("http") else f"https://seekingalpha.com/article/{aid}"
        final, html = _browser.load_html("seekingalpha", url, wait="networkidle", scrolls=2)
        return sa_record(final, parse_seekingalpha(html, final), save_raw("seekingalpha", aid, html, "html"))


# --- TikTok ---------------------------------------------------------------------------------------------

def tiktok_record(info: dict[str, Any], entries: list[dict[str, Any]] | None, source: str | None, raw_path: str | None) -> dict[str, Any]:
    desc = info.get("description") or info.get("title") or ""
    segs = [{"seq": 0, "kind": "caption", "locator": {"para": 0}, "author": {"handle": info.get("uploader")}, "text": desc or "(no caption)"}]
    if entries:
        for s in transcript_windows(entries):
            s["seq"] = len(segs)
            segs.append(s)
    r = refs(desc)
    ud = info.get("upload_date")
    return content_record(f"tiktok:{info['id']}", "tiktok", "short", segs, url=info.get("webpage_url"), title=(info.get("title") or desc)[:100], author={"handle": info.get("uploader_id") or info.get("uploader"), "display_name": info.get("uploader")},
                          published_at=f"{ud[:4]}-{ud[4:6]}-{ud[6:8]}" if ud and len(ud) == 8 else None, duration_sec=int(info["duration"]) if info.get("duration") else None,
                          metrics={"views": info.get("view_count"), "likes": info.get("like_count"), "comments": info.get("comment_count")}, links=r["links"], mentions=r["mentions"], raw_path=raw_path,
                          fetch_method="yt-dlp", extra={"caption_source": source, "has_speech_transcript": bool(entries)},
                          source={"id": f"tiktok:user:{(info.get('uploader_id') or info.get('uploader') or 'unknown').lower()}", "kind": "user", "title": info.get("uploader")})


class TikTok(PlatformAdapter):
    platform = "tiktok"
    capabilities = frozenset({"profile", "list", "fetch"})
    opts = {"fetch": [(("--no-whisper",), {"action": "store_true"})]}

    def _ydl(self, **extra: Any) -> Any:
        import yt_dlp
        opts: dict[str, Any] = {"quiet": True, "no_warnings": True, "skip_download": True, **extra}
        cookies = config.data_dir() / "sessions" / "cookies.txt"
        if cookies.exists():
            opts["cookiefile"] = str(cookies)
        return yt_dlp.YoutubeDL(opts)

    def profile(self, target, **_):
        h = target.rstrip("/").split("/")[-1].lstrip("@")
        with self._ydl(extract_flat=True, playlistend=1) as y:
            r = y.extract_info(f"https://www.tiktok.com/@{h}", download=False)
        return profile_record("tiktok", f"tiktok:user:{h.lower()}", f"@{h}", display_name=r.get("uploader") or r.get("title"), bio=r.get("description"), profile_url=f"https://www.tiktok.com/@{h}")

    def list(self, source, *, limit=20, cursor=None, since=None, **_):
        h = source.rstrip("/").split("/")[-1].lstrip("@")
        with self._ydl(extract_flat=True, playlistend=limit) as y:
            r = y.extract_info(f"https://www.tiktok.com/@{h}", download=False)
        items = [item_ref(e.get("url") or f"https://www.tiktok.com/@{h}/video/{e['id']}", f"tiktok:{e['id']}", "short", e.get("title"), f"@{h}", None, e.get("description"), {"views": e.get("view_count")}) for e in r.get("entries", []) if e.get("id")]
        return list_result(items[:limit], None, {"id": f"tiktok:user:{h.lower()}"})

    def fetch(self, item, *, no_whisper=False, **_):
        vid = re.search(r"/video/(\d+)|tiktok:(\d+)", item)
        url = item if item.startswith("http") else f"https://www.tiktok.com/@_/video/{next(g for g in vid.groups() if g)}" if vid else item
        with self._ydl() as y:
            info = y.extract_info(url, download=False)
        raw = save_raw("tiktok", info["id"], info)
        entries, source = None, "description"
        if not no_whisper:
            res = transcribe.transcribe(url, content_id=f"tiktok:{info['id']}")
            entries, source = transcribe.as_entries(res), "whisper"
        return tiktok_record(info, entries, source, raw)
