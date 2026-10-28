#!/usr/bin/env python3
"""Deprecated v1 name: wrapper for `papers.py trending` (docs/spec/05-platform-skills.md §1.4)."""

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    print("[deprecated] explore_trending.py is a wrapper for `papers.py trending`", file=sys.stderr)
    sys.argv = [str(Path(__file__).with_name("papers.py")), "trending", *sys.argv[1:]]
    runpy.run_path(sys.argv[0], run_name="__main__")
