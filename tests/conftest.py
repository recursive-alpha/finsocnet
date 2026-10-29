from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from finsocnet.core import config, migrations
from finsocnet.core.db import connect
from finsocnet.core.runs import start_run

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def repo(tmp_path, monkeypatch) -> Path:
    """A throw-away repo root with data/ and the real migrations, so tests never touch data/knowledge.db."""
    root = tmp_path / "repo"
    (root / "data" / "transcripts").mkdir(parents=True)
    shutil.copytree(Path(__file__).resolve().parents[1] / "migrations", root / "migrations")
    shutil.copytree(Path(__file__).resolve().parents[1] / "config", root / "config")
    for f in (FIXTURES / "transcripts").glob("*.json"):
        shutil.copy(f, root / "data" / "transcripts" / f.name)
    monkeypatch.setenv("FINSOCNET_ROOT", str(root))
    monkeypatch.setenv("KNOWLEDGE_DB_PATH", "data/knowledge.db")
    monkeypatch.delenv("FINSOCNET_RUN_ID", raising=False)
    return root


@pytest.fixture
def conn(repo):
    c = connect(config.db_path())
    migrations.migrate(c)
    yield c
    c.close()


@pytest.fixture
def run_id(conn) -> int:
    return start_run(conn, "test", "pytest", "manual", "test-model")


def reddit_record(**over):
    rec = json.loads((FIXTURES / "content" / "reddit_thread.json").read_text())
    rec.update(over)
    return rec


@pytest.fixture
def reddit():
    return reddit_record


@pytest.fixture
def seeded(conn, run_id):
    """DB with the vocabulary seed, a person, and a transcript content to cite."""
    from finsocnet.core import content, vocab
    seed = json.loads((Path(__file__).resolve().parents[1] / ".agents/skills/knowledge-transformer/references/vocabulary_seed.json").read_text())
    vocab.add(conn, seed, run_id)
    conn.execute("INSERT INTO persons (id, canonical_name) VALUES ('example-swing-trader', 'Example Swing Trader')")
    segs = [
        {"seq": 0, "kind": "transcript", "locator": {"start_sec": 0, "end_sec": 20},
         "text": "so what I do is, once it's up like 3, 4 days after the breakout I sell a third, a quarter maybe,"},
        {"seq": 1, "kind": "transcript", "locator": {"start_sec": 20, "end_sec": 40},
         "text": "and then the rest I just trail with the 10-day, and if it closes below the 10 I'm out. On slower names I use the 20."},
        {"seq": 2, "kind": "transcript", "locator": {"start_sec": 40, "end_sec": 60},
         "text": "I never hold a loser overnight hoping it comes back, that is how accounts blow up."},
    ]
    content.add_content(conn, {"id": "youtube:abc123def45", "platform": "youtube", "content_type": "video", "fetch_method": "yt-dlp", "title": "Selling into strength",
                               "segments": segs}, run_id)
    return conn


def make_card(**over):
    card = {
        "card_version": 1, "kind": "rule", "domain": "trading_strategy", "category": "trade_management",
        "subject": "partial profit then moving-average trailing exit after breakout",
        "claim": "IF breakout position AND 3-5 days since entry THEN EXIT_PARTIAL 1/4-1/3 of position THEN EXIT remainder UNTIL first tf_daily close below ma_10",
        "conditions": ["position entered on breakout", "3-5 trading days since entry"],
        "action": "EXIT_PARTIAL", "horizon": "swing_weeks", "instruments": ["equities"], "regime": [],
        "terms": ["breakout", "partial_profit", "trailing_stop", "ma_10", "tf_daily"],
        "aliases": ["10-day", "sell a third"], "entities": [],
        "numbers": {"partial_fraction": "1/4-1/3", "partial_after_days": "3-5"},
        "evidence_level": "claimed", "invalidation": None, "notes": None,
        "citation": {"content_id": "youtube:abc123def45", "segment_seq": 0,
                     "quote": "once it's up like 3, 4 days after the breakout I sell a third, a quarter maybe",
                     "speaker": {"person_id": "example-swing-trader", "handle": None, "role": "owner", "confidence": 0.95}},
    }
    card.update(over)
    return card


def make_decision(card=None, decision="new", candidate_ids=(), target=None, **over):
    d = {"new_card": card or make_card(), "candidate_ids": list(candidate_ids), "decision": decision,
         "rationale": "test decision" if candidate_ids else "no candidates"}
    if target is not None:
        d["target_card_id"] = target
    d.update(over)
    return d
