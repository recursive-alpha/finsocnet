#!/usr/bin/env python3
"""Papers adapter CLI (docs/spec/05-platform-skills.md)."""

from finsocnet.adapters.papers import Papers
from finsocnet.core.platform import run_platform_cli


def _setup(p):
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--has-code", action="store_true")


def _trending(adapter, args, conn):
    return {"items": adapter.trending(limit=args.limit, has_code=args.has_code)}


if __name__ == "__main__":
    run_platform_cli(Papers(), extra={"trending": (_setup, _trending)})
