"""`--ui`: terminal rendering of the envelope; the default stays one JSON object (specs/13-cli-ui-and-web.md §1)."""

from __future__ import annotations

import json
import sys

import pytest

from finsocnet.core import output, ui

SEARCH = {"query": "size after losses", "mode": "hybrid", "types": ["cards", "skills"], "filters": {"kind": ["rule"]}, "total": 2, "facets": {"cards": 1, "skills": 1},
          "results": [{"type": "cards", "id": "13", "title": "cap overnight position", "snippet": "IF holding THEN SIZE", "relevance": 1.0, "score": 0.03, "ranks": {"vec": 1}, "meta": {"kind": "rule"}},
                      {"type": "skills", "id": "39", "title": "Tim Furey — checklists", "snippet": "Checklist", "relevance": 0.8, "score": 0.02, "ranks": {"lex": 1}, "meta": {"category": "checklists"}}]}


@pytest.fixture(autouse=True)
def reset_ui():
    old = output._UI
    yield
    output._UI = old


def test_take_ui_strips_the_flag_and_switches_rendering_on():
    output._UI = False
    assert output.take_ui(["kb", "search", "x", "--ui", "--limit", "3"]) == ["kb", "search", "x", "--limit", "3"] and output.ui_enabled()
    output._UI = False
    assert output.take_ui(["kb", "stats"]) == ["kb", "stats"] and not output.ui_enabled()


def test_begin_strips_the_flag_from_sys_argv_for_directly_run_scripts(monkeypatch):
    output._UI = False
    monkeypatch.setattr(sys, "argv", ["reddit.py", "list", "r/x", "--ui", "--limit", "2"])
    output.begin()
    assert sys.argv == ["reddit.py", "list", "r/x", "--limit", "2"] and output.ui_enabled()


def test_default_output_is_exactly_one_json_object(capsys):
    output._UI = False
    output.emit("kb.search", SEARCH)
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["data"]["total"] == 2


def test_ui_renders_search_hits_and_warnings(capsys, monkeypatch):
    monkeypatch.setenv("COLUMNS", "140")
    output._UI = True
    output.emit("kb.search", SEARCH, ["no card embeddings"], {"elapsed_ms": 12})
    out = capsys.readouterr().out
    assert "kb.search" in out and "size after losses" in out and "cap overnight position" in out and "Tim Furey" in out and "! no card embeddings" in out and "12 ms" in out
    assert not out.lstrip().startswith("{")


def test_ui_failure_keeps_the_exit_code(capsys):
    output._UI = True
    with pytest.raises(SystemExit) as e:
        output.fail("kb.card.get", "NOT_FOUND", "card 9 not found", "list cards first")
    out = capsys.readouterr().out
    assert e.value.code == 5 and "NOT_FOUND" in out and "card 9 not found" in out and "list cards first" in out


def test_generic_renderer_handles_lists_dicts_and_strings(capsys, monkeypatch):
    monkeypatch.setenv("COLUMNS", "120")
    output._UI = True
    output.emit("kb.gap.list", {"gaps": [{"id": 1, "status": "open", "query": "pairs trading", "asked_count": 2}]})
    output.emit("kb.stats", {"cards": 87, "by_status": {"active": 80, "retired": 7}})
    output.emit("strategy", "# Rulebook\ntext")
    out = capsys.readouterr().out
    assert "pairs trading" in out and "asked_count" in out and "active" in out and "# Rulebook" in out


def test_platform_items_table(capsys, monkeypatch):
    monkeypatch.setenv("COLUMNS", "140")
    output._UI = True
    output.emit("reddit.list", {"items": [{"ref": "https://r/1", "id": "reddit:aaa111", "kind": "thread", "title": "Sizing after losses", "author_handle": "u/x", "known": False, "visited": "seen"}],
                                "next_cursor": "abc", "source": {"id": "reddit:subreddit:test"}, "hidden_known": 2})
    out = capsys.readouterr().out
    assert "reddit:subreddit:test" in out and "2 already-known item(s) hidden" in out and "Sizing after losses" in out and "seen" in out
