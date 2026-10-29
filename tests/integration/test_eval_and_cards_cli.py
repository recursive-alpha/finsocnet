from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from finsocnet.core import eval_cli
from tests.conftest import make_card, make_decision
from tests.integration.test_kb_content import kb

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def evals(repo):
    shutil.copytree(ROOT / "evals", repo / "evals")
    shutil.copytree(ROOT / ".agents" / "skills" / "knowledge-transformer", repo / ".agents" / "skills" / "knowledge-transformer")
    return repo / "evals"


def test_golden_sets_have_minimum_sizes(evals):
    assert len(eval_cli.case_files("transform")) >= 10 and len(eval_cli.case_files("dedup")) >= 15


def test_dedup_scoring_and_wrong_merge(evals, tmp_path):
    for name, path in eval_cli.case_files("dedup"):
        case = eval_cli.read(path)
        (tmp_path / f"{name}.decision.json").write_text(json.dumps({"decision": case["expected_decision"], "target_card_id": case.get("expected_target")}))
    rep = eval_cli.score_dedup(tmp_path)
    assert rep["metrics"] == {"accuracy": 1.0, "wrong_merge_rate": 0.0} and rep["failures"] == []
    (tmp_path / "d05-contradicts-opposite-action.decision.json").write_text(json.dumps({"decision": "same", "target_card_id": 2}))
    rep = eval_cli.score_dedup(tmp_path)
    assert rep["metrics"]["wrong_merge_rate"] > 0 and rep["metrics"]["accuracy"] < 1.0


def test_transform_scoring_counts_missing_invalid_and_no_card(evals, tmp_path):
    rep = eval_cli.score_transform(tmp_path)  # no outputs at all
    cases = eval_cli.case_files("transform")
    assert rep["metrics"]["recall"] == 0.0 and len(rep["failures"]) == len(cases)
    no_card = [n for n, p in cases if not eval_cli.read(p / "expected.json")["cards"]]
    assert len(no_card) >= 2
    for n in no_card:
        (tmp_path / f"{n}.cards.json").write_text("[]")
    (tmp_path / "t09-ticker-prediction-nocard.cards.json").write_text(json.dumps([make_card()]))
    rep = eval_cli.score_transform(tmp_path)
    assert rep["metrics"]["no_card_accuracy"] == round((len(no_card) - 1) / len(no_card), 3)
    assert any("expected no cards" in f["reason"] for f in rep["failures"])


def test_prepare_writes_inputs_without_answers(evals, tmp_path):
    res = eval_cli.prepare("dedup", tmp_path)
    assert res["cases"] == len(eval_cli.case_files("dedup")) >= 40
    data = json.loads((tmp_path / "d01-same-paraphrase.input.json").read_text())
    assert "expected_decision" not in data and data["candidates"]


