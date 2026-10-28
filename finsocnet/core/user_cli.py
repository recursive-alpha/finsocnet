"""User-facing commands on the remote host: `finsocnet explore add`, `finsocnet persons review`, `finsocnet feedback` (docs/spec/07 §1)."""

from __future__ import annotations

import sys
from typing import Any

from finsocnet.core import config, dispatch, output, persons, queue, runs
from finsocnet.core.db import connect
from finsocnet.core.output import CliError, Result
from finsocnet.core.session_cli import _Parser, _run


def _conn() -> Any:
    if not config.db_path().exists():
        raise CliError("NOT_FOUND", "database does not exist", "run `finsocnet kb init`")
    return connect()


def _user_run(conn: Any, skill: str, goal: str) -> int:
    return runs.start_run(conn, skill, goal, "manual", "user")


def explore_main(argv: list[str] | None = None) -> None:
    p = _Parser(prog="finsocnet explore")
    sub = p.add_subparsers(dest="cmd", required=True, parser_class=_Parser)
    a = sub.add_parser("add")
    a.add_argument("target", help="URL, @handle, person id or free-text query")
    a.add_argument("--priority", type=float, default=0.95)
    a.add_argument("--platform")
    a.add_argument("--reason")
    a.add_argument("--format", choices=["json", "text"], default="json")
    sub.add_parser("show").add_argument("--limit", type=int, default=20)

    def handler(args) -> Result:
        conn = _conn()
        try:
            if args.cmd == "show":
                return Result({"items": queue.list_items(conn, "pending", args.limit)})
            known = {r[0] for r in conn.execute("SELECT id FROM persons")}
            c = dispatch.classify(args.target, known)
            rid = _user_run(conn, "finsocnet-cli", f"explore add {args.target[:80]}")
            res = queue.add(conn, {"target": args.target, "target_kind": c["target_kind"], "platform": args.platform or c["platform"], "action": c["action"], "origin": "user",
                                   "priority": args.priority, "reason": args.reason or "added by the user"}, rid)
            runs.end_run(conn, rid, "success", {"queued": res["id"]})
            return Result({**res, "classified_as": c})
        finally:
            conn.close()

    _run("explore", p, list(sys.argv[1:] if argv is None else argv), handler)


def persons_main(argv: list[str] | None = None) -> None:
    p = _Parser(prog="finsocnet persons")
    sub = p.add_subparsers(dest="cmd", required=True, parser_class=_Parser)
    r = sub.add_parser("review", help="resolve appearances the matcher was unsure about")
    r.add_argument("--list", action="store_true", help="only list them (non-interactive)")
    r.add_argument("--confirm", type=int)
    r.add_argument("--reject", type=int)
    r.add_argument("--reassign", type=int)
    r.add_argument("--to")
    r.add_argument("--format", choices=["json", "text"], default="json")

    def handler(args) -> Result:
        conn = _conn()
        try:
            rid = None
            for flag, action in (("confirm", "confirm"), ("reject", "reject"), ("reassign", "reassign")):
                if getattr(args, flag) is not None:
                    rid = rid or _user_run(conn, "finsocnet-cli", f"persons review {action}")
                    return Result(persons.review_appearance(conn, getattr(args, flag), action, args.to))
            pending = persons.list_persons(conn, needs_review=True)
            if args.list or not sys.stdin.isatty():
                return Result({"needs_review": pending, "hint": "resolve with --confirm ID, --reject ID or --reassign ID --to PERSON"})
            done = []
            for a in pending:
                print(f"#{a['appearance_id']} {a['canonical_name']} as {a['role']} in {a['content_id'] or a['source_id']} (confidence {a['match_confidence']:.2f}): {a['evidence'] or ''}", file=sys.stderr)
                ans = input("[c]onfirm / [r]eject / [m]ove to another person / [s]kip / [q]uit: ").strip().lower()
                if ans == "q":
                    break
                if ans == "c":
                    done.append(persons.review_appearance(conn, a["appearance_id"], "confirm"))
                elif ans == "r":
                    done.append(persons.review_appearance(conn, a["appearance_id"], "reject"))
                elif ans == "m":
                    done.append(persons.review_appearance(conn, a["appearance_id"], "reassign", input("person id: ").strip()))
            return Result({"reviewed": done, "remaining": len(pending) - len(done)})
        finally:
            conn.close()

    _run("persons", p, list(sys.argv[1:] if argv is None else argv), handler)


def feedback_main(argv: list[str] | None = None) -> None:
    p = _Parser(prog="finsocnet feedback")
    p.set_defaults(cmd="add")
    p.add_argument("target_type", choices=runs.FEEDBACK_TARGETS)
    p.add_argument("target_id")
    p.add_argument("rating", help="+1, -1 or 0")
    p.add_argument("comment", nargs="*")
    p.add_argument("--format", choices=["json", "text"], default="json")

    def handler(args) -> Result:
        conn = _conn()
        try:
            rating = {"+1": 1, "1": 1, "-1": -1, "0": 0}.get(args.rating)
            if rating is None:
                raise CliError("USAGE", "rating must be +1, -1 or 0")
            return Result({"feedback_id": runs.add_feedback(conn, args.target_type, args.target_id, rating, " ".join(args.comment) or None)})
        finally:
            conn.close()

    _run("feedback", p, list(sys.argv[1:] if argv is None else argv), handler)
