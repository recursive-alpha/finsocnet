"""Terminal rendering of the JSON envelope for people (`--ui`; specs/13-cli-ui-and-web.md §1).

Every command keeps its single JSON envelope as the default. With `--ui` (or FINSOCNET_UI=1) the same data is drawn with rich: tables for
lists and search hits, panels for one record, key/value blocks for stats. Nothing here changes exit codes, and the data shown is exactly
the `data` field of the envelope.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

TYPE_STYLE = {"cards": "bold cyan", "contents": "green", "persons": "magenta", "skills": "yellow"}
PREFERRED = ["id", "ref", "name", "canonical_name", "title", "subject", "kind", "type", "category", "status", "platform", "action", "author_handle", "visited", "known",
             "score", "evidence_level", "persons", "cards", "claim", "reason", "target", "priority", "published_at", "updated_at"]
HIDDEN = {"extra_json", "metrics_json", "links_json", "mentions_json", "media_json", "locator_json", "snapshot_json"}


def console() -> Console:
    """Width follows the terminal (COLUMNS, or 120 when output is piped); colours only on a real terminal unless FINSOCNET_UI_COLOR is set."""
    import shutil
    width = int(os.getenv("COLUMNS") or shutil.get_terminal_size((120, 24)).columns)
    return Console(width=max(width, 100), force_terminal=bool(os.getenv("FINSOCNET_UI_COLOR")) or None, highlight=False)


def _short(v: Any, n: int = 70) -> str:
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "✓" if v else "·"
    if isinstance(v, float):
        return f"{v:.3f}".rstrip("0").rstrip(".")
    if isinstance(v, (list, tuple)):
        return ", ".join(_short(x, n) for x in v[:4]) + (" …" if len(v) > 4 else "")
    if isinstance(v, dict):
        return ", ".join(f"{k}={_short(x, 18)}" for k, x in list(v.items())[:3])
    s = " ".join(str(v).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def table_of(rows: list[dict[str, Any]], title: str | None = None, max_cols: int = 7) -> Table:
    keys: list[str] = []
    for k in PREFERRED:
        if any(k in r for r in rows if isinstance(r, dict)) and k not in HIDDEN:
            keys.append(k)
    for r in rows:
        for k, v in (r.items() if isinstance(r, dict) else []):
            if k not in keys and k not in HIDDEN and not isinstance(v, (dict, list)) and len(keys) < max_cols:
                keys.append(k)
    keys = keys[:max_cols]
    t = Table(title=title, box=box.SIMPLE_HEAD, header_style="bold", show_lines=False, pad_edge=False)
    for k in keys:
        t.add_column(k, overflow="ellipsis", no_wrap=k not in ("title", "subject", "claim", "snippet", "reason"), max_width=64 if k in ("claim", "snippet") else 40)
    for r in rows:
        t.add_row(*[_short(r.get(k), 90 if k in ("claim", "snippet") else 48) for k in keys])
    return t


def kv_table(d: dict[str, Any], title: str | None = None) -> Table:
    t = Table(title=title, box=box.SIMPLE, show_header=False, pad_edge=False)
    t.add_column(style="dim")
    t.add_column()
    for k, v in d.items():
        if k in HIDDEN:
            continue
        t.add_row(str(k), _short(v, 110))
    return t


def _bar(x: float, width: int = 8) -> str:
    n = max(0, min(width, round(x * width)))
    return "█" * n + "░" * (width - n)


# --- renderers --------------------------------------------------------------------------------------------------------

def r_search(data: dict[str, Any]) -> list[Any]:
    out: list[Any] = []
    facets = "  ".join(f"[{TYPE_STYLE.get(t, 'white')}]{t}[/] {n}" for t, n in (data.get("facets") or {}).items())
    out.append(Text.from_markup(f"[bold]“{data['query']}”[/]  mode [bold]{data.get('mode')}[/]  {facets}  · {data.get('total')} hits"))
    if data.get("filters"):
        out.append(Text(f"filters: {_short(data['filters'], 160)}", style="dim"))
    t = Table(box=box.SIMPLE_HEAD, header_style="bold", pad_edge=False, expand=True)
    t.add_column("#", width=3, no_wrap=True)
    t.add_column("type", width=15, no_wrap=True, overflow="ellipsis")
    t.add_column("match", width=13, no_wrap=True)
    t.add_column("title", ratio=2, overflow="ellipsis", no_wrap=True)
    t.add_column("snippet", ratio=3, overflow="ellipsis", no_wrap=True)
    t.add_column("id", width=12, no_wrap=True, overflow="ellipsis")
    for i, h in enumerate(data.get("results", []), 1):
        extra = h.get("meta", {})
        tag = extra.get("kind") or extra.get("platform") or extra.get("category") or ""
        t.add_row(str(i), Text(f"{h['type']}" + (f"/{tag}" if tag else ""), style=TYPE_STYLE.get(h["type"], "white")), _bar(h.get("relevance", 0)) + f" {h.get('relevance', 0):.2f}",
                  _short(h.get("title"), 200), _short((h.get("snippet") or "").replace("«", "").replace("»", ""), 300), _short(h["id"], 40))
    out.append(t)
    return out


def r_card_search(data: dict[str, Any]) -> list[Any]:
    t = Table(box=box.SIMPLE_HEAD, header_style="bold", pad_edge=False)
    for c in ("id", "score", "kind", "action", "subject", "who"):
        t.add_column(c, overflow="ellipsis", max_width=60 if c == "subject" else 28)
    for r in data.get("results", []):
        c = r["card"]
        who = ", ".join(x.get("person_name") or x.get("author_handle") or "?" for x in r.get("citations", [])[:2])
        t.add_row(str(c["id"]), f"{r['score']:.3f}", c["kind"], c["action"], _short(c["subject"], 60), who)
    return [Text(f"mode {data.get('mode', '?')} · terms {_short(data.get('terms_used'), 100)}", style="dim"), t]


def r_card_get(c: dict[str, Any]) -> list[Any]:
    body = Group(Text(c.get("claim", ""), style="bold"), Text(""), kv_table({k: c.get(k) for k in ("kind", "category", "action", "horizon", "evidence_level", "status", "terms", "aliases", "conditions", "numbers") if c.get(k) not in (None, [], {})}))
    out: list[Any] = [Panel(body, title=f"card #{c.get('id')} · {c.get('subject')}", border_style="cyan")]
    if c.get("citations"):
        t = Table(box=box.SIMPLE_HEAD, header_style="bold", pad_edge=False, title="citations")
        for col in ("who", "role", "quote", "from"):
            t.add_column(col, overflow="fold", max_width=70 if col == "quote" else 28)
        for x in c["citations"]:
            t.add_row(_short(x.get("person_name") or x.get("author_handle"), 26), _short(x.get("speaker_role"), 12), _short(x.get("quote"), 150), _short(x.get("content_title") or x.get("content_id"), 28))
        out.append(t)
    if c.get("links"):
        out.append(table_of(c["links"], "links"))
    return out


def r_person_get(p: dict[str, Any]) -> list[Any]:
    head = {k: p.get(k) for k in ("id", "moniker", "bio", "trading_style", "primary_markets", "avatar_path", "visibility", "status") if p.get(k)}
    out: list[Any] = [Panel(kv_table(head), title=f"{p.get('canonical_name')}", border_style="magenta")]
    if p.get("stats"):
        out.append(kv_table(p["stats"], "stats"))
    for key in ("aliases", "images", "sources", "appearances"):
        if p.get(key):
            out.append(table_of(p[key][:15], key))
    return out


def r_content_view(d: dict[str, Any]) -> list[Any]:
    return [Text(d.get("text", ""))]


def r_items(d: dict[str, Any]) -> list[Any]:
    out: list[Any] = []
    if d.get("source"):
        out.append(Text(f"source {d['source'].get('id')}  ·  next cursor {d.get('next_cursor')}", style="dim"))
    if d.get("hidden_known"):
        out.append(Text(f"{d['hidden_known']} already-known item(s) hidden (--new-only)", style="dim"))
    out.append(table_of(d.get("items", []), None, 7))
    return out


def r_generic(data: Any) -> list[Any]:
    if isinstance(data, list):
        return [table_of(data)] if data and isinstance(data[0], dict) else [Syntax(json.dumps(data, ensure_ascii=False, indent=1, default=str), "json")]
    if isinstance(data, str):
        return [Text(data)]
    if not isinstance(data, dict):
        return [Text(str(data))]
    out: list[Any] = []
    scalars = {k: v for k, v in data.items() if not isinstance(v, (list, dict))}
    if scalars:
        out.append(kv_table(scalars))
    for k, v in data.items():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            out.append(table_of(v, k))
        elif isinstance(v, list) and v:
            out.append(Text(f"{k}: {_short(v, 160)}"))
        elif isinstance(v, dict) and v:
            if all(not isinstance(x, (dict, list)) for x in v.values()):
                out.append(kv_table(v, k))
            else:
                out.append(Panel(Syntax(json.dumps(v, ensure_ascii=False, indent=1, default=str)[:3000], "json"), title=k, border_style="dim"))
    return out or [Text("(empty)")]


ROUTES = {"kb.search": r_search, "kb.card.search": r_card_search, "kb.card.get": r_card_get, "kb.person.get": r_person_get, "kb.content.view": r_content_view}


def render_success(command: str, data: Any, warnings: list[str] | None, meta: dict[str, Any] | None) -> None:
    c = console()
    c.print(Rule(Text(f" {command} ", style="bold"), style="dim", align="left"))
    fn = ROUTES.get(command)
    if fn is None and isinstance(data, dict) and isinstance(data.get("items"), list) and data["items"] and isinstance(data["items"][0], dict) and "ref" in data["items"][0]:
        fn = r_items
    for part in (fn or r_generic)(data):
        c.print(part)
    for w in warnings or []:
        c.print(Text(f"! {w}", style="yellow"))
    if meta and meta.get("elapsed_ms") is not None:
        c.print(Text(f"{meta['elapsed_ms']} ms", style="dim"), justify="right")


def render_failure(command: str, code: str, message: str, hint: str | None, retry_after_sec: int | None, details: list[dict[str, Any]] | None) -> None:
    c = console()
    lines = [Text(message, style="bold red")]
    if hint:
        lines.append(Text(f"→ {hint}", style="yellow"))
    if retry_after_sec:
        lines.append(Text(f"retry after {retry_after_sec}s", style="dim"))
    for d in details or []:
        lines.append(Text(f"  {d.get('path', '')}  {d.get('problem', '')}", style="dim"))
    c.print(Panel(Group(*lines), title=f"{command} · {code}", border_style="red"))
