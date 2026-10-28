#!/usr/bin/env python3
"""Deprecated v1 name: wrapper for `fetch` (docs/spec/05-platform-skills.md §1.4)."""

from finsocnet.adapters.annas import Annas
from finsocnet.core.legacy import run_legacy

if __name__ == "__main__":
    run_legacy(Annas(), "fetch")
