#!/usr/bin/env python3
"""Forum adapter CLI (docs/spec/05-platform-skills.md)."""

from finsocnet.adapters.forum import Forum
from finsocnet.core.platform import run_platform_cli


def _setup(p):
    p.add_argument("url")


def _detect(adapter, args, conn):
    return adapter.detect(args.url)

if __name__ == "__main__":
    run_platform_cli(Forum(), extra={"detect": (_setup, _detect)})
