#!/usr/bin/env python3
"""RSS adapter CLI (specs/05-platform-skills.md)."""

from finsocnet.adapters.rss import RSS
from finsocnet.core.platform import run_platform_cli


def _setup(p):
    p.add_argument("url")


def _discover(adapter, args, conn):
    return adapter.discover(args.url)


if __name__ == "__main__":
    run_platform_cli(RSS(), extra={"discover": (_setup, _discover)})
