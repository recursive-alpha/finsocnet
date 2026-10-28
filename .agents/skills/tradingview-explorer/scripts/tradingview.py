#!/usr/bin/env python3
"""TradingView adapter CLI (docs/spec/05-platform-skills.md)."""

from finsocnet.adapters.tradingview import TradingView
from finsocnet.core.platform import run_platform_cli

if __name__ == "__main__":
    run_platform_cli(TradingView())
