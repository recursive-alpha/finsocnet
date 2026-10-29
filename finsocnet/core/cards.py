"""Knowledge Cards: validation, candidate retrieval, search, atomic decision commit, merge/retire/update/undo.

Spec: specs/02-knowledge-cards.md, 03-pipelines.md §2–§3, 01-database.md §3. No embeddings, no LLM (ADR-001/002).
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from pathlib import Path
from typing import Any

from finsocnet.core import config, embed, fts, vocab
from finsocnet.core.db import dumps, loads, savepoint, transaction
from finsocnet.core.ids import parse_since, utc_now
from finsocnet.core.normalize import quote_in, quote_key
from finsocnet.core.output import CliError
from finsocnet.core.records import schema_errors
from finsocnet.core.runs import produced_by

GRAMMAR = {
    "rule": re.compile(r"^IF .+? THEN (EXIT_PARTIAL|LONG|SHORT|ADD|EXIT|AVOID|HOLD|SIZE)\b.+", re.DOTALL),
    "setup": re.compile(r"^IF .+? THEN (EXIT_PARTIAL|LONG|SHORT|ADD|EXIT|AVOID|HOLD|SIZE)\b.+", re.DOTALL),
    "observation": re.compile(r"^.+ TENDS TO .+ WHEN .+", re.DOTALL),
    "mechanism": re.compile(r"^.+ CAUSES .+ BECAUSE .+", re.DOTALL),
    "definition": re.compile(r"^[a-z0-9_]+ IS .+", re.DOTALL),
    "metric": re.compile(r"^.+ HAS [a-z0-9_]+ = .+", re.DOTALL),
    "practice": re.compile(r"^.+ (IMPROVES|HURTS) .+", re.DOTALL),
}
GRAMMAR_HINT = {
    "rule": "IF <conditions> THEN <ACTION> <object> … (ACTION: LONG SHORT ADD EXIT EXIT_PARTIAL AVOID HOLD SIZE)",
    "setup": "IF <conditions> THEN <ACTION> <object> …",
    "observation": "<subject> TENDS TO <outcome> WHEN <condition>",
    "mechanism": "<cause> CAUSES <effect> BECAUSE <reason>",
    "definition": "<term_key> IS <definition>",
    "metric": "<subject> HAS <metric_key> = <value>",
    "practice": "<practice> IMPROVES|HURTS <outcome>",
}
ACTION_RE = re.compile(r"\bTHEN (EXIT_PARTIAL|LONG|SHORT|ADD|EXIT|AVOID|HOLD|SIZE)\b")
TIMESTAMP_RE = re.compile(r"\[?\b\d{1,2}:\d{2}(:\d{2})?\b\]?")
EVIDENCE_ORDER = ["anecdotal", "claimed", "backtested", "audited"]
FILTER_FIELDS = ("kind", "domain", "category", "horizon")
CARD_JSON_FIELDS = {"conditions": "conditions_json", "instruments": "instruments_json", "regime": "regime_json",
                    "terms": "terms_json", "aliases": "aliases_json", "entities": "entities_json", "numbers": "numbers_json"}
SEG_LOOKAHEAD = 2
MAX_TERMS = 15


def transformer_version() -> str:
    """`metadata.version` of the knowledge-transformer SKILL.md (e.g. `kt-1.0`)."""
    p = config.repo_root() / ".agents" / "skills" / "knowledge-transformer" / "SKILL.md"
    try:
        m = re.search(r'^\s+version:\s*"?([^"\n]+)"?', p.read_text(encoding="utf-8"), re.M)
        return m.group(1).strip() if m else "kt-1.0"
    except OSError:
        return "kt-1.0"


# --- validation -----------------------------------------------------------------------------------------

def _problem(path: str, code: str, problem: str, suggestion: str | None = None) -> dict[str, Any]:
    d = {"path": path, "code": code, "problem": problem}
    if suggestion:
        d["suggestion"] = suggestion
    return d


def _term_surfaces(entry: dict[str, Any]) -> list[str]:
    return [entry["term"], entry["term"].replace("_", " "), entry["label"], *entry["aliases"]]


def validate_card(conn: sqlite3.Connection, card: dict[str, Any], legacy: bool = False) -> tuple[list[dict[str, Any]], list[str]]:
    """All checks of 02 §2.2, never short-circuited. Returns (problems, warnings)."""
    problems: list[dict[str, Any]] = []
    warnings: list[str] = []
    check = card
    cit = card.get("citation") if isinstance(card.get("citation"), dict) else {}
    legacy_cit = legacy and cit.get("segment_seq") is None
    if legacy_cit:
        check = {**card, "citation": {**cit, "segment_seq": 0}}
    for e in schema_errors("card", check):
        problems.append(_problem(e["path"], "VALIDATION_ERROR", e["problem"]))
    if not isinstance(card, dict) or not card.get("kind") in GRAMMAR:
        return problems, warnings

    claim = card.get("claim") or ""
    kind = card["kind"]
    if claim and not GRAMMAR[kind].match(claim):
        problems.append(_problem("/claim", "GRAMMAR_ERROR", f"claim does not match the {kind} grammar", GRAMMAR_HINT[kind]))
    elif claim and kind in ("rule", "setup"):
        m = ACTION_RE.search(claim)
        action = card.get("action")
        if m and action != m.group(1):
            problems.append(_problem("/action", "GRAMMAR_ERROR", f"first action after THEN is {m.group(1)} but action is {action!r}", m.group(1)))
    if claim and kind not in ("rule", "setup") and card.get("action") not in (None, "NONE"):
        problems.append(_problem("/action", "GRAMMAR_ERROR", f"{kind} cards must have action NONE or no action", "NONE"))

    terms = [t for t in card.get("terms", []) if isinstance(t, str)]
    regime = [t for t in card.get("regime", []) if isinstance(t, str)]
    entries: list[dict[str, Any]] = []
    for path, group in (("/terms", terms), ("/regime", regime)):
        for i, t in enumerate(group):
            e = vocab.get(conn, t)
            if e is not None and e["status"] == "active":
                if path == "/terms":
                    entries.append(e)
            else:
                problems.append(_problem(f"{path}/{i}", "VOCAB_UNKNOWN", f"unknown term '{t}'", vocab.suggest(conn, t)))

    haystack = vocab.surface_key(" ".join([claim, card.get("subject", ""), *card.get("conditions", [])]))
    if entries and not any(vocab.surface_key(s) and re.search(rf"(?<!\w){re.escape(vocab.surface_key(s))}(?!\w)", haystack)
                           for e in entries for s in _term_surfaces(e)):
        problems.append(_problem("/terms", "VALIDATION_ERROR", "no term (key, label or alias) appears in the claim, subject or conditions (tag stuffing?)",
                                 "use the surface words of the claim, or add them to aliases of the vocabulary term"))

    for field in ("subject", "claim"):
        if TIMESTAMP_RE.search(card.get(field) or ""):
            problems.append(_problem(f"/{field}", "VALIDATION_ERROR", "timestamps are not allowed", "remove the time reference"))
    for i, c in enumerate(card.get("conditions", [])):
        if isinstance(c, str) and TIMESTAMP_RE.search(c):
            problems.append(_problem(f"/conditions/{i}", "VALIDATION_ERROR", "timestamps are not allowed", "remove the time reference"))

    if cit:
        problems.extend(_check_citation(conn, cit, legacy_cit, legacy, warnings))

    # warnings
    if claim:
        scrubbed = re.sub(r"\b\w*_\w*\b", " ", claim)
        numbers_text = " ".join(str(v) for v in (card.get("numbers") or {}).values())
        missing = [n for n in re.findall(r"(?<![\w.])\d+(?:\.\d+)?", scrubbed) if n not in numbers_text]
        if missing:
            warnings.append(f"numbers in claim not in `numbers`: {', '.join(dict.fromkeys(missing))}")
    for field in ("claim", "subject"):
        text = card.get(field) or ""
        letters = [c for c in text if c.isalpha()]
        if letters and sum(1 for c in letters if c.isascii()) / len(letters) <= 0.8:
            warnings.append(f"{field} does not look English (cards are written in English)")
    return problems, warnings


def _check_citation(conn: sqlite3.Connection, cit: dict[str, Any], legacy_cit: bool, legacy: bool, warnings: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    cid, seq, quote = cit.get("content_id"), cit.get("segment_seq"), cit.get("quote") or ""
    content = conn.execute("SELECT id, fetch_method FROM contents WHERE id = ?", (cid,)).fetchone() if cid else None
    if content is None:
        out.append(_problem("/citation/content_id", "VALIDATION_ERROR", f"content {cid} does not exist"))
    elif not content["fetch_method"] and not legacy:
        out.append(_problem("/citation/content_id", "VALIDATION_ERROR", f"content {cid} has no fetch provenance (fetch_method is empty): its text was not fetched by a platform skill",
                            "fetch it with the platform skill (`fetch <url> --ingest --run R`); never write content text yourself (docs/agent-guide.md)"))
    elif legacy_cit:
        n = conn.execute("SELECT COUNT(*) FROM content_segments WHERE content_id = ?", (cid,)).fetchone()[0]
        if n:
            out.append(_problem("/citation/segment_seq", "VALIDATION_ERROR", "content has segments; a citation needs segment_seq (legacy null is only for text-less contents)"))
    elif isinstance(seq, int):
        rows = conn.execute("SELECT seq, text FROM content_segments WHERE content_id = ? AND seq BETWEEN ? AND ? ORDER BY seq",
                            (cid, seq, seq + SEG_LOOKAHEAD)).fetchall()
        if not rows or rows[0]["seq"] != seq:
            out.append(_problem("/citation/segment_seq", "VALIDATION_ERROR", f"segment {seq} of {cid} does not exist"))
        elif not quote_in(quote, " ".join(r["text"] for r in rows)):
            if legacy:  # --legacy relaxes only the quote check; the citation is stored with quote_verified = 0
                warnings.append(f"legacy citation: quote not found in segment {seq} of {cid} (stored unverified)")
            else:
                out.append(_problem("/citation/quote", "QUOTE_NOT_FOUND",
                                    f"quote not found in segments {seq}..{rows[-1]['seq']} (case and punctuation are ignored, words are not)",
                                    "copy the quote exactly from the segment text"))
    sp = cit.get("speaker") or {}
    pid = sp.get("person_id")
    if pid and conn.execute("SELECT 1 FROM persons WHERE id = ?", (pid,)).fetchone() is None:
        out.append(_problem("/citation/speaker/person_id", "VALIDATION_ERROR", f"person {pid} does not exist", "create it with `kb person upsert`"))
    if sp.get("role") in ("commenter", "member") and not pid and not sp.get("handle"):
        out.append(_problem("/citation/speaker/handle", "VALIDATION_ERROR", "commenter/member without person_id needs a handle"))
    return out


def validate_cards(conn: sqlite3.Connection, cards: list[dict[str, Any]], legacy: bool = False) -> dict[str, Any]:
    valid, errors, warnings = [], [], []
    for i, c in enumerate(cards):
        probs, warns = validate_card(conn, c, legacy)
        (errors.append({"index": i, "details": probs}) if probs else valid.append(i))
        warnings.extend(f"card {i}: {w}" for w in warns)
    return {"valid": valid, "errors": errors, "warnings": warnings}


def fingerprint(card: dict[str, Any]) -> str:
    c = card["citation"]
    return hashlib.sha1(f"{quote_key(card['claim'])}|{c['content_id']}|{c.get('segment_seq')}".encode()).hexdigest()


# --- retrieval ------------------------------------------------------------------------------------------

WEIGHTS = "3.0, 2.0, 1.0, 4.0, 1.5, 1.0, 0.5"
ISSUE_SQL = ("SELECT rowid, bm25(knowledge_cards_fts, " + WEIGHTS + ") AS s FROM knowledge_cards_fts "
             "WHERE knowledge_cards_fts MATCH ? ORDER BY s LIMIT 50")


def card_row(conn: sqlite3.Connection, card_id: int) -> dict[str, Any] | None:
    r = conn.execute("SELECT * FROM knowledge_cards WHERE id = ?", (card_id,)).fetchone()
    return _card_dict(r) if r else None


def _card_dict(r: sqlite3.Row) -> dict[str, Any]:
    d = dict(r)
    for plain, col in CARD_JSON_FIELDS.items():
        d[plain] = loads(d.pop(col), {} if plain == "numbers" else [])
    return d


def _citations(conn: sqlite3.Connection, card_id: int, limit: int | None = None) -> list[dict[str, Any]]:
    sql = ("SELECT c.*, p.canonical_name AS person_name, ct.title AS content_title, ct.url AS content_url "
           "FROM card_citations c LEFT JOIN persons p ON p.id = c.person_id LEFT JOIN contents ct ON ct.id = c.content_id "
           "WHERE c.card_id = ? ORDER BY c.attribution_confidence DESC, c.id")
    rows = conn.execute(sql + (f" LIMIT {int(limit)}" if limit else ""), (card_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["locator"] = loads(d.pop("locator_json"), {})
        out.append(d)
    return out


def _stats(conn: sqlite3.Connection, card_id: int) -> dict[str, int]:
    r = conn.execute("SELECT citations, persons, contents, contradictions FROM card_stats WHERE card_id = ?", (card_id,)).fetchone()
    return dict(r) if r else {}


class Spec:
    """Normalized retrieval input built from a card or a Query Card (03 §2.1)."""

    def __init__(self, terms: list[str], aliases: list[str], subject_words: list[str], claim_words: list[str],
                 entities: list[str], fts_queries: list[str] | None = None) -> None:
        self.terms, self.aliases, self.subject_words = terms, aliases, subject_words
        self.claim_words, self.entities, self.fts_queries = claim_words, entities, fts_queries or []


def _expand_terms(conn: sqlite3.Connection, terms: list[str], extra_broader: list[str] | None = None) -> list[str]:
    out = list(dict.fromkeys(terms))
    for t in terms:
        e = vocab.resolve(conn, t)
        if e and e["term"] not in out:
            out.append(e["term"])
        if e and e["broader"] and e["broader"] not in out:
            out.append(e["broader"])
    for b in extra_broader or []:
        if b not in out:
            out.append(b)
    return out


def spec_from_card(conn: sqlite3.Connection, card: dict[str, Any]) -> Spec:
    return Spec(_expand_terms(conn, card.get("terms", [])), list(card.get("aliases", [])),
                fts.significant_words(card.get("subject", "")), fts.significant_words(
                    " ".join([card.get("claim", ""), *card.get("conditions", [])]), 15)[:15],
                list(card.get("entities", [])))


def _phrases_to_terms(conn: sqlite3.Connection, text: str) -> list[str]:
    idx = vocab.surface_index(conn)
    words = vocab.surface_key(text).split()
    found: list[str] = []
    for n in (3, 2, 1):
        for i in range(len(words) - n + 1):
            t = idx.get(" ".join(words[i:i + n]))
            if t and t not in found:
                found.append(t)
    return found


def spec_from_query(conn: sqlite3.Connection, q: dict[str, Any]) -> Spec:
    terms = list(q.get("terms", []))
    for t in _phrases_to_terms(conn, " ".join([q.get("question", ""), q.get("subject", ""), *q.get("aliases", [])])):
        if t not in terms:
            terms.append(t)
    return Spec(_expand_terms(conn, terms, q.get("broader_terms")), list(q.get("aliases", [])),
                fts.significant_words(q.get("subject", "") + " " + q.get("question", "")),
                fts.significant_words(q.get("claim_pattern", ""), 15), list(q.get("entities", [])), list(q.get("fts_queries", [])))


def spec_from_text(conn: sqlite3.Connection, text: str) -> Spec:
    return Spec(_expand_terms(conn, _phrases_to_terms(conn, text)), [text], fts.significant_words(text), fts.significant_words(text, 15), [])


def _sub_queries(spec: Spec) -> list[tuple[str, str]]:
    q: list[tuple[str, str | None]] = [
        ("q_terms", fts.match_any(spec.terms, "terms")),
        ("q_subject", fts.match_any(spec.subject_words, "subject")),
        ("q_claim", fts.match_any(spec.claim_words, "{claim conditions}")),
        ("q_alias", fts.match_any([a for a in spec.aliases if a.strip()], "{aliases quotes}") if spec.aliases else None),
        ("q_entities", fts.match_any(spec.entities, "entities")),
    ]
    return [(n, e) for n, e in q if e]


def _passes(card: dict[str, Any], stats: dict[str, int], conn: sqlite3.Connection, f: dict[str, Any]) -> bool:
    for fld in FILTER_FIELDS:
        if f.get(fld) and card.get(fld) not in f[fld]:
            return False
    if f.get("instruments") and not set(f["instruments"]) & set(card["instruments"]):
        return False
    if f.get("evidence_level_min") and EVIDENCE_ORDER.index(card["evidence_level"]) < EVIDENCE_ORDER.index(f["evidence_level_min"]):
        return False
    if f.get("min_persons") and stats.get("persons", 0) < f["min_persons"]:
        return False
    if f.get("person_id") and not conn.execute(
            f"SELECT 1 FROM card_citations WHERE card_id = ? AND person_id IN ({','.join('?' * len(f['person_id']))})",
            [card["id"], *f["person_id"]]).fetchone():
        return False
    return True


VEC_WEIGHT = 2.0


def resolve_mode(conn: sqlite3.Connection, mode: str, vector_text: str | None, warnings: list[str]) -> str:
    """`auto` = hybrid when card vectors exist for the configured model, else lexical. An explicit semantic/hybrid without vectors degrades with a warning."""
    have = bool(vector_text) and embed.has_vectors(conn, "card")
    if mode == "auto":
        return "hybrid" if have else "lexical"
    if mode in ("semantic", "hybrid") and not have:
        warnings.append(f"no card embeddings for model {embed.model_id()}: run `finsocnet kb embed sync`; using lexical search")
        return "lexical"
    return mode


def retrieve(conn: sqlite3.Connection, spec: Spec, limit: int = 10, filters: dict[str, Any] | None = None,
             same_citation: tuple[str, int] | None = None, run_id: int | None = None, vector_text: str | None = None,
             mode: str = "lexical") -> dict[str, Any]:
    """Run the sub-queries (BM25 over the canonical form) and the vector query (cosine over card embeddings), fuse with RRF,
    filter, return `{candidates, siblings, warnings}` (deterministic for a given database and model)."""
    ranks: dict[int, dict[str, int]] = {}
    warnings: list[str] = []
    mode = resolve_mode(conn, mode, vector_text, warnings)
    if mode in ("semantic", "hybrid"):
        for cid, rk in embed.card_vector_ranks(conn, vector_text or "", 100).items():
            ranks.setdefault(cid, {})["vec"] = rk
    queries = (_sub_queries(spec) + [(f"q_agent_{i}", e) for i, e in enumerate(spec.fts_queries)]) if mode != "semantic" else []
    for name, expr in queries:
        try:
            rows = conn.execute(ISSUE_SQL, (expr,)).fetchall()
        except sqlite3.OperationalError as e:
            warnings.append(f"{name} skipped (FTS syntax error: {e})")
            continue
        for rank, r in enumerate(rows, 1):
            ranks.setdefault(r["rowid"], {})[name] = rank
    # the vector ranking sees the whole query at once, so it counts double against each BM25 sub-query
    scored = sorted(((-sum((VEC_WEIGHT if n == "vec" else 1.0) / (60 + rk) for n, rk in rs.items()), cid) for cid, rs in ranks.items()))
    out, siblings = [], []
    for neg, cid in scored:
        card = card_row(conn, cid)
        if card is None or card["status"] != "active":
            continue
        stats = _stats(conn, cid)
        if filters and not _passes(card, stats, conn, filters):
            continue
        item = {"card": card, "citations": _citations(conn, cid, 2), "stats": stats, "score": round(-neg, 6),
                "score_debug": ranks[cid]}
        if same_citation and run_id is not None and card["run_id"] == run_id and conn.execute(
                "SELECT 1 FROM card_citations WHERE card_id = ? AND content_id = ? AND segment_seq = ?", (cid, *same_citation)).fetchone():
            siblings.append(item)
            continue
        if len(out) < limit:
            out.append(item)
    return {"candidates": out, "siblings": siblings, "warnings": warnings}


def candidates(conn: sqlite3.Connection, cards: list[dict[str, Any]], index: int | None = None, limit: int = 10,
               run_id: int | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    res, warns = [], []
    for i, card in enumerate(cards):
        if index is not None and i != index:
            continue
        cit = card.get("citation", {})
        r = retrieve(conn, spec_from_card(conn, card), limit, None, (cit.get("content_id"), cit.get("segment_seq")), run_id,
                     vector_text=embed.card_text(card), mode="auto")
        res.append({"index": i, "candidates": r["candidates"], "siblings": r["siblings"]})
        warns.extend(r["warnings"])
    return res, warns


def search_cards(conn: sqlite3.Connection, query_card: dict[str, Any] | None = None, text: str | None = None,
                 limit: int = 30, mode: str = "auto", extra_filters: dict[str, Any] | None = None) -> dict[str, Any]:
    """`mode`: lexical (BM25 only) | semantic (vectors only) | hybrid (RRF of both) | auto (hybrid when vectors exist).
    The query must already be English: a Query Card is, free `--text` is the agent's responsibility (skill `translator`)."""
    if mode not in ("auto", "lexical", "semantic", "hybrid"):
        raise CliError("USAGE", f"unknown mode {mode!r}", "auto | lexical | semantic | hybrid")
    if query_card is not None:
        errs = schema_errors("query_card", query_card)
        if errs:
            raise CliError("VALIDATION_ERROR", "query card failed validation", details=[_problem(e["path"], "VALIDATION_ERROR", e["problem"]) for e in errs])
        spec, filters, vtext = spec_from_query(conn, query_card), query_card.get("filters"), embed.query_text(query_card)
    elif text:
        spec, filters, vtext = spec_from_text(conn, text), None, text
    else:
        raise CliError("USAGE", "give --query-card or --text")
    if extra_filters:
        filters = {**(filters or {}), **extra_filters}
    r = retrieve(conn, spec, limit, filters, vector_text=vtext, mode=mode)
    return {"results": r["candidates"], "terms_used": spec.terms, "warnings": r["warnings"], "mode": mode if mode != "auto" else ("hybrid" if embed.has_vectors(conn) else "lexical")}


