"""DuckDuckGo web search via ddgs (docs/spec/05 §2.8). Search only; use web-reader to read a result."""

from __future__ import annotations

from typing import Any

from finsocnet.core import budgets, ids
from finsocnet.core.db import connect
from finsocnet.core.platform import PlatformAdapter, item_ref


def to_ref(r: dict[str, Any]) -> dict[str, Any]:
    url = r.get("href") or r.get("url") or ""
    return item_ref(url, ids.web_content_id(url), "page", r.get("title"), r.get("source"), r.get("date"), r.get("body") or r.get("excerpt"))


class WebSearch(PlatformAdapter):
    platform = "web"
    capabilities = frozenset({"search"})
    opts = {"search": [(("--region",), {"default": "wt-wt"}), (("--timelimit",), {"choices": ["d", "w", "m", "y"]}), (("--site",), {}), (("--news",), {"action": "store_true"})]}

    def search(self, query, *, limit=20, since=None, region="wt-wt", timelimit=None, site=None, news=False, **_):
        from ddgs import DDGS
        try:
            conn = connect()
            try:
                budgets.charge(conn, "web")
            finally:
                conn.close()
        except Exception:  # noqa: BLE001
            pass
        q = f"site:{site} {query}" if site else query
        d = DDGS()
        rows = d.news(q, region=region, timelimit=timelimit, max_results=limit) if news else d.text(q, region=region, timelimit=timelimit, max_results=limit)
        return [to_ref(r) for r in rows][:limit]
