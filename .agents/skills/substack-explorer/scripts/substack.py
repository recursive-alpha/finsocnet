#!/usr/bin/env python3
"""Substack adapter CLI (docs/spec/05-platform-skills.md)."""

from finsocnet.adapters.substack import Substack
from finsocnet.core.platform import run_platform_cli


if __name__ == "__main__":
    run_platform_cli(Substack())
