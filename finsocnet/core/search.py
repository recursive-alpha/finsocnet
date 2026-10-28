"""Unified search over everything in the knowledge base (specs/10-semantic-search.md §5): cards, content text, persons, rulebooks.

One English query goes to the lexical index (SQLite FTS5, BM25) and the vector index (cosine over the stored embeddings) of every selected
data type; each type fuses its two rankings with RRF (the vector ranking counts double, as in `cards.retrieve`); filters apply per type; then
the types are merged: each hit's score is normalised to the best hit of its type and multiplied by a small type prior, so the strongest
results of every type interleave ("search all, then rank").
"""

from __future__ import annotations

import sqlite3
from typing import Any

from finsocnet.core import cards as cards_mod, embed, fts
from finsocnet.core.db import loads
from finsocnet.core.output import CliError

TYPES = ("cards", "contents", "persons", "skills")
PRIOR = {"cards": 1.0, "skills": 0.92, "persons": 0.88, "contents": 0.8}
VEC_WEIGHT = cards_mod.VEC_WEIGHT
K = 60
FILTERS = {"cards": ("kind", "category", "domain", "horizon", "evidence_level_min", "person_id", "instruments", "min_persons"),
           "contents": ("platform", "content_type", "person_id", "since", "language", "status"),
           "persons": (),
           "skills": ("person_id", "category")}


def _expr(query: str) -> str | None:
    return fts.match_any(fts.significant_words(query, 12))


def _rrf(lex: list[str], vec: list[str]) -> dict[str, tuple[float, dict[str, int]]]:
    out: dict[str, tuple[float, dict[str, int]]] = {}
    for src, ids, w in (("lex", lex, 1.0), ("vec", vec, VEC_WEIGHT)):
        for rank, ref in enumerate(ids, 1):
            sc, rk = out.get(ref, (0.0, {}))
            rk[src] = rank
            out[ref] = (sc + w / (K + rank), rk)
    return out


def _use_vectors(conn: sqlite3.Connection, mode: str, kind: str, warnings: list[str]) -> bool:
    if mode == "lexical":
        return False
    have = embed.has_vectors(conn, kind)
    if mode in ("semantic", "hybrid") and not have:
        warnings.append(f"no {kind} embeddings for model {embed.model_id()}: run `finsocnet kb embed sync --kinds {kind}`; that type is searched lexically")
    return have


def _cards(conn: sqlite3.Connection, q: str, mode: str, f: dict[str, Any], limit: int, warnings: list[str]) -> list[dict[str, Any]]:
    flt = {k: v for k, v in f.items() if k in FILTERS["cards"] and v not in (None, [], "")}
    for k in ("kind", "category", "domain", "horizon", "instruments", "person_id"):
        if k in flt and not isinstance(flt[k], list):
            flt[k] = [flt[k]]
    r = cards_mod.search_cards(conn, None, q, limit, mode, flt or None)
    warnings.extend(w for w in r["warnings"] if "does not look like English" not in w)
    out = []
    for h in r["results"]:
        c, cit = h["card"], h["citations"]
        out.append({"type": "cards", "id": str(c["id"]), "title": c["subject"], "snippet": c["claim"], "score": h["score"], "ranks": h["score_debug"],
                    "meta": {"kind": c["kind"], "category": c["category"], "action": c["action"], "evidence_level": c["evidence_level"], "persons": h["stats"].get("persons"),
                             "citations": h["stats"].get("citations"), "who": [x.get("person_name") or x.get("author_handle") for x in cit if x.get("person_name") or x.get("author_handle")][:3]}})
    return out


