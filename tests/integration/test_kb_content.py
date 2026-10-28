"""kb content semantics (docs/spec/01-database.md §3.1) and the envelope contract (00 §3)."""

from __future__ import annotations

import copy
import json

import pytest

from finsocnet.core import config, content, runs
from finsocnet.core.db import connect
from finsocnet.core.kb_cli import main as kb_main
from finsocnet.core.output import CliError


def kb(capsys, *argv):
    """Run the CLI in-process; return (exit_code, envelope). Asserts there is exactly one envelope on stdout."""
    code = 0
    try:
        kb_main(list(argv))
    except SystemExit as e:
        code = int(e.code or 0)
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 1, out
    return code, json.loads(out[0])


def test_add_created_updated_duplicate(conn, run_id, reddit):
    r1 = content.add_content(conn, reddit(), run_id)
    assert r1["status"] == "created" and r1["segments_added"] == 2

    rec = reddit()
    rec["segments"] += [
        {"seq": 2, "kind": "comment", "locator": {"comment_id": "t1_k2", "parent_id": "t3_1xg9xq1"}, "author": {"handle": "u/a"}, "text": "A third comment about sizing."},
        {"seq": 3, "kind": "comment", "locator": {"comment_id": "t1_k3", "parent_id": "t1_k2"}, "author": {"handle": "u/b"}, "text": "A fourth comment replying to the third."},
    ]
    r2 = content.add_content(conn, rec, run_id)
    assert r2["status"] == "updated" and r2["segments_added"] == 2
    assert conn.execute("SELECT COUNT(*) FROM content_segments WHERE content_id = 'reddit:1xg9xq1'").fetchone()[0] == 4

    # same text under another id -> duplicate (needs >= 500 chars)
    long_text = "Position sizing is the heart of risk management and every serious trader must master it. " * 8
    a = reddit(id="reddit:aaa", segments=[{"seq": 0, "kind": "post", "locator": {"comment_id": "t3_a"}, "text": long_text}])
    b = reddit(id="reddit:bbb", segments=[{"seq": 0, "kind": "post", "locator": {"comment_id": "t3_b"}, "text": long_text}])
    assert content.add_content(conn, a, run_id)["status"] == "created"
    dup = content.add_content(conn, b, run_id)
    assert dup["status"] == "duplicate" and dup["duplicate_of"] == "reddit:aaa"
    assert conn.execute("SELECT process_status FROM contents WHERE id = 'reddit:bbb'").fetchone()[0] == "skipped_duplicate"


def test_reprocessed_content_goes_back_to_new_when_segments_added(conn, run_id, reddit):
    content.add_content(conn, reddit(), run_id)
    content.claim_content(conn, "reddit:1xg9xq1", run_id)
    content.set_done(conn, "reddit:1xg9xq1", 1, 3, "kt-1.0", run_id)
    assert conn.execute("SELECT process_status FROM contents WHERE id = 'reddit:1xg9xq1'").fetchone()[0] == "processed"
    rec = reddit()
    rec["segments"].append({"seq": 2, "kind": "comment", "locator": {"comment_id": "t1_new"}, "text": "A brand new comment arrived."})
    content.add_content(conn, rec, run_id)
    row = conn.execute("SELECT process_status, processed_upto_seq FROM contents WHERE id = 'reddit:1xg9xq1'").fetchone()
    assert row["process_status"] == "new" and row["processed_upto_seq"] == 1


def test_cited_segment_text_is_kept(conn, run_id, reddit):
    content.add_content(conn, reddit(), run_id)
    # simulate a citation referencing seq 0
    conn.execute("INSERT INTO knowledge_cards (card_version, kind, domain, category, subject, claim, terms_json, evidence_level, transformer_version, produced_by) "
                 "VALUES (1,'rule','trading_strategy','risk_and_sizing','s','c','[\"x\"]','claimed','kt-1.0','t/t')")
    conn.execute("INSERT INTO card_citations (card_id, content_id, segment_seq, quote) VALUES (1, 'reddit:1xg9xq1', 0, 'q')")
    rec = reddit()
    rec["segments"][0]["text"] = "Edited text upstream."
    res = content.add_content(conn, rec, run_id)
    assert any("cited" in w for w in res["warnings"])
    assert "cut my position size" in conn.execute("SELECT text FROM content_segments WHERE content_id = 'reddit:1xg9xq1' AND seq = 0").fetchone()[0]


