"""DuckDuckGo web search via ddgs (docs/spec/05 §2.8). Search only; use web-reader to read a result."""

from __future__ import annotations

import time
from typing import Any

from finsocnet.core import budgets, ids
from finsocnet.core.db import connect
from finsocnet.core.output import CliError
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
        last: Exception | None = None
        for attempt in range(2):  # the backend fans out to several engines; one flaky engine should not fail the call
            try:
                rows = d.news(q, region=region, timelimit=timelimit, max_results=limit) if news else d.text(q, region=region, timelimit=timelimit, max_results=limit)
                return [to_ref(r) for r in rows][:limit]
            except Exception as e:  # noqa: BLE001 - ddgs raises DDGSException / TimeoutException / RatelimitException
                last = e
                if "No results found" in str(e) and "DNSError" not in str(e):
                    return []
                time.sleep(2 + attempt * 3)
        raise CliError("RATE_LIMITED", f"web search backend failed: {str(last).splitlines()[0][:200]}", hint="The search engines throttled or were unreachable; retry later or use google-searcher / a platform skill's own search.", retry_after_sec=120) from None
