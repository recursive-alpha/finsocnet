"""`finsocnet kb …`: the database CLI (docs/spec/01-database.md §6). Every command prints one JSON envelope."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Callable

from finsocnet.core import cards as cards_mod, config, content as content_mod, migrations, persons as persons_mod, runs, vocab as vocab_mod
from finsocnet.core import person_skills as skills_mod
from finsocnet.core import queue as queue_mod
from finsocnet.core import output
from finsocnet.core.db import backup as db_backup
from finsocnet.core.db import connect, default_backup_path, transaction
from finsocnet.core.output import CliError, Result

SQLITE_MIN = (3, 38, 0)


class _Parser(argparse.ArgumentParser):
    def error(self, message: str):  # type: ignore[override]
        raise CliError("USAGE", message)


class Ctx:
    """Per-invocation state: lazily opened connection and the resolved run id."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self._conn: sqlite3.Connection | None = None

    @property
    def db_path(self) -> Path:
        return config.resolve_path(self.args.db) if getattr(self.args, "db", None) else config.db_path()

    def conn(self, create: bool = False, require_v2: bool = True) -> sqlite3.Connection:
        if self._conn is None:
            if not create and not self.db_path.exists():
                raise CliError("NOT_FOUND", f"database {self.db_path} does not exist", "Create it with `finsocnet kb init`.")
            self._conn = connect(self.db_path)
        if require_v2 and not create:
            has = self._conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='agent_runs'").fetchone()
            if not has:
                raise CliError("CONFLICT", "database is not on the v2 schema",
                               "Run `finsocnet kb migrate` (a backup is taken first; confirm with the user for the real database).")
        return self._conn

    def run_id(self) -> int:
        return runs.resolve_run(self.conn(), getattr(self.args, "run", None))

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()


Handler = Callable[[Ctx], Result | Any]


def read_json(path: str | None) -> Any:
    if not path:
        raise CliError("USAGE", "missing --file (use '-' for stdin)")
    try:
        text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
        return json.loads(text)
    except FileNotFoundError:
        raise CliError("NOT_FOUND", f"file {path} not found")
    except ValueError as e:
        raise CliError("VALIDATION_ERROR", f"{path} is not valid JSON: {e}")


def parse_json_arg(text: str | None, what: str) -> Any:
    if text is None:
        return None
    try:
        return json.loads(text)
    except ValueError as e:
        raise CliError("USAGE", f"{what} must be valid JSON: {e}")


# --- admin ----------------------------------------------------------------------------------------------

SEED_PATH = ".agents/skills/knowledge-transformer/references/vocabulary_seed.json"


def load_seed(conn: sqlite3.Connection) -> int:
    """Load the vocabulary seed into an empty vocabulary table; returns the number of terms added."""
    seed = config.repo_root() / SEED_PATH
    if conn.execute("SELECT COUNT(*) FROM vocabulary").fetchone()[0] or not seed.exists():
        return 0
    run_id = runs.start_run(conn, "init", "load vocabulary seed", "manual")
    added = len(vocab_mod.add(conn, json.loads(seed.read_text(encoding="utf-8")), run_id)["added"])
    runs.end_run(conn, run_id, "success", {"terms": added})
    return added


def cmd_init(ctx: Ctx) -> Result:
    conn = ctx.conn(create=True, require_v2=False)
    res = migrations.migrate(conn)
    seeded = load_seed(conn)
    return Result({"db": str(ctx.db_path), "applied": res["applied"], "backups": res["backups"], "summaries": res["summaries"],
                   "vocabulary_seeded": seeded}, res["warnings"])


def cmd_migrate(ctx: Ctx) -> Result:
    conn = ctx.conn(require_v2=False)
    res = migrations.migrate(conn, dry_run=ctx.args.dry_run)
    return Result({"pending": res["pending"], "applied": res["applied"], "backups": res["backups"], "summaries": res["summaries"]}, res["warnings"])


def cmd_backup(ctx: Ctx) -> Result:
    conn = ctx.conn(require_v2=False)
    dest = config.resolve_path(ctx.args.to) if ctx.args.to else default_backup_path(ctx.db_path)
    return Result({"path": str(db_backup(conn, dest))})


FTS_EXTERNAL = ("segments_fts", "person_skills_fts")
FTS_STANDALONE = ("persons_fts", "vocabulary_fts", "knowledge_cards_fts")


def repair_fts(conn: sqlite3.Connection) -> list[str]:
    """Rebuild every FTS index from its source tables."""
    rebuilt = []
    with transaction(conn):
        for t in FTS_EXTERNAL:
            conn.execute(f"INSERT INTO {t}({t}) VALUES ('rebuild')")
            rebuilt.append(t)
        # Standalone indices are derived by triggers: clear them, then fire the UPDATE triggers once per row.
        conn.execute("DELETE FROM knowledge_cards_fts")
        conn.execute("UPDATE knowledge_cards SET id = id")
        conn.execute("DELETE FROM persons_fts")
        conn.execute("UPDATE persons SET id = id")
        conn.execute("DELETE FROM vocabulary_fts")
        conn.execute("UPDATE vocabulary SET term = term")
        rebuilt += list(FTS_STANDALONE)
    return rebuilt