def _contents(conn: sqlite3.Connection, q: str, mode: str, f: dict[str, Any], limit: int, warnings: list[str]) -> list[dict[str, Any]]:
    lex_hits: dict[str, tuple[int, str]] = {}
    lex_order: list[str] = []
    expr = _expr(q)
    if mode != "semantic" and expr:
        for r in conn.execute("""SELECT s.content_id, s.seq, snippet(segments_fts, 0, '«', '»', ' … ', 28) AS snip FROM segments_fts
                                 JOIN content_segments s ON s.id = segments_fts.rowid WHERE segments_fts MATCH ? ORDER BY bm25(segments_fts) LIMIT 300""", (expr,)):
            if r["content_id"] not in lex_hits:
                lex_hits[r["content_id"]] = (r["seq"], r["snip"])
                lex_order.append(r["content_id"])
    vec_order: list[str] = []
    vec_seq: dict[str, int] = {}
    if _use_vectors(conn, mode, "segment", warnings):
        for h in embed.vector_search(conn, q, ["segment"], 200):
            cid, _, seq = h["ref"].rpartition("#")
            if cid not in vec_seq:
                vec_seq[cid] = int(seq)
                vec_order.append(cid)
    fused = _rrf(lex_order, vec_order)
    out = []
    for cid, (score, ranks) in sorted(fused.items(), key=lambda kv: -kv[1][0]):
        row = conn.execute("SELECT id, platform, content_type, title, url, author_handle, person_id, published_at, language, process_status FROM contents WHERE id = ?", (cid,)).fetchone()
        if row is None or not _content_ok(row, f):
            continue
        seq = lex_hits.get(cid, (vec_seq.get(cid, 0), None))[0]
        snip = lex_hits.get(cid, (0, None))[1]
        if snip is None:
            snip = (conn.execute("SELECT text FROM content_segments WHERE content_id = ? AND seq = ?", (cid, seq)).fetchone() or [""])[0][:240]
        out.append({"type": "contents", "id": cid, "title": row["title"] or cid, "snippet": snip, "score": score, "ranks": ranks, "url": row["url"],
                    "meta": {"platform": row["platform"], "content_type": row["content_type"], "author": row["author_handle"], "published_at": row["published_at"], "segment": seq, "status": row["process_status"]}})
        if len(out) >= limit:
            break
    return out


def _content_ok(r: sqlite3.Row, f: dict[str, Any]) -> bool:
    if f.get("platform") and r["platform"] not in _as_list(f["platform"]):
        return False
    if f.get("content_type") and r["content_type"] not in _as_list(f["content_type"]):
        return False
    if f.get("person_id") and r["person_id"] not in _as_list(f["person_id"]):
        return False
    if f.get("language") and not (r["language"] or "").lower().startswith(str(f["language"]).lower()):
        return False
    if f.get("status") and r["process_status"] not in _as_list(f["status"]):
        return False
    if f.get("since") and (r["published_at"] or "")[:10] < str(f["since"])[:10]:
        return False
    return True


def _as_list(v: Any) -> list[Any]:
    return v if isinstance(v, list) else [v]


def _persons(conn: sqlite3.Connection, q: str, mode: str, f: dict[str, Any], limit: int, warnings: list[str]) -> list[dict[str, Any]]:
    lex: list[str] = []
    expr = _expr(q)
    if mode != "semantic" and expr:
        lex = [r[0] for r in conn.execute("SELECT person_id FROM persons_fts WHERE persons_fts MATCH ? ORDER BY bm25(persons_fts) LIMIT 100", (expr,))]
    vec = [h["ref"] for h in embed.vector_search(conn, q, ["person"], 100)] if _use_vectors(conn, mode, "person", warnings) else []
    out = []
    for pid, (score, ranks) in sorted(_rrf(lex, vec).items(), key=lambda kv: -kv[1][0]):
        p = conn.execute("SELECT p.id, p.canonical_name, p.bio, p.trading_style, p.primary_markets, p.avatar_path, p.status, COALESCE(s.cards, 0) AS cards FROM persons p "
                         "LEFT JOIN person_stats s ON s.person_id = p.id WHERE p.id = ?", (pid,)).fetchone()
        if p is None or p["status"] != "active":
            continue
        out.append({"type": "persons", "id": pid, "title": p["canonical_name"], "snippet": (p["trading_style"] or p["bio"] or "")[:240], "score": score, "ranks": ranks,
                    "meta": {"cards": p["cards"], "markets": p["primary_markets"], "avatar_path": p["avatar_path"]}})
        if len(out) >= limit:
            break
    return out