def test_fts_search_finds_segment_and_follows_updates(conn, run_id, reddit):
    content.add_content(conn, reddit(), run_id)
    hits = content.search_segments(conn, "snowballing")
    assert [(h["content_id"], h["seq"]) for h in hits] == [("reddit:1xg9xq1", 0)]
    assert "[snowballing]" in hits[0]["snippet"]
    assert content.search_segments(conn, "overtrading", platform="reddit")[0]["seq"] == 1
    assert content.search_segments(conn, "overtrading", platform="x") == []
    assert content.search_segments(conn, "!!! ???") == []
    # diacritics are removed on both sides
    rec = reddit(id="reddit:vn1", segments=[{"seq": 0, "kind": "post", "locator": {"comment_id": "a"}, "text": "Mình cắt lỗ 7% khi gãy hỗ trợ."}])
    content.add_content(conn, rec, run_id)
    assert content.search_segments(conn, "cat lo")[0]["content_id"] == "reddit:vn1"
    # a text update re-indexes
    conn.execute("UPDATE content_segments SET text = 'completely different words' WHERE content_id = 'reddit:1xg9xq1' AND seq = 0")
    assert content.search_segments(conn, "snowballing") == []
    assert content.search_segments(conn, "completely")


def test_validation_lists_every_problem(conn, run_id, reddit):
    rec = reddit()
    rec["segments"][1]["seq"] = 5
    rec["platform"] = "myspace"
    del rec["content_type"]
    with pytest.raises(CliError) as e:
        content.add_content(conn, rec, run_id)
    assert e.value.code == "VALIDATION_ERROR"
    paths = {d["path"] for d in e.value.details}
    assert "/platform" in paths and "/segments/1/seq" in paths


def test_view_chunks_claim_done(conn, run_id, reddit):
    segs = [{"seq": i, "kind": "transcript", "locator": {"start_sec": i * 10.0, "end_sec": i * 10.0 + 9}, "text": f"segment number {i} " + "word " * 40}
            for i in range(10)]
    content.add_content(conn, reddit(id="youtube:abc123def45", platform="youtube", content_type="video", source=None, segments=segs), run_id)
    cid = "youtube:abc123def45"

    view = content.view_content(conn, cid, 3, 4)["text"].splitlines()
    assert view[0].startswith("CONTENT youtube:abc123def45 | video |")
    assert any(l.startswith("[#3 | 00:30-00:39 | speaker ?]") for l in view)

    plan = content.chunks(conn, cid, max_chars=900, overlap=2)
    assert plan[0]["from_seq"] == 0 and plan[-1]["to_seq"] == 9 and len(plan) > 1
    assert plan[1]["from_seq"] == plan[0]["to_seq"] - 1  # overlap of 2 segments

    content.claim_content(conn, cid, run_id)
    other = runs.start_run(conn, "test", "other run")
    with pytest.raises(CliError) as e:
        content.claim_content(conn, cid, other)
    assert e.value.code == "CONFLICT"
    content.claim_content(conn, cid, run_id)  # the same run may resume

    r = content.set_done(conn, cid, plan[0]["to_seq"], 2, "kt-1.0", run_id)
    assert r["process_status"] == "processing" and r["processed_upto_seq"] == plan[0]["to_seq"]
    resumed = content.chunks(conn, cid, max_chars=900, overlap=2)
    assert resumed[0]["from_seq"] == plan[0]["to_seq"] + 1
    assert content.view_content(conn, cid, plan[0]["to_seq"] - 1, plan[0]["to_seq"] + 1)["text"].count("(context)") == 2
    done = content.set_done(conn, cid, 9, 5, "kt-1.0", run_id)
    assert done["process_status"] == "processed"
    row = conn.execute("SELECT processed_with, processed_at, cards_count FROM contents WHERE id = ?", (cid,)).fetchone()
    assert row["processed_with"] == "kt-1.0" and row["processed_at"] and row["cards_count"] == 5
    with pytest.raises(CliError):
        content.claim_content(conn, cid, run_id)
    content.claim_content(conn, cid, run_id, reprocess=True)
    assert conn.execute("SELECT processed_upto_seq FROM contents WHERE id = ?", (cid,)).fetchone()[0] == -1


def test_metadata_only_cannot_be_claimed_and_fail(conn, run_id, reddit):
    content.add_content(conn, reddit(id="youtube:catalogOnly", platform="youtube", content_type="video", source=None, segments=[]), run_id)
    assert conn.execute("SELECT process_status FROM contents WHERE id = 'youtube:catalogOnly'").fetchone()[0] == "metadata_only"
    with pytest.raises(CliError):
        content.claim_content(conn, "youtube:catalogOnly", run_id)
    content.add_content(conn, reddit(), run_id)
    content.set_failed(conn, "reddit:1xg9xq1", "unreadable")
    row = conn.execute("SELECT process_status, process_error FROM contents WHERE id = 'reddit:1xg9xq1'").fetchone()
    assert (row[0], row[1]) == ("failed", "unreadable")


