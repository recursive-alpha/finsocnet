#!/usr/bin/env python3
"""
Session manager for Medium.
Supports saving authentication cookies (uid, sid) or interactive browser login to data/sessions/medium_session.json.
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
DEFAULT_SESSION_FILE = Path(os.getenv("MEDIUM_SESSION_FILE", "data/sessions/medium_session.json"))


def save_medium_cookies(sid: str, uid: str, session_file: Path = DEFAULT_SESSION_FILE) -> Path:
    session_file.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "cookies": [
            {
                "name": "sid",
                "value": sid,
                "domain": ".medium.com",
                "path": "/",
                "expires": -1,
                "httpOnly": True,
                "secure": True,
                "sameSite": "Lax",
            },
            {
                "name": "uid",
                "value": uid,
                "domain": ".medium.com",
                "path": "/",
                "expires": -1,
                "httpOnly": False,
                "secure": True,
                "sameSite": "Lax",
            },
        ],
        "origins": [],
    }
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    print(f"Saved Medium session cookies to: {session_file}")
    return session_file


def interactive_login(session_file: Path = DEFAULT_SESSION_FILE) -> Path:
    session_file.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        print("Launching visible browser for Medium login. Please log in to your account...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://medium.com/m/signin")

        print("Waiting for login completion (navigate to medium.com home or feed)...")
        try:
            page.wait_for_timeout(90000)
            context.storage_state(path=str(session_file))
            print(f"Saved session state to: {session_file}")
        except Exception as e:
            print(f"Login timed out or failed: {e}", file=sys.stderr)
        finally:
            browser.close()

    return session_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure Medium browser authentication.")
    parser.add_argument("--sid", help="Value of 'sid' session cookie")
    parser.add_argument("--uid", default="", help="Value of 'uid' cookie")
    parser.add_argument("--interactive", action="store_true", help="Open browser window for manual login")
    parser.add_argument("--session-file", type=Path, default=DEFAULT_SESSION_FILE, help="Path to session JSON")

    args = parser.parse_args()

    if args.sid:
        save_medium_cookies(args.sid, args.uid, session_file=args.session_file)
        return 0

    if args.interactive:
        interactive_login(session_file=args.session_file)
        return 0

    print("Usage:")
    print("  uv run .agents/skills/medium-explorer/scripts/login_medium.py --sid <SID_COOKIE> [--uid <UID_COOKIE>]")
    print("  uv run .agents/skills/medium-explorer/scripts/login_medium.py --interactive")
    return 1


if __name__ == "__main__":
    sys.exit(main())
