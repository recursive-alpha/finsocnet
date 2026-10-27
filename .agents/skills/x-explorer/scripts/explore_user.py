#!/usr/bin/env python3
"""
Explore an X (Twitter) user profile, bio, followers, and recent posts.
Supports authenticated Playwright browsing (session/auth_token) with fallback to web search.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

DEFAULT_SESSION_FILE = Path(os.getenv("X_SESSION_FILE", "data/sessions/x_session.json"))


def clean_user_handle(handle: str) -> str:
    h = handle.strip()
    if h.startswith("http://") or h.startswith("https://"):
        h = h.split("?")[0].rstrip("/").split("/")[-1]
    return h.lstrip("@")


def explore_user_authenticated(handle: str, session_file: Path) -> Optional[dict[str, Any]]:
    """Scrape user profile and recent tweets using authenticated Playwright session."""
    if not session_file.exists():
        return None

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                storage_state=str(session_file),
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            page = context.new_page()
            url = f"https://x.com/{handle}"
            print(f"Navigating to {url} with authenticated session...", file=sys.stderr)
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(3000)

            # Check if redirected to login
            if "login" in page.url or "i/flow" in page.url:
                browser.close()
                return None

            profile_data = page.evaluate("""() => {
                const nameEl = document.querySelector('[data-testid="UserName"]');
                const bioEl = document.querySelector('[data-testid="UserDescription"]');
                const tweets = [];

                document.querySelectorAll('article[data-testid="tweet"]').forEach(t => {
                    const textEl = t.querySelector('[data-testid="tweetText"]');
                    const timeEl = t.querySelector('time');
                    const linkEl = t.querySelector('a[href*="/status/"]');
                    if (textEl) {
                        tweets.push({
                            text: textEl.innerText.trim(),
                            time: timeEl ? timeEl.getAttribute('datetime') : '',
                            url: linkEl ? linkEl.href : ''
                        });
                    }
                });

                return {
                    name_header: nameEl ? nameEl.innerText.split('\\n')[0] : '',
                    bio: bioEl ? bioEl.innerText.trim() : '',
                    tweets: tweets.slice(0, 15)
                };
            }""")
            browser.close()

            return {
                "handle": f"@{handle}",
                "name": profile_data.get("name_header") or handle,
                "bio": profile_data.get("bio", ""),
                "profile_url": url,
                "posts": profile_data.get("tweets", []),
                "source": "authenticated_browser",
            }
    except Exception as e:
        print(f"[WARN] Authenticated exploration failed: {e}", file=sys.stderr)
        return None


def explore_user_fallback(handle: str) -> dict[str, Any]:
    """Fallback profile exploration using public web search."""
    search_script = Path(__file__).resolve().parent.parent.parent / "web-searcher" / "scripts" / "search_web.py"
    import subprocess

    cmd = [sys.executable, str(search_script), f"@{handle}", "--site", "x.com", "--limit", "5", "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    posts = []
    bio = ""
    name = handle

    if proc.returncode == 0:
        try:
            results = json.loads(proc.stdout)
            for r in results:
                title = r.get("title", "")
                snippet = r.get("snippet", "")
                if f"@{handle}" in title.lower() or handle.lower() in title.lower():
                    name = title.split("(@")[0].strip() if "(@" in title else title.split("/")[0].strip()
                    if not bio and snippet:
                        bio = snippet
                if snippet:
                    posts.append({"text": snippet, "url": r.get("url", ""), "time": ""})
        except Exception:
            pass

    return {
        "handle": f"@{handle}",
        "name": name or handle,
        "bio": bio,
        "profile_url": f"https://x.com/{handle}",
        "posts": posts,
        "source": "public_search_fallback",
    }


def explore_user(handle_or_url: str, session_file: Path = DEFAULT_SESSION_FILE) -> dict[str, Any]:
    handle = clean_user_handle(handle_or_url)
    print(f"Exploring X profile for: @{handle}...", file=sys.stderr)

    data = explore_user_authenticated(handle, session_file)
    if not data:
        print(f"[INFO] Using search-assisted exploration for @{handle}...", file=sys.stderr)
        data = explore_user_fallback(handle)

    return data


def ingest_into_knowledge_db(profile: dict[str, Any]) -> None:
    db_script = Path(__file__).resolve().parent.parent.parent / "knowledge-db" / "scripts" / "db.py"
    import subprocess

    handle = profile["handle"]
    user_id = f"x_{handle.lstrip('@').lower()}"
    name = profile.get("name") or handle
    bio = profile.get("bio", "")
    profile_url = profile.get("profile_url", f"https://x.com/{handle.lstrip('@')}")

    # Add user
    cmd_user = [
        sys.executable, str(db_script), "add-user",
        user_id, name,
        "--handle", handle,
        "--platform", "x",
        "--profile-url", profile_url,
        "--topics", bio[:200],
    ]
    subprocess.run(cmd_user, capture_output=True, check=True)
    print(f"Recorded user {name} ({handle}) on X into knowledge.db", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Explore X (Twitter) user profile.")
    parser.add_argument("handle", help="User handle (e.g. @Qullamaggie) or profile URL")
    parser.add_argument("--session-file", type=Path, default=DEFAULT_SESSION_FILE, help="Path to session JSON")
    parser.add_argument("--save-json", type=Path, help="Save profile result to JSON file")
    parser.add_argument("--ingest-db", action="store_true", help="Ingest user profile into knowledge.db")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    profile = explore_user(args.handle, session_file=args.session_file)

    if args.save_json:
        args.save_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.save_json, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)
        print(f"Saved profile data to: {args.save_json}", file=sys.stderr)

    if args.ingest_db:
        ingest_into_knowledge_db(profile)

    if args.json:
        print(json.dumps(profile, indent=2))
        return 0

    print("\n" + "=" * 80)
    print(f"X PROFILE: {profile['name']} ({profile['handle']})")
    print(f"URL:     {profile['profile_url']}")
    print(f"SOURCE:  {profile['source']}")
    if profile.get('bio'):
        print(f"BIO:     {profile['bio']}")
    print("=" * 80)

    if profile.get("posts"):
        print(f"\nRecent Posts & Snippets ({len(profile['posts'])}):")
        for i, p in enumerate(profile["posts"], 1):
            print(f"[{i:02d}] {p['text']}")
            if p.get("url"):
                print(f"     URL: {p['url']}")
            print()
    else:
        print("\nNo recent posts retrieved (authenticate via login_x.py for full live feed).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
