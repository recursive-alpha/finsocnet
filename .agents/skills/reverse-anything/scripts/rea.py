#!/usr/bin/env python3
"""reverse-anything CLI: static REA inspection of unreadable artifacts -> text content (specs/13-reverse-anything.md)."""

import json

from finsocnet.adapters import rea
from finsocnet.core.platform import run_platform_cli


def _doctor_setup(p):
    pass


def _doctor(adapter, args, conn):
    return rea.doctor()


def _kinds_setup(p):
    pass


def _kinds(adapter, args, conn):
    return {"kinds": rea.COMMANDS, "default": "auto", "note": "static, read-only commands only; runtime capture, adb, debuggers and browser scenarios are not exposed here"}


if __name__ == "__main__":
    run_platform_cli(rea.Rea(), extra={"doctor": (_doctor_setup, _doctor), "kinds": (_kinds_setup, _kinds)})
