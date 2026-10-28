"""CLI of the skill-installer skill (specs/07 §5.1)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from finsocnet.core import config, runs, skill_install
from finsocnet.core.db import connect
from finsocnet.core.output import CliError, Result
from finsocnet.core.session_cli import _Parser, _run


def main(argv: list[str] | None = None) -> None:
    p = _Parser(prog="skill_installer.py")
    sub = p.add_subparsers(dest="cmd", required=True, parser_class=_Parser)
    common = _Parser(add_help=False)
    common.add_argument("--format", choices=["json", "text"], default="json")
    common.add_argument("--run", type=int)
    sub.add_parser("resolve", parents=[common]).add_argument("link")
    f = sub.add_parser("fetch", parents=[common])
    f.add_argument("link")
    f.add_argument("--skill")
    c = sub.add_parser("check", parents=[common])
    c.add_argument("staging_id")
    c.add_argument("--as", dest="as_name")
    d = sub.add_parser("diff", parents=[common])
    d.add_argument("staging_id")
    d.add_argument("--against", required=True)
    i = sub.add_parser("install", parents=[common])
    i.add_argument("staging_id")
    i.add_argument("--review", required=True)
    i.add_argument("--user-confirmed", action="store_true")
    i.add_argument("--as", dest="as_name")
    i.add_argument("--replace", action="store_true")
    i.add_argument("--harness")
    i.add_argument("--model")
    l = sub.add_parser("list", parents=[common])
    l.add_argument("--installed", action="store_true")
    o = sub.add_parser("outdated", parents=[common])
    o.add_argument("name", nargs="?")
    r = sub.add_parser("remove", parents=[common])
    r.add_argument("name")
    r.add_argument("--user-confirmed", action="store_true")
    sub.add_parser("discard", parents=[common]).add_argument("staging_id")

    def run_id(args) -> int:
        conn = connect()
        try:
            return runs.resolve_run(conn, args.run)
        finally:
            conn.close()

    def handler(a) -> Result:
        if a.cmd == "resolve":
            return Result(skill_install.resolve(a.link))
        if a.cmd == "fetch":
            return Result(skill_install.fetch(a.link, a.skill))
        if a.cmd == "check":
            return Result(skill_install.check(a.staging_id, a.as_name))
        if a.cmd == "diff":
            return Result(skill_install.diff(a.staging_id, a.against))
        if a.cmd == "install":
            rid = run_id(a)
            try:
                review = json.loads(Path(a.review).read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                raise CliError("REVIEW_INCOMPLETE", f"cannot read the review file: {e}") from e
            return Result(skill_install.install(a.staging_id, review, a.user_confirmed, a.as_name, a.replace, rid, {"harness": a.harness, "model": a.model}))
        if a.cmd == "list":
            return Result({"skills": skill_install.list_skills(a.installed)})
        if a.cmd == "outdated":
            return Result({"skills": skill_install.outdated(a.name)})
        if a.cmd == "remove":
            run_id(a)
            return Result(skill_install.remove(a.name, a.user_confirmed))
        import shutil
        shutil.rmtree(skill_install.staging_dir(a.staging_id))
        return Result({"discarded": a.staging_id})

    _run("skill_installer", p, list(sys.argv[1:] if argv is None else argv), handler)