def cmd_doctor(ctx: Ctx) -> Result:
    conn = ctx.conn(require_v2=False)
    warnings: list[str] = []
    if ctx.args.repair_fts:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'agent_runs'").fetchone():
            raise CliError("CONFLICT", "database is not on the v2 schema", "Run `finsocnet kb migrate` first.")
        warnings.append("rebuilt FTS indices: " + ", ".join(repair_fts(conn)))
    ver = sqlite3.sqlite_version_info
    if ver < SQLITE_MIN:
        warnings.append(f"SQLite {sqlite3.sqlite_version} < 3.38 (JSON functions / FTS5 may be missing)")
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    v2 = "agent_runs" in tables
    fts_ok: dict[str, Any] = {}
    orphans: dict[str, int] = {}
    if v2:
        for t in (*FTS_EXTERNAL, *FTS_STANDALONE):
            try:
                conn.execute(f"INSERT INTO {t}({t}) VALUES ('integrity-check')")
                fts_ok[t] = "ok"
            except sqlite3.DatabaseError as e:
                fts_ok[t] = f"FAILED: {e}"
        cards = conn.execute("SELECT COUNT(*) FROM knowledge_cards").fetchone()[0]
        indexed = conn.execute("SELECT COUNT(*) FROM knowledge_cards_fts").fetchone()[0]
        if cards != indexed:
            fts_ok["knowledge_cards_fts"] = f"FAILED: {indexed} indexed rows for {cards} cards"
        fk = conn.execute("PRAGMA foreign_key_check").fetchall()
        orphans["foreign_key_violations"] = len([v for v in fk if not str(v[0]).startswith("legacy_")])
        legacy_fk = len(fk) - orphans["foreign_key_violations"]
        if legacy_fk:
            warnings.append(f"{legacy_fk} pre-existing foreign-key orphan(s) in legacy_* tables (dropped with them in Phase 2)")
        orphans["active_cards_without_citations"] = conn.execute(
            "SELECT COUNT(*) FROM knowledge_cards k WHERE status = 'active' AND NOT EXISTS (SELECT 1 FROM card_citations c WHERE c.card_id = k.id)").fetchone()[0]
        orphans["processing_contents"] = conn.execute("SELECT COUNT(*) FROM contents WHERE process_status = 'processing'").fetchone()[0]
        for k, v in orphans.items():
            if v:
                warnings.append(f"{k}: {v}")
    else:
        warnings.append("database is on the v1 schema; run `finsocnet kb migrate`")
    ok = integrity == "ok" and all(v == "ok" for v in fts_ok.values()) and not orphans.get("foreign_key_violations")
    data = {"ok": ok, "sqlite_version": sqlite3.sqlite_version, "schema": "v2" if v2 else "v1", "integrity": integrity,
            "fts_integrity": fts_ok, "orphans": orphans, "migrations": migrations.status(conn)}
    return Result(data, warnings)


def _count_by(conn: sqlite3.Connection, sql: str) -> dict[str, int]:
    return {str(r[0]): r[1] for r in conn.execute(sql)}


STAT_TABLES = ["sources", "contents", "content_segments", "knowledge_cards", "card_citations", "card_links",
               "dedup_decisions", "vocabulary", "persons", "person_aliases", "person_appearances", "person_skills",
               "explore_queue", "knowledge_gaps", "agent_runs", "lessons", "feedback", "browser_sessions"]


def cmd_stats(ctx: Ctx) -> Result:
    conn = ctx.conn()
    data: dict[str, Any] = {"tables": {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in STAT_TABLES}}
    data["contents_by_status"] = _count_by(conn, "SELECT process_status, COUNT(*) FROM contents GROUP BY 1")
    data["contents_by_platform"] = _count_by(conn, "SELECT platform, COUNT(*) FROM contents GROUP BY 1")
    data["cards_by_status"] = _count_by(conn, "SELECT status, COUNT(*) FROM knowledge_cards GROUP BY 1")
    data["cards_by_category"] = _count_by(conn, "SELECT category, COUNT(*) FROM knowledge_cards WHERE status = 'active' GROUP BY 1")
    data["top_persons"] = [dict(r) for r in conn.execute(
        "SELECT p.id, p.canonical_name, s.cards, s.appearances FROM person_stats s JOIN persons p ON p.id = s.person_id ORDER BY s.cards DESC, p.id LIMIT 10")]
    data["open_gaps"] = conn.execute("SELECT COUNT(*) FROM knowledge_gaps WHERE status = 'open'").fetchone()[0]
    data["queue_by_status"] = _count_by(conn, "SELECT status, COUNT(*) FROM explore_queue GROUP BY 1")
    data["sessions"] = {"domains": conn.execute("SELECT COUNT(*) FROM browser_sessions").fetchone()[0],
                        "by_login_state": _count_by(conn, "SELECT login_state, COUNT(*) FROM browser_sessions GROUP BY 1")}
    return Result(data)


def cmd_prune(ctx: Ctx) -> Result:
    """Prune per 01 §4: processed audio > 30 days, budget_usage > 7 days, work dirs > 90 days."""
    conn = ctx.conn()
    now = time.time()
    audio: list[Path] = []
    adir = config.data_dir() / "audio"
    if adir.exists():
        for f in adir.iterdir():
            if f.is_file() and now - f.stat().st_mtime > 30 * 86400:
                row = conn.execute("SELECT process_status FROM contents WHERE id IN (?, ?)", (f"youtube:{f.stem}", f"audio:{f.stem}")).fetchone()
                if row and row["process_status"] == "processed":
                    audio.append(f)
    work: list[Path] = []
    wdir = config.data_dir() / "work"
    if wdir.exists():
        work = [d for d in wdir.iterdir() if d.is_dir() and now - d.stat().st_mtime > 90 * 86400]
    cutoff = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 7 * 86400))
    budget_rows = conn.execute("SELECT COUNT(*) FROM budget_usage WHERE window_start < ?", (cutoff,)).fetchone()[0]
    if not ctx.args.dry_run:
        import shutil
        for f in audio:
            f.unlink(missing_ok=True)
        for d in work:
            shutil.rmtree(d, ignore_errors=True)
        with transaction(conn):
            conn.execute("DELETE FROM budget_usage WHERE window_start < ?", (cutoff,))
    return Result({"dry_run": ctx.args.dry_run, "audio_files": [str(p) for p in audio], "work_dirs": [str(p) for p in work],
                   "budget_usage_rows": budget_rows})


