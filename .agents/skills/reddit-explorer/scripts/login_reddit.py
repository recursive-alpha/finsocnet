#!/usr/bin/env python3
"""
Session and authentication manager for Reddit.
Supports interactive browser login or automated username/password login,
saving session state to data/sessions/reddit_session.json.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
DEFAULT_SESSION_FILE = Path(os.getenv("REDDIT_SESSION_FILE", "data/sessions/reddit_session.json"))


def automated_login(username: str, password: str, session_file: Path = DEFAULT_SESSION_FILE) -> bool:
    session_file.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--host-resolver-rules=MAP www.reddit.com 151.101.1.140"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("Navigating to Reddit login page...", file=sys.stderr)
        page.goto("https://www.reddit.com/login", timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        try:
            page.fill('input[name="username"], #login-username', username)
            page.fill('input[name="password"], #login-password', password)
            page.press('input[name="password"], #login-password', "Enter")
            page.wait_for_timeout(5000)

            context.storage_state(path=str(session_file))
            print(f"Login completed. Saved Reddit session to: {session_file}", file=sys.stderr)
            browser.close()
            return True
        except Exception as e:
            print(f"Automated Reddit login failed: {e}", file=sys.stderr)
            browser.close()
            return False


def interactive_login(session_file: Path = DEFAULT_SESSION_FILE) -> Path:
    session_file.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        print("Launching visible browser for Reddit login...")
        browser = p.chromium.launch(
            headless=False,
            args=["--host-resolver-rules=MAP www.reddit.com 151.101.1.140"]
        )
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://www.reddit.com/login")

        print("Please log in to your Reddit account in the browser window (waiting up to 90s)...")
        try:
            page.wait_for_timeout(90000)
            context.storage_state(path=str(session_file))
            print(f"Saved Reddit session to: {session_file}")
        except Exception as e:
            print(f"Login timed out or error: {e}", file=sys.stderr)
        finally:
            browser.close()

    return session_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure Reddit browser authentication.")
    parser.add_argument("--interactive", action="store_true", help="Launch visible browser for login")
    parser.add_argument("--user", help="Reddit username")
    parser.add_argument("--password", help="Reddit password")
    parser.add_argument("--session-file", type=Path, default=DEFAULT_SESSION_FILE, help="Path to session JSON")

    args = parser.parse_args()

    if args.user and args.password:
        ok = automated_login(args.user, args.password, session_file=args.session_file)
        return 0 if ok else 1

    if args.interactive:
        interactive_login(session_file=args.session_file)
        return 0

    print("Usage:")
    print("  uv run .agents/skills/reddit-explorer/scripts/login_reddit.py --interactive")
    print("  uv run .agents/skills/reddit-explorer/scripts/login_reddit.py --user <USERNAME> --password <PASSWORD>")
    return 1


if __name__ == "__main__":
    sys.exit(main())
