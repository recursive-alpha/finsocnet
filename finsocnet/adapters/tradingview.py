"""TradingView ideas and Pine scripts through the agent browser (specs/05 §3.5). Selectors are unverified against the live
site (account required); the parser reads JSON-LD / Open Graph first and falls back to page text."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import quote_plus, urljoin

from lxml import html as lhtml

from finsocnet.adapters import _browser, web
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, profile_record, save_raw
from finsocnet.core.segments import code_segments, paragraph_segments, refs

BASE = "https://www.tradingview.com"


def kind_of(url: str) -> str:
    return "script" if "/script/" in url else "idea"


def native_id(url: str) -> str:
    m = re.search(r"/(?:chart|script)/(?:[^/]+/)?([A-Za-z0-9]{6,12})(?:-[^/]*)?/?", url) or re.search(r"/(?:chart|script)/([^/]+)/", url)
    if not m:
        raise CliError("USAGE", f"cannot read a TradingView id from {url!r}")
    return m.group(1)


def parse_page(html: str, url: str) -> dict[str, Any]:
    root = lhtml.fromstring(html)
    meta = lambda p: (root.xpath(f"//meta[@property='{p}']/@content|//meta[@name='{p}']/@content") or [None])[0]
    ld = {}
    for s in root.xpath("//script[@type='application/ld+json']/text()"):
        try:
            d = json.loads(s)
            ld = d[0] if isinstance(d, list) else d
            break
        except ValueError:
            continue
    desc_nodes = root.xpath("//*[@data-name='content-description' or contains(@class,'tv-chart-view__description') or contains(@class,'description-content')]")
    description = html_text(desc_nodes[0]) if desc_nodes else (ld.get("description") or meta("og:description") or "")
    code = "\n".join(c.text_content() for c in root.xpath("//pre[contains(@class,'pine') or contains(@class,'source-code') or @data-name='pine-source']|//code[contains(@class,'pine')]"))
    comments = [{"id": c.get("data-comment-id") or str(i), "author": (c.xpath(".//*[contains(@class,'username') or @data-username]/@data-username|.//*[contains(@class,'username')]/text()") or [None])[0],
                 "text": " ".join(c.xpath(".//*[contains(@class,'comment-content') or @data-name='comment-content']")[0].text_content().split()) if c.xpath(".//*[contains(@class,'comment-content') or @data-name='comment-content']") else ""}
                for i, c in enumerate(root.xpath("//*[@data-comment-id or contains(@class,'tv-chart-comment')]"))]
    symbol = (re.search(r"/symbols/([A-Z0-9:_-]+)/", html) or [None, None])[1] or meta("tv:symbol")
    direction = next((w for w in ("Long", "Short") if re.search(rf">\s*{w}\s*<", html)), None)
    return {"title": ld.get("headline") or meta("og:title") or " ".join(root.xpath("//title/text()")).strip(), "description": description, "author": (ld.get("author") or {}).get("name") if isinstance(ld.get("author"), dict) else ld.get("author"),
            "published": ld.get("datePublished"), "image": meta("og:image"), "code": code.strip(), "comments": [c for c in comments if c["text"]], "symbol": symbol, "direction": direction}


def html_text(node: Any) -> str:
    return "\n\n".join(" ".join(p.text_content().split()) for p in node.xpath(".//p|.//li") if p.text_content().strip()) or " ".join(node.text_content().split())


def build_record(url: str, d: dict[str, Any], raw_path: str | None) -> dict[str, Any]:
    kind = kind_of(url)
    nid = native_id(url)
    segs = paragraph_segments(d["description"], min_len=30) if d["description"] else []
    code_visible = bool(d["code"])
    if code_visible:
        segs += code_segments(d["code"], None, 60, len(segs))
    for c in d["comments"]:
        segs.append({"seq": len(segs), "kind": "comment", "locator": {"comment_id": c["id"]}, "author": {"handle": c["author"]}, "text": c["text"]})
    if not segs:
        segs = [{"seq": 0, "kind": "paragraph", "locator": {"para": 0}, "text": d["title"] or url}]
    r = refs(d["description"])
    return content_record(f"tradingview:{kind}:{nid}", "tradingview", kind if kind == "script" else "idea", segs, url=url, title=d["title"], description=d["description"][:500] or None,
                          author={"handle": d["author"]}, published_at=d["published"], links=r["links"], mentions=r["mentions"], media=[{"kind": "image", "url": d["image"]}] if d["image"] else [],
                          raw_path=raw_path, fetch_method="browser", extra={"symbol": d["symbol"], "direction": d["direction"], "code_visible": code_visible if kind == "script" else None},
                          source={"id": f"tradingview:user:{(d['author'] or 'unknown').lower()}", "kind": "user", "title": d["author"]})


class TradingView(PlatformAdapter):
    platform = "tradingview"
    capabilities = frozenset({"search", "profile", "list", "fetch"})
    opts = {"search": [(("--scripts",), {"action": "store_true"})]}

    def _links(self, url: str, scrolls: int = 2) -> list[dict[str, Any]]:
        final, html = _browser.load_html("tradingview", url, wait="networkidle", scrolls=scrolls)
        out, seen = [], set()
        for a in lhtml.fromstring(html).xpath("//a[contains(@href,'/chart/') or contains(@href,'/script/')]"):
            href = urljoin(BASE, a.get("href").split("?")[0])
            try:
                nid = native_id(href)
            except CliError:
                continue
            if nid in seen:
                continue
            seen.add(nid)
            out.append(item_ref(href, f"tradingview:{kind_of(href)}:{nid}", kind_of(href), " ".join(a.text_content().split())[:160] or None, None, None, None))
        return out

    def search(self, query, *, limit=20, since=None, scripts=False, **_):
        return self._links(f"{BASE}/{'scripts' if scripts else 'ideas'}/search/{quote_plus(query)}/")[:limit]

    def profile(self, target, **_):
        u = target.rstrip("/").split("/")[-1].lstrip("@")
        _f, html = _browser.load_html("tradingview", f"{BASE}/u/{u}/", wait="networkidle")
        md, meta = web.extract_markdown(html)
        return profile_record("tradingview", f"tradingview:user:{u.lower()}", u, display_name=meta.get("title") or u, avatar_url=meta.get("image"), bio=(meta.get("description") or md[:300]) or None, profile_url=f"{BASE}/u/{u}/")

    def list(self, source, *, limit=20, cursor=None, since=None, **_):
        if source.startswith("http") or "/" in source:
            url = source if source.startswith("http") else f"{BASE}/symbols/{source.replace(':', '-')}/ideas/"
            src = f"tradingview:symbol:{source}"
        else:
            url, src = f"{BASE}/u/{source.lstrip('@')}/#published-charts", f"tradingview:user:{source.lstrip('@').lower()}"
        return list_result(self._links(url)[:limit], None, {"id": src})

    def fetch(self, item, **_):
        final, html = _browser.load_html("tradingview", item, wait="networkidle", scrolls=1)
        return build_record(final, parse_page(html, final), save_raw("tradingview", native_id(final), html, "html"))
