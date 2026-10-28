"""`finsocnet`: entry point (specs/07 §1). Heavy commands live in `finsocnet.core.*_cli` and are dispatched before argparse so
that their own parsers (and one-envelope output) stay in charge."""

from __future__ import annotations

import argparse
import signal
import sys

if hasattr(signal, "SIGPIPE"):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

PASSTHROUGH = {
    "kb": ("finsocnet.core.kb_cli", "main"),
    "eval": ("finsocnet.core.eval_cli", "main"),
    "session": ("finsocnet.core.session_cli", "local_main"),
    "explore": ("finsocnet.core.user_cli", "explore_main"),
    "persons": ("finsocnet.core.user_cli", "persons_main"),
    "feedback": ("finsocnet.core.user_cli", "feedback_main"),
}


def print_stats() -> None:
    from finsocnet.core import config
    from finsocnet.core.db import connect
    if not config.db_path().exists():
        print("No database yet. Create it with: finsocnet kb init")
        return
    conn = connect()
    try:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'agent_runs'").fetchone():
            print("The database is on the v1 schema. Migrate it with: finsocnet kb migrate")
            return
        t = lambda q: conn.execute(q).fetchone()[0]
        print("=" * 72)
        print("FINSOCNET KNOWLEDGE BASE")
        print("=" * 72)
        print(f"  Persons: {t('SELECT COUNT(*) FROM persons WHERE status = \'active\''):,}   Sources: {t('SELECT COUNT(*) FROM sources'):,}   Contents: {t('SELECT COUNT(*) FROM contents'):,}")
        print(f"  Active cards: {t('SELECT COUNT(*) FROM knowledge_cards WHERE status = \'active\''):,}   Citations: {t('SELECT COUNT(*) FROM card_citations'):,}   Rulebooks: {t('SELECT COUNT(*) FROM person_skills'):,}")
        print(f"  Open gaps: {t('SELECT COUNT(*) FROM knowledge_gaps WHERE status = \'open\'')}   Queue pending: {t('SELECT COUNT(*) FROM explore_queue WHERE status = \'pending\'')}")
        print("\nContents by status:")
        for r in conn.execute("SELECT process_status, COUNT(*) c FROM contents GROUP BY 1 ORDER BY c DESC"):
            print(f"  - {r[0]:<18}: {r[1]:,}")
        print("\nTop persons by cards:")
        for r in conn.execute("SELECT p.canonical_name, s.cards FROM person_stats s JOIN persons p ON p.id = s.person_id WHERE s.cards > 0 ORDER BY s.cards DESC LIMIT 10"):
            print(f"  - {r[0]:<28}: {r[1]}")
        print("=" * 72)
    finally:
        conn.close()


def print_skills(skill_type: str | None = None) -> None:
    from finsocnet.skills import list_all_skills
    rows = list_all_skills(skill_type=skill_type)
    print("=" * 100)
    print(f"{'Skill':<30} | {'Type':<9} | {'Version':<9} | {'Description':<45}")
    print("-" * 100)
    for s in rows:
        print(f"{s['name'][:29]:<30} | {s['type']:<9} | {s['version'][:9]:<9} | {s['description'][:44]:<45}")
    print("=" * 100)
    print(f"Total: {len(rows)} skills ({sum(r['type'] == 'core' for r in rows)} core, {sum(r['type'] == 'installed' for r in rows)} installed).")


def print_strategy(name: str) -> int:
    from finsocnet.core import person_skills, persons
    from finsocnet.core.db import connect
    from finsocnet.core.output import CliError
    conn = connect()
    try:
        key = name.lower().strip()
        row = conn.execute("SELECT id FROM persons WHERE id = ? OR id LIKE ? ORDER BY id LIMIT 1", (key, f"%{key}%")).fetchone()
        pid = row["id"] if row else (persons.candidates(conn, name=name, handle=name)[:1] or [{}])[0].get("person", {}).get("id")
        if not pid:
            print(f"No person matches {name!r}. List them with: finsocnet kb person list", file=sys.stderr)
            return 5
        try:
            print(person_skills.render_markdown(conn, persons.resolve_id(conn, pid)))
        except CliError as e:
            print(f"{e.message}. {e.hint or ''}", file=sys.stderr)
            return 5
        return 0
    finally:
        conn.close()


def main() -> None:
    from finsocnet.core import output
    sys.argv[:] = [sys.argv[0], *output.take_ui(sys.argv[1:])]  # `--ui` is global: any command can print for humans instead of JSON
    if len(sys.argv) > 1 and sys.argv[1] == "search":  # shortcut for `kb search`
        sys.argv[1:2] = ["kb", "search"]
    if len(sys.argv) > 1 and sys.argv[1] in PASSTHROUGH:
        import importlib
        mod, fn = PASSTHROUGH[sys.argv[1]]
        getattr(importlib.import_module(mod), fn)(sys.argv[2:])
        return

    parser = argparse.ArgumentParser(prog="finsocnet", description="FinSocNet: agent-operated knowledge network (SQLite + FTS5 + embeddings, Knowledge Cards). Every command prints one JSON envelope; add --ui for a human terminal view.")
    sub = parser.add_subparsers(dest="cmd")
    for name, help_ in [("kb", "Database CLI: runs, contents, cards, vocabulary, persons, queue (finsocnet kb --help)"), ("eval", "Evaluation sets: prepare inputs, score agent outputs"),
                        ("session", "Local session bridge: init-local | export | push"), ("explore", "Add a seed to the exploration queue: explore add <target>"),
                        ("persons", "Review uncertain person matches: persons review"), ("feedback", "Record feedback: feedback <type> <id> <+1|-1> [comment]"), ("search", "Search everything (alias of kb search); add --ui for a terminal view")]:
        sub.add_parser(name, help=help_)
    sub.add_parser("tui", help="Terminal UI over the v2 data")
    sub.add_parser("stats", help="Knowledge base summary (text)")
    sk = sub.add_parser("skills", help="Core vs installed skills")
    sk.add_argument("--type", choices=["core", "installed"])
    st = sub.add_parser("strategy", help="Print a person's rulebook")
    st.add_argument("name")
    inst = sub.add_parser("install", help="Register slash commands and link skills in AI harnesses")
    inst.add_argument("harness", nargs="?", default="all", choices=["claude", "omp", "pi", "hermes", "codex", "openclaw", "shared", "all"])
    inst.add_argument("--uninstall", action="store_true")
    args = parser.parse_args()

    if args.cmd == "tui":
        from finsocnet.tui import run_tui
        run_tui()
    elif args.cmd in (None, "stats"):
        print_stats()
    elif args.cmd == "skills":
        print_skills(args.type)
    elif args.cmd == "strategy":
        sys.exit(print_strategy(args.name))
    elif args.cmd == "install":
        from finsocnet.installer import install_harness
        install_harness(args.harness, uninstall=args.uninstall)


if __name__ == "__main__":
    main()
