#!/usr/bin/env python3
"""
Transcribe audio files using openai/whisper-large-v3-turbo via faster-whisper.
Produces timestamped transcripts compatible with the zootube pipeline and knowledge.db.
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

DEFAULT_MODEL = os.getenv("WHISPER_MODEL", "large-v3-turbo")
DEFAULT_DEVICE = os.getenv("WHISPER_DEVICE", "auto")
DEFAULT_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
DEFAULT_TRANSCRIPTS_DIR = Path("data/transcripts")


def format_timestamp(seconds: float) -> str:
    s = int(seconds)
    hours = s // 3600
    minutes = (s % 3600) // 60
    secs = s % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def resolve_model_name(model_name: str) -> str:
    """Resolve model name between HF path and faster-whisper alias."""
    if "whisper-large-v3-turbo" in model_name:
        return "large-v3-turbo"
    return model_name


def load_whisper_model(
    model_name: str = DEFAULT_MODEL,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE_TYPE,
):
    from faster_whisper import WhisperModel

    resolved_model = resolve_model_name(model_name)
    actual_device = "cpu" if device in ["auto", "cpu"] else device
    actual_compute = compute_type
    if actual_device == "cpu" and actual_compute == "float16":
        actual_compute = "int8"

    print(f"Loading Whisper model '{resolved_model}' on {actual_device} ({actual_compute})...")
    model = WhisperModel(resolved_model, device=actual_device, compute_type=actual_compute)
    return model


def load_audio_as_numpy(audio_path: Path, sample_rate: int = 16000):
    """Decode any audio/video file directly to 16kHz float32 numpy array using ffmpeg."""
    import shutil
    import subprocess
    import numpy as np

    ffmpeg_bin = shutil.which("ffmpeg") or "/home/kim/.local/bin/ffmpeg"
    cmd = [ffmpeg_bin, "-y", "-i", str(audio_path), "-f", "f32le", "-ac", "1", "-ar", str(sample_rate), "pipe:1"]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True)
    return np.frombuffer(proc.stdout, dtype=np.float32)


def transcribe_audio_file(
    model,
    audio_path: Path,
    language: Optional[str] = None,
    beam_size: int = 5,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Transcribe audio file and return info + snippet list."""
    audio_arr = load_audio_as_numpy(audio_path)
    segments, info = model.transcribe(
        audio_arr,
        language=language,
        beam_size=beam_size,
        word_timestamps=False,
    )

    snippets: list[dict[str, Any]] = []
    print(f"Detected language '{info.language}' with probability {info.language_probability:.2f}")
    print(f"Transcribing audio duration: {info.duration:.1f}s...")

    for seg in segments:
        duration = round(seg.end - seg.start, 2)
        snippets.append({
            "start": round(seg.start, 2),
            "duration": duration,
            "text": seg.text.strip(),
        })

    info_dict = {
        "language": info.language,
        "language_probability": round(info.language_probability, 4),
        "duration": round(info.duration, 2),
        "duration_string": format_timestamp(info.duration),
    }
    return info_dict, snippets


def build_readable_text(title: str, channel: str, video_id: str, duration_str: str, snippets: list[dict[str, Any]]) -> str:
    lines = [
        f"TITLE: {title}",
        f"CHANNEL: {channel}",
        f"URL: https://www.youtube.com/watch?v={video_id}",
        f"DURATION: {duration_str}",
        f"SOURCE: Transcribed locally via openai/whisper-large-v3-turbo",
        "=" * 70,
        "",
    ]

    current_block: list[str] = []
    block_start = 0.0

    for i, s in enumerate(snippets):
        if not current_block:
            block_start = s["start"]
        current_block.append(s["text"])

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
    parser = argparse.ArgumentParser(description="Transcribe audio with openai/whisper-large-v3-turbo.")
    parser.add_argument("audio_file", type=Path, help="Path to audio file (.wav, .mp3, etc.)")
    parser.add_argument("--video-id", help="Optional video ID (defaults to audio file stem)")
    parser.add_argument("--title", help="Optional video title")
    parser.add_argument("--channel", default="Local/Whisper", help="Channel name or creator")
    parser.add_argument("--channel-id", default="local_whisper", help="Channel ID")
    parser.add_argument("--output-dir", "-o", type=Path, default=DEFAULT_TRANSCRIPTS_DIR)
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Whisper model name/path")
    parser.add_argument("--device", default=DEFAULT_DEVICE, help="Device (cpu, cuda, auto)")
    parser.add_argument("--compute-type", default=DEFAULT_COMPUTE_TYPE, help="Compute type (int8, float32, float16)")
    parser.add_argument("--lang", help="Force transcription language (e.g. en)")
    parser.add_argument("--ingest-db", action="store_true", help="Automatically ingest into knowledge.db and Chroma")

    args = parser.parse_args()

    if not args.audio_file.exists():
        print(f"Error: Audio file not found at: {args.audio_file}", file=sys.stderr)
        return 1

    video_id = args.video_id or args.audio_file.stem
    title = args.title or f"Video {video_id}"

    model = load_whisper_model(
        model_name=args.model,
        device=args.device,
        compute_type=args.compute_type,
    )

    info_dict, snippets = transcribe_audio_file(model, args.audio_file, language=args.lang)

    metadata = {
        "video_id": video_id,
        "title": title,
        "channel": args.channel,
        "channel_id": args.channel_id,
        "duration": int(info_dict["duration"]),
        "duration_string": info_dict["duration_string"],
        "transcribed_by": "openai/whisper-large-v3-turbo",
        "language": info_dict["language"],
    }

    payload = {
        "metadata": metadata,
        "transcript_length": len(snippets),
        "transcript": snippets,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / f"{video_id}.json"
    txt_path = args.output_dir / f"{video_id}.txt"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    readable_text = build_readable_text(title, args.channel, video_id, info_dict["duration_string"], snippets)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(readable_text)

    print(f"Transcription complete ({len(snippets)} snippets):")
    print(f"  JSON: {json_path}")
    print(f"  Text: {txt_path}")

    if args.ingest_db:
        db_script_dir = Path(__file__).resolve().parent.parent.parent / "knowledge-db" / "scripts"
        if str(db_script_dir) not in sys.path:
            sys.path.insert(0, str(db_script_dir))
        from db import DEFAULT_DB_PATH, get_connection, ingest_transcript_json, init_db

        init_db(DEFAULT_DB_PATH)
        conn = get_connection(DEFAULT_DB_PATH)
        ingest_transcript_json(conn, json_path)
        conn.close()
        print(f"Ingested transcript and indexed vector chunks into {DEFAULT_DB_PATH}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
