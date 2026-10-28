#!/usr/bin/env python3
"""Anna's Archive adapter CLI (docs/spec/05-platform-skills.md §2.12)."""

from finsocnet.adapters.annas import Annas
from finsocnet.core.platform import run_platform_cli


def _setup(p):
    p.add_argument("item")
    p.add_argument("--mirror", type=int, default=0)


def _download(adapter, args, conn):
    return adapter.download(args.item, args.mirror)


if __name__ == "__main__":
    run_platform_cli(Annas(), extra={"download": (_setup, _download)})
