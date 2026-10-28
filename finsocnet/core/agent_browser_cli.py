"""CLI for the agent browser: `agent_browser.py start|stop|status|open|vnc` (specs/04 §6.1)."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from finsocnet.core import browser, browser_proc, budgets, config, output
from finsocnet.core.db import connect
from finsocnet.core.output import CliError, Result
from finsocnet.core.session_cli import _Parser, _run


def main(argv: list[str] | None = None) -> None:
    p = _Parser(prog="agent_browser.py")
    sub = p.add_subparsers(dest="cmd", required=True, parser_class=_Parser)
    common = _Parser(add_help=False)
    common.add_argument("--format", choices=["json", "text"], default="json")
    s = sub.add_parser("start", parents=[common])
    s.add_argument("--headless", action="store_true")
    s.add_argument("--proxy")
    s.add_argument("--no-reapply", action="store_true")
    sub.add_parser("stop", parents=[common])
    st = sub.add_parser("status", parents=[common])
    st.add_argument("--ip", action="store_true", help="also fetch the egress IP through the browser")
    o = sub.add_parser("open", parents=[common])
    o.add_argument("url")
    o.add_argument("--platform", default="default")
    o.add_argument("--screenshot", action="store_true")
    v = sub.add_parser("vnc", parents=[common])
    v.add_argument("--stop", action="store_true")

    def handler(args: argparse.Namespace) -> Result:
        if args.cmd == "start":
            res = browser_proc.start(args.headless, args.proxy)
            if not args.no_reapply and (config.data_dir() / "sessions" / "store.age").exists():
                from finsocnet.core.sessions import import_remote
                try:
                    sink = import_remote.CdpSink()
                    try:
                        res["reapplied"] = import_remote.reapply(sink)
                    finally:
                        sink.close()
                except CliError as e:
                    res["reapply_error"] = e.message
            return Result(res)
        if args.cmd == "stop":
            return Result(browser_proc.stop())
        if args.cmd == "status":
            data = browser_proc.status(args.ip)
            conn = connect()
            try:
                data["budgets"] = {pf: budgets.remaining(conn, pf) for pf in ("default", *browser.platforms())[:6]}
            finally:
                conn.close()
            return Result(data)
        if args.cmd == "open":
            with browser.page(args.platform, block=()) as pg:
                browser.goto(pg, args.platform, args.url)
                res = {"url": pg.url, "title": pg.title()}
                if args.screenshot:
                    d = config.data_dir() / "screenshots"
                    d.mkdir(parents=True, exist_ok=True)
                    path = d / "open.png"
                    pg.screenshot(path=str(path))
                    res["screenshot"] = str(path)
            return Result(res)
        # vnc
        pid_file = browser.profile_dir() / ".vnc.pid"
        if args.stop:
            if pid_file.exists():
                import os, signal
                for pid in pid_file.read_text().split():
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                    except OSError:
                        pass
                pid_file.unlink()
            return Result({"vnc": "stopped"})
        if not shutil.which("x11vnc"):
            raise CliError("UNSUPPORTED", "x11vnc is not installed", "install x11vnc (and noVNC) on the host")
        display = __import__("os").getenv("XVFB_DISPLAY", ":99")
        proc = subprocess.Popen(["x11vnc", "-display", display, "-localhost", "-forever", "-nopw", "-rfbport", "5900", "-quiet"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        pids = [proc.pid]
        novnc = shutil.which("novnc_proxy") or shutil.which("websockify")
        if novnc:
            web = subprocess.Popen([novnc, "--listen", "127.0.0.1:6080", "--vnc", "127.0.0.1:5900"] if "novnc_proxy" in novnc else [novnc, "127.0.0.1:6080", "127.0.0.1:5900"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            pids.append(web.pid)
        pid_file.write_text(" ".join(map(str, pids)))
        return Result({"vnc": "started", "tunnel": "ssh -L 6080:127.0.0.1:6080 user@host", "url": "http://localhost:6080/vnc.html" if novnc else None, "rfb": "127.0.0.1:5900"})

    _run("agent_browser", p, list(sys.argv[1:] if argv is None else argv), handler)
