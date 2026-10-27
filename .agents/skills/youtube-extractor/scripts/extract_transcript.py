#!/usr/bin/env python3
"""
Extract YouTube video metadata and transcripts with precise timestamps.
Outputs structured JSON and human/agent-readable timestamped text.
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
from typing import Any, Dict, List, Optional


def extract_video_id(url_or_id: str) -> str:
    """Extract 11-character video ID from a YouTube URL or return the ID."""
    url_or_id = url_or_id.strip()
    if len(url_or_id) == 11 and re.match(r"^[A-Za-z0-9_-]{11}$", url_or_id):
        return url_or_id

    patterns = [
        r"(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/)([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)

    raise ValueError(f"Could not extract a valid YouTube video ID from: {url_or_id}")


def get_node_runtime_arg() -> list[str]:
    """Find node binary to suppress yt-dlp JS runtime warnings if available."""
    node_path = shutil.which("node") or "/home/kim/.local/bin/node"
    if os.path.exists(node_path) and os.access(node_path, os.X_OK):
        return ["--js-runtimes", f"node:{node_path}"]
    return []


def fetch_video_metadata(video_id: str) -> dict[str, Any]:
    """Fetch video details using yt-dlp without downloading media."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = [
        "yt-dlp",
        *get_node_runtime_arg(),
        "--skip-download",
        "--dump-json",
        url,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(proc.stdout)
        return {
            "video_id": video_id,
            "title": data.get("title", ""),
            "uploader": data.get("uploader", ""),
            "channel": data.get("channel", ""),
            "channel_id": data.get("channel_id", ""),
            "channel_url": data.get("channel_url", ""),
            "uploader_id": data.get("uploader_id", ""),
            "duration": data.get("duration", 0),
            "duration_string": data.get("duration_string", ""),
            "upload_date": data.get("upload_date", ""),
            "view_count": data.get("view_count", 0),
            "like_count": data.get("like_count", 0),
            "description": data.get("description", ""),
            "tags": data.get("tags", []),
            "categories": data.get("categories", []),
        }
    except Exception as e:
        print(f"[WARN] yt-dlp metadata extraction failed: {e}", file=sys.stderr)
        return {
            "video_id": video_id,
            "title": f"Video {video_id}",
            "channel": "Unknown",
            "channel_id": "",
            "channel_url": "",
            "duration": 0,
            "description": "",
        }


def fetch_transcript_api(video_id: str, languages: list[str]) -> list[dict[str, Any]]:
    """Fetch transcript using youtube-transcript-api."""
    from youtube_transcript_api import YouTubeTranscriptApi

    api = YouTubeTranscriptApi()
    try:
        fetched = api.fetch(video_id, languages=languages)
        return [
            {
                "start": round(float(snippet.start), 2),
                "duration": round(float(snippet.duration), 2),
                "text": snippet.text.replace("\n", " ").strip(),
            }
            for snippet in fetched
        ]
    except Exception as e:
        print(f"[INFO] youtube-transcript-api direct fetch failed ({e}), checking transcript list...", file=sys.stderr)

    # Try listing available transcripts
    try:
        transcript_list = api.list(video_id)
        # Try finding one matching requested languages or generated
        t = transcript_list.find_transcript(languages)
        fetched = t.fetch()
        return [
            {
                "start": round(float(snippet.start), 2),
                "duration": round(float(snippet.duration), 2),
                "text": snippet.text.replace("\n", " ").strip(),
            }
            for snippet in fetched
        ]
    except Exception as e:
        print(f"[WARN] Transcript listing also failed: {e}", file=sys.stderr)
        return []


