#!/usr/bin/env python3
"""
Deep-dive crawler to extract transcripts, mine empirical trading hypotheses,
and update knowledge.db & Chroma for the highest-value strategy videos across all 6 channels.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi

api = YouTubeTranscriptApi()

CHANNELS_DATA = [
    # 1. Trader Dante: 100% of his channel (all 16 videos)
    {
        "name": "Trader Dante",
        "slug": "trader_dante",
        "user_id": "UCT43ffXmotx7i903Yxcwxjw",
        "skill_name": "trader-dante-execution",
        "all_videos": True,
    },
    # 2. Kristjan Qullamaggie: Top setups & swing school
    {
        "name": "Kristjan Qullamaggie",
        "slug": "qullamaggie",
        "user_id": "UCLn8btkaQ5hVWNMt9TxQtsQ",
        "skill_name": "qullamaggie-swing-strategy",
        "selected_ids": ["KciAjkEFA6s", "ZdXxuBIFTZ0", "nm8iNDjHRoE", "pNWdgezy2VA", "JNVA5cd_m7M", "TZnX1qEiOkM"],
    },
    # 3. Lance Breitstein: Key levels, VWAP, and edge
    {
        "name": "Lance Breitstein",
        "slug": "lance_breitstein",
        "user_id": "UCzksXiC-Ju-DTIZmMiaOVfQ",
        "skill_name": "lance-breitstein-levels",
        "selected_ids": ["UAlhNPmvB14", "D2P-0xh6aEM", "uz4gpCGtkS4", "H01JbbEY7ac", "sxjsqauWE9E"],
    },
    # 4. Chat With Traders: Top legends & masterclass interviews
    {
        "name": "Chat With Traders",
        "slug": "chat_with_traders",
        "user_id": "UCdnzT5Tl6pAkATOiDsPhqcg",
        "skill_name": "chat-with-traders-defense",
        "selected_ids": ["K0F73Sq90j0", "EuYE4EB5wGE", "cewuawJHvCU", "rD5nQzbm0iI", "6lyl7flPOOU"],
    },
    # 5. SMB Capital: Prop desk playbooks & breakouts
    {
        "name": "SMB Capital",
        "slug": "smb_capital",
        "user_id": "UCg3B_joekBGJ1s_4fRjsMKA",
        "skill_name": "smb-capital-breakouts",
        "selected_ids": ["M1o0XqCaDiE", "8F3mdBtygzQ", "PNBtFXH-otc", "reWtEMpWlpA", "FQIH6o18y9g"],
    },
    # 6. Humbled Trader: Trend following & risk sizing
    {
        "name": "Humbled Trader",
        "slug": "humbled_trader",
        "user_id": "UCcIvNGMBSQWwo1v3n-ZRBCw",
        "skill_name": "humbled-trader-strategy",
        "selected_ids": ["zU0i9rBbEkI", "Jh5rJskkEkU", "CRPHmftchxU", "2HEsypfMcRQ", "I4yiHiM8OgI"],
    },
]


def format_timestamp(seconds: float) -> str:
    s = int(seconds)
    hours = s // 3600
    minutes = (s % 3600) // 60
    secs = s % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def process_video(vid: str, title: str, user_name: str, user_id: str) -> bool:
    json_path = Path(f"data/transcripts/{vid}.json")
    txt_path = Path(f"data/transcripts/{vid}.txt")

    if not json_path.exists():
        try:
            fetched = api.fetch(vid)
            snippets = [
                {
                    "start": round(float(s.start), 2),
                    "duration": round(float(s.duration), 2),
                    "text": s.text.replace("\n", " ").strip(),
                }
                for s in fetched
            ]
        except Exception as e:
            print(f"    [SKIP] Could not fetch transcript for {vid}: {e}")
            return False

        duration = int(snippets[-1]["start"] + snippets[-1]["duration"]) if snippets else 0
        metadata = {
            "video_id": vid,
            "title": title,
            "channel": user_name,
            "channel_id": user_id,
            "user_id": user_id,
            "duration": duration,
            "duration_string": format_timestamp(duration),
        }
        payload = {
            "metadata": metadata,
            "transcript_length": len(snippets),
            "transcript": snippets,
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        lines = [
            f"TITLE: {title}",
            f"CREATOR: {user_name}",
            f"URL: https://www.youtube.com/watch?v={vid}",
            f"DURATION: {format_timestamp(duration)}",
            "=" * 70,
            "",
        ]
        for s in snippets:
            lines.append(f"[{format_timestamp(s['start'])}] {s['text']}")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    # Ingest into DB & Chroma
    try:
        subprocess.run(
            [sys.executable, ".agents/skills/knowledge-db/scripts/db.py", "ingest-content", str(json_path), "--platform", "youtube"],
            capture_output=True,
            check=True,
        )
    except Exception as e:
        print(f"    [WARN] DB content ingestion failed for {vid}: {e}")

    # Mine hypotheses
    try:
        subprocess.run(
            [sys.executable, ".agents/skills/hypothesis-miner/scripts/extract_hypotheses.py", str(json_path), "--ingest-db", "--platform", "youtube"],
            capture_output=True,
            check=True,
        )
    except Exception as e:
        print(f"    [WARN] Hypothesis mining failed for {vid}: {e}")

    return True


def main():
    Path("data/transcripts").mkdir(parents=True, exist_ok=True)
    Path("data/hypotheses").mkdir(parents=True, exist_ok=True)

    total_processed = 0

    for ch in CHANNELS_DATA:
        name = ch["name"]
        slug = ch["slug"]
        user_id = ch["user_id"]
        skill_name = ch["skill_name"]

        print(f"\n=======================================================")
        print(f"Processing Channel: {name}")
        print(f"=======================================================")

        catalog_file = Path(f"data/channels/{slug}_catalog.json")
        with open(catalog_file, "r", encoding="utf-8") as f:
            cat_data = json.load(f)
        videos_by_id = {v["id"]: v["title"] for v in cat_data.get("videos", [])}

        target_ids = []
        if ch.get("all_videos"):
            target_ids = list(videos_by_id.keys())
        else:
            target_ids = ch.get("selected_ids", [])

        print(f"Targeting {len(target_ids)} key videos for {name}...")
        for vid in target_ids:
            title = videos_by_id.get(vid, f"Video {vid}")
            print(f"  -> Ingesting {vid}: '{title[:60]}'...")
            ok = process_video(vid, title, name, user_id)
            if ok:
                total_processed += 1

        # Re-synthesize the skill with all newly accumulated hypotheses
        print(f"Re-synthesizing User Skill '{skill_name}' with all mined hypotheses...")
        try:
            subprocess.run(
                [sys.executable, ".agents/skills/user-skill-synthesizer/scripts/synthesize_skill.py", skill_name, "--user-id", user_id, "--platform", "youtube"],
                capture_output=True,
                check=True,
            )
            print(f"  Successfully updated .agents/skills/{skill_name}/")
        except Exception as e:
            print(f"  [WARN] Skill synthesis failed: {e}")

    print("\n" + "=" * 80)
    print(f"DEEP CRAWL COMPLETE: Successfully transcribed and mined {total_processed} videos across all 6 creators!")


if __name__ == "__main__":
    main()
