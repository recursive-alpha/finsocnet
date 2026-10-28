#!/usr/bin/env python3
"""Web adapter CLI (specs/05-platform-skills.md)."""

from finsocnet.adapters.web import Web
from finsocnet.core.platform import run_platform_cli


def _setup(p):
    p.add_argument("url")


def _discover(adapter, args, conn):
    return {"items": adapter.discover(args.url)}

if __name__ == "__main__":
    run_platform_cli(Web(), extra={"discover": (_setup, _discover)})
