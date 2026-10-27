#!/usr/bin/env python3
"""
Session manager for Anna's Archive (https://annas-archive.gl).
Manages DDoS-Guard clearance cookies and membership secret keys, saving state to data/sessions/annas_archive_session.json.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
DEFAULT_SESSION_FILE = Path(os.getenv("ANNAS_ARCHIVE_SESSION_FILE", "data/sessions/annas_archive_session.json"))
BASE_URL = os.getenv("ANNAS_ARCHIVE_URL", "https://annas-archive.gl")


def interactive_session_capture(session_file: Path = DEFAULT_SESSION_FILE, url: str = BASE_URL) -> Path:
    """Launch visible browser for user to pass DDoS-Guard, then save session state."""
    session_file.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        print(f"Launching visible browser for Anna's Archive ({url})...")
        print("Please complete the DDoS-Guard browser check in the browser window.")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 850},
        )
        page = context.new_page()
        page.goto(f"{url}/search?q=trading")

        print("Waiting for check to clear and search page to load (up to 90s)...")
        try:
            # Wait until title is no longer DDOS-GUARD or check=1 is gone
            page.wait_for_function("() => !document.title.toLowerCase().includes('ddos') && !window.location.href.includes('check=1')", timeout=90000)
            context.storage_state(path=str(session_file))
            print(f"DDoS-Guard cleared successfully! Saved session state to: {session_file}")
        except Exception as e:
            print(f"Interactive session capture timed out or error: {e}", file=sys.stderr)
            # Try saving state anyway if cookies exist
            context.storage_state(path=str(session_file))
        finally:
            browser.close()

    return session_file


def verify_session(session_file: Path = DEFAULT_SESSION_FILE, url: str = BASE_URL) -> bool:
    """Verify if saved session state can access Anna's Archive search without challenge."""
    if not session_file.exists():
        print(f"No session file found at: {session_file}")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            storage_state=str(session_file),
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = context.new_page()
        print(f"Testing session against {url}/search?q=test...", file=sys.stderr)
        page.goto(f"{url}/search?q=test", timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        curr_url = page.url
        curr_title = page.title()
        browser.close()

        if "check=1" in curr_url or "ddos" in curr_title.lower():
            print(f"Session verification failed (DDoS-Guard active at: {curr_url})")
            return False

        print(f"Session valid! Successfully accessed Anna's Archive ({curr_title}).")
        return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage Anna's Archive session state.")
    parser.add_argument("--interactive", action="store_true", help="Open browser to complete DDoS-Guard check")
    parser.add_argument("--verify", action="store_true", help="Verify saved session state")
    parser.add_argument("--session-file", type=Path, default=DEFAULT_SESSION_FILE, help="Path to session JSON")
    parser.add_argument("--url", default=BASE_URL, help="Base Anna's Archive URL")

    args = parser.parse_args()

    if args.verify:
        ok = verify_session(args.session_file, url=args.url)
        return 0 if ok else 1

    if args.interactive:
        interactive_session_capture(args.session_file, url=args.url)
        return 0

    print("Usage:")
    print("  uv run .agents/skills/annas-archive-explorer/scripts/session_manager.py --interactive")
    print("  uv run .agents/skills/annas-archive-explorer/scripts/session_manager.py --verify")
    return 1


if __name__ == "__main__":
    sys.exit(main())
