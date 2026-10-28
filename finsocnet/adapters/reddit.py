"""Reddit JSON endpoints loaded through the agent browser, so cookies and proxy apply (specs/05 §2.5)."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus

import feedparser

from finsocnet.adapters import _browser
from finsocnet.core import http
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, profile_record, save_raw
from finsocnet.core.segments import refs

BASE = "https://www.reddit.com"
MAX_COMMENTS = 500


def iso(ts: float | None) -> str | None:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else None


def post_id(ref: str) -> str:
    m = re.search(r"comments/([a-z0-9]{5,8})|reddit:([a-z0-9]{5,8})|^([a-z0-9]{5,8})$|redd\.it/([a-z0-9]{5,8})", ref.strip())
    if not m:
        raise CliError("USAGE", f"cannot read a Reddit post id from {ref!r}")
    return next(g for g in m.groups() if g)


def listing_refs(d: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for c in d.get("data", {}).get("children", []):
        p = c["data"]
        if c["kind"] == "t3":
            out.append(item_ref(f"{BASE}{p['permalink']}", f"reddit:{p['id']}", "thread", html.unescape(p.get("title", "")), f"u/{p.get('author')}", iso(p.get("created_utc")), p.get("selftext") or p.get("url"),
                                {"score": p.get("score"), "comments": p.get("num_comments"), "subreddit": p.get("subreddit")}))
        elif c["kind"] == "t1":
            out.append(item_ref(f"{BASE}{p['permalink']}", f"reddit:{p['link_id'].removeprefix('t3_')}", "comment", None, f"u/{p.get('author')}", iso(p.get("created_utc")), p.get("body"), {"score": p.get("score")}))
    return out


def flatten_comments(listing: dict[str, Any], link: str) -> tuple[list[dict[str, Any]], list[str]]:
    """Depth-first comment dicts (with `depth`) and the ids of `more` stubs that still need /api/morechildren."""
    comments: list[dict[str, Any]] = []
    stubs: list[str] = []

    def walk(children: list[dict[str, Any]], parent: str) -> None:
        for c in children:
            if c["kind"] == "more":
                stubs.extend(c["data"].get("children", []))
            elif c["kind"] == "t1":
                comments.append(c["data"])
                rep = c["data"].get("replies")
                if isinstance(rep, dict):
                    walk(rep["data"]["children"], c["data"]["name"])

    walk(listing["data"]["children"], link)
    return comments, stubs


def segment_for(c: dict[str, Any], post_name: str) -> dict[str, Any]:
    deleted = c.get("body") in ("[deleted]", "[removed]") or c.get("author") in ("[deleted]", None)
    return {"seq": 0, "kind": "comment", "locator": {"comment_id": f"t1_{c['id']}", "parent_id": c.get("parent_id") or post_name, "score": c.get("score"), "depth": c.get("depth", 0)},
            "author": {"handle": None if c.get("author") in ("[deleted]", None) else f"u/{c['author']}"}, "text": c.get("body") or "[deleted]",
            **({"quotable": False} if deleted else {})}


def build_record(thread: list[dict[str, Any]], extra_comments: list[dict[str, Any]] | None, max_comments: int, warnings: list[str], raw_path: str | None) -> dict[str, Any]:
    post = thread[0]["data"]["children"][0]["data"]
    comments, stubs = flatten_comments(thread[1], post["name"])
    comments += extra_comments or []
    if len(comments) > max_comments:
        warnings.append(f"comment cap {max_comments} reached; {len(comments) - max_comments} comments not stored")
        comments = sorted(comments, key=lambda c: -(c.get("score") or 0))[:max_comments]
        keep = {c["name"] for c in comments}
        comments = [c for c in comments if c.get("parent_id") in keep or c.get("parent_id") == post["name"] or True]
    elif stubs and not extra_comments:
        warnings.append(f"{len(stubs)} 'more comments' stubs were not expanded")
    title = html.unescape(post.get("title", ""))
    body = html.unescape(post.get("selftext") or "")
    first = f"{title}\n\n{body}".strip() if body else f"{title}\n\n{post.get('url', '')}".strip()
    segs: list[dict[str, Any]] = [{"seq": 0, "kind": "post", "locator": {"comment_id": post["name"]}, "author": {"handle": f"u/{post.get('author')}"}, "text": first}]
    for c in comments:
        s = segment_for(c, post["name"])
        s.pop("quotable", None)
        s["text"] = html.unescape(s["text"])
        s["seq"] = len(segs)
        segs.append(s)
    r = refs("\n".join(s["text"] for s in segs))
    sub = post.get("subreddit", "").lower()
    return content_record(f"reddit:{post['id']}", "reddit", "thread", segs, url=f"{BASE}{post['permalink']}", title=title, author={"handle": f"u/{post.get('author')}", "platform_user_id": post.get("author_fullname")},
                          published_at=iso(post.get("created_utc")), language="en", metrics={"score": post.get("score"), "comments": post.get("num_comments")}, links=r["links"], mentions=r["mentions"],
                          raw_path=raw_path, fetch_method="json_endpoint", extra={"subreddit": post.get("subreddit"), "flair": post.get("link_flair_text"), "over_18": post.get("over_18")},
                          source={"id": f"reddit:subreddit:{sub}", "kind": "subreddit", "title": f"r/{post.get('subreddit')}", "url": f"{BASE}/r/{post.get('subreddit')}/"})


# --- RSS fallback -----------------------------------------------------------------------------------------
# Verified 2026-10-28 from a server IP: `www.reddit.com/*.json` is answered with "blocked by network security" (also in the agent browser),
# while `*.rss` (Atom) answers 200 to a browser user agent and 429 when polled too fast. Listings and search work through RSS; a thread's
# RSS carries the post and the first comments only, so the record is flagged `extra.partial`.
BROWSER_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0", "Accept": "application/atom+xml, application/xml;q=0.9, */*;q=0.8"}


def _rss(url: str) -> Any:
    return feedparser.parse(http.request("GET", url, platform="reddit", headers=BROWSER_UA).text)


def _entry_html(e: Any) -> str:
    return (e.content[0].value if e.get("content") else e.get("summary", "")) or ""


def _entry_author(e: Any) -> str | None:
    a = (e.get("author") or "").strip()
    return a.replace("/u/", "u/") if a else None


def rss_refs(feed: Any) -> list[dict[str, Any]]:
    out = []
    for e in feed.entries:
        m = re.search(r"/comments/([a-z0-9]+)/", e.get("link", ""))
        if not m or not e.get("id", "").startswith("t3_"):
            continue
        out.append(item_ref(e.link, f"reddit:{m.group(1)}", "thread", html.unescape(e.get("title", "")), _entry_author(e), e.get("updated"), re.sub(r"<[^>]+>", " ", _entry_html(e))))
    return out


def rss_thread_record(feed: Any, pid: str, warnings: list[str]) -> dict[str, Any]:
    from finsocnet.core.segments import html_to_markdown
    entries = list(feed.entries)
    post = next((e for e in entries if e.get("id") == f"t3_{pid}"), None) or (entries[0] if entries else None)
    if post is None:
        raise CliError("NOT_FOUND", f"reddit post {pid} has no RSS entries")
    sub_m = re.search(r"/r/([^/]+)/", post.get("link", ""))
    sub = sub_m.group(1) if sub_m else "unknown"
    title = html.unescape(post.get("title", ""))
    body = html_to_markdown(_entry_html(post))
    segs = [{"seq": 0, "kind": "post", "locator": {"comment_id": f"t3_{pid}"}, "author": {"handle": _entry_author(post)}, "text": f"{title}\n\n{body}".strip()}]
    for e in entries:
        if e is post or not e.get("id", "").startswith("t1_"):
            continue
        txt = html_to_markdown(_entry_html(e))
        if txt:
            segs.append({"seq": len(segs), "kind": "comment", "locator": {"comment_id": e["id"], "parent_id": f"t3_{pid}"}, "author": {"handle": _entry_author(e)}, "text": txt})
    warnings.append("JSON endpoints are blocked from this network; the RSS feed carries the post and only the first comments (extra.partial)")
    r = refs("\n".join(s["text"] for s in segs))
    return content_record(f"reddit:{pid}", "reddit", "thread", segs, url=post.get("link"), title=title, author={"handle": _entry_author(post)}, published_at=post.get("updated"), links=r["links"], mentions=r["mentions"],
                          fetch_method="rss", extra={"subreddit": sub, "partial": True, "warnings": warnings},
                          source={"id": f"reddit:subreddit:{sub.lower()}", "kind": "subreddit", "title": f"r/{sub}", "url": f"{BASE}/r/{sub}/"})


def _json_or(url: str, rss_url: str) -> tuple[str, Any]:
    """('json', data) or, when Reddit answers with a block page, ('rss', parsed feed)."""
    try:
        return "json", _browser.load_json("reddit", url)
    except CliError as e:
        if e.code not in ("CHECKPOINT", "LOGIN_REQUIRED"):
            raise
        return "rss", _rss(rss_url)


class Reddit(PlatformAdapter):
    platform = "reddit"
    requires_session = False
    capabilities = frozenset({"search", "profile", "list", "fetch"})
    opts = {
        "search": [(("--subreddit",), {}), (("--type",), {"default": "posts", "choices": ["posts", "sr"]})],
        "list": [(("--sort",), {"default": "hot", "choices": ["hot", "new", "top", "rising"]}), (("--t",), {"default": "week", "choices": ["day", "week", "month", "year", "all"]}),
                 (("--kind",), {"default": "posts", "choices": ["posts", "comments"]})],
        "fetch": [(("--max-comments",), {"type": int, "default": MAX_COMMENTS})],
    }

    def search(self, query, *, limit=25, since=None, subreddit=None, type="posts", **_):
        if type == "sr":
            d = _browser.load_json("reddit", f"{BASE}/subreddits/search.json?q={quote_plus(query)}&limit={min(limit, 100)}")
            return [item_ref(f"{BASE}{c['data']['url']}", f"reddit:subreddit:{c['data']['display_name'].lower()}", "subreddit", c["data"]["display_name_prefixed"], None, None,
                             c["data"].get("public_description"), {"subscribers": c["data"].get("subscribers")}) for c in d["data"]["children"]]
        tail = f"q={quote_plus(query)}&sort=relevance&t=all&limit={min(limit, 100)}"
        base = f"{BASE}/r/{subreddit}/search" if subreddit else f"{BASE}/search"
        mode, d = _json_or(f"{base}.json?{'restrict_sr=1&' if subreddit else ''}{tail}", f"{base}.rss?{'restrict_sr=1&' if subreddit else ''}{tail}")
        refs_ = rss_refs(d) if mode == "rss" else listing_refs(d)
        return [i for i in refs_ if not since or (i["published_at"] or "")[:10] >= since][:limit]

    def profile(self, target, **_):
        t = target.strip().rstrip("/")
        if t.startswith(("r/", "/r/")) or "/r/" in t:
            name = t.split("r/")[-1].split("/")[0]
            a = _browser.load_json("reddit", f"{BASE}/r/{name}/about.json")["data"]
            return profile_record("reddit", f"reddit:subreddit:{name.lower()}", f"r/{name}", display_name=a.get("title"), bio=a.get("public_description"), followers=a.get("subscribers"),
                                  profile_url=f"{BASE}/r/{name}/", joined_at=(iso(a.get("created_utc")) or "")[:10])
        name = t.split("user/")[-1].split("/")[0].removeprefix("u/")
        a = _browser.load_json("reddit", f"{BASE}/user/{name}/about.json")["data"]
        return profile_record("reddit", f"reddit:user:{name.lower()}", f"u/{name}", display_name=a.get("name"), bio=(a.get("subreddit") or {}).get("public_description"), followers=a.get("link_karma"),
                              profile_url=f"{BASE}/user/{name}", joined_at=(iso(a.get("created_utc")) or "")[:10])

    def list(self, source, *, limit=25, cursor=None, since=None, sort="hot", t="week", kind="posts", **_):
        s = source.strip().rstrip("/")
        if "/user/" in s or s.startswith(("u/", "user/")):
            name = s.split("user/")[-1].removeprefix("u/").split("/")[0]
            url, src = f"{BASE}/user/{name}/{'submitted' if kind == 'posts' else 'comments'}.json?limit={min(limit, 100)}", f"reddit:user:{name.lower()}"
        else:
            name = s.split("r/")[-1].split("/")[0]
            url, src = f"{BASE}/r/{name}/{sort}.json?limit={min(limit, 100)}&t={t}", f"reddit:subreddit:{name.lower()}"
        if cursor:
            url += f"&after={cursor}"
        rss_url = (f"{BASE}/r/{name}/{sort if sort != 'hot' else ''}/.rss".replace("//.rss", "/.rss") if "subreddit" in src else f"{BASE}/user/{name}/{'submitted' if kind == 'posts' else 'comments'}/.rss") + f"?limit={min(limit, 100)}"
        mode, d = _json_or(url, rss_url)
        if mode == "rss":
            items = [i for i in rss_refs(d) if not since or (i["published_at"] or "")[:10] >= since]
            return list_result(items[:limit], None, {"id": src})
        items = [i for i in listing_refs(d) if not since or (i["published_at"] or "")[:10] >= since]
        return list_result(items[:limit], d.get("data", {}).get("after"), {"id": src})

    def fetch(self, item, *, max_comments=MAX_COMMENTS, **_):
        pid = post_id(item)
        mode, d = _json_or(f"{BASE}/comments/{pid}.json?limit=500&depth=10&sort=top&raw_json=1", f"{BASE}/comments/{pid}/.rss?limit=100")
        if mode == "rss":
            warnings_: list[str] = []
            rec = rss_thread_record(d, pid, warnings_)
            rec["raw_path"] = save_raw("reddit", pid, str(d.get("entries", [])), "txt")
            return rec
        if not isinstance(d, list) or len(d) < 2:
            raise CliError("NOT_FOUND", f"reddit post {pid} not found")
        warnings: list[str] = []
        post = d[0]["data"]["children"][0]["data"]
        comments, stubs = flatten_comments(d[1], post["name"])
        extra: list[dict[str, Any]] = []
        want = min(post.get("num_comments", 0), max_comments) - len(comments)
        for i in range(0, len(stubs), 100):
            if want <= 0 or len(comments) + len(extra) >= max_comments:
                break
            chunk = ",".join(stubs[i:i + 100])
            r = _browser.load_json("reddit", f"{BASE}/api/morechildren.json?api_type=json&link_id={post['name']}&children={chunk}&raw_json=1")
            for th in r.get("json", {}).get("data", {}).get("things", []):
                if th["kind"] == "t1":
                    extra.append(th["data"])
        rec = build_record(d, extra, max_comments, warnings, save_raw("reddit", pid, d))
        rec["extra"]["warnings"] = warnings
        return rec