def test_vocab_and_card_cli_flow(repo, capsys, tmp_path):
    db = str(tmp_path / "k.db")
    shutil.copytree(ROOT / ".agents" / "skills" / "knowledge-transformer", repo / ".agents" / "skills" / "knowledge-transformer")
    kb(capsys, "init", "--db", db)
    _, env = kb(capsys, "run", "start", "--db", db, "--skill", "test", "--harness", "manual", "--model", "m")
    run = str(env["data"]["run_id"])
    code, env = kb(capsys, "vocab", "lookup", "stop loss", "--db", db)
    assert code == 0 and env["data"]["matches"][0]["term"] == "stop_loss"

    rec = {"id": "youtube:abc123def45", "platform": "youtube", "content_type": "video", "fetch_method": "yt-dlp",
           "segments": [{"seq": 0, "kind": "transcript", "locator": {"start_sec": 0}, "text": "so what I do is, once it's up like 3, 4 days after the breakout I sell a third, a quarter maybe,"}]}
    (tmp_path / "rec.json").write_text(json.dumps(rec))
    kb(capsys, "content", "add", "--db", db, "--run", run, "--file", str(tmp_path / "rec.json"))
    import sqlite3
    c = sqlite3.connect(db)
    c.execute("INSERT INTO persons (id, canonical_name) VALUES ('example-swing-trader', 'Example Swing Trader')")
    c.commit()
    c.close()

    cards = tmp_path / "cards.json"
    bad = make_card(terms=["ema10"])
    cards.write_text(json.dumps([make_card(), bad]))
    code, env = kb(capsys, "card", "validate", "--db", db, "--file", str(cards))
    assert code == 0 and env["data"]["valid"] == [0] and env["data"]["errors"][0]["details"][0]["code"] == "VOCAB_UNKNOWN"
    assert env["data"]["errors"][0]["details"][0]["suggestion"] == "ema_10"

    code, env = kb(capsys, "card", "candidates", "--db", db, "--file", str(cards), "--index", "0")
    assert code == 0 and env["data"]["results"][0]["candidates"] == []

    dec = tmp_path / "dec.json"
    dec.write_text(json.dumps([make_decision()]))
    code, env = kb(capsys, "card", "commit", "--db", db, "--file", str(dec))
    assert code == 2 and env["error"]["code"] == "RUN_REQUIRED"
    code, env = kb(capsys, "card", "commit", "--db", db, "--run", run, "--file", str(dec))
    assert code == 0 and env["data"]["committed"] == 1 and env["data"]["results"][0]["result_card"] == 1
    code, env = kb(capsys, "card", "commit", "--db", db, "--run", run, "--file", str(dec))
    assert env["data"]["results"][0]["status"] == "already_committed"
    code, env = kb(capsys, "card", "get", "1", "--db", db, "--citations", "--links", "--history")
    assert code == 0 and env["data"]["citations"][0]["quote_verified"] == 1
    code, env = kb(capsys, "card", "search", "--db", db, "--text", "trailing stop ma 10 breakout")
    assert code == 0 and env["data"]["results"][0]["card"]["id"] == 1
    code, env = kb(capsys, "decision", "list", "--db", db, "--reviewed", "none")
    assert len(env["data"]["decisions"]) == 1
    code, env = kb(capsys, "card", "retire", "1", "--db", db, "--run", run, "--reason", "test")
    assert code == 0 and env["data"]["status"] == "retired"


def test_attribution_golden_set_and_scoring(evals, tmp_path):
    cases = eval_cli.case_files("attribution")
    assert len(cases) >= 10
    for name, path in cases:
        case = eval_cli.read(path)
        (tmp_path / f"{name}.attribution.json").write_text(json.dumps(case["expected"]))
    assert eval_cli.score_attribution(tmp_path)["metrics"]["accuracy"] == 1.0
    (tmp_path / "a02-interview-qa.attribution.json").write_text(json.dumps({"0": "example-guest", "1": "example-guest", "2": "example-guest", "3": "example-guest"}))
    assert eval_cli.score_attribution(tmp_path)["metrics"]["accuracy"] < 1.0


def test_search_golden_set_scores_a_query_card_against_the_fixture_db(evals, tmp_path):
    assert len(eval_cli.case_files("search")) >= 15
    qc = {"intent": "find_rules", "subject": "risk per trade as a percent of the account", "terms": ["risk_per_trade", "position_sizing"], "aliases": ["risk at most 1% of equity", "small risk per trade"]}
    (tmp_path / "s02.query_card.json").write_text(json.dumps(qc))
    (tmp_path / "s07.query_card.json").write_text(json.dumps({"intent": "find_rules", "subject": "vix spikes", "terms": ["vix"]}))
    rep = eval_cli.score_search(tmp_path)
    miss = {f["case"] for f in rep["failures"] if "missing" in f["reason"]}
    assert "s02" not in miss and "s07" in miss and rep["n"] == len(eval_cli.case_files("search"))
    assert 0 < rep["metrics"]["recall@10"] < 1
