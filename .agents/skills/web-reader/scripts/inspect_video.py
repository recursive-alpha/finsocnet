#!/usr/bin/env python3
"""
Inspect web pages for embedded videos, media players, streaming manifests, and caption/subtitle tracks.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.sync_api import sync_playwright


def inspect_page_media(url: str, timeout_ms: int = 30000) -> dict[str, Any]:
    media_sniffed: list[str] = []
    captions_sniffed: list[str] = []

    def handle_request(req):
        req_url = req.url
        if any(ext in req_url.lower() for ext in [".m3u8", ".mp4", ".webm", ".mpd", "videoplayback"]):
            if req_url not in media_sniffed:
                media_sniffed.append(req_url)
        if any(ext in req_url.lower() for ext in [".vtt", ".srt", "timedtext", "captions"]):
            if req_url not in captions_sniffed:
                captions_sniffed.append(req_url)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.on("request", handle_request)

        print(f"Inspecting media on {url}...", file=sys.stderr)
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(3000)

        # DOM inspection
        dom_media = page.evaluate("""() => {
            const out = {
                videos: [],
                iframes: [],
                captions: []
            };

            // HTML5 video tags
            document.querySelectorAll('video').forEach(v => {
                const src = v.src || (v.querySelector('source') ? v.querySelector('source').src : '');
                out.videos.push({
                    src: src,
                    currentSrc: v.currentSrc,
                    poster: v.poster,
                    duration: v.duration || 0
                });

                // tracks
                v.querySelectorAll('track').forEach(t => {
                    out.captions.push({
                        kind: t.kind,
                        src: t.src,
                        srclang: t.srclang,
                        label: t.label
                    });
                });
            });

            // Iframes (YouTube, Vimeo, Rumble, etc.)
            document.querySelectorAll('iframe').forEach(f => {
                const s = f.src;
                if (s && (s.includes('youtube') || s.includes('youtu.be') || s.includes('vimeo') || s.includes('rumble') || s.includes('player'))) {
                    out.iframes.push(s);
                }
            });

            return out;
        }""")

        browser.close()

        return {
            "url": url,
            "videos_dom": dom_media.get("videos", []),
            "iframes_embeds": dom_media.get("iframes", []),
            "captions_dom": dom_media.get("captions", []),
            "network_media_streams": media_sniffed[:20],
            "network_caption_tracks": captions_sniffed[:20],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect web page for video and caption streams.")
    parser.add_argument("url", help="Web page URL to inspect")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--timeout", type=int, default=30000, help="Timeout in ms")

    args = parser.parse_args()

    try:
        data = inspect_page_media(args.url, timeout_ms=args.timeout)
    except Exception as e:
        print(f"Error inspecting media at {args.url}: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    print("\n" + "=" * 80)
    print(f"MEDIA INSPECTION: {data['url']}")
    print("=" * 80)

    if data["videos_dom"]:
        print(f"\nHTML5 Video Elements ({len(data['videos_dom'])}):")
        for i, v in enumerate(data["videos_dom"], 1):
            print(f"  [{i}] Source: {v['src'] or v['currentSrc']}")
            if v["poster"]:
                print(f"      Poster: {v['poster']}")

    if data["captions_dom"]:
        print(f"\nCaption & Subtitle Tracks ({len(data['captions_dom'])}):")
        for i, c in enumerate(data["captions_dom"], 1):
            print(f"  [{i}] [{c['srclang']}] ({c['kind']}) -> {c['src']}")

    if data["iframes_embeds"]:
        print(f"\nEmbedded Video Players / Iframes ({len(data['iframes_embeds'])}):")
        for i, f in enumerate(data["iframes_embeds"], 1):
            print(f"  [{i}] {f}")

    if data["network_media_streams"]:
        print(f"\nNetwork Media Streams Sniffed ({len(data['network_media_streams'])}):")
        for i, s in enumerate(data["network_media_streams"][:5], 1):
            print(f"  [{i}] {s[:120]}...")

    if data["network_caption_tracks"]:
        print(f"\nNetwork Captions Sniffed ({len(data['network_caption_tracks'])}):")
        for i, c in enumerate(data["network_caption_tracks"][:5], 1):
            print(f"  [{i}] {c}")

    if not (data["videos_dom"] or data["iframes_embeds"] or data["network_media_streams"]):
        print("\nNo embedded video players or media streams found on page.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
