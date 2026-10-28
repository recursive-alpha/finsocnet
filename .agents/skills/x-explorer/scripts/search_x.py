#!/usr/bin/env python3
"""Deprecated v1 name: wrapper for `search` (docs/spec/05-platform-skills.md §1.4)."""

from finsocnet.adapters.x import X
from finsocnet.core.legacy import run_legacy

if __name__ == "__main__":
    run_legacy(X(), "search")
