#!/usr/bin/env python3
"""
Explore and catalog YouTube channels: list videos, playlists, durations, and view stats.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


def get_node_runtime_arg() -> list[str]:
    """Find node binary to suppress yt-dlp JS runtime warnings if available."""
    node_path = shutil.which("node") or "/home/kim/.local/bin/node"
    if os.path.exists(node_path) and os.access(node_path, os.X_OK):
        return ["--js-runtimes", f"node:{node_path}"]
    return []


def normalize_channel_url(target: str, tab: str = "videos", sort: str = "latest") -> str:
    """Normalize input into an official YouTube tab URL."""
    target = target.strip()

    if target.startswith("http://") or target.startswith("https://"):
        base = target.split("?")[0].rstrip("/")
        # If ends with /videos or /shorts or /streams or /playlists, keep it
        if any(base.endswith(f"/{t}") for t in ["videos", "shorts", "streams", "playlists"]):
            base_url = base
        else:
            base_url = f"{base}/{tab}"
    elif target.startswith("@"):
        base_url = f"https://www.youtube.com/{target}/{tab}"
    elif target.startswith("UC") and len(target) == 24:
        base_url = f"https://www.youtube.com/channel/{target}/{tab}"
    else:
        # Assume handle if plain text
        handle = f"@{target}" if not target.startswith("@") else target
        base_url = f"https://www.youtube.com/{handle}/{tab}"

    if sort == "popular":
        return f"{base_url}?view=0&sort=p"
    return base_url


def fetch_channel_info_and_videos(url: str, limit: Optional[int] = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Fetch channel summary and video list via yt-dlp flat-playlist."""
    cmd = [
        "yt-dlp",
        *get_node_runtime_arg(),
        "--flat-playlist",
    ]
    if limit and limit > 0:
        cmd.extend(["--playlist-end", str(limit)])
    cmd.extend(["--dump-json", url])
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 and not proc.stdout:
        raise RuntimeError(f"yt-dlp failed to inspect channel at {url}:\n{proc.stderr}")

    videos: list[dict[str, Any]] = []
    channel_meta: dict[str, Any] = {}

    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if not channel_meta:
            channel_meta = {
                "channel": entry.get("channel") or entry.get("uploader", ""),
                "channel_id": entry.get("channel_id") or entry.get("uploader_id", ""),
                "channel_url": entry.get("channel_url") or entry.get("uploader_url", ""),
                "uploader_id": entry.get("uploader_id", ""),
            }

        duration = entry.get("duration") or 0
        duration_str = entry.get("duration_string") or (
            f"{int(duration)//60}:{int(duration)%60:02d}" if duration else "N/A"
        )

        videos.append({
            "id": entry.get("id", ""),
            "title": entry.get("title", ""),
            "url": entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id', '')}",
            "duration": duration,
            "duration_string": duration_str,
            "view_count": entry.get("view_count", 0),
            "upload_date": entry.get("upload_date", ""),
            "description": (entry.get("description") or "")[:200],
        })

    return channel_meta, videos


def main() -> int:
    parser = argparse.ArgumentParser(description="Explore YouTube channel videos and metadata.")
    parser.add_argument("channel", help="Channel handle (e.g. @HumbledTraderOfficial), channel URL, or UC ID")
    parser.add_argument("--limit", "-n", type=int, default=0, help="Number of videos to list (default: 0 for all)")
    parser.add_argument("--tab", choices=["videos", "shorts", "streams", "playlists", "all"], default="all", help="Channel tab to explore (default: all)")
    parser.add_argument("--sort", choices=["latest", "popular"], default="latest", help="Sort order (latest or popular)")
    parser.add_argument("--save-json", help="Path to save full result JSON")

    args = parser.parse_args()

    tabs_to_fetch = ["videos", "shorts", "streams"] if args.tab == "all" else [args.tab]
    all_videos: list[dict[str, Any]] = []
    channel_meta: dict[str, Any] = {}

    print(f"Inspecting channel: {args.channel} across tabs: {tabs_to_fetch} (limit: {args.limit or 'ALL'})...")

    for t in tabs_to_fetch:
        t_url = normalize_channel_url(args.channel, tab=t, sort=args.sort)
        try:
            c_meta, v_list = fetch_channel_info_and_videos(t_url, limit=args.limit if args.limit > 0 else None)
            if not channel_meta and c_meta:
                channel_meta = c_meta
            for v in v_list:
                v["tab"] = t
                v["content_type"] = "short" if t == "shorts" else ("stream" if t == "streams" else "video")
            all_videos.extend(v_list)
        except Exception:
            pass

    channel_name = channel_meta.get("channel") or "Unknown Channel"
    uploader_id = channel_meta.get("uploader_id") or ""
    print("\n" + "=" * 80)
    print(f"Channel: {channel_name} ({uploader_id})")
    print(f"Total Items Retrieved: {len(all_videos)} (tabs: {', '.join(tabs_to_fetch)})")
    print("=" * 80)

    preview_limit = args.limit if args.limit > 0 else 10
    for i, v in enumerate(all_videos[:preview_limit], start=1):
        views = f"{v['view_count']:,}" if v['view_count'] else "N/A"
        date = v["upload_date"] or "N/A"
        print(f"[{i:02d}] [{v.get('tab', 'video').upper()}] {v['title']}")
        print(f"     ID: {v['id']} | Duration: {v['duration_string']} | Views: {views} | Date: {date}")
        print(f"     URL: {v['url']}")
        print()

    if len(all_videos) > preview_limit:
        print(f"... and {len(all_videos) - preview_limit} more items.")

    if args.save_json:
        out_path = Path(args.save_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "channel": channel_meta,
            "tabs": tabs_to_fetch,
            "sort": args.sort,
            "video_count": len(all_videos),
            "videos": all_videos,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(f"Saved full catalog of {len(all_videos)} items to: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
