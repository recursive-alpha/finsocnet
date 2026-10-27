#!/usr/bin/env python3
"""
Extract audio from YouTube videos or local video files for local Whisper transcription.
Converts audio to 16kHz mono WAV format (optimal for Whisper models).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()
DEFAULT_AUDIO_DIR = Path(os.getenv("AUDIO_DOWNLOAD_DIR", "data/audio"))


def find_ffmpeg() -> str:
    """Find ffmpeg binary location."""
    p = shutil.which("ffmpeg") or "/home/kim/.local/bin/ffmpeg"
    if os.path.exists(p) and os.access(p, os.X_OK):
        return p
    return "ffmpeg"


def get_node_runtime_arg() -> list[str]:
    """Find node binary to suppress yt-dlp JS runtime warnings."""
    node_path = shutil.which("node") or "/home/kim/.local/bin/node"
    if os.path.exists(node_path) and os.access(node_path, os.X_OK):
        return ["--js-runtimes", f"node:{node_path}"]
    return []


def extract_video_id(url_or_id: str) -> str:
    """Extract 11-char video ID or slug."""
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

    # If it's a local file path
    p = Path(url_or_id)
    if p.exists():
        return p.stem

    return "audio_extract"


def download_youtube_audio(url_or_id: str, out_dir: Path, video_id: str, max_duration_sec: Optional[int] = None) -> Path:
    """Download audio stream from YouTube and convert to 16kHz WAV."""
    url = f"https://www.youtube.com/watch?v={video_id}" if len(video_id) == 11 else url_or_id
    out_wav = out_dir / f"{video_id}.wav"

    if out_wav.exists() and out_wav.stat().st_size > 1024:
        print(f"Audio file already exists: {out_wav}")
        return out_wav

    ffmpeg_bin = find_ffmpeg()
    cmd = [
        "yt-dlp",
        *get_node_runtime_arg(),
        "--ffmpeg-location", ffmpeg_bin,
        "-x",
        "--audio-format", "wav",
        "--postprocessor-args", f"ffmpeg:-ar 16000 -ac 1",
        "-o", str(out_dir / f"{video_id}.%(ext)s"),
        url,
    ]

    print(f"Downloading audio from YouTube ({url})...")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"yt-dlp audio download failed:\n{proc.stderr}\n{proc.stdout}")

    if not out_wav.exists():
        # Search for any generated audio in out_dir with that stem
        candidates = list(out_dir.glob(f"{video_id}.*"))
        if candidates:
            # Convert candidate to 16kHz mono wav
            src = candidates[0]
            if src.suffix.lower() != ".wav":
                convert_cmd = [ffmpeg_bin, "-y", "-i", str(src), "-vn", "-ar", "16000", "-ac", "1", str(out_wav)]
                subprocess.run(convert_cmd, check=True, capture_output=True)
                src.unlink(missing_ok=True)
            else:
                return src

    if not out_wav.exists():
        raise FileNotFoundError(f"Expected audio file not found at: {out_wav}")

    return out_wav


def convert_local_file_to_wav(input_path: Path, out_dir: Path) -> Path:
    """Convert local video/audio file to 16kHz mono WAV."""
    ffmpeg_bin = find_ffmpeg()
    out_wav = out_dir / f"{input_path.stem}.wav"

    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", str(input_path),
        "-vn",
        "-ar", "16000",
        "-ac", "1",
        str(out_wav),
    ]
    print(f"Converting {input_path} to 16kHz WAV...")
    subprocess.run(cmd, check=True, capture_output=True)
    return out_wav


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract audio for Whisper transcription.")
    parser.add_argument("source", help="YouTube URL, video ID, or local file path")
    parser.add_argument("--out-dir", "-o", type=Path, default=DEFAULT_AUDIO_DIR, help="Output directory for audio")
    parser.add_argument("--max-duration", type=int, help="Optional duration limit in seconds")

    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    source_path = Path(args.source)
    if source_path.exists() and source_path.is_file():
        out_wav = convert_local_file_to_wav(source_path, args.out_dir)
    else:
        video_id = extract_video_id(args.source)
        out_wav = download_youtube_audio(args.source, args.out_dir, video_id, max_duration_sec=args.max_duration)

    print(f"Successfully extracted audio:")
    print(f"  Path: {out_wav}")
    print(f"  Size: {out_wav.stat().st_size / (1024 * 1024):.2f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
