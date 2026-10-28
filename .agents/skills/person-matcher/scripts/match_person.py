#!/usr/bin/env python3
"""
Person Identity & Entity Matcher for FinSocNet.
Manages canonical trader identities, cross-platform appearances, and matches
guest/host appearances across YouTube channels, podcasts, X, and articles to canonical persons.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()
DEFAULT_DB_PATH = Path(os.getenv("KNOWLEDGE_DB_PATH", "data/knowledge.db"))
PERSONS_DIR = Path("data/persons")


def get_db_connection(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def list_persons(db_path: Path = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    conn = get_db_connection(db_path)
    rows = conn.execute("SELECT * FROM persons ORDER BY canonical_name ASC").fetchall()
    persons = []
    for r in rows:
        p = dict(r)
        apps = conn.execute(
            "SELECT platform, handle_or_name, role, content_title FROM person_appearances WHERE person_id = ?",
            (p["id"],)
        ).fetchall()
        p["appearances_count"] = len(apps)
        p["appearances"] = [dict(a) for a in apps]
        persons.append(p)
    conn.close()
    return persons


def get_person(person_id: str, db_path: Path = DEFAULT_DB_PATH) -> Optional[dict[str, Any]]:
    conn = get_db_connection(db_path)
    row = conn.execute("SELECT * FROM persons WHERE id = ?", (person_id,)).fetchone()
    if not row:
        conn.close()
        return None
    person = dict(row)
    apps = conn.execute(
        "SELECT platform, platform_id, handle_or_name, role, content_id, content_title, notes FROM person_appearances WHERE person_id = ?",
        (person_id,)
    ).fetchall()
    person["appearances"] = [dict(a) for a in apps]
    conn.close()
    return person


def match_content_to_person(
    title: str = "",
    channel_name: str = "",
    channel_id: str = "",
    transcript_snippet: str = "",
    db_path: Path = DEFAULT_DB_PATH,
) -> Optional[dict[str, Any]]:
    """
    Match arbitrary content (title, channel, or text) to the canonical Person.
    Handles cross-channel guest interviews (e.g. Tim Furey or Lance Breitstein on CWT or Humbled Trader).
    """
    conn = get_db_connection(db_path)
    persons = conn.execute("SELECT * FROM persons").fetchall()
    appearances = conn.execute("SELECT * FROM person_appearances").fetchall()
    conn.close()

    text_to_match = f"{title} {channel_name} {transcript_snippet}".lower()

    # 1. Direct channel/platform ID match (ownership)
    for app in appearances:
        if channel_id and app["platform_id"] == channel_id and app["role"] == "owner":
            return get_person(app["person_id"], db_path)

    # 2. Name & Moniker regex scoring
    best_match = None
    highest_score = 0

    for p in persons:
        score = 0
        p_name = p["canonical_name"].lower()
        p_moniker = (p["moniker"] or "").lower()

        # Check full name in title
        if p_name in title.lower():
            score += 50
        elif p_name in text_to_match:
            score += 30

        # Check moniker in title
        if p_moniker and p_moniker in title.lower():
            score += 40
        elif p_moniker and p_moniker in text_to_match:
            score += 20

        # Check specific name tokens (first + last name)
        tokens = p_name.split()
        if len(tokens) >= 2:
            if all(t in title.lower() for t in tokens):
                score += 35
            elif all(t in text_to_match for t in tokens):
                score += 15

        if score > highest_score and score >= 20:
            highest_score = score
            best_match = p

    if best_match:
        res = dict(best_match)
        res["confidence_score"] = highest_score
        return res

    # 3. Fallback to channel appearance lookup
    for app in appearances:
        if app["handle_or_name"] and app["handle_or_name"].lower() in channel_name.lower():
            return get_person(app["person_id"], db_path)

    return None


def register_appearance(
    person_id: str,
    platform: str,
    platform_id: str = "",
    handle_or_name: str = "",
    role: str = "guest",
    content_id: str = "",
    content_title: str = "",
    notes: str = "",
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    conn = get_db_connection(db_path)
    conn.execute(
        """
        INSERT INTO person_appearances (person_id, platform, platform_id, handle_or_name, role, content_id, content_title, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (person_id, platform, platform_id, handle_or_name, role, content_id, content_title, notes)
    )
    conn.commit()
    conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage person identities and resolve cross-channel appearances.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="List all canonical trading persons")

    # get
    get_p = subparsers.add_parser("get", help="Get person details by person_id")
    get_p.add_argument("person_id", help="Canonical person ID slug (e.g. lance-breitstein, tim-furey)")

    # match
    match_p = subparsers.add_parser("match", help="Match content title/channel to a canonical person")
    match_p.add_argument("--title", default="", help="Content title")
    match_p.add_argument("--channel", default="", help="Channel name or handle")
    match_p.add_argument("--channel-id", default="", help="Channel ID")
    match_p.add_argument("--text", default="", help="Snippet or transcript text")

    args = parser.parse_args()

    if args.command == "list":
        persons = list_persons()
        print(f"=== Tracked Trading Personalities ({len(persons)}) ===")
        for p in persons:
            print(f"- [{p['id']}] {p['canonical_name']} ({p['moniker']})")
            print(f"  Style: {p['trading_style']}")
            print(f"  Markets: {p['primary_markets']}")
            print(f"  Appearances ({p['appearances_count']}): {', '.join(a['platform'] + ':' + a['handle_or_name'] for a in p['appearances'][:3])}")
            print()
        return 0

    elif args.command == "get":
        p = get_person(args.person_id)
        if not p:
            print(f"Error: Person '{args.person_id}' not found.", file=sys.stderr)
            return 1
        print(json.dumps(p, indent=2))
        return 0

    elif args.command == "match":
        match = match_content_to_person(
            title=args.title,
            channel_name=args.channel,
            channel_id=args.channel_id,
            transcript_snippet=args.text,
        )
        if match:
            print("Match Found:")
            print(f"  Person ID: {match.get('id')}")
            print(f"  Name:      {match.get('canonical_name')}")
            print(f"  Moniker:   {match.get('moniker')}")
            print(f"  Style:     {match.get('trading_style')}")
            if "confidence_score" in match:
                print(f"  Score:     {match.get('confidence_score')}")
        else:
            print("No matching person found.")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
