"""`finsocnet serve`: a warm, local-only command runner for the web UI.

Every `uv run finsocnet ...` pays Python start-up and imports (about a second) and, for semantic search, loads the
embedding model again. This process keeps them loaded and runs the same CLI entry points in-process, one request at a time
(the CLI prints to stdout, so runs are serialized). The contract is unchanged: the answer is the JSON envelope the CLI prints.
Only `kb`, `search` and `strategy` are accepted, and only from the local machine."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ALLOWED = {"kb", "search", "strategy"}
_lock = threading.Lock()


def run_cli(args: list[str]) -> tuple[str, int]:
    """Run `finsocnet <args>` in this process; return (stdout, exit code)."""
    if not args or args[0] not in ALLOWED:
        return json.dumps({"ok": False, "command": " ".join(args[:2]), "error": {"code": "UNSUPPORTED", "message": f"only {', '.join(sorted(ALLOWED))} are served", "hint": None, "retry_after_sec": None}}), 2
    from finsocnet import cli
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with _lock, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        old = sys.argv
        sys.argv = ["finsocnet", *args]
        try:
            cli.main()
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        finally:
            sys.argv = old
    return out.getvalue(), code


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):  # quiet
        pass

    def _send(self, status: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self._send(200, {"ok": True, "service": "finsocnet-serve"}) if self.path == "/health" else self._send(404, {"ok": False})

    def do_POST(self):
        if self.path != "/run":
            return self._send(404, {"ok": False})
        try:
            args = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")["args"]
            assert isinstance(args, list) and all(isinstance(a, str) for a in args)
        except Exception:  # noqa: BLE001
            return self._send(400, {"ok": False, "error": "body must be {\"args\": [strings]}"})
        t0 = time.time()
        stdout, code = run_cli(args)
        self._send(200, {"stdout": stdout, "code": code, "ms": int((time.time() - t0) * 1000)})


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="finsocnet serve", description="Warm local command runner for the web UI (127.0.0.1 only)")
    p.add_argument("--port", type=int, default=8787)
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--no-warm", action="store_true", help="do not preload the embedding model")
    a = p.parse_args(argv)
    if not a.no_warm:
        threading.Thread(target=lambda: run_cli(["kb", "stats"]), daemon=True).start()
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"finsocnet serve on http://{a.host}:{a.port}", file=sys.stderr, flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
