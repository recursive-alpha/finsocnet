#!/usr/bin/env python3
"""Facebook adapter CLI (specs/05-platform-skills.md)."""

from finsocnet.adapters.social import Facebook
from finsocnet.core.platform import run_platform_cli

if __name__ == "__main__":
    run_platform_cli(Facebook())
