"""
Simple, responsive Terminal UI for FinSocNet using Textual.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Rule,
    Static,
    TabbedContent,
    TabPane,
)

from finsocnet.db import get_db, get_hypothesis, get_stats, list_contents, list_creators, list_hypotheses
from finsocnet.skills import list_all_skills


class FinSocNetApp(App):
    CSS = """
    Screen {
        background: #0d1117;
        color: #c9d1d9;
    }
    Header {
        background: #161b22;
        color: #58a6ff;
        text-style: bold;
    }
    Footer {
        background: #161b22;
    }
    TabbedContent {
        height: 100%;
    }
    TabPane {
        padding: 1;
        height: 100%;
    }
    #search_input {
        margin-bottom: 1;
        border: solid #30363d;
        background: #161b22;
        color: #f0f6fc;
    }
    DataTable {
        height: 14;
        border: solid #30363d;
        background: #0d1117;
    }
    #detail_container {
        height: 14;
        border: solid #30363d;
        background: #161b22;
        padding: 1;
        overflow-y: scroll;
    }
    .card-title {
        color: #58a6ff;
        text-style: bold;
    }
    .card-meta {
        color: #8b949e;
    }
    .card-quote {
        color: #7ee787;
        text-style: italic;
    }
    .stat-box {
        border: solid #30363d;
        background: #161b22;
        padding: 1;
        margin: 1;
        height: 7;
    }
    .stat-number {
        color: #58a6ff;
        text-style: bold;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "focus_search", "Search"),
        ("1", "tab_1", "Hypotheses"),
        ("2", "tab_2", "Creators"),
        ("3", "tab_3", "Contents"),
        ("4", "tab_4", "Skills"),
        ("5", "tab_5", "Stats"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(id="tabs"):
            with TabPane("Hypotheses [1]", id="tab_hypotheses"):
                yield Input(placeholder="Search hypotheses by keyword or semantic query (e.g. overnight, SMC, VCP)...", id="search_input")
                yield DataTable(id="table_hypotheses", cursor_type="row")
                with VerticalScroll(id="detail_container"):
                    yield Static("Select a hypothesis row above to view details, setup rules, and verbatim quotes.", id="detail_text")

            with TabPane("Creators [2]", id="tab_creators"):
                yield DataTable(id="table_creators", cursor_type="row")

            with TabPane("Contents [3]", id="tab_contents"):
                yield DataTable(id="table_contents", cursor_type="row")

            with TabPane("Skills [4]", id="tab_skills"):
                yield DataTable(id="table_skills", cursor_type="row")

            with TabPane("Metrics [5]", id="tab_stats"):
                with Horizontal():
                    with Vertical(classes="stat-box"):
                        yield Label("Total Creators & Users")
                        yield Label("0", id="stat_users", classes="stat-number")
                    with Vertical(classes="stat-box"):
                        yield Label("Cataloged Contents")
                        yield Label("0", id="stat_contents", classes="stat-number")
                    with Vertical(classes="stat-box"):
                        yield Label("Mined Hypotheses")
                        yield Label("0", id="stat_hypotheses", classes="stat-number")
                    with Vertical(classes="stat-box"):
                        yield Label("Agent Skills")
                        yield Label("0", id="stat_skills", classes="stat-number")
                with Vertical(classes="stat-box"):
                    yield Label("Multi-Platform Breakdown", classes="card-title")
                    yield Static("", id="stat_platform_details")

        yield Footer()

    def on_mount(self) -> None:
        self.title = "FinSocNet: Financial Intelligence Terminal"
        self.sub_title = "Multi-Platform Social & Trading Alpha Explorer"

        # 1. Setup Hypotheses Table
        t_hyp = self.query_one("#table_hypotheses", DataTable)
        t_hyp.add_columns("ID", "Dir", "Category", "Platform", "Title", "Creator")
        self.refresh_hypotheses()

        # 2. Setup Creators Table
        t_creat = self.query_one("#table_creators", DataTable)
        t_creat.add_columns("Name", "Handle", "Platform", "Contents", "Hypotheses", "Topics")
        self.refresh_creators()

        # 3. Setup Contents Table
        t_cont = self.query_one("#table_contents", DataTable)
        t_cont.add_columns("ID", "Type", "Platform", "Title", "Views")
        self.refresh_contents()

        # 4. Setup Skills Table
        t_skill = self.query_one("#table_skills", DataTable)
        t_skill.add_columns("Skill Name", "Type", "Version", "Description")
        self.refresh_skills()

        # 5. Setup Stats
        self.refresh_stats()

    def refresh_hypotheses(self, query: str = "") -> None:
        t_hyp = self.query_one("#table_hypotheses", DataTable)
        t_hyp.clear()

        # Keyword filter only; the TUI moves to v2 card data in Phase 8.
        rows = list_hypotheses(query=query or None, limit=50)
        for h in rows:
            t_hyp.add_row(
                str(h["id"]),
                h["direction"],
                h["category"],
                h.get("user_platform", "youtube"),
                h["title"],
                h["user_name"],
                key=str(h["id"]),
            )

    def refresh_creators(self) -> None:
        t_creat = self.query_one("#table_creators", DataTable)
        t_creat.clear()
        creators = list_creators()
        for c in creators:
            t_creat.add_row(
                c["name"],
                c["handle"],
                c["platform"].upper(),
                str(c["content_count"]),
                str(c["hypothesis_count"]),
                (c.get("topics") or "")[:40],
            )

    def refresh_contents(self) -> None:
        t_cont = self.query_one("#table_contents", DataTable)
        t_cont.clear()
        contents = list_contents(limit=50)
        for c in contents:
            views = f"{c['view_count']:,}" if c["view_count"] else "-"
            t_cont.add_row(
                c["id"][:12],
                c["content_type"].upper(),
                c["platform"].upper(),
                c["title"][:50],
                views,
            )

    def refresh_skills(self) -> None:
        t_skill = self.query_one("#table_skills", DataTable)
        t_skill.clear()
        skills = list_all_skills()
        for s in skills:
            t_skill.add_row(
                s["name"],
                s["type"].upper(),
                s["version"],
                s["description"][:55],
            )

    def refresh_stats(self) -> None:
        stats = get_stats()
        self.query_one("#stat_users", Label).update(str(stats["users"]))
        self.query_one("#stat_contents", Label).update(f"{stats['contents']:,}")
        self.query_one("#stat_hypotheses", Label).update(str(stats["hypotheses"]))
        self.query_one("#stat_skills", Label).update(str(stats["skills"]))

        details = " | ".join(f"{p.upper()}: {c:,}" for p, c in stats["platforms"].items())
        self.query_one("#stat_platform_details", Static).update(f"Active Platforms: {details}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search_input":
            self.refresh_hypotheses(event.value.strip())

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "table_hypotheses":
            row_key = event.row_key.value
            if row_key and row_key.isdigit():
                h = get_hypothesis(int(row_key))
                if h:
                    detail = (
                        f"[b]{h['title']}[/b]  ([cyan]{h['direction']}[/cyan] | [yellow]{h['category']}[/yellow] | [magenta]{h['user_platform'].upper()}[/magenta])\n"
                        f"Creator: {h['user_name']} ({h['user_handle']}) | Source: {h['content_title']}\n"
                        f"--------------------------------------------------------------------------------\n"
                        f"[b]HYPOTHESIS:[/b] {h['hypothesis_statement']}\n\n"
                        f"[b]CONDITIONS:[/b] {h.get('setup_conditions') or 'None'}\n"
                        f"[b]HOLDING:[/b]    {h.get('holding_period') or 'Flexible'}\n\n"
                        f"[b]VERBATIM QUOTE:[/b]\n"
                        f"[green]\"{h['verbatim_quote']}\"[/green]\n"
                    )
                    self.query_one("#detail_text", Static).update(detail)

    def action_focus_search(self) -> None:
        self.query_one("#tabs", TabbedContent).active = "tab_hypotheses"
        self.query_one("#search_input", Input).focus()

    def action_tab_1(self) -> None:
        self.query_one("#tabs", TabbedContent).active = "tab_hypotheses"

    def action_tab_2(self) -> None:
        self.query_one("#tabs", TabbedContent).active = "tab_creators"

    def action_tab_3(self) -> None:
        self.query_one("#tabs", TabbedContent).active = "tab_contents"

    def action_tab_4(self) -> None:
        self.query_one("#tabs", TabbedContent).active = "tab_skills"

    def action_tab_5(self) -> None:
        self.query_one("#tabs", TabbedContent).active = "tab_stats"


def run_tui():
    app = FinSocNetApp()
    app.run()


if __name__ == "__main__":
    run_tui()