# --- runs, lessons, feedback ----------------------------------------------------------------------------

def cmd_run_start(ctx: Ctx) -> Result:
    a = ctx.args
    return Result({"run_id": runs.start_run(ctx.conn(), a.skill, a.goal, a.harness, a.model, a.parent)})


def cmd_run_end(ctx: Ctx) -> Result:
    a = ctx.args
    return Result(runs.end_run(ctx.conn(), ctx.run_id(), a.outcome, parse_json_arg(a.stats, "--stats"), parse_json_arg(a.errors, "--errors")))


def cmd_run_list(ctx: Ctx) -> Result:
    a = ctx.args
    return Result({"runs": runs.list_runs(ctx.conn(), a.skill, a.since, a.limit)})


def cmd_lesson_add(ctx: Ctx) -> Result:
    a = ctx.args
    return Result({"lesson_id": runs.add_lesson(ctx.conn(), ctx.run_id(), a.skill, a.kind, a.observation, a.evidence, a.proposal)})


def cmd_lesson_list(ctx: Ctx) -> Result:
    return Result({"lessons": runs.list_lessons(ctx.conn(), ctx.args.status, ctx.args.skill, ctx.args.limit)})


def cmd_lesson_update(ctx: Ctx) -> Result:
    ctx.run_id()
    return Result(runs.update_lesson(ctx.conn(), ctx.args.id, ctx.args.status, ctx.args.ref))


def cmd_feedback_add(ctx: Ctx) -> Result:
    a = ctx.args
    return Result({"feedback_id": runs.add_feedback(ctx.conn(), a.target_type, a.target_id, a.rating, a.comment)})


def cmd_feedback_list(ctx: Ctx) -> Result:
    return Result({"feedback": runs.list_feedback(ctx.conn(), ctx.args.status, ctx.args.limit)})


def cmd_feedback_handle(ctx: Ctx) -> Result:
    ctx.run_id()
    return Result(runs.handle_feedback(ctx.conn(), ctx.args.id))


# --- sources --------------------------------------------------------------------------------------------

def cmd_source_upsert(ctx: Ctx) -> Result:
    conn = ctx.conn()
    ctx.run_id()
    payload = read_json(ctx.args.file)
    items = payload if isinstance(payload, list) else [payload]
    results = []
    with transaction(conn):
        for src in items:
            results.append(content_mod.upsert_source(conn, src))
    return Result({"sources": results})


def cmd_source_get(ctx: Ctx) -> Result:
    return Result(content_mod.get_source(ctx.conn(), ctx.args.id))


def cmd_source_list(ctx: Ctx) -> Result:
    a = ctx.args
    return Result({"sources": content_mod.list_sources(ctx.conn(), a.platform, a.person, a.status, a.limit)})


def cmd_source_cursor(ctx: Ctx) -> Result:
    ctx.run_id()
    conn = ctx.conn()
    with transaction(conn):
        res = content_mod.set_source_cursor(conn, ctx.args.id, ctx.args.set)
    return Result(res)


# --- contents -------------------------------------------------------------------------------------------

def cmd_content_add(ctx: Ctx) -> Result:
    run_id = ctx.run_id()
    payload = read_json(ctx.args.file)
    records = payload if isinstance(payload, list) else [payload]
    conn = ctx.conn()
    results, warnings = [], []
    for rec in records:
        r = content_mod.add_content(conn, rec, run_id)
        warnings.extend(f"{r['id']}: {w}" for w in r.pop("warnings", []))
        results.append(r)
    return Result(results[0] if len(results) == 1 and not isinstance(payload, list) else {"contents": results}, warnings)


def cmd_content_get(ctx: Ctx) -> Result:
    return Result(content_mod.get_content(ctx.conn(), ctx.args.id, ctx.args.meta_only))


def cmd_content_view(ctx: Ctx) -> Result:
    a = ctx.args
    return Result(content_mod.view_content(ctx.conn(), a.id, a.from_seq, a.to_seq))


def cmd_content_chunks(ctx: Ctx) -> Result:
    a = ctx.args
    return Result({"chunks": content_mod.chunks(ctx.conn(), a.id, a.max_chars, a.overlap)})


def cmd_content_list(ctx: Ctx) -> Result:
    a = ctx.args
    return Result({"contents": content_mod.list_contents(ctx.conn(), a.status, a.platform, a.source, a.person, a.limit)})


def cmd_content_claim(ctx: Ctx) -> Result:
    return Result(content_mod.claim_content(ctx.conn(), ctx.args.id, ctx.run_id(), ctx.args.reprocess))


def cmd_content_done(ctx: Ctx) -> Result:
    a = ctx.args
    return Result(content_mod.set_done(ctx.conn(), a.id, a.upto_seq, a.cards, a.transformer, ctx.run_id()))