# --- commit ---------------------------------------------------------------------------------------------

def _snapshot(conn: sqlite3.Connection, card_id: int, reason: str, run_id: int | None) -> int:
    r = conn.execute("SELECT * FROM knowledge_cards WHERE id = ?", (card_id,)).fetchone()
    snap = dict(r)
    snap["citation_ids"] = [x[0] for x in conn.execute("SELECT id FROM card_citations WHERE card_id = ? ORDER BY id", (card_id,))]
    snap["links"] = [dict(x) for x in conn.execute("SELECT * FROM card_links WHERE from_card = ? OR to_card = ?", (card_id, card_id))]
    cur = conn.execute("INSERT INTO card_history (card_id, snapshot_json, reason, run_id) VALUES (?, ?, ?, ?)", (card_id, dumps(snap), reason, run_id))
    return int(cur.lastrowid)


def _insert_card(conn: sqlite3.Connection, card: dict[str, Any], run_id: int) -> int:
    cur = conn.execute(
        """INSERT INTO knowledge_cards (card_version, kind, domain, category, subject, claim, conditions_json, action, horizon,
               instruments_json, regime_json, terms_json, aliases_json, entities_json, numbers_json, evidence_level,
               invalidation, notes, transformer_version, produced_by, run_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (card["card_version"], card["kind"], card["domain"], card["category"], card["subject"], card["claim"],
         dumps(card.get("conditions", [])), card.get("action") or "NONE", card.get("horizon") or "n/a",
         dumps(card.get("instruments", [])), dumps(card.get("regime", [])), dumps(card["terms"]),
         dumps(card.get("aliases", [])), dumps(card.get("entities", [])), dumps(card.get("numbers", {})),
         card["evidence_level"], card.get("invalidation"), card.get("notes"), transformer_version(),
         produced_by(conn, run_id), run_id),
    )
    return int(cur.lastrowid)


def _insert_citation(conn: sqlite3.Connection, card_id: int, cit: dict[str, Any], stance: str, run_id: int) -> int | None:
    seq = cit.get("segment_seq")
    locator = cit.get("locator") or {}
    if seq is not None:
        r = conn.execute("SELECT locator_json FROM content_segments WHERE content_id = ? AND seq = ?", (cit["content_id"], seq)).fetchone()
        locator = loads(r["locator_json"], {}) if r else locator
    sp = cit["speaker"]
    role = sp["role"]
    verified = 0 if seq is None else int(quote_in(cit["quote"], " ".join(
        r[0] for r in conn.execute("SELECT text FROM content_segments WHERE content_id = ? AND seq BETWEEN ? AND ? ORDER BY seq", (cit["content_id"], seq, seq + SEG_LOOKAHEAD)))))
    cur = conn.execute(
        """INSERT OR IGNORE INTO card_citations (card_id, content_id, segment_seq, locator_json, person_id, author_handle,
               speaker_role, attribution_confidence, quote, quote_verified, stance, run_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (card_id, cit["content_id"], seq, dumps(locator), sp.get("person_id"), sp.get("handle"), role, sp["confidence"],
         cit["quote"], verified, stance, run_id),
    )
    if sp.get("person_id") and role != "unknown":
        _ensure_appearance(conn, sp["person_id"], cit["content_id"], role, sp["confidence"], run_id)
    return int(cur.lastrowid) if cur.rowcount else None


def _ensure_appearance(conn: sqlite3.Connection, person_id: str, content_id: str, role: str, confidence: float, run_id: int | None) -> None:
    if conn.execute("SELECT 1 FROM person_appearances WHERE person_id = ? AND content_id = ? AND role = ?", (person_id, content_id, role)).fetchone():
        return
    conn.execute("INSERT INTO person_appearances (person_id, content_id, role, match_confidence, match_status, evidence, run_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (person_id, content_id, role, confidence, "confirmed" if confidence >= 0.7 else "needs_review", "card citation", run_id))


def _union(old: list[Any], add: list[Any]) -> list[Any]:
    return list(dict.fromkeys([*old, *add]))


def apply_updates(conn: sqlite3.Connection, target: dict[str, Any], upd: dict[str, Any]) -> dict[str, Any]:
    """Apply the allowed `refines` updates (03 §3.4); returns the column changes."""
    ch: dict[str, Any] = {}
    details: list[dict[str, Any]] = []
    if upd.get("conditions_add"):
        conds = _union(target["conditions"], upd["conditions_add"])
        if len(conds) > 12:
            details.append(_problem("/updates/conditions_add", "VALIDATION_ERROR", "at most 12 conditions per card"))
        ch["conditions_json"] = dumps(conds)
    if upd.get("numbers_set"):
        nums = dict(target["numbers"])
        for k, v in upd["numbers_set"].items():
            if k in nums and str(nums[k]) != str(v):
                details.append(_problem(f"/updates/numbers_set/{k}", "VALIDATION_ERROR", f"{k} is already {nums[k]!r}; put the conflicting number in notes_append"))
            nums[k] = v
        ch["numbers_json"] = dumps(nums)
    if upd.get("terms_add"):
        for t in upd["terms_add"]:
            e = vocab.get(conn, t)
            if e is None or e["status"] != "active":
                details.append(_problem("/updates/terms_add", "VOCAB_UNKNOWN", f"unknown term '{t}'", vocab.suggest(conn, t)))
        terms = _union(target["terms"], upd["terms_add"])
        if len(terms) > MAX_TERMS:
            details.append(_problem("/updates/terms_add", "VALIDATION_ERROR", f"at most {MAX_TERMS} terms per card"))
        ch["terms_json"] = dumps(terms)
    if upd.get("aliases_add"):
        ch["aliases_json"] = dumps(_union(target["aliases"], upd["aliases_add"])[:20])
    if upd.get("entities_add"):
        ch["entities_json"] = dumps(_union(target["entities"], upd["entities_add"])[:20])
    if upd.get("notes_append"):
        notes = "\n".join(x for x in (target.get("notes"), upd["notes_append"]) if x)
        if len(notes) > 500:
            details.append(_problem("/updates/notes_append", "VALIDATION_ERROR", "notes would exceed 500 characters"))
        ch["notes"] = notes
    if upd.get("evidence_level_upgrade"):
        if EVIDENCE_ORDER.index(upd["evidence_level_upgrade"]) > EVIDENCE_ORDER.index(target["evidence_level"]):
            ch["evidence_level"] = upd["evidence_level_upgrade"]
        else:
            details.append(_problem("/updates/evidence_level_upgrade", "VALIDATION_ERROR", "evidence level can only be raised"))
    if upd.get("invalidation_set"):
        if target.get("invalidation"):
            details.append(_problem("/updates/invalidation_set", "VALIDATION_ERROR", "invalidation is already set"))
        else:
            ch["invalidation"] = upd["invalidation_set"]
    if details:
        raise CliError(details[0]["code"], "update rejected", details=details)
    return ch


def _set_cols(conn: sqlite3.Connection, card_id: int, changes: dict[str, Any]) -> None:
    if changes:
        sets = ", ".join(f"{k} = ?" for k in changes)
        conn.execute(f"UPDATE knowledge_cards SET {sets}, updated_at = ? WHERE id = ?", [*changes.values(), utc_now(), card_id])


def commit_one(conn: sqlite3.Connection, dec: dict[str, Any], run_id: int, legacy: bool = False) -> dict[str, Any]:
    """Apply one decision. Caller provides the transaction/savepoint."""
    probe = dec
    cit = (dec.get("new_card") or {}).get("citation") if isinstance(dec, dict) else None
    if legacy and isinstance(cit, dict) and cit.get("segment_seq") is None:
        probe = {**dec, "new_card": {**dec["new_card"], "citation": {**cit, "segment_seq": 0}}}
    errs = schema_errors("decision", probe)
    if errs:
        raise CliError("VALIDATION_ERROR", "decision failed schema validation", details=[_problem(e["path"], "VALIDATION_ERROR", e["problem"]) for e in errs])
    kind, card = dec["decision"], dec["new_card"]
    links = dec.get("links") or []
    if kind in ("related", "contradicts") and not any(l["relation"] == kind for l in links):
        raise CliError("VALIDATION_ERROR", f"a '{kind}' decision needs at least one link with relation '{kind}'",
                       details=[_problem("/links", "VALIDATION_ERROR", f"missing {kind} link")])
    probs, _ = validate_card(conn, card, legacy)
    if probs:
        raise CliError(probs[0]["code"], f"new_card failed validation ({len(probs)} problem(s))", details=probs)

    fp = fingerprint(card)
    prior = conn.execute("SELECT id, decision, result_card, target_card FROM dedup_decisions WHERE fingerprint = ?", (fp,)).fetchone()
    if prior:
        return {"status": "already_committed", "decision": prior["decision"], "result_card": prior["result_card"], "target_card": prior["target_card"]}

    target_id = dec.get("target_card_id")
    target = None
    if kind in ("same", "refines"):
        target = card_row(conn, target_id)
        if target is None or target["status"] != "active":
            raise CliError("CONFLICT", f"target card {target_id} is not active (merged/retired since candidates were fetched)",
                           "re-run `kb card candidates` for this card and decide again")
    for l in links:
        if card_row(conn, l["to_card"]) is None:
            raise CliError("NOT_FOUND", f"linked card {l['to_card']} not found")

    if kind == "same":
        result = target_id
        merged = {"aliases_json": dumps(_union(target["aliases"], card.get("aliases", []))[:20]),
                  "entities_json": dumps(_union(target["entities"], card.get("entities", []))[:20])}
        if merged["aliases_json"] != dumps(target["aliases"]) or merged["entities_json"] != dumps(target["entities"]):
            _snapshot(conn, target_id, "dedup same: union aliases/entities", run_id)
            _set_cols(conn, target_id, merged)
        _insert_citation(conn, result, card["citation"], "supports", run_id)
    elif kind == "refines":
        result = target_id
        changes = apply_updates(conn, target, dec.get("updates") or {})
        _snapshot(conn, target_id, "dedup refines", run_id)
        _set_cols(conn, target_id, changes)
        _insert_citation(conn, result, card["citation"], "refines", run_id)
    else:
        result = _insert_card(conn, card, run_id)
        _insert_citation(conn, result, card["citation"], "supports", run_id)

    from_card = target_id if kind in ("same", "refines") else result
    for l in links:
        if l["to_card"] != from_card:
            conn.execute("INSERT OR IGNORE INTO card_links (from_card, to_card, relation, rationale, run_id) VALUES (?, ?, ?, ?, ?)",
                         (from_card, l["to_card"], l["relation"], l.get("rationale"), run_id))
    conn.execute(
        """INSERT INTO dedup_decisions (fingerprint, new_card_json, candidate_ids_json, decision, target_card, result_card,
               rationale, produced_by, run_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (fp, dumps(card), dumps(dec["candidate_ids"]), kind, target_id if target else None, result, dec["rationale"], produced_by(conn, run_id), run_id),
    )
    return {"status": "committed", "decision": kind, "result_card": result, "target_card": target_id if target else None}


def commit_decisions(conn: sqlite3.Connection, decisions: list[dict[str, Any]], run_id: int, legacy: bool = False) -> list[dict[str, Any]]:
    """One BEGIN IMMEDIATE for the file, one SAVEPOINT per decision: a failed decision rolls back only itself."""
    results: list[dict[str, Any]] = []
    with transaction(conn):
        for i, dec in enumerate(decisions):
            try:
                with savepoint(conn, "decision"):
                    res = commit_one(conn, dec, run_id, legacy)
                results.append({"index": i, **res})
            except CliError as e:
                err = {"code": e.code, "message": e.message}
                if e.hint:
                    err["hint"] = e.hint
                if e.details:
                    err["details"] = e.details
                results.append({"index": i, "status": "error", "error": err})
    return results


# --- get / list / maintenance ---------------------------------------------------------------------------

def get_card(conn: sqlite3.Connection, card_id: int, citations: bool = False, links: bool = False, history: bool = False) -> dict[str, Any]:
    card = card_row(conn, card_id)
    if card is None:
        raise CliError("NOT_FOUND", f"card {card_id} not found")
    card["stats"] = _stats(conn, card_id)
    if citations:
        card["citations"] = _citations(conn, card_id)
    if links:
        card["links"] = [dict(r) for r in conn.execute("SELECT * FROM card_links WHERE from_card = ? OR to_card = ? ORDER BY relation, from_card, to_card", (card_id, card_id))]
    if history:
        card["history"] = [{"id": r["id"], "reason": r["reason"], "at": r["at"], "run_id": r["run_id"]}
                           for r in conn.execute("SELECT id, reason, at, run_id FROM card_history WHERE card_id = ? ORDER BY id", (card_id,))]
    return card


def list_cards(conn: sqlite3.Connection, person: str | None = None, category: str | None = None, status: str | None = "active",
               since: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    sql, args = "SELECT k.id FROM knowledge_cards k WHERE 1=1", []
    if status:
        sql += " AND k.status = ?"
        args.append(status)
    if category:
        sql += " AND k.category = ?"
        args.append(category)
    if since:
        sql += " AND k.created_at >= ?"
        args.append(parse_since(since))
    if person:
        sql += " AND EXISTS (SELECT 1 FROM card_citations c WHERE c.card_id = k.id AND c.person_id = ?)"
        args.append(person)
    sql += " ORDER BY k.id LIMIT ?"
    args.append(limit)
    out = []
    for r in conn.execute(sql, args):
        c = card_row(conn, r["id"])
        out.append({k: c[k] for k in ("id", "kind", "category", "subject", "claim", "terms", "evidence_level", "status")} | {"stats": _stats(conn, r["id"])})
    return out


def _require_active(conn: sqlite3.Connection, card_id: int) -> dict[str, Any]:
    c = card_row(conn, card_id)
    if c is None:
        raise CliError("NOT_FOUND", f"card {card_id} not found")
    if c["status"] != "active":
        raise CliError("CONFLICT", f"card {card_id} is {c['status']}")
    return c


DIRECT_FIELDS = ("kind", "category", "domain", "claim", "subject")


def update_card(conn: sqlite3.Connection, card_id: int, patch: dict[str, Any], reason: str, run_id: int) -> dict[str, Any]:
    with transaction(conn):
        card = _require_active(conn, card_id)
        direct = {k: patch[k] for k in DIRECT_FIELDS if k in patch}
        ops = {k: v for k, v in patch.items() if k not in DIRECT_FIELDS}
        unknown = set(ops) - {"conditions_add", "numbers_set", "aliases_add", "terms_add", "entities_add", "notes_append",
                              "evidence_level_upgrade", "invalidation_set"}
        if unknown:
            raise CliError("VALIDATION_ERROR", f"fields not allowed in update: {', '.join(sorted(unknown))}")
        changes = apply_updates(conn, card, ops)
        probe = {**card, **direct}
        if direct:
            sample = {"card_version": 1, "kind": probe["kind"], "domain": probe["domain"], "category": probe["category"],
                      "subject": probe["subject"], "claim": probe["claim"], "terms": probe["terms"], "evidence_level": probe["evidence_level"],
                      "citation": {"content_id": "x", "segment_seq": 0, "quote": "placeholder quote", "speaker": {"role": "unknown", "confidence": 1}},
                      "action": probe["action"]}
            probs = [p for p in (_problem(e["path"], "VALIDATION_ERROR", e["problem"]) for e in schema_errors("card", sample)) if not p["path"].startswith("/citation")]
            if not GRAMMAR[probe["kind"]].match(probe["claim"]):
                probs.append(_problem("/claim", "GRAMMAR_ERROR", f"claim does not match the {probe['kind']} grammar", GRAMMAR_HINT[probe["kind"]]))
            if probs:
                raise CliError(probs[0]["code"], "update rejected", details=probs)
        _snapshot(conn, card_id, reason, run_id)
        _set_cols(conn, card_id, {**changes, **direct})
    return get_card(conn, card_id)


def retire_card(conn: sqlite3.Connection, card_id: int, reason: str, run_id: int) -> dict[str, Any]:
    with transaction(conn):
        _require_active(conn, card_id)
        _snapshot(conn, card_id, f"retire: {reason}", run_id)
        _set_cols(conn, card_id, {"status": "retired"})
    return {"card_id": card_id, "status": "retired"}


def merge_cards(conn: sqlite3.Connection, src: int, dst: int, reason: str, run_id: int) -> dict[str, Any]:
    if src == dst:
        raise CliError("VALIDATION_ERROR", "cannot merge a card into itself")
    skipped: list[int] = []
    with transaction(conn):
        a, b = _require_active(conn, src), _require_active(conn, dst)
        _snapshot(conn, src, f"merge into {dst}: {reason}", run_id)
        _snapshot(conn, dst, f"merge from {src}: {reason}", run_id)
        moved = 0
        for c in conn.execute("SELECT id, content_id, segment_seq FROM card_citations WHERE card_id = ? ORDER BY id", (src,)).fetchall():
            if c["segment_seq"] is not None and conn.execute(
                    "SELECT 1 FROM card_citations WHERE card_id = ? AND content_id = ? AND segment_seq = ?", (dst, c["content_id"], c["segment_seq"])).fetchone():
                skipped.append(c["id"])
                continue
            conn.execute("UPDATE card_citations SET card_id = ? WHERE id = ?", (dst, c["id"]))
            moved += 1
        for l in conn.execute("SELECT * FROM card_links WHERE from_card = ? OR to_card = ?", (src, src)).fetchall():
            conn.execute("DELETE FROM card_links WHERE from_card = ? AND to_card = ? AND relation = ?", (l["from_card"], l["to_card"], l["relation"]))
            f, t = (dst if l["from_card"] == src else l["from_card"]), (dst if l["to_card"] == src else l["to_card"])
            if f != t:
                conn.execute("INSERT OR IGNORE INTO card_links (from_card, to_card, relation, rationale, run_id) VALUES (?, ?, ?, ?, ?)",
                             (f, t, l["relation"], l["rationale"], run_id))
        _set_cols(conn, dst, {"aliases_json": dumps(_union(b["aliases"], a["aliases"])[:20]),
                              "entities_json": dumps(_union(b["entities"], a["entities"])[:20]),
                              "terms_json": dumps(_union(b["terms"], a["terms"])[:MAX_TERMS])})
        _set_cols(conn, src, {"status": "merged", "merged_into": dst})
    return {"merged": src, "into": dst, "citations_moved": moved, "citations_skipped": skipped}


def link_cards(conn: sqlite3.Connection, src: int, dst: int, relation: str, reason: str, run_id: int) -> dict[str, Any]:
    """Add a link between two active cards after the fact (self-improver data fix). The source card is snapshotted first; `unlink_cards` reverts it."""
    if relation not in ("related", "contradicts", "prerequisite", "example_of", "refines"):
        raise CliError("VALIDATION_ERROR", f"unknown relation {relation!r}")
    if src == dst:
        raise CliError("VALIDATION_ERROR", "cannot link a card to itself")
    with transaction(conn):
        _require_active(conn, src)
        _require_active(conn, dst)
        if conn.execute("SELECT 1 FROM card_links WHERE from_card = ? AND to_card = ? AND relation = ?", (src, dst, relation)).fetchone():
            return {"from_card": src, "to_card": dst, "relation": relation, "status": "exists"}
        _snapshot(conn, src, f"link {relation} -> {dst}: {reason}", run_id)
        conn.execute("INSERT INTO card_links (from_card, to_card, relation, rationale, run_id) VALUES (?, ?, ?, ?, ?)", (src, dst, relation, reason, run_id))
    return {"from_card": src, "to_card": dst, "relation": relation, "status": "created"}


def unlink_cards(conn: sqlite3.Connection, src: int, dst: int, relation: str, reason: str, run_id: int) -> dict[str, Any]:
    """Remove one link (the inverse of `link_cards`); the source card is snapshotted first, so the link is recoverable from `card_history`."""
    with transaction(conn):
        if not conn.execute("SELECT 1 FROM card_links WHERE from_card = ? AND to_card = ? AND relation = ?", (src, dst, relation)).fetchone():
            raise CliError("NOT_FOUND", f"no {relation} link {src} -> {dst}")
        _snapshot(conn, src, f"unlink {relation} -> {dst}: {reason}", run_id)
        conn.execute("DELETE FROM card_links WHERE from_card = ? AND to_card = ? AND relation = ?", (src, dst, relation))
    return {"from_card": src, "to_card": dst, "relation": relation, "status": "removed"}


def undo(conn: sqlite3.Connection, history_id: int, run_id: int) -> dict[str, Any]:
    """Restore a card's fields from a snapshot and move its citations back (links are re-added, never removed)."""
    h = conn.execute("SELECT * FROM card_history WHERE id = ?", (history_id,)).fetchone()
    if h is None:
        raise CliError("NOT_FOUND", f"history entry {history_id} not found")
    snap = loads(h["snapshot_json"], {})
    cid = h["card_id"]
    cols = ["kind", "domain", "category", "subject", "claim", "conditions_json", "action", "horizon", "instruments_json", "regime_json",
            "terms_json", "aliases_json", "entities_json", "numbers_json", "evidence_level", "invalidation", "notes", "status", "merged_into"]
    with transaction(conn):
        _snapshot(conn, cid, f"undo of history {history_id}", run_id)
        _set_cols(conn, cid, {c: snap[c] for c in cols if c in snap})
        back = 0
        for cit_id in snap.get("citation_ids", []):
            row = conn.execute("SELECT card_id, content_id, segment_seq FROM card_citations WHERE id = ?", (cit_id,)).fetchone()
            if row and row["card_id"] != cid and not conn.execute(
                    "SELECT 1 FROM card_citations WHERE card_id = ? AND content_id = ? AND segment_seq IS ?", (cid, row["content_id"], row["segment_seq"])).fetchone():
                conn.execute("UPDATE card_citations SET card_id = ? WHERE id = ?", (cid, cit_id))
                back += 1
        for l in snap.get("links", []):
            conn.execute("INSERT OR IGNORE INTO card_links (from_card, to_card, relation, rationale, run_id) VALUES (?, ?, ?, ?, ?)",
                         (l["from_card"], l["to_card"], l["relation"], l["rationale"], run_id))
    return {"card_id": cid, "restored_from": history_id, "citations_moved_back": back}


def attribute_citation(conn: sqlite3.Connection, citation_id: int, person_id: str, role: str, confidence: float, run_id: int) -> dict[str, Any]:
    if role not in ("owner", "guest", "host", "co_host", "author", "co_author", "commenter", "member", "unknown"):
        raise CliError("VALIDATION_ERROR", "invalid role")
    with transaction(conn):
        c = conn.execute("SELECT * FROM card_citations WHERE id = ?", (citation_id,)).fetchone()
        if c is None:
            raise CliError("NOT_FOUND", f"citation {citation_id} not found")
        if conn.execute("SELECT 1 FROM persons WHERE id = ?", (person_id,)).fetchone() is None:
            raise CliError("NOT_FOUND", f"person {person_id} not found")
        conn.execute("UPDATE card_citations SET person_id = ?, speaker_role = ?, attribution_confidence = ? WHERE id = ?",
                     (person_id, role, confidence, citation_id))
        if role != "unknown":
            _ensure_appearance(conn, person_id, c["content_id"], role, confidence, run_id)
    return {"citation_id": citation_id, "person_id": person_id, "role": role, "confidence": confidence}


def list_decisions(conn: sqlite3.Connection, since: str | None = None, reviewed: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    sql, args = "SELECT id, decision, target_card, result_card, rationale, produced_by, run_id, reviewed, review_note, created_at FROM dedup_decisions WHERE 1=1", []
    if since:
        sql += " AND created_at >= ?"
        args.append(parse_since(since))
    if reviewed == "none":
        sql += " AND reviewed IS NULL"
    elif reviewed:
        sql += " AND reviewed = ?"
        args.append(reviewed)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    return [dict(r) for r in conn.execute(sql, args)]


def review_decision(conn: sqlite3.Connection, decision_id: int, verdict: str, note: str | None) -> dict[str, Any]:
    if verdict not in ("agreed", "overturned"):
        raise CliError("USAGE", "verdict must be agreed or overturned")
    with transaction(conn):
        if conn.execute("SELECT 1 FROM dedup_decisions WHERE id = ?", (decision_id,)).fetchone() is None:
            raise CliError("NOT_FOUND", f"decision {decision_id} not found")
        conn.execute("UPDATE dedup_decisions SET reviewed = ?, review_note = ? WHERE id = ?", (verdict, note, decision_id))
    return {"decision_id": decision_id, "reviewed": verdict}
