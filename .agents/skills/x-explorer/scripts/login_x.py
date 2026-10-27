#!/usr/bin/env python3
"""
Session and authentication manager for X (Twitter).
Configures persistent login state using auth_token cookie or interactive browser login.
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

DEFAULT_SESSION_FILE = Path(os.getenv("X_SESSION_FILE", "data/sessions/x_session.json"))
ENV_AUTH_TOKEN = os.getenv("X_AUTH_TOKEN", "").strip()


def save_token_session(auth_token: str, session_file: Path = DEFAULT_SESSION_FILE) -> Path:
    """Save auth_token cookie into Playwright storage state format."""
    session_file.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "cookies": [
            {
                "name": "auth_token",
                "value": auth_token,
                "domain": ".x.com",
                "path": "/",
                "expires": -1,
                "httpOnly": True,
                "secure": True,
                "sameSite": "None",
            },
            {
                "name": "auth_token",
                "value": auth_token,
                "domain": ".twitter.com",
                "path": "/",
                "expires": -1,
                "httpOnly": True,
                "secure": True,
                "sameSite": "None",
            },
        ],
        "origins": [],
    }
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    print(f"Saved auth_token session to: {session_file}")
    return session_file


def interactive_login(session_file: Path = DEFAULT_SESSION_FILE) -> Path:
    """Launch visible browser for manual user login, then save session state."""
    session_file.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        print("Launching visible browser for X login. Please log in to your account...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://x.com/i/flow/login")

        print("Waiting for login completion (navigate to x.com/home)...")
        try:
            page.wait_for_url("**/home", timeout=120000)
            context.storage_state(path=str(session_file))
            print(f"Login successful! Saved session state to: {session_file}")
        except Exception as e:
            print(f"Interactive login timed out or failed: {e}", file=sys.stderr)
        finally:
            browser.close()

    return session_file


def automated_login_x(username: str, password: str, session_file: Path = DEFAULT_SESSION_FILE) -> bool:
    session_file.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        print("Navigating to X login flow...", file=sys.stderr)
        page.goto("https://x.com/i/flow/login", timeout=25000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        try:
            page.fill('input[autocomplete="username"], input[name="text"]', username)
            page.press('input[autocomplete="username"], input[name="text"]', "Enter")
            page.wait_for_timeout(3000)
            page.fill('input[name="password"]', password)
            page.press('input[name="password"]', "Enter")
            page.wait_for_timeout(5000)
            context.storage_state(path=str(session_file))
            print(f"Saved authenticated X session to: {session_file}")
            browser.close()
            return True
        except Exception as e:
            print(f"Automated X login failed: {e}", file=sys.stderr)
            browser.close()
            return False


def verify_session(session_file: Path = DEFAULT_SESSION_FILE) -> bool:
    """Verify if saved session is authenticated on X."""
    if not session_file.exists():
        print(f"No session file found at: {session_file}")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(session_file))
        page = context.new_page()
        page.goto("https://x.com/home", timeout=15000, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)
        current_url = page.url
        browser.close()

        if "login" in current_url or "i/flow" in current_url:
            print("Session verification failed: redirected to login.")
            return False

        print("Session verified: successfully authenticated on X!")
        return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure authentication for X (Twitter).")
    parser.add_argument("--token", help="auth_token cookie string from logged-in browser")
    parser.add_argument("--interactive", action="store_true", help="Open browser window for manual login")
    parser.add_argument("--verify", action="store_true", help="Test if current session is authenticated")
    parser.add_argument("--session-file", type=Path, default=DEFAULT_SESSION_FILE, help="Path to session JSON file")
    parser.add_argument("--user", help="X username / handle")
    parser.add_argument("--password", help="X password")
    args = parser.parse_args()

    if args.verify:
        ok = verify_session(args.session_file)
        return 0 if ok else 1

    if args.token:
        save_token_session(args.token, args.session_file)
        return 0

    if args.interactive:
        interactive_login(args.session_file)
        return 0

    if args.user and args.password:
        ok = automated_login_x(args.user, args.password, args.session_file)
        return 0 if ok else 1
    if ENV_AUTH_TOKEN:
        print(f"Found X_AUTH_TOKEN in environment (.env). Generating session file...")
        save_token_session(ENV_AUTH_TOKEN, args.session_file)
        return 0

    print("No token provided. Usage:")
    print("  uv run .agents/skills/x-explorer/scripts/login_x.py --token <YOUR_AUTH_TOKEN>")
    print("  uv run .agents/skills/x-explorer/scripts/login_x.py --interactive")
    print("  uv run .agents/skills/x-explorer/scripts/login_x.py --verify")
    return 1


if __name__ == "__main__":
    sys.exit(main())
