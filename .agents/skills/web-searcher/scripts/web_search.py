#!/usr/bin/env python3
"""WebSearch adapter CLI (specs/05-platform-skills.md)."""

from finsocnet.adapters.web_search import WebSearch
from finsocnet.core.platform import run_platform_cli

if __name__ == "__main__":
    run_platform_cli(WebSearch())
