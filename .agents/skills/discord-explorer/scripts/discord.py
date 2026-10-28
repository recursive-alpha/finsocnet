#!/usr/bin/env python3
"""Discord adapter CLI (specs/05-platform-skills.md)."""

from finsocnet.adapters.discord import Discord
from finsocnet.core.platform import run_platform_cli

if __name__ == "__main__":
    run_platform_cli(Discord())
