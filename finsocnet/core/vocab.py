"""Controlled vocabulary (specs/02-knowledge-cards.md §4, 01 §2.4). Makes lexical search work without embeddings."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from finsocnet.core import fts
from finsocnet.core.db import dumps, loads, transaction
from finsocnet.core.normalize import alias_key, strip_diacritics
from finsocnet.core.output import CliError

FACETS = ("indicator pattern setup order_type timeframe metric concept instrument market event risk psychology "
          "process asset_class data tool").split()
TERM_RE = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")


def surface_key(text: str) -> str:
    """Comparison key for aliases/labels/phrases: casefold, no diacritics, punctuation → space, collapsed."""
    t = strip_diacritics(text.casefold())
    t = re.sub(r"[^\w\s]|_", " ", t)
    return " ".join(t.split())


def _row(r: sqlite3.Row) -> dict[str, Any]:
    return {"term": r["term"], "label": r["label"], "facet": r["facet"], "aliases": loads(r["aliases_json"], []),
            "broader": r["broader"], "definition": r["definition"], "status": r["status"], "merged_into": r["merged_into"]}


def get(conn: sqlite3.Connection, term: str) -> dict[str, Any] | None:
    r = conn.execute("SELECT * FROM vocabulary WHERE term = ?", (term,)).fetchone()
    return _row(r) if r else None


def resolve(conn: sqlite3.Connection, term: str) -> dict[str, Any] | None:
    """The active entry for a term, following `merged_into` chains."""
    seen = set()
    e = get(conn, term)
    while e and e["status"] == "merged" and e["merged_into"] and e["term"] not in seen:
        seen.add(e["term"])
        e = get(conn, e["merged_into"])
    return e if e and e["status"] == "active" else None


def surface_index(conn: sqlite3.Connection) -> dict[str, str]:
    """surface_key(alias | label | term words) → term, for active terms (exact matching of phrases)."""
    idx: dict[str, str] = {}
    for r in conn.execute("SELECT term, label, aliases_json FROM vocabulary WHERE status = 'active'"):
        for s in [r["label"], r["term"].replace("_", " "), *loads(r["aliases_json"], [])]:
            idx.setdefault(surface_key(s), r["term"])
    return idx


def lookup(conn: sqlite3.Connection, phrase: str, limit: int = 5) -> list[dict[str, Any]]:
    """Match order: exact term, exact alias, label, FTS."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def push(entry: dict[str, Any] | None, how: str) -> None:
        if entry and entry["term"] not in seen:
            seen.add(entry["term"])
            out.append({**{k: entry[k] for k in ("term", "label", "facet", "aliases", "broader")}, "match": how})

    key = surface_key(phrase)
    snake = "_".join(key.split())
    push(resolve(conn, snake) if TERM_RE.match(snake) else None, "exact_term")
    rows = conn.execute("SELECT * FROM vocabulary WHERE status = 'active'").fetchall()
    for r in rows:
        if any(surface_key(a) == key for a in loads(r["aliases_json"], [])):
            push(_row(r), "exact_alias")
    for r in rows:
        if surface_key(r["label"]) == key:
            push(_row(r), "label")
    expr = fts.match_text(" ".join(fts.significant_words(phrase)) or phrase, "or")
    if expr and len(out) < limit:
        try:
            for r in conn.execute(
                "SELECT v.* FROM vocabulary_fts f JOIN vocabulary v ON v.rowid = f.rowid "
                "WHERE vocabulary_fts MATCH ? AND v.status = 'active' ORDER BY bm25(vocabulary_fts, 4.0, 3.0, 2.0, 1.0) LIMIT ?",
                (expr, limit * 2),
            ):
                push(_row(r), "fts")
        except sqlite3.OperationalError:
            pass
    return out[:limit]


