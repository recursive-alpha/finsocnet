#!/usr/bin/env python3
"""
Web Reader using Playwright to load dynamic pages, execute JS, and extract clean text/markdown.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.sync_api import sync_playwright


def extract_page_content(
    url: str,
    selector: Optional[str] = None,
    timeout_ms: int = 30000,
    screenshot_path: Optional[Path] = None,
) -> dict[str, Any]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        print(f"Navigating to {url}...", file=sys.stderr)
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(2000)

        if screenshot_path:
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"Saved full-page screenshot to {screenshot_path}", file=sys.stderr)

        # Extract title and meta tags
        title = page.title()
        meta_desc = page.evaluate("""() => {
            const el = document.querySelector('meta[name="description"], meta[property="og:description"]');
            return el ? el.content : '';
        }""")

        # Extract main text
        clean_text = page.evaluate("""(targetSelector) => {
            // Remove noise elements
            const removeSelectors = ['script', 'style', 'noscript', 'nav', 'footer', 'header', '.ad', '.ads', '#cookie-banner'];
            for (const s of removeSelectors) {
                document.querySelectorAll(s).forEach(el => el.remove());
            }

            const target = targetSelector ? document.querySelector(targetSelector) : (document.querySelector('main, article, #content, .content') || document.body);
            return target ? target.innerText : document.body.innerText;
        }""", selector)

        # Extract links
        links = page.evaluate("""() => {
            const out = [];
            document.querySelectorAll('a[href^="http"]').forEach(a => {
                const text = a.innerText.trim();
                if (text.length > 2) {
                    out.push({ text: text.slice(0, 80), href: a.href });
                }
            });
            return out.slice(0, 30);
        }""")

        browser.close()

        # Format markdown text
        lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
        formatted_body = "\n\n".join(lines)

        return {
            "url": url,
            "title": title,
            "description": meta_desc,
            "body": formatted_body,
            "links": links,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read web pages using Playwright.")
    parser.add_argument("url", help="Web page URL to read")
    parser.add_argument("--selector", "-s", help="CSS selector to scope extraction")
    parser.add_argument("--screenshot", type=Path, help="Save page screenshot to path")
    parser.add_argument("--timeout", type=int, default=30000, help="Navigation timeout in ms")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--links", action="store_true", help="Display extracted external links")

    args = parser.parse_args()

    try:
        data = extract_page_content(
            url=args.url,
            selector=args.selector,
            timeout_ms=args.timeout,
            screenshot_path=args.screenshot,
        )
    except Exception as e:
        print(f"Error reading {args.url}: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    print("\n" + "=" * 80)
    print(f"TITLE: {data['title']}")
    print(f"URL:   {data['url']}")
    if data['description']:
        print(f"DESC:  {data['description']}")
    print("=" * 80 + "\n")
    print(data['body'][:3000])
    if len(data['body']) > 3000:
        print(f"\n... [{len(data['body']) - 3000} more characters truncated]")

    if args.links and data['links']:
        print("\n" + "-" * 80)
        print("Page Links:")
        for l in data['links']:
            print(f"  - {l['text']} -> {l['href']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
