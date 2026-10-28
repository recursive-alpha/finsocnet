"""Bluesky via the public AppView (docs/spec/05 §3.11)."""

from __future__ import annotations

import re
from typing import Any

from finsocnet.core import http
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, profile_record, save_raw
from finsocnet.core.segments import refs

API = "https://public.api.bsky.app/xrpc"
MAX_REPLIES = 100


def rkey(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def did_of(uri: str) -> str:
    return uri.split("/")[2]


def post_url(post: dict[str, Any]) -> str:
    return f"https://bsky.app/profile/{post['author']['handle']}/post/{rkey(post['uri'])}"


def cid(post: dict[str, Any]) -> str:
    return f"bluesky:{did_of(post['uri'])}:{rkey(post['uri'])}"


def parse_ref(item: str) -> str:
    """`https://bsky.app/profile/<handle>/post/<rkey>` or an `at://` URI -> at:// URI (handles stay as handle for the API)."""
    m = re.search(r"bsky\.app/profile/([^/]+)/post/([A-Za-z0-9]+)", item)
    if m:
        return f"at://{m.group(1)}/app.bsky.feed.post/{m.group(2)}"
    if item.startswith("at://"):
        return item
    raise CliError("USAGE", f"cannot read a Bluesky post from {item!r}")


def feed_refs(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item_ref(post_url(p), cid(p), "post", None, p["author"]["handle"], p["record"].get("createdAt"), p["record"].get("text"),
                     {"likes": p.get("likeCount"), "reposts": p.get("repostCount"), "replies": p.get("replyCount")}) for p in posts]


def build_record(thread: dict[str, Any], raw_path: str | None) -> dict[str, Any]:
    root = thread["post"]
    author_did = root["author"]["did"]
    segs: list[dict[str, Any]] = []

    def seg(post: dict[str, Any], kind: str, parent: str | None) -> dict[str, Any]:
        return {"seq": len(segs), "kind": kind, "locator": {"comment_id": rkey(post["uri"]), "parent_id": parent, "score": post.get("likeCount")},
                "author": {"handle": post["author"]["handle"], "display_name": post["author"].get("displayName"), "platform_user_id": post["author"]["did"]},
                "text": post["record"].get("text", "")}

    segs.append(seg(root, "post", None))
    cur = thread
    while True:  # the author's self-thread: consecutive replies by the same author
        nxt = next((r for r in cur.get("replies", []) if r.get("post", {}).get("author", {}).get("did") == author_did), None)
        if not nxt:
            break
        segs.append(seg(nxt["post"], "post", rkey(cur["post"]["uri"])))
        cur = nxt
    others = [r for r in thread.get("replies", []) if r.get("post", {}).get("author", {}).get("did") != author_did]
    others.sort(key=lambda r: -(r["post"].get("likeCount") or 0))
    for r in others[:MAX_REPLIES]:
        segs.append(seg(r["post"], "reply", rkey(root["uri"])))
    segs = [s for s in segs if s["text"].strip()] or [{"seq": 0, "kind": "post", "locator": {}, "text": "(no text)"}]
    r = refs("\n".join(s["text"] for s in segs))
    media = [{"kind": "image", "url": i.get("fullsize")} for i in (root.get("embed") or {}).get("images", [])]
    return content_record(cid(root), "bluesky", "thread" if len(segs) > 1 else "post", segs, url=post_url(root), author={"handle": root["author"]["handle"], "platform_user_id": author_did},
                          published_at=root["record"].get("createdAt"), language=(root["record"].get("langs") or [None])[0], metrics={"likes": root.get("likeCount"), "reposts": root.get("repostCount"), "replies": root.get("replyCount")},
                          links=r["links"], mentions=r["mentions"], media=media, raw_path=raw_path, fetch_method="appview",
                          source={"id": f"bluesky:user:{root['author']['handle'].lower()}", "kind": "user", "title": root["author"].get("displayName") or root["author"]["handle"]})


class Bluesky(PlatformAdapter):
    platform = "bluesky"
    capabilities = frozenset({"search", "profile", "list", "fetch"})

    def search(self, query, *, limit=20, since=None, **_):
        params: dict[str, Any] = {"q": query, "limit": min(limit, 100)}
        if since:
            params["since"] = f"{since}T00:00:00Z"
        try:
            return feed_refs(http.get_json(f"{API}/app.bsky.feed.searchPosts", platform="bluesky", params=params).get("posts", []))[:limit]
        except CliError as e:
            if e.code == "LOGIN_REQUIRED":  # verified 2026-10-28: the public AppView answers 403 to searchPosts
                raise CliError("LOGIN_REQUIRED", "Bluesky post search needs an authenticated AppView", "use web-searcher with `--site bsky.app`, or `list` a known profile") from e
            raise

    def profile(self, target, **_):
        h = target.rsplit("/", 1)[-1].lstrip("@")
        p = http.get_json(f"{API}/app.bsky.actor.getProfile", platform="bluesky", params={"actor": h})
        return profile_record("bluesky", f"bluesky:user:{p['handle'].lower()}", p["handle"], display_name=p.get("displayName"), bio=p.get("description"), followers=p.get("followersCount"),
                              avatar_url=p.get("avatar"), profile_url=f"https://bsky.app/profile/{p['handle']}", joined_at=(p.get("createdAt") or "")[:10] or None,
                              links=refs(p.get("description") or "")["links"])

    def list(self, source, *, limit=50, cursor=None, since=None, **_):
        h = source.rsplit("/", 1)[-1].lstrip("@")
        params: dict[str, Any] = {"actor": h, "limit": min(limit, 100), "filter": "posts_no_replies"}
        if cursor:
            params["cursor"] = cursor
        d = http.get_json(f"{API}/app.bsky.feed.getAuthorFeed", platform="bluesky", params=params)
        posts = [f["post"] for f in d.get("feed", []) if not f.get("reason")]
        items = [i for i in feed_refs(posts) if (not since or (i["published_at"] or "")[:10] >= since)]
        return list_result(items, d.get("cursor"), {"id": f"bluesky:user:{h.lower()}"})

    def fetch(self, item, **_):
        uri = parse_ref(item)
        d = http.get_json(f"{API}/app.bsky.feed.getPostThread", platform="bluesky", params={"uri": uri, "depth": 10})
        return build_record(d["thread"], save_raw("bluesky", rkey(uri), d))
