"""X/Twitter through the agent browser, reading the site's own GraphQL responses (docs/spec/05 §2.4). Session required.
The parser walks the JSON recursively, so it survives the frequent query-id and nesting changes."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Iterator
from urllib.parse import quote_plus

from finsocnet.adapters import _browser
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, profile_record, save_raw
from finsocnet.core.segments import refs

MAX_REPLIES = 100
GQL = r"/i/api/graphql/[^/]+/(SearchTimeline|UserTweets|UserTweetsAndReplies|TweetDetail|UserByScreenName)"


def tweet_id(ref: str) -> str:
    m = re.search(r"status(?:es)?/(\d+)|x:(\d+)|^(\d{6,})$", ref.strip())
    if not m:
        raise CliError("USAGE", f"cannot read a tweet id from {ref!r}")
    return next(g for g in m.groups() if g)


def handle_of(ref: str) -> str:
    return ref.strip().rstrip("/").split("/")[-1].lstrip("@") if "/" in ref else ref.strip().lstrip("@")


def iso(created: str | None) -> str | None:
    if not created:
        return None
    try:
        return datetime.strptime(created, "%a %b %d %H:%M:%S %z %Y").astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return created


def iter_nodes(obj: Any) -> Iterator[dict[str, Any]]:
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from iter_nodes(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_nodes(v)


def _user_fields(core: dict[str, Any]) -> dict[str, Any]:
    res = ((core or {}).get("user_results") or {}).get("result") or {}
    legacy = res.get("legacy") or {}
    return {"handle": (res.get("core") or {}).get("screen_name") or legacy.get("screen_name"), "name": (res.get("core") or {}).get("name") or legacy.get("name"), "id": res.get("rest_id"),
            "verified": res.get("is_blue_verified")}


def parse_tweet(node: dict[str, Any]) -> dict[str, Any] | None:
    n = node.get("tweet") if "tweet" in node and "legacy" not in node else node
    if not isinstance(n, dict) or "legacy" not in n or "rest_id" not in n:
        return None
    leg = n["legacy"]
    note = (((n.get("note_tweet") or {}).get("note_tweet_results") or {}).get("result") or {}).get("text")
    text = note or leg.get("full_text") or ""
    for u in (leg.get("entities") or {}).get("urls", []):
        text = text.replace(u.get("url", "\0"), u.get("expanded_url", u.get("url", "")))
    media = [{"kind": "video" if m.get("type") in ("video", "animated_gif") else "image", "url": m.get("media_url_https")} for m in (leg.get("extended_entities") or leg.get("entities") or {}).get("media", [])]
    u = _user_fields(n.get("core"))
    quoted = n.get("quoted_status_result", {}).get("result")
    return {"id": n["rest_id"], "text": text.strip(), "created_at": iso(leg.get("created_at")), "author": u, "likes": leg.get("favorite_count"), "retweets": leg.get("retweet_count"),
            "replies": leg.get("reply_count"), "reply_to": leg.get("in_reply_to_status_id_str"), "conversation": leg.get("conversation_id_str"), "media": media,
            "quoted": parse_tweet(quoted) if isinstance(quoted, dict) else None, "views": (n.get("views") or {}).get("count")}


def collect_tweets(bodies: list[Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for b in bodies:
        for node in iter_nodes(b):
            t = parse_tweet(node)
            if t and t["id"] not in out:
                out[t["id"]] = t
    return out


def tweet_ref(t: dict[str, Any]) -> dict[str, Any]:
    h = t["author"].get("handle")
    return item_ref(f"https://x.com/{h}/status/{t['id']}", f"x:{t['id']}", "post", None, f"@{h}" if h else None, t["created_at"], t["text"], {"likes": t["likes"], "retweets": t["retweets"], "views": t["views"]})


def build_record(root_id: str, tweets: dict[str, dict[str, Any]], max_replies: int, raw_path: str | None) -> dict[str, Any]:
    if root_id not in tweets:
        raise CliError("NOT_FOUND", f"tweet {root_id} was not in the captured responses (deleted, private or not loaded)")
    root = tweets[root_id]
    author = root["author"]["id"]
    thread = [t for t in tweets.values() if t["author"]["id"] == author and (t["conversation"] or root_id) == root_id and t["id"] != root_id]
    thread.sort(key=lambda t: int(t["id"]))
    own_ids = {root_id, *(t["id"] for t in thread)}
    replies = sorted((t for t in tweets.values() if t["id"] not in own_ids and (t["conversation"] or root_id) == root_id), key=lambda t: -(t["likes"] or 0))[:max_replies]
    segs = []
    for t, kind in [(root, "post"), *[(t, "post") for t in thread], *[(t, "reply") for t in replies]]:
        segs.append({"seq": len(segs), "kind": kind, "locator": {"tweet_id": t["id"], "parent_id": t["reply_to"], "score": t["likes"]},
                     "author": {"handle": f"@{t['author']['handle']}" if t["author"]["handle"] else None, "display_name": t["author"]["name"], "platform_user_id": t["author"]["id"]}, "text": t["text"] or "(media only)"})
    if root.get("quoted") and root["quoted"]["text"]:
        q = root["quoted"]
        segs.append({"seq": len(segs), "kind": "reply", "locator": {"tweet_id": q["id"], "quoted_id": q["id"]}, "author": {"handle": f"@{q['author']['handle']}" if q["author"]["handle"] else None}, "text": q["text"]})
    r = refs("\n".join(s["text"] for s in segs))
    h = root["author"]["handle"]
    media = [m for t in [root, *thread] for m in t["media"]]
    return content_record(f"x:{root_id}", "x", "thread" if thread else "post", segs, url=f"https://x.com/{h}/status/{root_id}", title=(root["text"] or "")[:100], author={"handle": f"@{h}", "display_name": root["author"]["name"], "platform_user_id": author},
                          published_at=root["created_at"], metrics={"likes": root["likes"], "retweets": root["retweets"], "views": root["views"]}, links=r["links"], mentions=r["mentions"], media=media,
                          raw_path=raw_path, fetch_method="graphql_capture", extra={"quoted": root.get("quoted") and root["quoted"]["text"]},
                          source={"id": f"x:user:{h.lower()}", "kind": "user", "title": root["author"]["name"], "url": f"https://x.com/{h}"})


def parse_profile(bodies: list[Any], handle: str) -> dict[str, Any]:
    for b in bodies:
        for node in iter_nodes(b):
            res = node.get("user") and node["user"].get("result")
            if isinstance(res, dict) and "legacy" in res:
                leg = res["legacy"]
                h = (res.get("core") or {}).get("screen_name") or leg.get("screen_name") or handle
                links = [u.get("expanded_url") for u in ((leg.get("entities") or {}).get("url") or {}).get("urls", []) if u.get("expanded_url")]
                links += [u.get("expanded_url") for u in ((leg.get("entities") or {}).get("description") or {}).get("urls", []) if u.get("expanded_url")]
                return profile_record("x", f"x:user:{h.lower()}", f"@{h}", display_name=(res.get("core") or {}).get("name") or leg.get("name"), bio=leg.get("description"), links=links,
                                      followers=leg.get("followers_count"), verified=res.get("is_blue_verified"), avatar_url=leg.get("profile_image_url_https"), profile_url=f"https://x.com/{h}",
                                      location=leg.get("location") or None, joined_at=(iso(leg.get("created_at")) or "")[:10] or None)
    raise CliError("NOT_FOUND", f"X profile @{handle} was not in the captured responses")


class X(PlatformAdapter):
    platform = "x"
    requires_session = True
    capabilities = frozenset({"search", "profile", "list", "fetch"})
    opts = {"search": [(("--top",), {"action": "store_true"})], "list": [(("--with-replies",), {"action": "store_true"})], "fetch": [(("--max-replies",), {"type": int, "default": MAX_REPLIES})]}

    def search(self, query, *, limit=20, since=None, top=False, **_):
        q = f"{query} since:{since}" if since else query
        _u, bodies = _browser.capture("x", f"https://x.com/search?q={quote_plus(q)}&src=typed_query&f={'top' if top else 'live'}", GQL, scrolls=max(2, limit // 8),
                                      until=lambda b: len(collect_tweets(b)) >= limit)
        ts = sorted(collect_tweets(bodies).values(), key=lambda t: -int(t["id"]))
        return [tweet_ref(t) for t in ts][:limit]

    def profile(self, target, **_):
        h = handle_of(target)
        _u, bodies = _browser.capture("x", f"https://x.com/{h}", GQL, scrolls=0)
        return parse_profile(bodies, h)

    def list(self, source, *, limit=20, cursor=None, since=None, with_replies=False, **_):
        h = handle_of(source)
        stop = int(cursor) if cursor else 0
        _u, bodies = _browser.capture("x", f"https://x.com/{h}{'/with_replies' if with_replies else ''}", GQL, scrolls=max(2, limit // 6),
                                      until=lambda b: len([t for t in collect_tweets(b).values() if t["author"]["handle"] and t["author"]["handle"].lower() == h.lower()]) >= limit)
        ts = [t for t in collect_tweets(bodies).values() if t["author"]["handle"] and t["author"]["handle"].lower() == h.lower() and int(t["id"]) > stop]
        ts.sort(key=lambda t: -int(t["id"]))
        items = [tweet_ref(t) for t in ts if not since or (t["created_at"] or "")[:10] >= since][:limit]
        return list_result(items, items[-1]["id"].split(":")[1] if items else cursor, {"id": f"x:user:{h.lower()}"})

    def fetch(self, item, *, max_replies=MAX_REPLIES, **_):
        tid = tweet_id(item)
        url = item if item.startswith("http") else f"https://x.com/i/status/{tid}"
        _u, bodies = _browser.capture("x", url, GQL, scrolls=2)
        return build_record(tid, collect_tweets(bodies), max_replies, save_raw("x", tid, bodies))
