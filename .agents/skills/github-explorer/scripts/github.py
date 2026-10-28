#!/usr/bin/env python3
"""GitHub adapter CLI (docs/spec/05-platform-skills.md)."""

from finsocnet.adapters.github import GitHub
from finsocnet.core.platform import run_platform_cli


def _setup(p):
    p.add_argument("item")
    p.add_argument("--branch")


def _tree(adapter, args, conn):
    return adapter.tree(args.item, branch=args.branch)

if __name__ == "__main__":
    run_platform_cli(GitHub(), extra={"tree": (_setup, _tree)})