def suggest(conn: sqlite3.Connection, term: str) -> str | None:
    """Best replacement for an unknown term: its merged target, or the best lookup match."""
    e = get(conn, term)
    if e and e["status"] == "merged":
        r = resolve(conn, term)
        return r["term"] if r else None
    hits = lookup(conn, term.replace("_", " "), 3)
    if hits:
        return hits[0]["term"]
    squashed = re.sub(r"[^a-z0-9]", "", term.lower())
    for r in conn.execute("SELECT term FROM vocabulary WHERE status = 'active'"):
        if re.sub(r"[^a-z0-9]", "", r["term"]) == squashed:
            return r["term"]
    return None


def add(conn: sqlite3.Connection, items: list[dict[str, Any]], run_id: int) -> dict[str, Any]:
    """Add terms. A batch is all-or-nothing; `broader` may point to a term in the same batch."""
    details: list[dict[str, Any]] = []
    owners: dict[str, str] = {}
    for r in conn.execute("SELECT term, label, aliases_json FROM vocabulary WHERE status = 'active'"):
        for s in [r["label"], *loads(r["aliases_json"], [])]:
            owners.setdefault(surface_key(s), r["term"])
    existing = {r[0] for r in conn.execute("SELECT term FROM vocabulary")}
    batch_terms = {i.get("term") for i in items}
    seen_terms: set[str] = set()
    for n, it in enumerate(items):
        path = f"/{n}"
        t = it.get("term", "")
        if not isinstance(t, str) or not TERM_RE.match(t):
            details.append({"path": f"{path}/term", "problem": f"invalid term key {t!r} (snake_case, lowercase ASCII)"})
            continue
        if t in existing or t in seen_terms:
            details.append({"path": f"{path}/term", "problem": f"term {t!r} already exists", "suggestion": "use `kb vocab update`"})
            continue
        seen_terms.add(t)
        if it.get("facet") not in FACETS:
            details.append({"path": f"{path}/facet", "problem": f"facet must be one of {', '.join(FACETS)}"})
        if not it.get("label"):
            details.append({"path": f"{path}/label", "problem": "label is required"})
        b = it.get("broader")
        if b and b not in existing and b not in batch_terms:
            details.append({"path": f"{path}/broader", "problem": f"broader term {b!r} does not exist", "suggestion": suggest(conn, b)})
        for a in [it.get("label", ""), *it.get("aliases", [])]:
            k = surface_key(a)
            if k in owners and owners[k] != t:
                details.append({"path": f"{path}/aliases", "problem": f"{a!r} is already owned by term {owners[k]!r}", "suggestion": owners[k]})
            else:
                owners.setdefault(k, t)
    if details:
        raise CliError("VALIDATION_ERROR", f"vocabulary batch rejected ({len(details)} problem(s))", details=details)

    pending = [i for i in items]
    inserted: list[str] = []
    with transaction(conn):
        known = set(existing)
        while pending:
            progress = False
            for it in list(pending):
                if not it.get("broader") or it["broader"] in known:
                    conn.execute(
                        "INSERT INTO vocabulary (term, label, facet, aliases_json, broader, definition, run_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (it["term"], it["label"], it["facet"], dumps(it.get("aliases", [])), it.get("broader"), it.get("definition"), run_id),
                    )
                    known.add(it["term"])
                    inserted.append(it["term"])
                    pending.remove(it)
                    progress = True
            if not progress:
                raise CliError("VALIDATION_ERROR", "circular broader references in batch", details=[{"path": "/", "problem": ", ".join(i["term"] for i in pending)}])
    return {"added": inserted}


