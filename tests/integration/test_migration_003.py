"""Migration tests of specs/01-database.md §5.4 against a fixture v1 database."""

from __future__ import annotations

import json
import sqlite3
import sys

import pytest

from finsocnet.core import config, migrations
from finsocnet.core.db import connect
from finsocnet.core.normalize import clean_text
from tests.fixtures.legacy.make_v1_db import CHANNEL, make_v1_db


@pytest.fixture
def v1(repo):
    path = config.db_path()
    make_v1_db(path)
    return path


def test_fixture_migrates_and_maps_rows(repo, v1):
    conn = connect(v1)
    res = migrations.migrate(conn)
    assert res["applied"][0] == "003_v2_schema"
    assert res["backups"] and all(sys.modules["pathlib"].Path(b).exists() for b in res["backups"])  # pre-migration backup

    legacy = conn.execute("SELECT COUNT(*) FROM legacy_contents").fetchone()[0]
    assert conn.execute("SELECT COUNT(*) FROM contents").fetchone()[0] == legacy == 9

    for (cid,) in conn.execute("SELECT id FROM contents WHERE platform = 'youtube'"):
        assert len(cid.split(":", 1)[1]) == 11

    # metadata_only = legacy rows with neither transcript nor raw text
    meta_only = conn.execute("SELECT COUNT(*) FROM contents WHERE process_status = 'metadata_only'").fetchone()[0]
    assert meta_only == conn.execute("SELECT COUNT(*) FROM legacy_contents WHERE transcript_path IS NULL AND (raw_text IS NULL OR raw_text = '')").fetchone()[0] == 2

    ids = {r["id"]: r for r in conn.execute("SELECT * FROM contents")}
    assert "reddit:1xg9xq1" in ids and ids["reddit:1xg9xq1"]["content_type"] == "thread"
    assert "x:1851234567890123456" in ids and ids["x:1851234567890123456"]["process_status"] == "needs_review"  # stub <= 150 chars
    assert "medium:data-cleaning-00f164ca71a0" in ids
    assert "arxiv:2610.34467" in ids and ids["arxiv:2610.34467"]["content_type"] == "paper"
    assert ids["book:aa-87377793416593215"]["process_status"] == "needs_review"
    assert ids["youtube:abc123def45"]["metrics_json"] == '{"views":1200}'
    assert ids["youtube:abc123def45"]["published_at"] == "2026-09-02"


def test_transcript_segments_equal_legacy_text(repo, v1):
    conn = connect(v1)
    migrations.migrate(conn)
    data = json.loads((repo / "data" / "transcripts" / "abc123def45.json").read_text())
    legacy_text = " ".join(" ".join(e["text"].split()) for e in data["transcript"])
    rows = conn.execute("SELECT seq, kind, locator_json, text FROM content_segments WHERE content_id = 'youtube:abc123def45' ORDER BY seq").fetchall()
    assert rows and all(r["kind"] == "transcript" for r in rows)
    assert [r["seq"] for r in rows] == list(range(len(rows)))
    assert clean_text(" ".join(r["text"] for r in rows)) == clean_text(legacy_text)
    for r in rows:
        loc = json.loads(r["locator_json"])
        assert loc["end_sec"] - loc["start_sec"] <= 45 + 7  # a window may end with one entry that crosses 45 s
        assert len(r["text"]) <= 600


def test_paragraph_segments_for_raw_text(repo, v1):
    conn = connect(v1)
    migrations.migrate(conn)
    rows = conn.execute("SELECT kind, locator_json, text FROM content_segments WHERE content_id = 'reddit:1xg9xq1' ORDER BY seq").fetchall()
    assert all(r["kind"] == "paragraph" for r in rows)
    assert len(rows) == 3  # the 5-char paragraph merged into its neighbour
    assert any("short" in r["text"] for r in rows)


def test_sources_persons_aliases(repo, v1):
    conn = connect(v1)
    migrations.migrate(conn)
    sources = {r["id"]: r for r in conn.execute("SELECT * FROM sources")}
    assert f"youtube:channel:{CHANNEL}" in sources
    assert sources["youtube:handle:lewiskelly8"]["status"] == "needs_review"
    assert sources["x:user:x_trader"]["status"] == "needs_review"
    assert "x:user:qullamaggie" in sources and "reddit:user:hseldon2020" in sources and "medium:user:ztraderdorian" in sources
    assert not any(s.startswith(("annas", "arxiv", "system")) for s in sources)
    assert sources["x:user:qullamaggie"]["person_id"] == "kristjan-qullamaggie"  # owner appearance

    assert conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0] == 3
    aliases = conn.execute("SELECT platform FROM person_aliases WHERE alias_key = 'qullamaggie' AND person_id = 'kristjan-qullamaggie'").fetchall()
    assert aliases
    assert conn.execute("SELECT COUNT(*) FROM person_appearances").fetchone()[0] == 5
    assert conn.execute("SELECT COUNT(*) FROM legacy_id_map WHERE kind = 'content'").fetchone()[0] == 9
    # persons_fts is maintained by triggers
    assert conn.execute("SELECT person_id FROM persons_fts WHERE persons_fts MATCH 'qullamaggie'").fetchone()
    # legacy tables stay for Phase 2
    assert conn.execute("SELECT COUNT(*) FROM legacy_hypotheses").fetchone()[0] == 1
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_second_run_is_a_noop(repo, v1):
    conn = connect(v1)
    migrations.migrate(conn)
    again = migrations.migrate(conn)
    assert again["applied"] == [] and again["pending"] == []


def test_refuses_when_expected_empty_table_has_rows(repo, v1):
    c = sqlite3.connect(v1)
    c.execute("INSERT INTO persons (id, canonical_name) VALUES ('x', 'X')")
    c.execute("INSERT INTO person_skills (person_id, skill_name, category, title, content_markdown) VALUES ('x','s','c','t','m')")
    c.commit()
    c.close()
    conn = connect(v1)
    with pytest.raises(RuntimeError, match="person_skills"):
        migrations.migrate(conn)
    # rolled back: still v1
    assert conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'users'").fetchone()
    assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'agent_runs'").fetchone()


def test_fresh_database_gets_v2_schema(conn):
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
    for t in ("agent_runs", "sources", "contents", "content_segments", "segments_fts", "knowledge_cards", "knowledge_cards_fts",
              "card_citations", "card_links", "card_history", "dedup_decisions", "vocabulary", "vocabulary_fts", "persons",
              "person_aliases", "person_appearances", "persons_fts", "person_skills", "explore_queue", "knowledge_gaps",
              "history_entries", "browser_sessions", "budget_usage", "lessons", "feedback", "card_stats", "person_stats"):
        assert t in names, t
    assert not names & {"vector_embeddings", "market_ideas"}