def _skills(conn: sqlite3.Connection, q: str, mode: str, f: dict[str, Any], limit: int, warnings: list[str]) -> list[dict[str, Any]]:
    lex: list[str] = []
    expr = _expr(q)
    if mode != "semantic" and expr:
        lex = [str(r[0]) for r in conn.execute("SELECT rowid FROM person_skills_fts WHERE person_skills_fts MATCH ? ORDER BY bm25(person_skills_fts) LIMIT 100", (expr,))]
    vec = [h["ref"] for h in embed.vector_search(conn, q, ["skill"], 100)] if _use_vectors(conn, mode, "skill", warnings) else []
    out = []
    for sid, (score, ranks) in sorted(_rrf(lex, vec).items(), key=lambda kv: -kv[1][0]):
        s = conn.execute("SELECT k.id, k.person_id, k.category, k.title, k.summary, p.canonical_name FROM person_skills k JOIN persons p ON p.id = k.person_id WHERE k.id = ?", (int(sid),)).fetchone()
        if s is None:
            continue
        if f.get("person_id") and s["person_id"] not in _as_list(f["person_id"]):
            continue
        if f.get("category") and s["category"] not in _as_list(f["category"]):
            continue
        out.append({"type": "skills", "id": str(s["id"]), "title": f"{s['canonical_name']} — {s['title']}", "snippet": (s["summary"] or "")[:240], "score": score, "ranks": ranks,
                    "meta": {"person_id": s["person_id"], "person": s["canonical_name"], "category": s["category"]}})
        if len(out) >= limit:
            break
    return out


_RUN = {"cards": _cards, "contents": _contents, "persons": _persons, "skills": _skills}


def search(conn: sqlite3.Connection, query: str, *, types: list[str] | None = None, mode: str = "auto", filters: dict[str, Any] | None = None,
           limit: int = 30, per_type: int | None = None) -> dict[str, Any]:
    """Search `types` (default: all), merge and rank. `mode`: auto | lexical | semantic | hybrid. Returns `{results, facets, mode, warnings}`."""
    query = (query or "").strip()
    if not query:
        raise CliError("USAGE", "give a query")
    if mode not in ("auto", "lexical", "semantic", "hybrid"):
        raise CliError("USAGE", f"unknown mode {mode!r}", "auto | lexical | semantic | hybrid")
    types = list(types or TYPES)
    bad = [t for t in types if t not in TYPES]
    if bad:
        raise CliError("USAGE", f"unknown type(s) {', '.join(bad)}", f"one of {', '.join(TYPES)}")
    filters = {k: v for k, v in (filters or {}).items() if v not in (None, "", [])}
    ignored = sorted(k for k in filters if not any(k in FILTERS[t] for t in types))
    warnings: list[str] = [f"filter(s) {', '.join(ignored)} do not apply to the selected types and were ignored"] if ignored else []
    cap = per_type or max(limit, 30)
    merged: list[dict[str, Any]] = []
    facets: dict[str, int] = {}
    for t in types:
        # a filter that only exists for other types removes this type when it is the only constraint set for it
        hits = _RUN[t](conn, query, mode, filters, cap, warnings)
        facets[t] = len(hits)
        top = max((h["score"] for h in hits), default=1.0) or 1.0
        for h in hits:
            h["relevance"] = round(PRIOR[t] * h["score"] / top, 4)
            h["score"] = round(h["score"], 6)
        merged.extend(hits)
    merged.sort(key=lambda h: (-h["relevance"], h["type"], h["id"]))
    effective = mode if mode != "auto" else ("hybrid" if embed.has_vectors(conn, "card") or embed.has_vectors(conn, "segment") else "lexical")
    return {"query": query, "mode": effective, "types": types, "filters": filters, "total": len(merged), "facets": facets, "results": merged[:limit], "warnings": warnings}