def update(conn: sqlite3.Connection, term: str, patch: dict[str, Any], run_id: int) -> dict[str, Any]:
    cur = get(conn, term)
    if cur is None:
        raise CliError("NOT_FOUND", f"term {term} not found")
    allowed = {"label", "facet", "aliases", "aliases_add", "broader", "definition"}
    bad = set(patch) - allowed
    if bad:
        raise CliError("VALIDATION_ERROR", f"cannot update field(s): {', '.join(sorted(bad))}")
    aliases = list(cur["aliases"])
    if "aliases" in patch:
        aliases = list(patch["aliases"])
    for a in patch.get("aliases_add", []):
        if a not in aliases:
            aliases.append(a)
    for r in conn.execute("SELECT term, label, aliases_json FROM vocabulary WHERE status = 'active' AND term <> ?", (term,)):
        owned = {surface_key(s) for s in [r["label"], *loads(r["aliases_json"], [])]}
        for a in aliases:
            if surface_key(a) in owned:
                raise CliError("VALIDATION_ERROR", f"alias {a!r} is already owned by term {r['term']!r}",
                               details=[{"path": "/aliases", "problem": "owned by another term", "suggestion": r["term"]}])
    if patch.get("facet") and patch["facet"] not in FACETS:
        raise CliError("VALIDATION_ERROR", f"facet must be one of {', '.join(FACETS)}")
    if patch.get("broader") and not get(conn, patch["broader"]):
        raise CliError("VALIDATION_ERROR", f"broader term {patch['broader']!r} does not exist")
    with transaction(conn):
        conn.execute(
            "UPDATE vocabulary SET label = ?, facet = ?, aliases_json = ?, broader = ?, definition = ? WHERE term = ?",
            (patch.get("label", cur["label"]), patch.get("facet", cur["facet"]), dumps(aliases),
             patch.get("broader", cur["broader"]), patch.get("definition", cur["definition"]), term),
        )
    return get(conn, term) or {}


def merge(conn: sqlite3.Connection, src: str, dst: str, run_id: int) -> dict[str, Any]:
    """Merge `src` into `dst`: rewrite cards' terms/regime, move aliases, repoint `broader`."""
    a, b = get(conn, src), get(conn, dst)
    if a is None or b is None:
        raise CliError("NOT_FOUND", f"term {src if a is None else dst} not found")
    if src == dst or a["status"] != "active" or b["status"] != "active":
        raise CliError("VALIDATION_ERROR", "both terms must be distinct and active")
    changed = 0
    with transaction(conn):
        for c in conn.execute("SELECT id, terms_json, regime_json FROM knowledge_cards WHERE terms_json LIKE ? OR regime_json LIKE ?",
                              (f'%"{src}"%', f'%"{src}"%')).fetchall():
            terms, regime = loads(c["terms_json"], []), loads(c["regime_json"], [])
            if src not in terms and src not in regime:
                continue
            snap = conn.execute("SELECT * FROM knowledge_cards WHERE id = ?", (c["id"],)).fetchone()
            conn.execute("INSERT INTO card_history (card_id, snapshot_json, reason, run_id) VALUES (?, ?, ?, ?)",
                         (c["id"], dumps(dict(snap)), f"vocab merge {src} -> {dst}", run_id))
            nt = list(dict.fromkeys(dst if t == src else t for t in terms))
            nr = list(dict.fromkeys(dst if t == src else t for t in regime))
            conn.execute("UPDATE knowledge_cards SET terms_json = ?, regime_json = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id = ?",
                         (dumps(nt), dumps(nr), c["id"]))
            changed += 1
        moved = [x for x in [a["label"], *a["aliases"]] if surface_key(x) not in {surface_key(y) for y in [b["label"], *b["aliases"]]}]
        conn.execute("UPDATE vocabulary SET status = 'merged', merged_into = ?, aliases_json = '[]' WHERE term = ?", (dst, src))
        conn.execute("UPDATE vocabulary SET aliases_json = ? WHERE term = ?", (dumps(b["aliases"] + moved), dst))
        conn.execute("UPDATE vocabulary SET broader = ? WHERE broader = ?", (dst, src))
    return {"merged": src, "into": dst, "cards_rewritten": changed, "aliases_moved": moved}


def list_terms(conn: sqlite3.Connection, facet: str | None = None, status: str = "active") -> list[dict[str, Any]]:
    sql, args = "SELECT * FROM vocabulary WHERE status = ?", [status]
    if facet:
        sql += " AND facet = ?"
        args.append(facet)
    return [_row(r) for r in conn.execute(sql + " ORDER BY facet, term", args)]


def export(conn: sqlite3.Connection, out: str | Path) -> dict[str, Any]:
    rows = [{k: t[k] for k in ("term", "label", "facet", "aliases", "broader", "definition")} for t in list_terms(conn)]
    Path(out).write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"path": str(out), "terms": len(rows)}