def cmd_content_fail(ctx: Ctx) -> Result:
    ctx.run_id()
    return Result(content_mod.set_failed(ctx.conn(), ctx.args.id, ctx.args.error))


def cmd_content_link_duplicate(ctx: Ctx) -> Result:
    ctx.run_id()
    return Result(content_mod.link_duplicate(ctx.conn(), ctx.args.id, ctx.args.of))


def cmd_content_search(ctx: Ctx) -> Result:
    a = ctx.args
    hits = content_mod.search_segments(ctx.conn(), a.text, a.platform, a.person, a.content, a.limit)
    return Result({"hits": hits})



# --- vocabulary -----------------------------------------------------------------------------------------

def cmd_vocab_lookup(ctx: Ctx) -> Result:
    return Result({"matches": vocab_mod.lookup(ctx.conn(), ctx.args.phrase, ctx.args.limit)})


def cmd_vocab_add(ctx: Ctx) -> Result:
    payload = read_json(ctx.args.file)
    return Result(vocab_mod.add(ctx.conn(), payload if isinstance(payload, list) else [payload], ctx.run_id()))


def cmd_vocab_update(ctx: Ctx) -> Result:
    return Result(vocab_mod.update(ctx.conn(), ctx.args.term, read_json(ctx.args.file), ctx.run_id()))


def cmd_vocab_merge(ctx: Ctx) -> Result:
    return Result(vocab_mod.merge(ctx.conn(), ctx.args.src, ctx.args.dst, ctx.run_id()))


def cmd_vocab_list(ctx: Ctx) -> Result:
    return Result({"terms": vocab_mod.list_terms(ctx.conn(), ctx.args.facet)})


def cmd_vocab_export(ctx: Ctx) -> Result:
    return Result(vocab_mod.export(ctx.conn(), config.resolve_path(ctx.args.out)))


# --- cards ----------------------------------------------------------------------------------------------

def _cards_file(path: str | None) -> list[dict[str, Any]]:
    payload = read_json(path)
    return payload if isinstance(payload, list) else [payload]


def cmd_card_validate(ctx: Ctx) -> Result:
    res = cards_mod.validate_cards(ctx.conn(), _cards_file(ctx.args.file), ctx.args.legacy)
    return Result({"valid": res["valid"], "errors": res["errors"]}, res["warnings"])


def cmd_card_candidates(ctx: Ctx) -> Result:
    a = ctx.args
    res, warns = cards_mod.candidates(ctx.conn(), _cards_file(a.file), a.index, a.limit, getattr(a, "run", None) or config.env_run_id())
    return Result({"results": res}, warns)


def cmd_card_commit(ctx: Ctx) -> Result:
    run_id = ctx.run_id()
    results = cards_mod.commit_decisions(ctx.conn(), _cards_file(ctx.args.file), run_id, ctx.args.legacy)
    failed = [r for r in results if r["status"] == "error"]
    warnings = [f"decision {r['index']} failed: {r['error']['code']} {r['error']['message']}" for r in failed]
    return Result({"results": results, "committed": sum(r["status"] == "committed" for r in results), "errors": len(failed)}, warnings)


def cmd_card_search(ctx: Ctx) -> Result:
    a = ctx.args
    qc = read_json(a.query_card) if a.query_card else None
    res = cards_mod.search_cards(ctx.conn(), qc, a.text, a.limit)
    return Result({"results": res["results"], "terms_used": res["terms_used"]}, res["warnings"])


def cmd_card_get(ctx: Ctx) -> Result:
    a = ctx.args
    return Result(cards_mod.get_card(ctx.conn(), a.id, a.citations, a.links, a.history))


def cmd_card_list(ctx: Ctx) -> Result:
    a = ctx.args
    return Result({"cards": cards_mod.list_cards(ctx.conn(), a.person, a.category, None if a.status == "any" else a.status, a.since, a.limit)})


def cmd_card_update(ctx: Ctx) -> Result:
    return Result(cards_mod.update_card(ctx.conn(), ctx.args.id, read_json(ctx.args.file), ctx.args.reason, ctx.run_id()))


def cmd_card_merge(ctx: Ctx) -> Result:
    a = ctx.args
    return Result(cards_mod.merge_cards(ctx.conn(), a.src, a.dst, a.reason, ctx.run_id()))


def cmd_card_link(ctx: Ctx) -> Result:
    a = ctx.args
    return Result(cards_mod.link_cards(ctx.conn(), a.src, a.dst, a.relation, a.reason, ctx.run_id()))


def cmd_card_unlink(ctx: Ctx) -> Result:
    a = ctx.args
    return Result(cards_mod.unlink_cards(ctx.conn(), a.src, a.dst, a.relation, a.reason, ctx.run_id()))


def cmd_card_retire(ctx: Ctx) -> Result:
    return Result(cards_mod.retire_card(ctx.conn(), ctx.args.id, ctx.args.reason, ctx.run_id()))


def cmd_card_undo(ctx: Ctx) -> Result:
    return Result(cards_mod.undo(ctx.conn(), ctx.args.history_id, ctx.run_id()))


def cmd_citation_attribute(ctx: Ctx) -> Result:
    a = ctx.args
    return Result(cards_mod.attribute_citation(ctx.conn(), a.id, a.person, a.role, a.confidence, ctx.run_id()))


def cmd_decision_list(ctx: Ctx) -> Result:
    a = ctx.args
    return Result({"decisions": cards_mod.list_decisions(ctx.conn(), a.since, a.reviewed, a.limit)})


