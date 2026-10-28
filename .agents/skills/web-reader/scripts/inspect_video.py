#!/usr/bin/env python3
"""Deprecated v1 name: wrapper for `web.py discover` (docs/spec/05-platform-skills.md §1.4)."""

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    print("[deprecated] inspect_video.py is a wrapper for `web.py discover`", file=sys.stderr)
    sys.argv = [str(Path(__file__).with_name("web.py")), "discover", *sys.argv[1:]]
    runpy.run_path(sys.argv[0], run_name="__main__")
