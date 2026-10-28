#!/usr/bin/env python3
"""
Batch pipeline runner to explore all target YouTube channels, extract transcripts,
mine trading hypotheses, ingest into knowledge.db & Chroma, and synthesize User Agent Skills.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

CHANNELS_CONFIG = [
    {
        "name": "Humbled Trader",
        "slug": "humbled_trader",
        "handle": "@HumbledTraderOfficial",
        "primary_video_id": "zU0i9rBbEkI",
        "skill_name": "humbled-trader-strategy",
        "platform": "youtube",
    },
    {
        "name": "Chat With Traders",
        "slug": "chat_with_traders",
        "handle": "@ChatWithTradersPodcast",
        "primary_video_id": "6lyl7flPOOU",
        "skill_name": "chat-with-traders-defense",
        "platform": "youtube",
    },
    {
        "name": "Trader Dante",
        "slug": "trader_dante",
        "handle": "@TraderDante",
        "primary_video_id": "pLWcPj859wA",
        "skill_name": "trader-dante-execution",
        "platform": "youtube",
    },
    {
        "name": "SMB Capital",
        "slug": "smb_capital",
        "handle": "@smbcapital",
        "primary_video_id": "M1o0XqCaDiE",
        "skill_name": "smb-capital-breakouts",
        "platform": "youtube",
    },
    {
        "name": "Kristjan Qullamaggie",
        "slug": "qullamaggie",
        "handle": "@Qullamaggie",
        "primary_video_id": "TZnX1qEiOkM",
        "skill_name": "qullamaggie-swing-strategy",
        "platform": "youtube",
    },
    {
        "name": "Lance Breitstein",
        "slug": "lance_breitstein",
        "handle": "@TheOneLanceB",
        "primary_video_id": "UAlhNPmvB14",
        "skill_name": "lance-breitstein-levels",
        "platform": "youtube",
    },
]


def run_cmd(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({' '.join(cmd)}):\n{proc.stderr}\n{proc.stdout}")
    return proc.stdout


def process_channel(cfg: dict[str, str]) -> dict[str, Any]:
    name = cfg["name"]
    handle = cfg["handle"]
    vid = cfg["primary_video_id"]
    slug = cfg["slug"]
    skill_name = cfg["skill_name"]
    platform = cfg["platform"]

    print(f"[{name}] 1. Cataloging channel {handle}...")
    cat_path = f"data/channels/{slug}.json"
    run_cmd([
        sys.executable,
        ".agents/skills/youtube-extractor/scripts/explore_channel.py",
        handle,
        "--limit", "5",
        "--save-json", cat_path,
    ])

    print(f"[{name}] 2. Extracting transcript for {vid}...")
    run_cmd([
        sys.executable,
        ".agents/skills/youtube-extractor/scripts/extract_transcript.py",
        vid,
    ])

    json_path = f"data/transcripts/{vid}.json"

    print(f"[{name}] 3. Ingesting content into knowledge.db...")
    run_cmd([
        sys.executable,
        ".agents/skills/knowledge-db/scripts/db.py",
        "ingest-content",
        json_path,
        "--platform", platform,
    ])

    print(f"[{name}] 4. Mining hypotheses into knowledge.db and Chroma...")
    run_cmd([
        sys.executable,
        ".agents/skills/hypothesis-miner/scripts/extract_hypotheses.py",
        json_path,
        "--ingest-db",
        "--platform", platform,
    ])

    print(f"[{name}] 5. Synthesizing User Agent Skill '{skill_name}'...")
    run_cmd([
        sys.executable,
        ".agents/skills/user-skill-synthesizer/scripts/synthesize_skill.py",
        skill_name,
        "--content-id", vid,
        "--platform", platform,
    ])

    return {
        "name": name,
        "handle": handle,
        "video_id": vid,
        "skill_name": skill_name,
        "skill_path": f".agents/skills/{skill_name}",
    }


def main():
    print(f"Starting batch pipeline for {len(CHANNELS_CONFIG)} channels...")
    Path("data/channels").mkdir(parents=True, exist_ok=True)
    Path("data/transcripts").mkdir(parents=True, exist_ok=True)
    Path("data/hypotheses").mkdir(parents=True, exist_ok=True)

    results = []
    # Sequential execution to prevent Chroma/SQLite lock conflicts
    for cfg in CHANNELS_CONFIG:
        try:
            res = process_channel(cfg)
            results.append(res)
            print(f"[SUCCESS] Processed {cfg['name']} -> {res['skill_path']}\n")
        except Exception as e:
            print(f"[ERROR] Failed {cfg['name']}: {e}\n", file=sys.stderr)

    print("=" * 80)
    print(f"Batch processing completed: {len(results)}/{len(CHANNELS_CONFIG)} successful.")
    for r in results:
        print(f"  - {r['name']} ({r['handle']}): Skill -> {r['skill_path']}")


if __name__ == "__main__":
    main()
