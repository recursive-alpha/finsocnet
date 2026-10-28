"""Hacker News via the Algolia API (specs/05 §4). No session."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from finsocnet.core import http
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, profile_record, save_raw
from finsocnet.core.segments import html_to_markdown, refs

API = "https://hn.algolia.com/api/v1"


def hn_id(item_id: Any) -> str:
    return f"hn:{item_id}"


def parse_item_id(ref: str) -> str:
    m = re.search(r"(?:id=|hn:|^)(\d+)$", ref.strip())
    if not m:
        raise CliError("USAGE", f"cannot read a Hacker News item id from {ref!r}", "give an item id or https://news.ycombinator.com/item?id=<id>")
    return m.group(1)


def parse_search(data: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for h in data.get("hits", []):
        oid = h.get("objectID") or h.get("story_id")
        title = h.get("title") or h.get("story_title")
        out.append(item_ref(f"https://news.ycombinator.com/item?id={oid}", hn_id(oid), "story" if h.get("title") else "comment", title, h.get("author"), h.get("created_at"),
                            h.get("story_text") or h.get("comment_text") or h.get("url"), {"points": h.get("points"), "comments": h.get("num_comments")}))
    return out


def parse_item(data: dict[str, Any], raw_path: str | None = None) -> dict[str, Any]:
    segments: list[dict[str, Any]] = []
    all_text: list[str] = []

    def walk(node: dict[str, Any], parent: Any, depth: int) -> None:
        text = html_to_markdown(node.get("text") or "") if node.get("text") else ""
        if node is not data and text:
            segments.append({"seq": len(segments), "kind": "comment", "locator": {"comment_id": str(node["id"]), "parent_id": str(parent), "depth": depth, "score": node.get("points")},
                             "author": {"handle": node.get("author")}, "text": text})
            all_text.append(text)
        for c in node.get("children", []):
            walk(c, node["id"], depth + 1)

    head = [data.get("title") or ""]
    if data.get("text"):
        head.append(html_to_markdown(data["text"]))
    if data.get("url"):
        head.append(data["url"])
    first = "\n\n".join(h for h in head if h)
    segments.append({"seq": 0, "kind": "post", "locator": {"comment_id": str(data["id"])}, "author": {"handle": data.get("author")}, "text": first or f"HN item {data['id']}"})
    for c in data.get("children", []):
        walk(c, data["id"], 1)
    r = refs(first + "\n" + "\n".join(all_text))
    created = data.get("created_at")
    return content_record(
        hn_id(data["id"]), "hackernews", "thread" if data.get("children") else "post", segments, url=f"https://news.ycombinator.com/item?id={data['id']}", title=data.get("title"),
        author={"handle": data.get("author")}, published_at=created, language="en", metrics={"score": data.get("points"), "comments": len(segments) - 1},
        links=r["links"], mentions=r["mentions"], raw_path=raw_path, fetch_method="algolia", source={"id": "hackernews:site:news.ycombinator.com", "kind": "site", "title": "Hacker News"})


class HackerNews(PlatformAdapter):
    platform = "hackernews"
    capabilities = frozenset({"search", "profile", "list", "fetch"})
    opts = {"search": [(("--comments",), {"action": "store_true", "help": "search comments instead of stories"})]}

    def search(self, query, *, limit=20, since=None, comments=False, **_):
        params: dict[str, Any] = {"query": query, "tags": "comment" if comments else "story", "hitsPerPage": min(limit, 100)}
        if since:
            params["numericFilters"] = f"created_at_i>{int(datetime.fromisoformat(since).replace(tzinfo=timezone.utc).timestamp())}"
        return parse_search(http.get_json(f"{API}/search", platform="hackernews", params=params))[:limit]

    def profile(self, target, **_):
        name = target.rsplit("=", 1)[-1].strip("/")
        d = http.get_json(f"{API}/users/{name}", platform="hackernews")
        return profile_record("hackernews", f"hackernews:user:{name.lower()}", name, display_name=name, bio=html_to_markdown(d.get("about") or "") or None,
                              followers=None, profile_url=f"https://news.ycombinator.com/user?id={name}")

    def list(self, source, *, limit=50, cursor=None, since=None, **_):
        name = source.rsplit("=", 1)[-1].strip("/")
        d = http.get_json(f"{API}/search_by_date", platform="hackernews", params={"tags": f"author_{name},story", "hitsPerPage": min(limit, 100), "page": int(cursor or 0)})
        nxt = str(d["page"] + 1) if d.get("page", 0) + 1 < d.get("nbPages", 0) else None
        return list_result(parse_search(d)[:limit], nxt, {"id": f"hackernews:user:{name.lower()}"})

    def fetch(self, item, **_):
        iid = parse_item_id(item)
        data = http.get_json(f"{API}/items/{iid}", platform="hackernews")
        return parse_item(data, save_raw("hackernews", iid, data))
