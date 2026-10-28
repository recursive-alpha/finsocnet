"""Any RSS/Atom feed (docs/spec/05 §3.7). Items use `web:<sha1(canonical_url)[:16]>` ids, the same as web-reader."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

import feedparser

from finsocnet.core import http, ids
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, save_raw
from finsocnet.core.segments import html_paragraphs, refs

COMMON_PATHS = ["/feed", "/rss", "/atom.xml", "/index.xml", "/feed.xml", "/rss.xml"]


def entry_date(e: Any) -> str | None:
    t = e.get("published_parsed") or e.get("updated_parsed")
    return datetime(*t[:6], tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if t else None


def entry_html(e: Any) -> str:
    c = e.get("content")
    return (c[0].get("value") if c else None) or e.get("summary") or e.get("description") or ""


def feed_items(xml: str, feed_url: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    f = feedparser.parse(xml)
    src = {"id": ids.rss_source_id(feed_url), "kind": "feed", "title": f.feed.get("title"), "url": feed_url}
    items = []
    for e in f.entries:
        link = e.get("link") or ""
        eid = ids.web_content_id(link) if link else f"web:{ids.hashlib.sha1((e.get('id') or e.get('title', '')).encode()).hexdigest()[:16]}"
        items.append({"entry": e, "ref": item_ref(link, eid, "article", e.get("title"), e.get("author"), entry_date(e), re.sub(r"<[^>]+>", " ", entry_html(e))[:300]), "guid": e.get("id") or link})
    return src, items


def entry_record(e: Any, feed_url: str, src: dict[str, Any], body_html: str | None = None, raw_path: str | None = None) -> dict[str, Any]:
    link = e.get("link") or feed_url
    html_body = body_html if body_html is not None else entry_html(e)
    segs = html_paragraphs(html_body) or [{"seq": 0, "kind": "paragraph", "locator": {"para": 0}, "text": e.get("title") or link}]
    r = refs(re.sub(r"<[^>]+>", " ", html_body) + " " + " ".join(re.findall(r'href="([^"]+)"', html_body)))
    return content_record(ids.web_content_id(link), "web", "article", segs, url=link, title=e.get("title"), author={"handle": e.get("author")}, published_at=entry_date(e),
                          links=r["links"], mentions=r["mentions"], raw_path=raw_path, fetch_method="rss", extra={"feed": feed_url, "guid": e.get("id")}, source=src)


class _LinkFinder(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.feeds: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "link" and a.get("rel") == "alternate" and (a.get("type") or "").endswith(("rss+xml", "atom+xml")) and a.get("href"):
            self.feeds.append({"href": a["href"], "title": a.get("title") or "", "type": a["type"]})


def discover_feeds(html: str, base_url: str) -> list[dict[str, str]]:
    p = _LinkFinder()
    p.feed(html)
    return [{**f, "href": urljoin(base_url, f["href"])} for f in p.feeds]


class RSS(PlatformAdapter):
    platform = "rss"
    capabilities = frozenset({"list", "fetch", "discover", "profile"})
    opts = {"fetch": [(("--feed",), {"help": "feed URL when fetching an entry that is not a URL"})]}

    def profile(self, target, **_):
        from finsocnet.core.platform import profile_record
        xml = http.get_text(target, platform="rss")
        src, _items = feed_items(xml, target)
        f = feedparser.parse(xml).feed
        return profile_record("rss", src["id"], target, display_name=f.get("title"), bio=f.get("subtitle") or f.get("description"), profile_url=f.get("link") or target)

    def list(self, source, *, limit=50, cursor=None, since=None, **_):
        xml = http.get_text(source, platform="rss")
        save_raw("rss", ids.rss_source_id(source), xml, "xml")
        src, items = feed_items(xml, source)
        out = []
        for it in items:
            if cursor and it["guid"] == cursor:
                break
            if since and (it["ref"]["published_at"] or "")[:10] < since:
                continue
            out.append(it["ref"])
        return list_result(out[:limit], items[0]["guid"] if items else None, src)

    def fetch(self, item, *, feed=None, **_):
        """`item` is an entry URL; `--feed` points at the feed that lists it (full `content:encoded` is used when present)."""
        if feed:
            xml = http.get_text(feed, platform="rss")
            src, items = feed_items(xml, feed)
            for it in items:
                if it["ref"]["ref"].rstrip("/") == item.rstrip("/") or it["ref"]["id"] == item:
                    html_body = entry_html(it["entry"])
                    if len(re.sub(r"<[^>]+>", "", html_body)) > 400:
                        return entry_record(it["entry"], feed, src, raw_path=save_raw("rss", it["ref"]["id"], xml, "xml"))
                    break
        raise CliError("UNSUPPORTED", "this entry has only a summary in the feed", "use web-reader fetch on the link")

    def discover(self, url: str) -> dict[str, Any]:
        html = http.get_text(url, platform="rss")
        found = discover_feeds(html, url)
        if not found:
            for path in COMMON_PATHS:
                u = urljoin(url, path)
                try:
                    txt = http.get_text(u, platform="rss", retries=0)
                except CliError:
                    continue
                if "<rss" in txt[:2000] or "<feed" in txt[:2000]:
                    found.append({"href": u, "title": "", "type": "guess"})
        return {"url": url, "feeds": found}
