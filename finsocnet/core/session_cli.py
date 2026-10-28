"""CLI for the session bridge: `finsocnet session …` (local machine) and `session_bridge.py …` (remote host)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from finsocnet.core import config, output, runs
from finsocnet.core.db import connect
from finsocnet.core.output import CliError, Result
from finsocnet.core.sessions import bundle, export_local, import_remote


class _Parser(argparse.ArgumentParser):
    def error(self, message: str):  # type: ignore[override]
        raise CliError("USAGE", message)


def _run(command: str, parser: argparse.ArgumentParser, argv: list[str], handler) -> None:
    output.begin()
    output.setup_logging(config.log_level())
    try:
        args = parser.parse_args(argv)
    except CliError as e:
        output.fail(command, e.code, e.message, e.hint)
        return
    output.run_command(f"{command}.{args.cmd}", lambda: handler(args), getattr(args, "format", "json"))


# --- local: finsocnet session ----------------------------------------------------------------------------

def local_main(argv: list[str] | None = None) -> None:
    p = _Parser(prog="finsocnet session")
    sub = p.add_subparsers(dest="cmd", required=True, parser_class=_Parser)
    a = sub.add_parser("init-local")
    a.add_argument("--recipient", required=True)
    a.add_argument("--remote", required=True)
    a.add_argument("--remote-path", required=True)
    b = sub.add_parser("export")
    b.add_argument("--browser", default="chrome", choices=["chrome", "chromium", "brave", "edge", "firefox"])
    b.add_argument("--profile", default="Default")
    b.add_argument("--from-dir")
    b.add_argument("--history", action="store_true")
    b.add_argument("--exclude", action="append", default=[], metavar="DOMAIN")
    b.add_argument("--out")
    c = sub.add_parser("push")
    c.add_argument("file", nargs="?")
    c.add_argument("--no-import", action="store_true")

    def handler(args: argparse.Namespace) -> Result:
        if args.cmd == "init-local":
            return Result(export_local.init_local(args.recipient, args.remote, args.remote_path))
        if args.cmd == "export":
            return Result(export_local.export(args.browser, args.profile, args.from_dir, args.history, args.exclude, args.out))
        return Result(export_local.push(args.file, not args.no_import))

    _run("session", p, list(sys.argv[1:] if argv is None else argv), handler)


# --- remote: session_bridge.py ---------------------------------------------------------------------------

def _sink(required: bool = True) -> import_remote.Sink | None:
    try:
        return import_remote.CdpSink()
    except CliError:
        if required:
            raise
        return None


def bridge_main(argv: list[str] | None = None) -> None:
    p = _Parser(prog="session_bridge.py")
    sub = p.add_subparsers(dest="cmd", required=True, parser_class=_Parser)
    common = _Parser(add_help=False)
    common.add_argument("--run", type=int)
    common.add_argument("--db")
    common.add_argument("--format", choices=["json", "text"], default="json")
    k = sub.add_parser("keygen", parents=[common])
    k.add_argument("--force", action="store_true")
    i = sub.add_parser("import", parents=[common])
    i.add_argument("path")
    i.add_argument("--no-verify", action="store_true")
    s = sub.add_parser("status", parents=[common])
    s.add_argument("--platform")
    v = sub.add_parser("verify", parents=[common])
    g = v.add_mutually_exclusive_group()
    g.add_argument("--platform")
    g.add_argument("--all", action="store_true")
    sub.add_parser("reapply", parents=[common])
    r = sub.add_parser("purge", parents=[common])
    r.add_argument("--domain", action="append", default=None)
    r.add_argument("--all", action="store_true")

    def handler(args: argparse.Namespace) -> Result:
        if args.cmd == "keygen":
            path = import_remote.identity_path()
            if path.exists() and not args.force:
                return Result({"identity_file": str(path), "recipient": bundle.recipient_of(path), "created": False})
            return Result({"identity_file": str(path), "recipient": bundle.generate_identity(path), "created": True,
                           "next": "give this recipient to `finsocnet session init-local --recipient …` on your machine"})
        conn = connect(config.resolve_path(args.db) if args.db else None)
        try:
            if args.cmd == "import":
                run_id = runs.resolve_run(conn, args.run)
                sink = _sink()
                try:
                    return Result(import_remote.import_session(conn, Path(args.path), run_id, sink, not args.no_verify))
                finally:
                    getattr(sink, "close", lambda: None)()
            if args.cmd == "status":
                sink = _sink(False)
                try:
                    return Result(import_remote.status(conn, sink, args.platform))
                finally:
                    getattr(sink, "close", lambda: None)()
            if args.cmd == "verify":
                sink = _sink()
                try:
                    if args.platform:
                        return Result(import_remote.verify(conn, sink, args.platform))
                    return Result({"platforms": import_remote.verify_all(conn, sink)})
                finally:
                    getattr(sink, "close", lambda: None)()
            if args.cmd == "reapply":
                sink = _sink()
                try:
                    return Result(import_remote.reapply(sink))
                finally:
                    getattr(sink, "close", lambda: None)()
            if args.cmd == "purge":
                runs.resolve_run(conn, args.run)
                if not args.all and not args.domain:
                    raise CliError("USAGE", "give --domain D (repeatable) or --all")
                sink = _sink(False)
                try:
                    return Result(import_remote.purge(conn, sink, None if args.all else args.domain))
                finally:
                    getattr(sink, "close", lambda: None)()
            raise CliError("USAGE", "unknown command")
        finally:
            conn.close()

    _run("session_bridge", p, list(sys.argv[1:] if argv is None else argv), handler)
