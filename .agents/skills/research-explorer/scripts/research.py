#!/usr/bin/env python3
"""Research adapter CLI (docs/spec/05-platform-skills.md)."""

from finsocnet.adapters.research import Research
from finsocnet.core.platform import run_platform_cli


if __name__ == "__main__":
    run_platform_cli(Research())
