"""StockTwits (specs/05 §4). The public API answers 403 to plain HTTP clients (checked 2026-10-28), so every call
goes through the agent browser, which loads the JSON endpoints like a page."""

from __future__ import annotations

import json
from typing import Any

from finsocnet.core import browser
from finsocnet.core.output import CliError
from finsocnet.core.platform import PlatformAdapter, content_record, item_ref, list_result, profile_record, save_raw
from finsocnet.core.segments import refs

API = "https://api.stocktwits.com/api/2"


def parse_message(m: dict[str, Any]) -> dict[str, Any]:
    u = m.get("user") or {}
    return {"seq": 0, "kind": "post", "locator": {"comment_id": str(m["id"])}, "author": {"handle": u.get("username"), "platform_user_id": str(u.get("id") or "") or None},
            "text": m.get("body", "")}


def message_record(m: dict[str, Any], raw_path: str | None) -> dict[str, Any]:
    seg = parse_message(m)
    r = refs(seg["text"])
    syms = [s["symbol"] for s in m.get("symbols", [])]
    sentiment = ((m.get("entities") or {}).get("sentiment") or {}).get("basic")
    return content_record(f"stocktwits:{m['id']}", "stocktwits", "post", [seg], url=f"https://stocktwits.com/{(m.get('user') or {}).get('username')}/message/{m['id']}",
                          author={"handle": (m.get("user") or {}).get("username")}, published_at=m.get("created_at"), language="en",
                          metrics={"likes": (m.get("likes") or {}).get("total")}, links=r["links"], mentions=list(dict.fromkeys(r["mentions"] + [f"${s}" for s in syms])),
                          raw_path=raw_path, fetch_method="browser_json", extra={"symbols": syms, "sentiment": sentiment},
                          source={"id": f"stocktwits:user:{(m.get('user') or {}).get('username', '').lower()}", "kind": "user", "title": (m.get("user") or {}).get("username")})


def stream_refs(d: dict[str, Any]) -> list[dict[str, Any]]:
    return [item_ref(f"https://stocktwits.com/{(m.get('user') or {}).get('username')}/message/{m['id']}", f"stocktwits:{m['id']}", "post", None, (m.get("user") or {}).get("username"),
                     m.get("created_at"), m.get("body"), {"likes": (m.get("likes") or {}).get("total")}) for m in d.get("messages", [])]


def _json(url: str) -> Any:
    with browser.page("stocktwits", block=("media", "font", "image")) as pg:
        pg.goto(url, wait_until="domcontentloaded")
        browser.check_page("stocktwits", pg)
        try:
            return json.loads(pg.inner_text("body"))
        except ValueError as e:
            raise CliError("CHECKPOINT", "StockTwits did not return JSON (bot check?)", "open it once in the agent browser: agent_browser.py open https://stocktwits.com") from e


class StockTwits(PlatformAdapter):
    platform = "stocktwits"
    capabilities = frozenset({"search", "profile", "list", "fetch"})

    def search(self, query, *, limit=20, since=None, **_):
        return self._symbol(query.lstrip("$").upper(), limit)

    def _symbol(self, sym: str, limit: int) -> list[dict[str, Any]]:
        return stream_refs(_json(f"{API}/streams/symbol/{sym}.json"))[:limit]

    def profile(self, target, **_):
        name = target.rsplit("/", 1)[-1].lstrip("@")
        u = _json(f"{API}/streams/user/{name}.json").get("user", {})
        return profile_record("stocktwits", f"stocktwits:user:{name.lower()}", name, display_name=u.get("name"), bio=u.get("bio"), followers=u.get("followers"), verified=u.get("official"),
                              avatar_url=u.get("avatar_url"), profile_url=f"https://stocktwits.com/{name}", joined_at=(u.get("join_date") or "")[:10] or None)

    def list(self, source, *, limit=50, cursor=None, since=None, **_):
        if source.startswith("$") or source.isupper():
            sym = source.lstrip("$")
            url, src = f"{API}/streams/symbol/{sym}.json" + (f"?max={cursor}" if cursor else ""), f"stocktwits:symbol:{sym}"
        else:
            name = source.lstrip("@")
            url, src = f"{API}/streams/user/{name}.json" + (f"?max={cursor}" if cursor else ""), f"stocktwits:user:{name.lower()}"
        d = _json(url)
        items = [i for i in stream_refs(d) if not since or (i["published_at"] or "")[:10] >= since][:limit]
        return list_result(items, str((d.get("cursor") or {}).get("max")) if (d.get("cursor") or {}).get("more") else None, {"id": src})

    def fetch(self, item, **_):
        mid = item.rsplit("/", 1)[-1].replace("stocktwits:", "")
        d = _json(f"{API}/messages/show/{mid}.json")
        return message_record(d["message"], save_raw("stocktwits", mid, d))
