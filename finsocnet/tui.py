"""Textual UI over the v2 data: stats, card search, persons and rulebooks, gaps and queue, sessions."""

from __future__ import annotations

import sqlite3
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import DataTable, Footer, Header, Input, Static, TabbedContent, TabPane

from finsocnet.core import cards, config, person_skills, persons, queue
from finsocnet.core.db import connect


def open_db() -> sqlite3.Connection | None:
    if not config.db_path().exists():
        return None
    c = connect()
    if not c.execute("SELECT 1 FROM sqlite_master WHERE name = 'agent_runs'").fetchone():
        c.close()
        return None
    return c


def stats_text(conn: sqlite3.Connection) -> str:
    t = lambda q: conn.execute(q).fetchone()[0]
    lines = [f"Persons {t('SELECT COUNT(*) FROM persons WHERE status = \'active\'')} · Sources {t('SELECT COUNT(*) FROM sources')} · Contents {t('SELECT COUNT(*) FROM contents')}",
             f"Active cards {t('SELECT COUNT(*) FROM knowledge_cards WHERE status = \'active\'')} · Citations {t('SELECT COUNT(*) FROM card_citations')} · Rulebooks {t('SELECT COUNT(*) FROM person_skills')}",
             f"Open gaps {t('SELECT COUNT(*) FROM knowledge_gaps WHERE status = \'open\'')} · Queue pending {t('SELECT COUNT(*) FROM explore_queue WHERE status = \'pending\'')}", "", "Contents by status"]
    lines += [f"  {r[0]:<18} {r[1]:>6}" for r in conn.execute("SELECT process_status, COUNT(*) FROM contents GROUP BY 1 ORDER BY 2 DESC")]
    return "\n".join(lines)


def card_detail(conn: sqlite3.Connection, card_id: int) -> str:
    c = cards.get_card(conn, card_id, citations=True, links=True)
    out = [f"#{c['id']} [{c['kind']}] {c['subject']}", "", c["claim"], "", f"terms: {', '.join(c['terms'])}", f"evidence: {c['evidence_level']} · persons {c['stats'].get('persons')} · citations {c['stats'].get('citations')}", ""]
    for ci in c["citations"][:5]:
        out.append(f"“{ci['quote'][:240]}” — {ci.get('person_name') or ci.get('author_handle') or '?'} ({ci['speaker_role']}) · {ci.get('content_title')}")
    return "\n".join(out)


class FinSocNetApp(App):
    CSS = "DataTable { height: 1fr; } #detail { padding: 1 2; } Input { margin: 0 0 1 0; }"
    BINDINGS = [("q", "quit", "Quit"), ("r", "refresh", "Refresh"), ("s", "focus_search", "Search cards")]

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Stats", id="tab_stats"):
                yield VerticalScroll(Static(id="stats"))
            with TabPane("Cards", id="tab_cards"):
                yield Input(placeholder="Search cards (e.g. trailing stop 10-day, overnight gap risk)…", id="search")
                with Horizontal():
                    yield DataTable(id="cards")
                    yield VerticalScroll(Static(id="detail"))
            with TabPane("Persons", id="tab_persons"):
                with Horizontal():
                    yield DataTable(id="persons")
                    yield VerticalScroll(Static(id="rulebook"))
            with TabPane("Gaps & queue", id="tab_gaps"):
                yield DataTable(id="gaps")
                yield DataTable(id="queue")
            with TabPane("Sessions", id="tab_sessions"):
                yield DataTable(id="sessions")
        yield Footer()

    def on_mount(self) -> None:
        for tid, cols in {"cards": ("ID", "Kind", "Category", "Subject", "Persons"), "persons": ("ID", "Name", "Cards", "Appearances"), "gaps": ("ID", "Asked", "Verdict", "Question"),
                          "queue": ("ID", "Prio", "Status", "Origin", "Target"), "sessions": ("Platform", "Domain", "Cookies", "Login", "Verified")}.items():
            t = self.query_one(f"#{tid}", DataTable)
            t.cursor_type = "row"
            t.add_columns(*cols)
        self.action_refresh()

    def action_refresh(self) -> None:
        conn = open_db()
        if conn is None:
            self.query_one("#stats", Static).update("No v2 database. Run: finsocnet kb init (or finsocnet kb migrate)")
            return
        try:
            self.query_one("#stats", Static).update(stats_text(conn))
            self.fill("persons", [(p["id"], p["canonical_name"], p["cards"], p["appearances"]) for p in persons.list_persons(conn)])
            self.fill("gaps", [(g["id"], g["asked_count"], g["verdict"], g["query"][:90]) for g in queue.gap_list(conn)])
            self.fill("queue", [(q["id"], q["priority"], q["status"], q["origin"], q["target"][:80]) for q in queue.list_items(conn, None, 50)])
            self.fill("sessions", [tuple(r) for r in conn.execute("SELECT COALESCE(platform, '-'), domain, cookie_count, login_state, COALESCE(verified_at, '-') FROM browser_sessions ORDER BY 1, 2")])
            self.fill("cards", [(c["id"], c["kind"], c["category"], c["subject"][:70], c["stats"].get("persons", 0)) for c in cards.list_cards(conn, limit=100)], key_col=0)
        finally:
            conn.close()

    def fill(self, table_id: str, rows: list[tuple[Any, ...]], key_col: int = 0) -> None:
        t = self.query_one(f"#{table_id}", DataTable)
        t.clear()
        for r in rows:
            t.add_row(*[str(x) for x in r], key=str(r[key_col]))

    def action_focus_search(self) -> None:
        self.query_one("#search", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        conn = open_db()
        if conn is None or not event.value.strip():
            return
        try:
            res = cards.search_cards(conn, text=event.value.strip(), limit=40)["results"]
            self.fill("cards", [(r["card"]["id"], r["card"]["kind"], r["card"]["category"], r["card"]["subject"][:70], r["stats"].get("persons", 0)) for r in res])
        finally:
            conn.close()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is None or event.row_key.value is None:
            return
        conn = open_db()
        if conn is None:
            return
        try:
            if event.data_table.id == "cards":
                self.query_one("#detail", Static).update(card_detail(conn, int(event.row_key.value)))
            elif event.data_table.id == "persons":
                try:
                    self.query_one("#rulebook", Static).update(person_skills.render_markdown(conn, event.row_key.value))
                except Exception:  # noqa: BLE001 - no rulebook yet
                    self.query_one("#rulebook", Static).update("No rulebook yet for this person.")
        finally:
            conn.close()


def run_tui() -> None:
    FinSocNetApp().run()
