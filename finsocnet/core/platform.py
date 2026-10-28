"""Platform adapter contract and the standard CLI (specs/05-platform-skills.md §1)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from finsocnet.core import config, content, output, persons, queue, runs, seen
from finsocnet.core.db import connect
from finsocnet.core.ids import utc_now
from finsocnet.core.output import CliError, Result
from finsocnet.core.records import schema_errors
from finsocnet.core.segments import renumber

Opts = list[tuple[tuple[str, ...], dict[str, Any]]]


def item_ref(ref: str, id: str, kind: str, title: str | None = None, author_handle: str | None = None, published_at: str | None = None,
             snippet: str | None = None, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"ref": ref, "id": id, "kind": kind, "title": title, "author_handle": author_handle, "published_at": published_at,
            "snippet": (snippet or "")[:300] or None, "metrics": metrics or {}, "known": False}


def profile_record(platform: str, source_id: str, handle: str, **kw: Any) -> dict[str, Any]:
    base = {"platform": platform, "source_id": source_id, "handle": handle, "display_name": None, "bio": None, "links": [], "followers": None,
            "verified": None, "avatar_url": None, "profile_url": None, "location": None, "joined_at": None, "known_person_id": None}
    base.update(kw)
    return base


def list_result(items: list[dict[str, Any]], next_cursor: str | None = None, source: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"items": items, "next_cursor": next_cursor, "source": source}


def content_record(id: str, platform: str, content_type: str, segments: list[dict[str, Any]], **kw: Any) -> dict[str, Any]:
    """A ContentRecord dict with defaults; segments are renumbered from 0 and the record is schema-checked."""
    rec: dict[str, Any] = {"id": id, "platform": platform, "content_type": content_type, "segments": renumber(segments),
                           "fetched_at": utc_now(), "metrics": {}, "links": [], "mentions": [], "media": [], "extra": {}}
    rec.update({k: v for k, v in kw.items() if v is not None})
    errs = schema_errors("content_record", rec)
    if errs:
        raise CliError("INTERNAL", f"adapter produced an invalid ContentRecord: {errs[0]['path']} {errs[0]['problem']}", details=errs)
    return rec


def save_raw(platform: str, native_id: str, data: Any, ext: str = "json") -> str:
    """Save the original response under data/raw/<platform>/ so content can be re-parsed without re-fetching."""
    d = config.data_dir() / "raw" / platform
    d.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in native_id)[:120] or hashlib.sha1(native_id.encode()).hexdigest()[:12]
    p = d / f"{safe}.{ext}"
    p.write_text(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return str(p.relative_to(config.repo_root()))


def since_ok(published_at: str | None, since: str | None) -> bool:
    """True when the item is not older than `since` (YYYY-MM-DD); items without a date are kept."""
    if not since or not published_at:
        return True
    return published_at[:10] >= since[:10]


class PlatformAdapter:
    """Base class; subclasses implement what the platform supports and list it in `capabilities`."""

    platform: str = ""
    requires_session: bool = False
    capabilities: frozenset[str] = frozenset()
    #: extra argparse options per subcommand: {"search": [(("--type",), {"default": "video"}), ...]}
    opts: dict[str, Opts] = {}

    def search(self, query: str, *, limit: int = 20, since: str | None = None, **opts: Any) -> list[dict[str, Any]]:
        raise self._unsupported("search")

    def profile(self, target: str, **opts: Any) -> dict[str, Any]:
        raise self._unsupported("profile")

    def list(self, source: str, *, limit: int = 50, cursor: str | None = None, since: str | None = None, **opts: Any) -> dict[str, Any]:
        raise self._unsupported("list")

    def fetch(self, item: str, **opts: Any) -> dict[str, Any]:
        raise self._unsupported("fetch")

    def _unsupported(self, what: str) -> CliError:
        return CliError("UNSUPPORTED", f"{self.platform} does not support '{what}'", f"supported: {', '.join(sorted(self.capabilities)) or 'none'}")


# --- standard CLI ---------------------------------------------------------------------------------------

class _Parser(argparse.ArgumentParser):
    def error(self, message: str):  # type: ignore[override]
        raise CliError("USAGE", message)


def _add_opts(p: argparse.ArgumentParser, opts: Opts | None) -> None:
    for flags, kw in opts or []:
        p.add_argument(*flags, **kw)


def build_parser(adapter: PlatformAdapter, extra: dict[str, tuple[Callable[[argparse.ArgumentParser], None], Callable[..., Any]]] | None = None) -> _Parser:
    root = _Parser(prog=f"{adapter.platform}.py")
    sub = root.add_subparsers(dest="cmd", required=True, parser_class=_Parser)
    common = _Parser(add_help=False)
    common.add_argument("--format", choices=["json", "text"], default="json")
    common.add_argument("--run", type=int)
    common.add_argument("--db")
    common.add_argument("--no-track", action="store_true", help="do not record the items in seen_items (specs/11 §1)")
    s = sub.add_parser("search", parents=[common])
    s.add_argument("query")
    s.add_argument("--new-only", action="store_true", help="drop items that were already fetched or skipped")
    s.add_argument("--limit", type=int, default=20)
    s.add_argument("--since")
    _add_opts(s, adapter.opts.get("search"))
    p = sub.add_parser("profile", parents=[common])
    p.add_argument("target")
    p.add_argument("--ingest", action="store_true")
    _add_opts(p, adapter.opts.get("profile"))
    l = sub.add_parser("list", parents=[common])
    l.add_argument("source")
    l.add_argument("--limit", type=int, default=50)
    l.add_argument("--cursor")
    l.add_argument("--since")
    l.add_argument("--save-cursor", action="store_true")
    l.add_argument("--enqueue", action="store_true")
    l.add_argument("--new-only", action="store_true", help="drop items that were already fetched or skipped")
    _add_opts(l, adapter.opts.get("list"))
    f = sub.add_parser("fetch", parents=[common])
    f.add_argument("item")
    f.add_argument("--ingest", action="store_true")
    f.add_argument("--full", action="store_true", help="print the whole ContentRecord instead of a summary")
    _add_opts(f, adapter.opts.get("fetch"))
    for name, (setup, _handler) in (extra or {}).items():
        e = sub.add_parser(name, parents=[common])
        setup(e)
    return root


def _opts(args: argparse.Namespace, skip: set[str]) -> dict[str, Any]:
    return {k: v for k, v in vars(args).items() if k not in skip}


STD_SKIP = {"cmd", "format", "run", "db", "ingest", "full", "save_cursor", "enqueue", "new_only", "no_track", "query", "target", "source", "item", "limit", "since", "cursor"}


def _mark_known(conn: Any, items: list[dict[str, Any]]) -> None:
    if conn is None or not items:
        return
    ids = [i["id"] for i in items]
    known: set[str] = set()
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        known |= {r[0] for r in conn.execute(f"SELECT id FROM contents WHERE id IN ({','.join('?' * len(chunk))})", chunk)}
    for it in items:
        it["known"] = it["id"] in known


def _track(conn: Any, args: argparse.Namespace, platform: str, items: list[dict[str, Any]], source_id: str | None = None) -> None:
    """Record sightings when the call belongs to a run (`--run` or FINSOCNET_RUN_ID); an ad-hoc look-around leaves no trace."""
    if conn is None or getattr(args, "no_track", False) or not items:
        return
    try:
        run_id = runs.resolve_run(conn, args.run)
        seen.mark_seen(conn, platform, items, run_id, source_id)
    except (CliError, Exception):  # noqa: BLE001 - tracking must never break a fetch
        return


def _visit(conn: Any, args: argparse.Namespace, key: str, status: str, **kw: Any) -> None:
    if conn is None or getattr(args, "no_track", False):
        return
    try:
        seen.set_status(conn, key, status, runs.resolve_run(conn, args.run), **kw)
    except (CliError, Exception):  # noqa: BLE001
        return


def _check_session(adapter: PlatformAdapter, conn: Any) -> None:
    if not adapter.requires_session or conn is None:
        return
    states = [r[0] for r in conn.execute("SELECT login_state FROM browser_sessions WHERE platform = ?", (adapter.platform,))]
    if "logged_in" not in states:
        state = "no session imported" if not states else f"login_state {'/'.join(sorted(set(states)))}"
        raise CliError("LOGIN_REQUIRED", f"{adapter.platform} needs a logged-in session ({state})",
                       f"On your machine: log in to {adapter.platform}, then `finsocnet session export && finsocnet session push`.")


def summarize(rec: dict[str, Any], record_path: str) -> dict[str, Any]:
    segs = rec["segments"]
    return {"id": rec["id"], "content_type": rec["content_type"], "title": rec.get("title"), "url": rec.get("url"), "segments": len(segs),
            "chars": sum(len(s["text"]) for s in segs), "published_at": rec.get("published_at"), "author": rec.get("author"),
            "preview": [s["text"][:160] for s in segs[:3]], "record_path": record_path}


def write_record(rec: dict[str, Any]) -> str:
    d = config.data_dir() / "records" / rec["platform"]
    d.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in rec["id"].split(":", 1)[1])[:120]
    p = d / f"{safe}.json"
    p.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
    return str(p.relative_to(config.repo_root()))


def run_platform_cli(adapter: PlatformAdapter, extra: dict[str, tuple[Callable[[argparse.ArgumentParser], None], Callable[..., Any]]] | None = None,
                     argv: list[str] | None = None) -> None:
    """Builds argparse with the standard subcommands, charges budgets (in `http`/`browser`), marks `known`, emits the envelope."""
    output.begin()
    output.setup_logging(config.log_level())
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser(adapter, extra)
    fmt = "text" if "--format" in argv and argv[argv.index("--format") + 1:][:1] == ["text"] else "json"
    try:
        args = parser.parse_args(argv)
    except CliError as e:
        output.fail(f"{adapter.platform}", e.code, e.message, e.hint, fmt=fmt)
        return
    command = f"{adapter.platform}.{args.cmd}"

    def run() -> Result:
        conn = None
        try:
            conn = connect(config.resolve_path(args.db) if args.db else None) if (args.db or config.db_path().exists()) else None
        except Exception:  # noqa: BLE001
            conn = None
        try:
            if adapter.requires_session or args.cmd in {"fetch", "profile", "list", "search"}:
                if args.cmd not in (extra or {}):
                    _check_session(adapter, conn)
            skip = STD_SKIP
            if extra and args.cmd in extra:
                return Result(extra[args.cmd][1](adapter, args, conn))
            if args.cmd == "search":
                items = adapter.search(args.query, limit=args.limit, since=args.since, **_opts(args, skip))
                _mark_known(conn, items)
                seen.annotate(conn, items)
                _track(conn, args, adapter.platform, items)
                total = len(items)
                if args.new_only:
                    items = [i for i in items if not i["known"]]
                return Result({"items": items, "count": len(items), "hidden_known": total - len(items)})
            if args.cmd == "profile":
                prof = adapter.profile(args.target, **_opts(args, skip))
                data: dict[str, Any] = {"profile": prof}
                if conn is not None and "persons" in {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}:
                    cands = persons.candidates(conn, name=prof.get("display_name"), handle=prof.get("handle"), platform=adapter.platform)
                    data["person_candidates"] = cands
                    if cands and cands[0]["score"] >= 0.9:
                        prof["known_person_id"] = cands[0]["person"]["id"]
                if args.ingest:
                    if conn is None:
                        raise CliError("NOT_FOUND", "database does not exist", "run `finsocnet kb init`")
                    run_id = runs.resolve_run(conn, args.run)
                    data["ingest"] = _ingest_source(conn, prof, run_id)
                return Result(data)
            if args.cmd == "list":
                res = adapter.list(args.source, limit=args.limit, cursor=args.cursor, since=args.since, **_opts(args, skip))
                _mark_known(conn, res["items"])
                seen.annotate(conn, res["items"])
                _track(conn, args, adapter.platform, res["items"], (res.get("source") or {}).get("id"))
                data = dict(res)
                if args.new_only:
                    data["items"] = [i for i in res["items"] if not i["known"]]
                    data["hidden_known"] = len(res["items"]) - len(data["items"])
                if args.enqueue or args.save_cursor:
                    if conn is None:
                        raise CliError("NOT_FOUND", "database does not exist", "run `finsocnet kb init`")
                    run_id = runs.resolve_run(conn, args.run)
                    if args.enqueue:
                        data["enqueued"] = [queue.add(conn, {"target": it["ref"], "target_kind": "url", "platform": adapter.platform, "action": "fetch",
                                                              "origin": "source_refresh", "origin_ref": (res.get("source") or {}).get("id") or args.source,
                                                              "reason": it.get("title") or "new item from source refresh", "priority": 0.4}, run_id)
                                            for it in res["items"] if not it["known"] and it.get("visited") != "queued"]
                        for it in res["items"]:
                            if not it["known"] and it.get("visited") != "queued":
                                _visit(conn, args, it["id"], "queued", platform=adapter.platform, url=it.get("ref"), title=it.get("title"))
                    if args.save_cursor and (res.get("source") or {}).get("id"):
                        from finsocnet.core.db import transaction
                        with transaction(conn):
                            content.upsert_source(conn, {"id": res["source"]["id"], "title": res["source"].get("title")})
                            content.set_source_cursor(conn, res["source"]["id"], res.get("next_cursor"))
                return Result(data)
            rec = adapter.fetch(args.item, **_opts(args, skip))
            path = write_record(rec)
            _visit(conn, args, rec["id"], "fetched" if args.ingest else "seen", platform=adapter.platform, url=rec.get("url"), title=rec.get("title"))
            out = rec if args.full else summarize(rec, path)
            data = {"content": out}
            if args.ingest:
                if conn is None:
                    raise CliError("NOT_FOUND", "database does not exist", "run `finsocnet kb init`")
                run_id = runs.resolve_run(conn, args.run)
                ing = content.add_content(conn, rec, run_id)
                data["ingest"] = ing
                return Result(data, ing.pop("warnings", []))
            return Result(data)
        finally:
            if conn is not None:
                conn.close()

    output.run_command(command, run, fmt)


def _ingest_source(conn: Any, prof: dict[str, Any], run_id: int) -> dict[str, Any]:
    from finsocnet.core.db import transaction
    with transaction(conn):
        return content.upsert_source(conn, {"id": prof["source_id"], "title": prof.get("display_name") or prof.get("handle"), "url": prof.get("profile_url"),
                                            "requires_session": False})
