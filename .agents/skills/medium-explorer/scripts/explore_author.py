#!/usr/bin/env python3
"""
Explore a Medium author or publication profile, bio, follower metrics, and published articles.
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
from playwright.sync_api import sync_playwright

load_dotenv()
DEFAULT_SESSION_FILE = Path(os.getenv("MEDIUM_SESSION_FILE", "data/sessions/medium_session.json"))


def clean_author_handle(handle_or_url: str) -> str:
    h = handle_or_url.strip()
    if h.startswith("http://") or h.startswith("https://"):
        h = h.split("?")[0].rstrip("/").split("/")[-1]
    return h.lstrip("@")


def explore_medium_author(handle: str, session_file: Path = DEFAULT_SESSION_FILE) -> dict[str, Any]:
    username = clean_author_handle(handle)
    url = f"https://medium.com/@{username}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context_kwargs = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "viewport": {"width": 1280, "height": 900},
        }
        if session_file.exists():
            context_kwargs["storage_state"] = str(session_file)

        context = browser.new_context(**context_kwargs)
        page = context.new_page()

        print(f"Loading Medium author profile: @{username} ({url})...", file=sys.stderr)
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        page.wait_for_timeout(3000)

        author_data = page.evaluate("""() => {
            const nameEl = document.querySelector('h1, h2');
            const bioEl = document.querySelector('div[class*=\"bio\"], p[class*=\"bio\"], p');
            const followersEl = Array.from(document.querySelectorAll('span, a')).find(el => el.innerText.includes('Followers') || el.innerText.includes('followers'));

            const articles = [];
            const seen = new Set();
            document.querySelectorAll('article h2, article h3').forEach(h => {
                const title = h.innerText.trim();
                if (!title || seen.has(title)) return;
                seen.add(title);
                const a = h.closest('a') || h.querySelector('a');
                let link = a ? a.href : '';
                if (link.includes('?')) link = link.split('?')[0];
                articles.push({ title, url: link });
            });

            return {
                name: nameEl ? nameEl.innerText.trim() : '',
                bio: bioEl ? bioEl.innerText.trim() : '',
                followers: followersEl ? followersEl.innerText.trim() : '',
                articles: articles.slice(0, 15)
            };
        }""")

        browser.close()

        return {
            "handle": f"@{username}",
            "name": author_data.get("name") or username,
            "bio": author_data.get("bio", ""),
            "followers": author_data.get("followers", ""),
            "profile_url": url,
            "articles": author_data.get("articles", []),
        }


def ingest_into_knowledge_db(author_data: dict[str, Any]) -> None:
    db_script = Path(__file__).resolve().parent.parent.parent / "knowledge-db" / "scripts" / "db.py"
    import subprocess

    handle = author_data["handle"]
    user_id = f"medium_{handle.lstrip('@').lower()}"
    name = author_data.get("name") or handle
    bio = author_data.get("bio", "")
    profile_url = author_data.get("profile_url", "")

    cmd_user = [
        sys.executable, str(db_script), "add-user",
        user_id, name,
        "--handle", handle,
        "--platform", "medium",
        "--profile-url", profile_url,
        "--topics", bio[:200],
    ]
    subprocess.run(cmd_user, capture_output=True, check=True)
    print(f"Recorded author {name} ({handle}) on Medium into knowledge.db", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Explore Medium author profile.")
    parser.add_argument("handle", help="Author handle (e.g. @username) or profile URL")
    parser.add_argument("--session-file", type=Path, default=DEFAULT_SESSION_FILE, help="Path to session JSON")
    parser.add_argument("--save-json", type=Path, help="Save author data to JSON file")
    parser.add_argument("--ingest-db", action="store_true", help="Ingest author profile into knowledge.db")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    data = explore_medium_author(args.handle, session_file=args.session_file)

    if args.save_json:
        args.save_json.parent.mkdir(parents=True, exist_ok=True)
        with open(args.save_json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved author data to: {args.save_json}", file=sys.stderr)

    if args.ingest_db:
        ingest_into_knowledge_db(data)

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    print("\n" + "=" * 80)
    print(f"MEDIUM AUTHOR: {data['name']} ({data['handle']})")
    print(f"URL: {data['profile_url']}")
    if data['followers']:
        print(f"METRICS: {data['followers']}")
    if data['bio']:
        print(f"BIO: {data['bio']}")
    print("=" * 80)

    if data.get("articles"):
        print(f"\nPublished Stories ({len(data['articles'])}):")
        for i, a in enumerate(data["articles"], 1):
            print(f"[{i:02d}] {a['title']}")
            print(f"     URL: {a['url']}")
            print()
    else:
        print("\nNo recent stories retrieved.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
