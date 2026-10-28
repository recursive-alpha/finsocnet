"""Acquisition helpers for browser-based adapters. Every call goes through `finsocnet.core.browser.page()` (one agent Chrome,
budgets, login/checkpoint guard); parsing lives in each adapter's pure `parse_*` functions so it can be tested with fixtures."""

from __future__ import annotations

import json
import os
from typing import Any

from finsocnet.core import browser
from finsocnet.core.output import CliError

TIMEOUT_MS = int(os.getenv("BROWSER_TIMEOUT_MS", "30000"))


def load_html(platform: str, url: str, *, wait: str = "domcontentloaded", scrolls: int = 0, block: tuple[str, ...] = ("media", "font")) -> tuple[str, str]:
    """Open `url`, optionally scroll, return `(final_url, rendered_html)`."""
    with browser.page(platform, block=block) as pg:
        browser.goto(pg, platform, url, wait=wait, timeout_ms=TIMEOUT_MS)
        if wait == "networkidle":
            pass
        if scrolls:
            browser.scroll(pg, platform, max_scrolls=scrolls)
        return pg.url, pg.content()


def load_json(platform: str, url: str) -> Any:
    """Load a `.json` URL as a page (cookies and proxy apply) and parse the body."""
    with browser.page(platform, block=("media", "font", "image", "stylesheet")) as pg:
        browser.goto(pg, platform, url, timeout_ms=TIMEOUT_MS)
        txt = pg.inner_text("body")
        try:
            return json.loads(txt)
        except ValueError as e:
            raise CliError("CHECKPOINT", f"{platform} did not answer with JSON at {url}", "open the URL once in the agent browser to clear a bot check") from e


def capture(platform: str, url: str, pattern: str, *, scrolls: int = 5, until: Any = None) -> tuple[str, list[Any]]:
    """Navigate and scroll while collecting the JSON bodies of responses whose URL matches `pattern`."""
    with browser.page(platform, block=("media", "font")) as pg:
        with browser.capture_json(pg, pattern) as bodies:
            browser.goto(pg, platform, url, timeout_ms=TIMEOUT_MS)
            if scrolls:
                browser.scroll(pg, platform, max_scrolls=scrolls, until=(lambda: until(bodies)) if until else None)
            pg.wait_for_timeout(1200)
            return pg.url, list(bodies)
