"""
Main Command Line Interface for FinSocNet.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from finsocnet.db import get_db, get_hypothesis, get_stats, list_contents, list_creators, list_hypotheses
from finsocnet.migrations import auto_migrate, get_migration_status
from finsocnet.search import rag_search, vector_search
from finsocnet.skills import list_all_skills


def print_stats():
    stats = get_stats()
    print("=" * 80)
    print("FINSOCNET KNOWLEDGE BASE & MULTI-PLATFORM METRICS")
    print("=" * 80)
    print(f"  Total Creators & Users:   {stats['users']}")
    print(f"  Total Cataloged Content:  {stats['contents']:,}")
    print(f"  Mined Hypotheses:         {stats['hypotheses']}")
    print(f"  Synthesized Agent Skills: {stats['skills']}")
    print("\nContent by Platform:")
    for p, c in stats["platforms"].items():
        print(f"  - {p:<15} : {c:,}")
    print("\nHypotheses by Category:")
    for cat, c in stats["categories"].items():
        print(f"  - {cat:<20} : {c}")
    print("\nHypotheses by Market Bias:")
    for d, c in stats["directions"].items():
        print(f"  - {d:<10} : {c}")
    print("=" * 80)


def print_creators(platform: Optional[str] = None):
    creators = list_creators(platform=platform)
    print("=" * 95)
    print(f"{'Creator / Name':<25} | {'Handle':<22} | {'Platform':<10} | {'Contents':<10} | {'Hypotheses':<10}")
    print("-" * 95)
    for c in creators:
        p_str = c['platform']
        print(f"{c['name'][:24]:<25} | {c['handle'][:21]:<22} | {p_str:<10} | {c['content_count']:<10} | {c['hypothesis_count']:<10}")
    print("=" * 95)
    print(f"Total: {len(creators)} creators listed.")


def print_contents(platform: Optional[str] = None, content_type: Optional[str] = None, limit: int = 30):
    contents = list_contents(platform=platform, content_type=content_type, limit=limit)
    print("=" * 105)
    print(f"{'ID':<15} | {'Type':<8} | {'Platform':<10} | {'Title':<45} | {'Views':<10}")
    print("-" * 105)
    for c in contents:
        views = f"{c['view_count']:,}" if c['view_count'] else "N/A"
        print(f"{c['id'][:14]:<15} | {c['content_type'][:7]:<8} | {c['platform'][:9]:<10} | {c['title'][:44]:<45} | {views:<10}")
    print("=" * 105)
    print(f"Showing top {len(contents)} items.")


def print_skills(skill_type: Optional[str] = None):
    skills = list_all_skills(skill_type=skill_type)
    print("=" * 95)
    print(f"{'Skill Name':<30} | {'Classification':<12} | {'Version':<8} | {'Description':<38}")
    print("-" * 95)
    for s in skills:
        print(f"{s['name'][:29]:<30} | {s['type'].upper():<12} | {s['version']:<8} | {s['description'][:37]:<38}")
    print("=" * 95)
    print(f"Total: {len(skills)} skills ({'all' if not skill_type else skill_type}).")


def view_hypothesis_card(hyp_id: int):
    h = get_hypothesis(hyp_id)
    if not h:
        print(f"Error: Hypothesis #{hyp_id} not found.", file=sys.stderr)
        return

    print("\n" + "=" * 80)
    print(f"HYPOTHESIS #{h['id']} [{h['direction']}] {h['title']}")
    print("=" * 80)
    print(f"Creator:    {h['user_name']} ({h['user_handle']}) [{h['user_platform'].upper()}]")
    print(f"Content:    {h['content_title']}")
    print(f"Source URL: {h['content_url']}")
    print(f"Category:   {h['category']} | Instrument: {h['instrument']}")
    if h.get('timestamp_formatted'):
        print(f"Timestamp:  {h['timestamp_formatted']}")
    print("-" * 80)
    print("STATEMENT:")
    print(f"> {h['hypothesis_statement']}")
    print("\nSETUP CONDITIONS:")
    print(f"  {h.get('setup_conditions') or 'None specified'}")
    print(f"\nHOLDING PERIOD: {h.get('holding_period') or 'Flexible'}")
    print(f"STATISTICAL CLAIM: {h.get('statistical_claim') or 'Empirical observation'}")
    print(f"RISK / INVALIDATION: {h.get('invalidation_risk') or 'Standard stop discipline'}")
    print("-" * 80)
    print("VERBATIM QUOTE:")
    print(f"\"{h['verbatim_quote']}\"")
    print("=" * 80 + "\n")


def search_command(query: str, limit: int = 10, category: Optional[str] = None, direction: Optional[str] = None, platform: Optional[str] = None):
    # Try semantic vector search first
    v_results = vector_search(query, limit=limit, category=category, direction=direction, platform=platform)

    if v_results:
        print("\n" + "=" * 85)
        print(f"SEMANTIC VECTOR SEARCH: '{query}' ({len(v_results)} results)")
        print("=" * 85)
        for r in v_results:
            m = r["metadata"]
            print(f"[Score: {r['score']:.4f}] #{m.get('hypothesis_id')} [{m.get('direction')}] {m.get('title')} ({m.get('category')}) - {m.get('platform')}")
            print(f"  Holding: {m.get('holding_period')}")
            lines = r['document'].splitlines()
            for l in lines[3:6]:
                print(f"  {l}")
            print("-" * 85)
    else:
        # Fallback to SQL keyword search
        h_results = list_hypotheses(query=query, category=category, direction=direction, platform=platform, limit=limit)
        print("\n" + "=" * 85)
        print(f"KEYWORD SEARCH: '{query}' ({len(h_results)} results)")
        print("=" * 85)
        for h in h_results:
            print(f"#{h['id']} [{h['direction']}] {h['title']} ({h['user_name']} - {h['category']})")
            print(f"  {h['hypothesis_statement'][:140]}...")
            print("-" * 85)


def main():
    parser = argparse.ArgumentParser(
        prog="finsocnet",
        description="FinSocNet: Multi-Platform Financial Social Intelligence & Trading Strategy Synthesizer",
    )
    sub = parser.add_subparsers(dest="cmd")

    # tui (default when no args)
    sub.add_parser("tui", help="Launch the interactive Terminal UI")

    # search
    search_p = sub.add_parser("search", help="Semantic vector search for trading hypotheses")
    search_p.add_argument("query", help="Natural language query")
    search_p.add_argument("--limit", "-n", type=int, default=10, help="Max results")
    search_p.add_argument("--category", "-c", help="Filter by category")
    search_p.add_argument("--direction", "-d", choices=["LONG", "SHORT", "NEUTRAL", "BOTH"])
    search_p.add_argument("--platform", "-p", help="Filter by platform (youtube, x, reddit, medium, arxiv)")

    # view
    view_p = sub.add_parser("view", help="View detailed hypothesis card by ID")
    view_p.add_argument("id", type=int, help="Hypothesis ID")

    # list
    list_p = sub.add_parser("list", help="List hypotheses with filters")
    list_p.add_argument("--query", "-q", help="Text search")
    list_p.add_argument("--category", "-c", help="Category filter")
    list_p.add_argument("--direction", "-d", choices=["LONG", "SHORT", "NEUTRAL", "BOTH"])
    list_p.add_argument("--platform", "-p", help="Platform filter")
    list_p.add_argument("--limit", "-n", type=int, default=30)

    # creators
    creators_p = sub.add_parser("creators", help="List all cataloged creators and users")
    creators_p.add_argument("--platform", "-p", help="Filter by platform")

    # contents
    contents_p = sub.add_parser("contents", help="List cataloged media and articles")
    contents_p.add_argument("--platform", "-p", help="Filter by platform")
    contents_p.add_argument("--type", "-t", help="Filter by content type (video, short, post, thread, book, paper)")
    contents_p.add_argument("--limit", "-n", type=int, default=30)

    # skills
    skills_p = sub.add_parser("skills", help="List System Skills vs Improved Strategy Skills")
    skills_p.add_argument("--type", choices=["system", "improved"], help="Filter by skill type")

    # stats
    sub.add_parser("stats", help="Display summary database metrics")

    # rag
    rag_p = sub.add_parser("rag", help="RAG search across raw transcript and content chunks")
    rag_p.add_argument("query", help="Natural language query")
    rag_p.add_argument("--limit", "-n", type=int, default=5)
    rag_p.add_argument("--platform", "-p", help="Filter by platform")

    # migrate
    mig_p = sub.add_parser("migrate", help="Run or inspect database migrations")
    mig_p.add_argument("--status", action="store_true", help="Display migration status")

    args = parser.parse_args()

    if args.cmd is None or args.cmd == "tui":
        from finsocnet.tui import run_tui
        run_tui()
        return

    if args.cmd == "stats":
        print_stats()
    elif args.cmd == "search":
        search_command(args.query, limit=args.limit, category=args.category, direction=args.direction, platform=args.platform)
    elif args.cmd == "view":
        view_hypothesis_card(args.id)
    elif args.cmd == "list":
        hyps = list_hypotheses(query=args.query, category=args.category, direction=args.direction, platform=args.platform, limit=args.limit)
        print("=" * 95)
        print(f"{'ID':<5} | {'Dir':<6} | {'Category':<16} | {'Title':<35} | {'Creator':<25}")
        print("-" * 95)
        for h in hyps:
            print(f"#{h['id']:<4} | {h['direction']:<6} | {h['category']:<16} | {h['title'][:34]:<35} | {h['user_name'][:24]:<25}")
        print("=" * 95)
        print(f"Total: {len(hyps)} hypotheses shown.")
    elif args.cmd == "creators":
        print_creators(platform=args.platform)
    elif args.cmd == "contents":
        print_contents(platform=args.platform, content_type=args.type, limit=args.limit)
    elif args.cmd == "skills":
        print_skills(skill_type=args.type)
    elif args.cmd == "rag":
        res = rag_search(args.query, limit=args.limit, platform=args.platform)
        print("\n" + "=" * 85)
        print(f"RAG CHUNK RETRIEVAL: '{args.query}' ({len(res)} chunks)")
        print("=" * 85)
        for r in res:
            m = r["metadata"]
            print(f"[Score: {r['score']:.4f}] {m.get('title')} [{m.get('platform')}] at [{m.get('timestamp_formatted')}]")
            print(f"  {r['document']}")
            print("-" * 85)
    elif args.cmd == "migrate":
        conn = get_db()
        if args.status:
            status = get_migration_status(conn)
            print("=" * 65)
            print(f"{'Version':<8} | {'Migration Name':<35} | {'Status':<10}")
            print("-" * 65)
            for s in status:
                print(f"{s['version']:<8} | {s['filename']:<35} | {s['status'].upper():<10}")
            print("=" * 65)
        else:
            new_m = auto_migrate(conn, verbose=True)
            if not new_m:
                print("Database is already up to date. No pending migrations.")
            else:
                print(f"Applied {len(new_m)} migrations: {new_m}")
        conn.close()


if __name__ == "__main__":
    main()
