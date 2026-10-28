from __future__ import annotations

import json

import pytest

from finsocnet.core import cards, person_skills, persons
from finsocnet.core.output import CliError
from tests.conftest import make_card, make_decision
from tests.integration.test_cards import commit
from tests.integration.test_kb_content import kb


def test_upsert_aliases_and_candidates(conn, run_id):
    persons.upsert(conn, {"id": "kristjan-qullamaggie", "canonical_name": "Kristjan Kullamägi", "moniker": "Qullamaggie",
                          "aliases": [{"alias": "@Qullamaggie", "platform": "x"}, {"alias": "Qullamaggie", "platform": ""}]}, run_id)
    persons.upsert(conn, {"id": "other-person", "canonical_name": "Other Person", "aliases": [{"alias": "@qullamaggie_fan", "platform": "x"}]}, run_id)
    c = persons.candidates(conn, handle="@qullamaggie", platform="x")
    assert c[0]["person"]["id"] == "kristjan-qullamaggie" and c[0]["score"] == 1.0
    assert persons.candidates(conn, handle="qullamaggie", platform="youtube")[0]["score"] == 0.9
    by_name = persons.candidates(conn, name="Kristjan Kullamagi", context="interview with Kristjan Kullamägi today")
    assert by_name[0]["person"]["id"] == "kristjan-qullamaggie" and by_name[0]["score"] >= 0.6
    assert persons.candidates(conn, name="Nobody Atall") == []
    with pytest.raises(CliError) as e:
        persons.alias_add(conn, "other-person", "@Qullamaggie", "x")
    assert e.value.code == "CONFLICT"


def test_owner_signal_and_appearance_updates_source_and_content(seeded, run_id):
    persons.upsert(seeded, {"id": "example-owner", "canonical_name": "Example Owner"}, run_id)
    seeded.execute("INSERT INTO sources (id, platform, kind, person_id) VALUES ('youtube:channel:UCx', 'youtube', 'channel', 'example-owner')")
    seeded.execute("UPDATE contents SET source_id = 'youtube:channel:UCx' WHERE id = 'youtube:abc123def45'")
    c = persons.candidates(seeded, name="Someone Else", content_id="youtube:abc123def45")
    assert c and c[0]["person"]["id"] == "example-owner" and c[0]["score"] == 0.9
    r = persons.add_appearance(seeded, {"person_id": "example-owner", "content_id": "youtube:abc123def45", "role": "owner", "match_confidence": 0.95}, run_id)
    assert r["status"] == "created"
    assert persons.add_appearance(seeded, {"person_id": "example-owner", "content_id": "youtube:abc123def45", "role": "owner", "match_confidence": 0.5}, run_id)["status"] == "updated"
    low = persons.add_appearance(seeded, {"person_id": "example-owner", "content_id": "youtube:abc123def45", "role": "guest", "match_confidence": 0.5}, run_id)
    assert low["appearance_id"] in [r["appearance_id"] for r in persons.list_persons(seeded, needs_review=True)]
    with pytest.raises(CliError):
        persons.add_appearance(seeded, {"person_id": "example-owner", "role": "nope"}, run_id)


def _mk_rulebook(conn, run_id):
    commit(conn, run_id, make_decision())
    return {"person_id": "example-swing-trader", "skill_name": "example-swing-trader-core", "category": "trade_management",
            "title": "Trade management: partials and trails", "summary": "Sells a third then trails the rest.",
            "content_markdown": "## Rules\n1. After 3-5 days sell 1/4-1/3. (cards 1)\n", "rules": [{"rule": "After 3-5 days sell 1/4-1/3.", "card_ids": [1]}]}