def format_timestamp(seconds: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS."""
    s = int(seconds)
    hours = s // 3600
    minutes = (s % 3600) // 60
    secs = s % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def build_readable_text(metadata: dict[str, Any], snippets: list[dict[str, Any]]) -> str:
    """Generate a readable text transcript grouped logically by time."""
    lines = [
        f"TITLE: {metadata.get('title', '')}",
        f"CHANNEL: {metadata.get('channel', '')} ({metadata.get('uploader_id', '')})",
        f"URL: https://www.youtube.com/watch?v={metadata.get('video_id', '')}",
        f"DURATION: {metadata.get('duration_string', '')}",
        "=" * 70,
        "",
    ]

    # Group snippets into ~15-30 second coherent blocks or by pauses
    current_block: list[str] = []
    block_start = 0.0

    for i, s in enumerate(snippets):
        if not current_block:
            block_start = s["start"]

        current_block.append(s["text"])

        # Flush if gap or accumulated ~25 seconds or last item
        is_last = (i == len(snippets) - 1)
        next_start = snippets[i + 1]["start"] if not is_last else s["start"]
        time_span = s["start"] + s["duration"] - block_start

        if is_last or time_span >= 25.0 or (next_start - (s["start"] + s["duration"])) > 2.5:
            ts_str = format_timestamp(block_start)
            block_text = " ".join(current_block).strip()
            lines.append(f"[{ts_str}] ({block_start:.1f}s) {block_text}")
            current_block = []

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract YouTube video transcript and metadata.")
    parser.add_argument("url_or_id", help="YouTube video URL or 11-char ID")
    parser.add_argument("--output-dir", "-o", default="data/transcripts", help="Directory to save output files")
    parser.add_argument("--lang", "-l", default="en", help="Comma-separated language codes (default: en)")
    parser.add_argument("--print", "-p", action="store_true", help="Print formatted transcript to stdout")
    parser.add_argument("--limit-lines", type=int, default=0, help="Limit printed lines if --print")
    parser.add_argument("--force-whisper", action="store_true", help="Force local transcription using openai/whisper-large-v3-turbo")
    parser.add_argument("--no-fallback", action="store_true", help="Do not fallback to Whisper if YouTube transcript is missing")

    args = parser.parse_args()

    try:
        video_id = extract_video_id(args.url_or_id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching metadata for video: {video_id}...")
    metadata = fetch_video_metadata(video_id)

    languages = [l.strip() for l in args.lang.split(",") if l.strip()]
    print(f"Fetching transcript for video: {video_id} (languages: {languages})...")
    snippets = []
    if not args.force_whisper:
        snippets = fetch_transcript_api(video_id, languages)

    if not snippets and not args.no_fallback:
        print(f"[INFO] YouTube transcript unavailable or force-whisper active. Falling back to local openai/whisper-large-v3-turbo...", file=sys.stderr)
        try:
            audio_skill_dir = Path(__file__).resolve().parent.parent.parent / "audio-transcriber" / "scripts"
            if str(audio_skill_dir) not in sys.path:
                sys.path.insert(0, str(audio_skill_dir))
            from extract_audio import download_youtube_audio, DEFAULT_AUDIO_DIR
            from transcribe_whisper import load_whisper_model, transcribe_audio_file

            DEFAULT_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
            audio_path = download_youtube_audio(args.url_or_id, DEFAULT_AUDIO_DIR, video_id)
            model = load_whisper_model()
            info_dict, snippets = transcribe_audio_file(model, audio_path, language=languages[0] if languages else None)
            metadata["transcribed_by"] = "openai/whisper-large-v3-turbo"
        except Exception as e:
            print(f"[ERROR] Local Whisper fallback failed: {e}", file=sys.stderr)

    if not snippets:
        print(f"[ERROR] No transcript could be extracted for {video_id}", file=sys.stderr)
        return 2

    payload = {
        "metadata": metadata,
        "transcript_length": len(snippets),
        "transcript": snippets,
    }

    json_path = out_dir / f"{video_id}.json"
    txt_path = out_dir / f"{video_id}.txt"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    readable_text = build_readable_text(metadata, snippets)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(readable_text)

    print(f"Successfully saved transcript:")
    print(f"  JSON: {json_path}")
    print(f"  Text: {txt_path} ({len(snippets)} snippets)")

    if args.print:
        lines = readable_text.splitlines()
        if args.limit_lines > 0:
            lines = lines[:args.limit_lines]
        print("\n" + "\n".join(lines))

    return 0


if __name__ == "__main__":
    sys.exit(main())
