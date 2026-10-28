#!/usr/bin/env python3
"""Hacker News adapter CLI (specs/05-platform-skills.md §4)."""

from finsocnet.adapters.hackernews import HackerNews
from finsocnet.core.platform import run_platform_cli

if __name__ == "__main__":
    run_platform_cli(HackerNews())
