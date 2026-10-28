"""Google Web/News search through the agent browser (specs/05 §2.9). Strict budget; CAPTCHA pages exit 3."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, quote_plus, urlsplit

from lxml import html as lhtml

from finsocnet.adapters import _browser
from finsocnet.core import ids
from finsocnet.core.platform import PlatformAdapter, item_ref

DATE_RE = re.compile(r"^(?:[A-Z][a-z]{2} \d{1,2}, \d{4}|\d+ (?:minutes?|hours?|days?|weeks?|months?) ago)")


def unwrap(href: str) -> str | None:
    if href.startswith("/url?"):
        q = parse_qs(urlsplit(href).query).get("q")
        return q[0] if q else None
    return href if href.startswith("http") and "google." not in urlsplit(href).netloc else None


def parse_results(html: str) -> list[dict[str, Any]]:
    """Organic results: an <a href> that wraps an <h3> inside #search/#rso; ads (data-text-ad, #tads) are ignored."""
    root = lhtml.fromstring(html)
    out, seen = [], set()
    for h3 in root.xpath("//div[@id='search' or @id='rso' or @id='main']//a[.//h3]/h3"):
        a = h3.getparent() if h3.getparent().tag == "a" else h3.xpath("ancestor::a[1]")[0]
        if a.xpath("ancestor::*[@data-text-ad or @id='tads' or @id='tadsb']"):
            continue
        url = unwrap(a.get("href", ""))
        if not url or url in seen:
            continue
        seen.add(url)
        block = h3.xpath("ancestor::div[.//div[@data-sncf or @class][string-length(normalize-space(.)) > 40]][1]")
        text = " ".join(block[0].text_content().split()) if block else ""
        title = h3.text_content().strip()
        snippet = text.replace(title, "", 1).strip()
        date = (DATE_RE.match(snippet) or [None])[0]
        out.append(item_ref(url, ids.web_content_id(url), "page", title, urlsplit(url).netloc, date, snippet))
    return out


class Google(PlatformAdapter):
    platform = "google"
    requires_session = False
    capabilities = frozenset({"search"})
    opts = {"search": [(("--news",), {"action": "store_true"})]}

    def search(self, query, *, limit=20, since=None, news=False, **_):
        url = f"https://www.google.com/search?q={quote_plus(query)}&num={min(limit, 50)}&hl=en"
        if news:
            url += "&tbm=nws"
        if since:
            d = datetime.fromisoformat(since)
            url += f"&tbs=cdr:1,cd_min:{d.month}/{d.day}/{d.year}"
        final, html = _browser.load_html("google", url, block=("media", "font", "image"))
        return parse_results(html)[:limit]
