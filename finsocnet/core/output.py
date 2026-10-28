"""JSON envelope, exit codes and the command runner (docs/spec/00-conventions.md §3)."""

from __future__ import annotations

import json
import logging
import sys
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable

EXIT_CODES: dict[str, int] = {
    "INTERNAL": 1,
    "USAGE": 2,
    "RUN_REQUIRED": 2,
    "UNSUPPORTED": 2,
    "LOGIN_REQUIRED": 3,
    "CHECKPOINT": 3,
    "RATE_LIMITED": 4,
    "BUDGET_EXHAUSTED": 4,
    "NOT_FOUND": 5,
    "GONE": 5,
    "VALIDATION_ERROR": 6,
    "VOCAB_UNKNOWN": 6,
    "QUOTE_NOT_FOUND": 6,
    "GRAMMAR_ERROR": 6,
    "REVIEW_INCOMPLETE": 6,
    "SKILL_INVALID": 6,
    "BLOCKED": 6,
    "BROWSER_UNAVAILABLE": 7,
    "CONFLICT": 8,
}

_started = time.monotonic()
log = logging.getLogger("finsocnet")


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        stream=sys.stderr,
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(levelname)s %(name)s: %(message)s",
    )


def begin() -> None:
    global _started
    _started = time.monotonic()


def elapsed_ms() -> int:
    return int((time.monotonic() - _started) * 1000)


class CliError(Exception):
    """Raised by commands; the runner turns it into a failure envelope."""

    def __init__(
        self,
        code: str,
        message: str,
        hint: str | None = None,
        retry_after_sec: int | None = None,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint
        self.retry_after_sec = retry_after_sec
        self.details = details


@dataclass
class Result:
    """What a command returns: data plus optional warnings and meta."""

    data: Any = None
    warnings: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


def _dump(obj: dict[str, Any], fmt: str = "json") -> str:
    if fmt == "text":
        return json.dumps(obj, ensure_ascii=False, indent=2, default=str)
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str)


def success_envelope(command: str, data: Any, warnings: list[str] | None = None, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    m = {"elapsed_ms": elapsed_ms()}
    m.update(meta or {})
    return {"ok": True, "command": command, "data": data, "warnings": warnings or [], "meta": m}


def failure_envelope(
    command: str,
    code: str,
    message: str,
    hint: str | None = None,
    retry_after_sec: int | None = None,
    details: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message, "hint": hint, "retry_after_sec": retry_after_sec}
    if details is not None:
        error["details"] = details
    m = {"elapsed_ms": elapsed_ms()}
    m.update(meta or {})
    return {"ok": False, "command": command, "error": error, "warnings": warnings or [], "meta": m}


def emit(command: str, data: Any, warnings: list[str] | None = None, meta: dict[str, Any] | None = None, fmt: str = "json") -> None:
    """Print the success envelope (exactly one JSON object on stdout)."""
    sys.stdout.write(_dump(success_envelope(command, data, warnings, meta), fmt) + "\n")
    sys.stdout.flush()


def fail(
    command: str,
    code: str,
    message: str,
    hint: str | None = None,
    retry_after_sec: int | None = None,
    details: list[dict[str, Any]] | None = None,
    fmt: str = "json",
) -> "None":
    """Print the failure envelope and exit with the mapped code."""
    sys.stdout.write(_dump(failure_envelope(command, code, message, hint, retry_after_sec, details), fmt) + "\n")
    sys.stdout.flush()
    sys.exit(EXIT_CODES.get(code, 1))


def run_command(command: str, func: Callable[[], Result | Any], fmt: str = "json") -> None:
    """Run `func`, emitting exactly one envelope; exits non-zero on failure."""
    try:
        res = func()
    except CliError as e:
        fail(command, e.code, e.message, e.hint, e.retry_after_sec, e.details, fmt)
        return
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001 - last resort: still emit an envelope
        traceback.print_exc(file=sys.stderr)
        fail(command, "INTERNAL", f"{type(e).__name__}: {e}", "see traceback on stderr", fmt=fmt)
        return
    if isinstance(res, Result):
        emit(command, res.data, res.warnings, res.meta, fmt)
    else:
        emit(command, res, fmt=fmt)