def cmd_decision_review(ctx: Ctx) -> Result:
    ctx.run_id()
    a = ctx.args
    return Result(cards_mod.review_decision(ctx.conn(), a.id, a.verdict, a.note))


# --- persons and rulebooks ------------------------------------------------------------------------------

def cmd_person_candidates(ctx: Ctx) -> Result:
    a = ctx.args
    if not (a.name or a.handle):
        raise CliError("USAGE", "give --name and/or --handle")
    return Result({"candidates": persons_mod.candidates(ctx.conn(), a.name, a.handle, a.platform, a.context, a.content)})


def cmd_person_upsert(ctx: Ctx) -> Result:
    conn, run = ctx.conn(), ctx.run_id()
    payload = read_json(ctx.args.file)
    items = payload if isinstance(payload, list) else [payload]
    res = [persons_mod.upsert(conn, p, run) for p in items]
    return Result(res[0] if not isinstance(payload, list) else {"persons": res})


def cmd_person_alias_add(ctx: Ctx) -> Result:
    ctx.run_id()
    a = ctx.args
    return Result(persons_mod.alias_add(ctx.conn(), a.person, a.alias, a.platform or ""))


def cmd_person_appearance_add(ctx: Ctx) -> Result:
    run = ctx.run_id()
    payload = read_json(ctx.args.file)
    res = [persons_mod.add_appearance(ctx.conn(), p, run) for p in (payload if isinstance(payload, list) else [payload])]
    return Result(res[0] if not isinstance(payload, list) else {"appearances": res})


def cmd_person_get(ctx: Ctx) -> Result:
    return Result(persons_mod.get(ctx.conn(), ctx.args.id))


def cmd_person_list(ctx: Ctx) -> Result:
    key = "needs_review" if ctx.args.needs_review else "persons"
    return Result({key: persons_mod.list_persons(ctx.conn(), ctx.args.needs_review, ctx.args.limit)})


def cmd_person_cards(ctx: Ctx) -> Result:
    return Result(persons_mod.person_cards(ctx.conn(), ctx.args.id, ctx.args.category))


def cmd_person_merge(ctx: Ctx) -> Result:
    return Result(persons_mod.merge(ctx.conn(), ctx.args.src, ctx.args.dst, ctx.run_id()))


def cmd_skill_upsert(ctx: Ctx) -> Result:
    conn, run = ctx.conn(), ctx.run_id()
    payload = read_json(ctx.args.file)
    res = [skills_mod.upsert_skill(conn, s, run) for s in (payload if isinstance(payload, list) else [payload])]
    return Result(res[0] if not isinstance(payload, list) else {"skills": res})


def cmd_skill_get(ctx: Ctx) -> Result:
    a = ctx.args
    if a.render == "markdown":
        return Result({"person_id": a.person, "markdown": skills_mod.render_markdown(ctx.conn(), a.person, a.skill_name, a.category)})
    rows = skills_mod.get_skills(ctx.conn(), a.person, a.skill_name, a.category)
    if not rows:
        raise CliError("NOT_FOUND", f"no rulebook for {a.person}")
    return Result({"skills": rows})


def cmd_skill_list(ctx: Ctx) -> Result:
    return Result({"skills": skills_mod.list_skills(ctx.conn(), ctx.args.person)})


# --- exploration ----------------------------------------------------------------------------------------

def cmd_queue_add(ctx: Ctx) -> Result:
    a, run = ctx.args, ctx.run_id()
    if a.file:
        payload = read_json(a.file)
        items = payload if isinstance(payload, list) else [payload]
    else:
        items = [{"target": a.target, "target_kind": a.target_kind, "platform": a.platform or "", "action": a.action, "origin": a.origin,
                  "origin_ref": a.origin_ref, "reason": a.reason, "priority": a.priority}]
    res = [queue_mod.add(ctx.conn(), i, run) for i in items]
    return Result(res[0] if not a.file else {"items": res})


def cmd_queue_next(ctx: Ctx) -> Result:
    return Result({"items": queue_mod.next_items(ctx.conn(), ctx.args.limit, ctx.args.platform)})


def cmd_queue_update(ctx: Ctx) -> Result:
    ctx.run_id()
    a = ctx.args
    return Result(queue_mod.update(ctx.conn(), a.id, a.status, a.error, a.retry_after))


def cmd_queue_list(ctx: Ctx) -> Result:
    return Result({"items": queue_mod.list_items(ctx.conn(), ctx.args.status, ctx.args.limit)})


def cmd_gap_add(ctx: Ctx) -> Result:
    a, run = ctx.args, ctx.run_id()
    return Result(queue_mod.gap_add(ctx.conn(), a.query, a.verdict, read_json(a.query_card) if a.query_card else None, run))


def cmd_gap_list(ctx: Ctx) -> Result:
    return Result({"gaps": queue_mod.gap_list(ctx.conn(), ctx.args.status, ctx.args.limit)})


def cmd_gap_update(ctx: Ctx) -> Result:
    ctx.run_id()
    a = ctx.args
    return Result(queue_mod.gap_update(ctx.conn(), a.id, a.status, [int(x) for x in a.filled_by.split(",")] if a.filled_by else None))


def cmd_history_pending(ctx: Ctx) -> Result:
    return Result({"entries": queue_mod.history_pending(ctx.conn(), ctx.args.limit)})


def cmd_history_mark(ctx: Ctx) -> Result:
    ctx.run_id()
    return Result(queue_mod.history_mark(ctx.conn(), ctx.args.urls, ctx.args.triage))