# --- CLI envelope contract ---------------------------------------------------------------------------------

def test_cli_init_doctor_and_run_required(repo, capsys, tmp_path):
    db = str(tmp_path / "new" / "k.db")
    code, env = kb(capsys, "init", "--db", db)
    assert code == 0 and env["ok"] and "003_v2_schema" in env["data"]["applied"]
    code, env = kb(capsys, "doctor", "--db", db)
    assert code == 0 and env["data"]["ok"] is True and env["data"]["schema"] == "v2"

    code, env = kb(capsys, "lesson", "add", "--db", db, "--skill", "s", "--kind", "other", "--observation", "o")
    assert code == 2 and env["error"]["code"] == "RUN_REQUIRED"
    code, env = kb(capsys, "content", "claim", "x:y", "--db", db)
    assert code == 2 and env["error"]["code"] == "RUN_REQUIRED"

    code, env = kb(capsys, "run", "start", "--db", db, "--skill", "test", "--goal", "g", "--harness", "manual", "--model", "m")
    rid = env["data"]["run_id"]
    code, env = kb(capsys, "lesson", "add", "--db", db, "--run", str(rid), "--skill", "s", "--kind", "other", "--observation", "o")
    assert code == 0 and env["data"]["lesson_id"] == 1
    code, env = kb(capsys, "run", "end", "--db", db, "--run", str(rid), "--outcome", "success", "--stats", '{"cards": 0}')
    assert code == 0 and env["data"]["outcome"] == "success"
    code, env = kb(capsys, "stats", "--db", db)
    assert code == 0 and env["data"]["tables"]["agent_runs"] == 2  # migration run + this one


def test_cli_content_flow(repo, capsys, tmp_path, reddit):
    db = str(tmp_path / "k.db")
    kb(capsys, "init", "--db", db)
    _, env = kb(capsys, "run", "start", "--db", db, "--skill", "test")
    rid = str(env["data"]["run_id"])
    f = tmp_path / "rec.json"
    f.write_text(json.dumps(reddit()))
    code, env = kb(capsys, "content", "add", "--db", db, "--run", rid, "--file", str(f))
    assert code == 0 and env["data"]["status"] == "created"
    code, env = kb(capsys, "content", "search", "snowballing", "--db", db)
    assert env["data"]["hits"][0]["seq"] == 0
    code, env = kb(capsys, "content", "get", "reddit:1xg9xq1", "--db", db, "--meta-only")
    assert env["data"]["segment_count"] == 2 and "_claim" not in json.dumps(env["data"])
    code, env = kb(capsys, "content", "get", "nope:1", "--db", db)
    assert code == 5 and env["error"]["code"] == "NOT_FOUND"
    code, env = kb(capsys, "content", "bogus", "--db", db)
    assert code == 2 and env["error"]["code"] == "USAGE"
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    code, env = kb(capsys, "content", "add", "--db", db, "--run", rid, "--file", str(bad))
    assert code == 6 and env["error"]["details"]


def test_cli_v1_database_is_refused(repo, capsys, tmp_path):
    from tests.fixtures.legacy.make_v1_db import make_v1_db
    p = make_v1_db(tmp_path / "v1.db")
    code, env = kb(capsys, "stats", "--db", str(p))
    assert code == 8 and "migrate" in env["error"]["hint"]
    code, env = kb(capsys, "doctor", "--db", str(p))
    assert code == 0 and env["data"]["schema"] == "v1"


def test_doctor_repair_fts_rebuilds_indices(repo, capsys, conn, run_id, reddit):
    content.add_content(conn, reddit(), run_id)
    conn.execute("DELETE FROM persons_fts")
    conn.execute("INSERT INTO persons (id, canonical_name, moniker) VALUES ('p-1', 'Pat Trader', 'Patty')")
    conn.execute("INSERT INTO segments_fts(segments_fts) VALUES ('delete-all')")  # simulate a corrupted external-content index
    assert content.search_segments(conn, "snowballing") == []
    conn.close()
    code, env = kb(capsys, "doctor", "--repair-fts")
    assert code == 0 and env["data"]["ok"] is True
    c2 = connect(config.db_path())
    assert content.search_segments(c2, "snowballing")
    assert c2.execute("SELECT person_id FROM persons_fts WHERE persons_fts MATCH 'patty'").fetchone()
    c2.close()
