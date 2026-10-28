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