# --- parser ---------------------------------------------------------------------------------------------

def _common() -> argparse.ArgumentParser:
    p = _Parser(add_help=False)
    p.add_argument("--db", help="database path (default: KNOWLEDGE_DB_PATH)")
    p.add_argument("--run", type=int, help="run id (or env FINSOCNET_RUN_ID); required by write commands")
    p.add_argument("--format", choices=["json", "text"], default="json")
    return p


def build_parser() -> _Parser:
    root = _Parser(prog="finsocnet kb", description="FinSocNet database CLI (SQLite + FTS5)")
    groups = root.add_subparsers(dest="group", required=True, parser_class=_Parser)
    common = _common()
    handlers: dict[tuple[str, ...], Handler] = {}

    def leaf(subs, path: tuple[str, ...], name: str, handler: Handler, help_: str = "") -> argparse.ArgumentParser:
        p = subs.add_parser(name, parents=[common], help=help_)
        handlers[path] = handler
        return p

    def group(name: str, help_: str = ""):
        g = groups.add_parser(name, help=help_)
        return g.add_subparsers(dest="cmd", required=True, parser_class=_Parser)

    def top(name: str, handler: Handler, help_: str = "") -> argparse.ArgumentParser:
        p = groups.add_parser(name, parents=[common], help=help_)
        p.set_defaults(cmd=None)
        handlers[(name,)] = handler
        return p

    top("init", cmd_init, "create the database and run migrations")
    p = top("migrate", cmd_migrate, "apply pending migrations")
    p.add_argument("--dry-run", action="store_true")
    p = top("backup", cmd_backup, "copy the database")
    p.add_argument("--to")
    p = top("doctor", cmd_doctor, "health check")
    p.add_argument("--repair-fts", action="store_true", help="rebuild all FTS indices before checking")
    top("stats", cmd_stats, "counts and distributions")
    p = top("prune", cmd_prune, "prune cache files and old rows (01 §4)")
    p.add_argument("--dry-run", action="store_true")

    g = group("run", "agent runs")
    p = leaf(g, ("run", "start"), "start", cmd_run_start)
    p.add_argument("--skill", required=True)
    p.add_argument("--goal")
    p.add_argument("--harness")
    p.add_argument("--model")
    p.add_argument("--parent", type=int)
    p = leaf(g, ("run", "end"), "end", cmd_run_end)
    p.add_argument("--outcome", required=True, choices=runs.OUTCOMES)
    p.add_argument("--stats")
    p.add_argument("--errors")
    p = leaf(g, ("run", "list"), "list", cmd_run_list)
    p.add_argument("--skill")
    p.add_argument("--since")
    p.add_argument("--limit", type=int, default=20)

    g = group("lesson", "lessons learned")
    p = leaf(g, ("lesson", "add"), "add", cmd_lesson_add)
    p.add_argument("--skill", required=True)
    p.add_argument("--kind", required=True, choices=runs.LESSON_KINDS)
    p.add_argument("--observation", required=True)
    p.add_argument("--evidence")
    p.add_argument("--proposal")
    p = leaf(g, ("lesson", "list"), "list", cmd_lesson_list)
    p.add_argument("--status", choices=runs.LESSON_STATUSES)
    p.add_argument("--skill")
    p.add_argument("--limit", type=int, default=50)
    p = leaf(g, ("lesson", "update"), "update", cmd_lesson_update)
    p.add_argument("id", type=int)
    p.add_argument("--status", choices=runs.LESSON_STATUSES)
    p.add_argument("--ref")

    g = group("feedback", "user feedback")
    p = leaf(g, ("feedback", "add"), "add", cmd_feedback_add)
    p.add_argument("--target-type", required=True, choices=runs.FEEDBACK_TARGETS)
    p.add_argument("--target-id", required=True)
    p.add_argument("--rating", required=True, type=int, choices=[-1, 0, 1])
    p.add_argument("--comment")
    p = leaf(g, ("feedback", "list"), "list", cmd_feedback_list)
    p.add_argument("--status", choices=["open", "handled"])
    p.add_argument("--limit", type=int, default=50)
    p = leaf(g, ("feedback", "handle"), "handle", cmd_feedback_handle)
    p.add_argument("id", type=int)

    g = group("source", "sources")
    p = leaf(g, ("source", "upsert"), "upsert", cmd_source_upsert)
    p.add_argument("--file", required=True)
    p = leaf(g, ("source", "get"), "get", cmd_source_get)
    p.add_argument("id")
    p = leaf(g, ("source", "list"), "list", cmd_source_list)
    p.add_argument("--platform")
    p.add_argument("--person")
    p.add_argument("--status")
    p.add_argument("--limit", type=int, default=100)
    p = leaf(g, ("source", "cursor"), "cursor", cmd_source_cursor)
    p.add_argument("id")
    p.add_argument("--set", required=True)

    g = group("content", "contents and segments")
    p = leaf(g, ("content", "add"), "add", cmd_content_add)
    p.add_argument("--file", required=True, help="ContentRecord JSON (or array); '-' for stdin")
    p = leaf(g, ("content", "get"), "get", cmd_content_get)
    p.add_argument("id")
    p.add_argument("--meta-only", action="store_true")
    p = leaf(g, ("content", "view"), "view", cmd_content_view)
    p.add_argument("id")
    p.add_argument("--from-seq", type=int)
    p.add_argument("--to-seq", type=int)
    p = leaf(g, ("content", "chunks"), "chunks", cmd_content_chunks)
    p.add_argument("id")
    p.add_argument("--max-chars", type=int, default=12000)
    p.add_argument("--overlap", type=int, default=2)
    p = leaf(g, ("content", "list"), "list", cmd_content_list)
    p.add_argument("--status")
    p.add_argument("--platform")
    p.add_argument("--source")
    p.add_argument("--person")
    p.add_argument("--limit", type=int, default=50)
    p = leaf(g, ("content", "claim"), "claim", cmd_content_claim)
    p.add_argument("id")
    p.add_argument("--reprocess", action="store_true", help="mine an already processed content again")
    p = leaf(g, ("content", "done"), "done", cmd_content_done)
    p.add_argument("id")
    p.add_argument("--upto-seq", type=int, required=True)
    p.add_argument("--cards", type=int, required=True)
    p.add_argument("--transformer")
    p = leaf(g, ("content", "fail"), "fail", cmd_content_fail)
    p.add_argument("id")
    p.add_argument("--error", required=True)
    p = leaf(g, ("content", "link-duplicate"), "link-duplicate", cmd_content_link_duplicate)
    p.add_argument("id")
    p.add_argument("--of", required=True)
    p = leaf(g, ("content", "search"), "search", cmd_content_search)
    p.add_argument("text")
    p.add_argument("--platform")
    p.add_argument("--person")
    p.add_argument("--content")
    p.add_argument("--limit", type=int, default=20)

    g = group("vocab", "controlled vocabulary")
    p = leaf(g, ("vocab", "lookup"), "lookup", cmd_vocab_lookup)
    p.add_argument("phrase")
    p.add_argument("--limit", type=int, default=5)
    p = leaf(g, ("vocab", "add"), "add", cmd_vocab_add)
    p.add_argument("--file", required=True)
    p = leaf(g, ("vocab", "update"), "update", cmd_vocab_update)
    p.add_argument("term")
    p.add_argument("--file", required=True)
    p = leaf(g, ("vocab", "merge"), "merge", cmd_vocab_merge)
    p.add_argument("--from", dest="src", required=True)
    p.add_argument("--into", dest="dst", required=True)
    p = leaf(g, ("vocab", "list"), "list", cmd_vocab_list)
    p.add_argument("--facet")
    p = leaf(g, ("vocab", "export"), "export", cmd_vocab_export)
    p.add_argument("--out", required=True)

    g = group("card", "knowledge cards")
    p = leaf(g, ("card", "validate"), "validate", cmd_card_validate)
    p.add_argument("--file", required=True)
    p.add_argument("--legacy", action="store_true")
    p = leaf(g, ("card", "candidates"), "candidates", cmd_card_candidates)
    p.add_argument("--file", required=True)
    p.add_argument("--index", type=int)
    p.add_argument("--limit", type=int, default=10)
    p = leaf(g, ("card", "commit"), "commit", cmd_card_commit)
    p.add_argument("--file", required=True, help="array of decision JSON (03 §3.3)")
    p.add_argument("--legacy", action="store_true", help="Phase 2 only: allow segment_seq null for contents without text")
    p = leaf(g, ("card", "search"), "search", cmd_card_search)
    p.add_argument("--query-card")
    p.add_argument("--text")
    p.add_argument("--limit", type=int, default=30)
    p = leaf(g, ("card", "get"), "get", cmd_card_get)
    p.add_argument("id", type=int)
    p.add_argument("--citations", action="store_true")
    p.add_argument("--links", action="store_true")
    p.add_argument("--history", action="store_true")
    p = leaf(g, ("card", "list"), "list", cmd_card_list)
    p.add_argument("--person")
    p.add_argument("--category")
    p.add_argument("--status", default="active", choices=["active", "merged", "retired", "any"])
    p.add_argument("--since")
    p.add_argument("--limit", type=int, default=50)
    p = leaf(g, ("card", "update"), "update", cmd_card_update)
    p.add_argument("id", type=int)
    p.add_argument("--file", required=True)
    p.add_argument("--reason", required=True)
    p = leaf(g, ("card", "merge"), "merge", cmd_card_merge)
    p.add_argument("--from", dest="src", type=int, required=True)
    p.add_argument("--into", dest="dst", type=int, required=True)
    p.add_argument("--reason", required=True)
    for name, fn in (("link", cmd_card_link), ("unlink", cmd_card_unlink)):
        p = leaf(g, ("card", name), name, fn)
        p.add_argument("--from", dest="src", type=int, required=True)
        p.add_argument("--to", dest="dst", type=int, required=True)
        p.add_argument("--relation", default="related", choices=["related", "contradicts", "prerequisite", "example_of", "refines"])
        p.add_argument("--reason", required=True)
    p = leaf(g, ("card", "retire"), "retire", cmd_card_retire)
    p.add_argument("id", type=int)
    p.add_argument("--reason", required=True)
    p = leaf(g, ("card", "undo"), "undo", cmd_card_undo)
    p.add_argument("--history-id", type=int, required=True)

    g = group("citation", "citations")
    p = leaf(g, ("citation", "attribute"), "attribute", cmd_citation_attribute)
    p.add_argument("id", type=int)
    p.add_argument("--person", required=True)
    p.add_argument("--role", required=True)
    p.add_argument("--confidence", type=float, required=True)

    g = group("decision", "dedup decisions")
    p = leaf(g, ("decision", "list"), "list", cmd_decision_list)
    p.add_argument("--since")
    p.add_argument("--reviewed", choices=["none", "agreed", "overturned"])
    p.add_argument("--limit", type=int, default=50)
    p = leaf(g, ("decision", "review"), "review", cmd_decision_review)
    p.add_argument("id", type=int)
    p.add_argument("--verdict", required=True, choices=["agreed", "overturned"])
    p.add_argument("--note")

    g = group("person", "canonical persons")
    p = leaf(g, ("person", "candidates"), "candidates", cmd_person_candidates)
    p.add_argument("--name")
    p.add_argument("--handle")
    p.add_argument("--platform")
    p.add_argument("--context")
    p.add_argument("--content", help="content id: its source owner counts as a signal")
    p = leaf(g, ("person", "upsert"), "upsert", cmd_person_upsert)
    p.add_argument("--file", required=True)
    for noun, handler, extra in (("alias", cmd_person_alias_add, "alias"), ("appearance", cmd_person_appearance_add, "appearance")):
        ng = g.add_parser(noun, help=f"{noun} commands").add_subparsers(dest="sub", required=True, parser_class=_Parser)
        handlers[("person", noun, "add")] = handler
        p = ng.add_parser("add", parents=[common])
        if noun == "alias":
            p.add_argument("--person", required=True)
            p.add_argument("--alias", required=True)
            p.add_argument("--platform")
        else:
            p.add_argument("--file", required=True)
    p = leaf(g, ("person", "get"), "get", cmd_person_get)
    p.add_argument("id")
    p = leaf(g, ("person", "list"), "list", cmd_person_list)
    p.add_argument("--needs-review", action="store_true")
    p.add_argument("--limit", type=int, default=100)
    p = leaf(g, ("person", "cards"), "cards", cmd_person_cards)
    p.add_argument("id")
    p.add_argument("--category")
    p = leaf(g, ("person", "merge"), "merge", cmd_person_merge)
    p.add_argument("--from", dest="src", required=True)
    p.add_argument("--into", dest="dst", required=True)

    g = group("skill", "person rulebooks")
    p = leaf(g, ("skill", "upsert"), "upsert", cmd_skill_upsert)
    p.add_argument("--file", required=True)
    p = leaf(g, ("skill", "get"), "get", cmd_skill_get)
    p.add_argument("person")
    p.add_argument("--skill-name")
    p.add_argument("--category")
    p.add_argument("--render", choices=["markdown"])
    p = leaf(g, ("skill", "list"), "list", cmd_skill_list)
    p.add_argument("--person")

    g = group("queue", "exploration queue")
    p = leaf(g, ("queue", "add"), "add", cmd_queue_add)
    p.add_argument("--target")
    p.add_argument("--target-kind", choices=queue_mod.TARGET_KINDS)
    p.add_argument("--platform")
    p.add_argument("--action", default="fetch", choices=queue_mod.ACTIONS)
    p.add_argument("--origin", choices=queue_mod.ORIGINS)
    p.add_argument("--origin-ref")
    p.add_argument("--reason")
    p.add_argument("--priority", type=float, default=0.5)
    p.add_argument("--file")
    p = leaf(g, ("queue", "next"), "next", cmd_queue_next)
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--platform")
    p = leaf(g, ("queue", "update"), "update", cmd_queue_update)
    p.add_argument("id", type=int)
    p.add_argument("--status", required=True, choices=queue_mod.STATUSES)
    p.add_argument("--error")
    p.add_argument("--retry-after", type=int)
    p = leaf(g, ("queue", "list"), "list", cmd_queue_list)
    p.add_argument("--status", choices=queue_mod.STATUSES)
    p.add_argument("--limit", type=int, default=100)

    g = group("gap", "knowledge gaps")
    p = leaf(g, ("gap", "add"), "add", cmd_gap_add)
    p.add_argument("--query", required=True)
    p.add_argument("--query-card")
    p.add_argument("--verdict", required=True, choices=queue_mod.VERDICTS)
    p = leaf(g, ("gap", "list"), "list", cmd_gap_list)
    p.add_argument("--status", default="open", choices=[*queue_mod.GAP_STATUSES, "any"])
    p.add_argument("--limit", type=int, default=100)
    p = leaf(g, ("gap", "update"), "update", cmd_gap_update)
    p.add_argument("id", type=int)
    p.add_argument("--status", required=True, choices=queue_mod.GAP_STATUSES)
    p.add_argument("--filled-by", help="comma-separated card ids")

    g = group("history", "browsing history triage")
    p = leaf(g, ("history", "pending"), "pending", cmd_history_pending)
    p.add_argument("--limit", type=int, default=200)
    p = leaf(g, ("history", "mark"), "mark", cmd_history_mark)
    p.add_argument("urls", nargs="+")
    p.add_argument("--triage", required=True, choices=["queued", "not_relevant", "pending"])

    root.set_defaults(_handlers=handlers)
    return root


def main(argv: list[str] | None = None) -> None:
    output.begin()
    output.setup_logging(config.log_level())
    argv = list(sys.argv[1:] if argv is None else argv)
    fmt = "text" if "--format" in argv and argv[argv.index("--format") + 1:][:1] == ["text"] else "json"
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except CliError as e:
        output.fail("kb", e.code, e.message, e.hint, fmt=fmt)
        return
    path = tuple(x for x in (args.group, args.cmd, getattr(args, "sub", None)) if x)
    handler = parser.get_default("_handlers")[path]
    ctx = Ctx(args)
    try:
        output.run_command("kb." + ".".join(path), lambda: handler(ctx), fmt)
    finally:
        ctx.close()
