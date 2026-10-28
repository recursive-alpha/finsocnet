"""Any web page rendered in the agent browser (specs/05 §2.10), plus feed/sitemap/media discovery."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlsplit

from lxml import html as lhtml

from finsocnet.adapters import _browser
from finsocnet.core import ids
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, save_raw
from finsocnet.core.segments import paragraph_segments, refs

MIN_EXTRACT_CHARS = 200
MEDIA_HOSTS = ("youtube.com/embed", "youtube-nocookie.com/embed", "player.vimeo.com", "rumble.com/embed", "twitch.tv", "dailymotion.com/embed")


def extract_markdown(html: str, url: str | None = None) -> tuple[str, dict[str, Any]]:
    """trafilatura first; DOM text of <article>/<main>/<body> when trafilatura returns too little."""
    import trafilatura
    md = trafilatura.extract(html, output_format="markdown", include_comments=True, include_tables=True, url=url, favor_recall=True) or ""
    meta_obj = trafilatura.extract_metadata(html)
    meta = {k: getattr(meta_obj, k, None) for k in ("title", "author", "date", "sitename", "description", "image")} if meta_obj else {}
    if len(md) < MIN_EXTRACT_CHARS:
        root = lhtml.fromstring(html)
        for bad in root.xpath("//script|//style|//nav|//header|//footer|//noscript|//aside|//form"):
            bad.getparent().remove(bad)
        node = (root.xpath("//article") or root.xpath("//main") or root.xpath("//body") or [root])[0]
        md = "\n\n".join(" ".join(p.text_content().split()) for p in node.xpath(".//p|.//h1|.//h2|.//h3|.//li|.//pre") if p.text_content().strip())
        meta["fallback"] = "dom"
    return md, meta


def canonical_of(html: str, url: str) -> str:
    root = lhtml.fromstring(html)
    c = root.xpath("//link[@rel='canonical']/@href")
    return urljoin(url, c[0]) if c else url


def page_record(url: str, html: str, raw_path: str | None = None, final_url: str | None = None) -> dict[str, Any]:
    final = final_url or url
    canon = ids.canonical_url(canonical_of(html, final))
    md, meta = extract_markdown(html, final)
    segs = paragraph_segments(md, min_len=40) or [{"seq": 0, "kind": "page", "locator": {"page": 1}, "text": (meta.get("title") or final)}]
    root = lhtml.fromstring(html)
    anchors = [urljoin(final, a) for a in root.xpath("//a/@href") if a.startswith(("http", "/"))]
    r = refs(md)
    host = urlsplit(final).netloc.lower().removeprefix("www.")
    media = [{"kind": "embed", "url": u} for u in dict.fromkeys(root.xpath("//iframe/@src") + root.xpath("//video/@src") + root.xpath("//video/source/@src")) if u]
    media += [{"kind": "caption_track", "url": urljoin(final, u)} for u in root.xpath("//track/@src")]
    return content_record(ids.web_content_id(canon), "web", "page", segs, url=canon, title=meta.get("title"), description=meta.get("description"),
                          author={"handle": meta.get("author")}, published_at=(meta.get("date") or None), links=list(dict.fromkeys(r["links"] + anchors))[:300], mentions=r["mentions"],
                          media=media, raw_path=raw_path, fetch_method="browser+trafilatura", extra={"extraction": meta.get("fallback") or "trafilatura", "final_url": final},
                          source={"id": f"web:site:{host}", "kind": "site", "title": meta.get("sitename") or host, "url": f"https://{host}"})


def discover_page(html: str, base: str) -> list[dict[str, Any]]:
    """RSS/Atom links, outbound links, embedded media, caption tracks and PDFs as ItemRefs for the agent to enqueue."""
    root = lhtml.fromstring(html)
    host = urlsplit(base).netloc
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(url: str, kind: str, title: str | None = None) -> None:
        u = urljoin(base, url)
        if u in seen or not u.startswith("http"):
            return
        seen.add(u)
        out.append(item_ref(u, ids.web_content_id(u), kind, title, None, None, None))

    for l in root.xpath("//link[@rel='alternate']"):
        if (l.get("type") or "").endswith(("rss+xml", "atom+xml")) and l.get("href"):
            add(l.get("href"), "feed", l.get("title"))
    for a in root.xpath("//a[@href]"):
        h = urljoin(base, a.get("href"))
        if h.lower().split("?")[0].endswith((".pdf", ".epub")):
            add(h, "document", a.text_content().strip()[:100])
        elif urlsplit(h).netloc and urlsplit(h).netloc != host:
            add(h, "outbound", a.text_content().strip()[:100])
    for src in root.xpath("//iframe/@src") + root.xpath("//video/@src") + root.xpath("//video/source/@src"):
        if any(m in src for m in MEDIA_HOSTS) or src.endswith((".mp4", ".webm", ".m3u8")):
            add(src, "media")
    for t in root.xpath("//track/@src"):
        add(t, "caption_track")
    return out


class Web(PlatformAdapter):
    platform = "web"
    capabilities = frozenset({"fetch", "discover"})
    opts = {"fetch": [(("--wait",), {"default": "networkidle", "choices": ["load", "domcontentloaded", "networkidle"]})]}

    def fetch(self, item, *, wait="networkidle", **_):
        if not item.startswith("http"):
            raise CliError("USAGE", "give an http(s) URL")
        if item.lower().split("?")[0].endswith(".pdf"):
            raise CliError("UNSUPPORTED", "PDFs are read by document-reader", f"uv run .agents/skills/document-reader/scripts/document.py fetch {item}")
        final, html = _browser.load_html("web", item, wait=wait)
        return page_record(item, html, save_raw("web", ids.web_content_id(item).split(":")[1], html, "html"), final)

    def discover(self, url: str) -> list[dict[str, Any]]:
        final, html = _browser.load_html("web", url, wait="networkidle")
        return discover_page(html, final)