def test_person_cards_and_rulebook_validation_render(seeded, run_id):
    skill = _mk_rulebook(seeded, run_id)
    grouped = persons.person_cards(seeded, "example-swing-trader")
    assert grouped["total"] == 1 and list(grouped["categories"]) == ["trade_management"]
    assert grouped["categories"]["trade_management"][0]["citations"][0]["person_id"] == "example-swing-trader"

    assert person_skills.upsert_skill(seeded, skill, run_id)["status"] == "created"
    assert person_skills.upsert_skill(seeded, skill, run_id)["status"] == "updated"
    overview = {**skill, "category": "overview", "title": "Overview", "summary": None, "content_markdown": "Swing trader.", "rules": [{"rule": "Style", "card_ids": [1]}]}
    person_skills.upsert_skill(seeded, overview, run_id)
    md = person_skills.render_markdown(seeded, "example-swing-trader")
    assert md.index("Overview") < md.index("Trade management") and "cards 1" in md
    assert seeded.execute("SELECT rowid FROM person_skills_fts WHERE person_skills_fts MATCH 'trails'").fetchone()

    for bad, problem in [({"rules": [{"rule": "x", "card_ids": [99]}]}, "does not exist"),
                         ({"content_markdown": "At 12:40 he sells."}, "timestamps"),
                         ({"person_id": "nobody"}, "does not exist")]:
        with pytest.raises(CliError) as e:
            person_skills.upsert_skill(seeded, {**skill, **bad}, run_id)
        assert any(problem in d["problem"] for d in e.value.details)
    seeded.execute("INSERT INTO persons (id, canonical_name) VALUES ('p2', 'P Two')")
    with pytest.raises(CliError) as e:  # card 1 is not cited by p2
        person_skills.upsert_skill(seeded, {**skill, "person_id": "p2"}, run_id)
    assert "no citation by p2" in e.value.details[0]["problem"]


def test_person_merge_moves_everything(seeded, run_id):
    skill = _mk_rulebook(seeded, run_id)
    person_skills.upsert_skill(seeded, skill, run_id)
    persons.upsert(seeded, {"id": "handle-dup", "canonical_name": "Swing Dup", "aliases": [{"alias": "@swingdup", "platform": "x"}]}, run_id)
    out = persons.merge(seeded, "example-swing-trader", "handle-dup", run_id)
    assert out["moved"]["card_citations"] == 1
    assert seeded.execute("SELECT status, merged_into FROM persons WHERE id = 'example-swing-trader'").fetchone()[:] == ("merged", "handle-dup")
    assert seeded.execute("SELECT person_id FROM person_skills").fetchone()[0] == "handle-dup"
    assert persons.candidates(seeded, name="Example Swing Trader")[0]["person"]["id"] == "handle-dup"
    with pytest.raises(CliError):
        persons.merge(seeded, "example-swing-trader", "handle-dup", run_id)


def test_cli_person_and_skill_flow(repo, capsys, tmp_path):
    import shutil
    from pathlib import Path
    shutil.copytree(Path(__file__).resolve().parents[2] / ".agents/skills/knowledge-transformer", repo / ".agents/skills/knowledge-transformer")
    db = str(tmp_path / "k.db")
    kb(capsys, "init", "--db", db)
    _, env = kb(capsys, "run", "start", "--db", db, "--skill", "t")
    run = str(env["data"]["run_id"])
    f = tmp_path / "p.json"
    f.write_text(json.dumps({"id": "example-swing-trader", "canonical_name": "Example Swing Trader", "aliases": [{"alias": "@exs", "platform": "x"}]}))
    assert kb(capsys, "person", "upsert", "--db", db, "--file", str(f))[1]["error"]["code"] == "RUN_REQUIRED"
    code, env = kb(capsys, "person", "upsert", "--db", db, "--run", run, "--file", str(f))
    assert code == 0 and env["data"]["status"] == "created"
    code, env = kb(capsys, "person", "alias", "add", "--db", db, "--run", run, "--person", "example-swing-trader", "--alias", "ExSwing")
    assert code == 0 and env["data"]["added"] is True
    code, env = kb(capsys, "person", "candidates", "--db", db, "--handle", "@exs", "--platform", "x")
    assert env["data"]["candidates"][0]["person"]["id"] == "example-swing-trader"
    code, env = kb(capsys, "person", "get", "example-swing-trader", "--db", db)
    assert len(env["data"]["aliases"]) == 3
    code, env = kb(capsys, "person", "list", "--db", db)
    assert env["data"]["persons"][0]["id"] == "example-swing-trader"
    code, env = kb(capsys, "skill", "get", "example-swing-trader", "--db", db, "--render", "markdown")
    assert code == 5
