"""Thin wrappers for the v1 script names (docs/spec/05 §1.4). They translate old flags to the new subcommands and are removed in Phase 8."""

from __future__ import annotations

import sys
from typing import Any, Callable

DROP_WITH_VALUE = {"--save-json", "--output", "-o", "--tab-limit", "--session-file", "--out"}
RENAME = {"--ingest-db": "--ingest"}


def translate(argv: list[str]) -> list[str]:
    out, skip = [], False
    for a in argv:
        if skip:
            skip = False
            continue
        if a in DROP_WITH_VALUE:
            skip = True
            print(f"[deprecated] {a} is ignored; fetch returns a record path and --ingest stores it", file=sys.stderr)
            continue
        out.append(RENAME.get(a, a))
    return out


def run_legacy(adapter: Any, subcommand: str, extra: dict[str, Any] | None = None, argv: list[str] | None = None) -> None:
    from finsocnet.core.platform import run_platform_cli
    print(f"[deprecated] this script name is a wrapper for `{adapter.platform}.py {subcommand}` and will be removed", file=sys.stderr)
    run_platform_cli(adapter, extra=extra, argv=[subcommand, *translate(list(sys.argv[1:] if argv is None else argv))])
