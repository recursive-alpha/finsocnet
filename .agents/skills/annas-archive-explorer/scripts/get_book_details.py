#!/usr/bin/env python3
"""
Retrieve book details and download mirrors from Anna's Archive by MD5 or URL.
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
DEFAULT_SESSION_FILE = Path(os.getenv("ANNAS_ARCHIVE_SESSION_FILE", "data/sessions/annas_archive_session.json"))
BASE_URL = os.getenv("ANNAS_ARCHIVE_URL", "https://annas-archive.gl").rstrip("/")


def extract_md5(url_or_md5: str) -> str:
    url_or_md5 = url_or_md5.strip()
    match = re.search(r"([a-f0-9]{32})", url_or_md5)
    if match:
        return match.group(1)
    raise ValueError(f"Could not extract a valid 32-char MD5 from: {url_or_md5}")


def get_book_details(
    url_or_md5: str,
    session_file: Path = DEFAULT_SESSION_FILE,
    base_url: str = BASE_URL,
) -> dict[str, Any]:
    md5 = extract_md5(url_or_md5)
    url = f"{base_url}/md5/{md5}"
    print(f"Fetching book details for MD5: {md5}...", file=sys.stderr)

    try:
        from playwright.sync_api import sync_playwright

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

            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(3000)

            data = page.evaluate("""() => {
                const titleEl = document.querySelector('main h1, .font-bold');
                const title = titleEl ? titleEl.innerText.trim() : document.title;

                const mirrors = [];
                document.querySelectorAll('a[href*=\"fast_download\"], a[href*=\"slow_download\"], a[href*=\"libgen\"], a[href*=\"ipfs\"]').forEach(a => {
                    mirrors.push({
                        label: a.innerText.trim().replace(/\\n+/g, ' '),
                        url: a.href
                    });
                });

                const descEl = document.querySelector('div[class*=\"description\"], div.mb-4');
                const desc = descEl ? descEl.innerText.trim() : '';

                return {
                    title: title,
                    description: desc,
                    mirrors: mirrors.slice(0, 10)
                };
            }""")
            browser.close()

            return {
                "md5": md5,
                "url": url,
                "title": data.get("title", ""),
                "description": data.get("description", ""),
                "mirrors": data.get("mirrors", []),
            }
    except Exception as e:
        print(f"[WARN] Playwright extraction failed: {e}", file=sys.stderr)
        return {
            "md5": md5,
            "url": url,
            "title": f"Book {md5}",
            "description": "Book details available on Anna's Archive.",
            "mirrors": [],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Get Anna's Archive book details and download mirrors.")
    parser.add_argument("target", help="Book MD5 hash or Anna's Archive URL")
    parser.add_argument("--session-file", type=Path, default=DEFAULT_SESSION_FILE, help="Path to session JSON")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")

    args = parser.parse_args()

    data = get_book_details(args.target, session_file=args.session_file)

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    print("\n" + "=" * 80)
    print(f"ANNA'S ARCHIVE BOOK: {data['title']}")
    print(f"MD5: {data['md5']}")
    print(f"URL: {data['url']}")
    print("=" * 80)

    if data.get("description"):
        print("\nDescription:")
        print(data["description"][:1000])

    if data.get("mirrors"):
        print(f"\nDownload Mirrors ({len(data['mirrors'])}):")
        for i, m in enumerate(data["mirrors"], 1):
            print(f"  [{i}] {m['label']}")
            print(f"      {m['url']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
