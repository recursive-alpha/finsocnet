"""The golden sets meet the spec minimums (06 §3.1) and the stored baseline outputs still score as recorded."""

import json
from pathlib import Path

import pytest

from finsocnet.core import eval_cli

ROOT = Path(__file__).resolve().parents[2]
MINIMUM = {"transform": 30, "dedup": 40, "search": 30, "attribution": 15}


def _count(name: str) -> int:
    d = ROOT / "evals" / name
    if name == "transform":
        return len([p for p in d.iterdir() if p.is_dir()])
    return len([p for p in d.glob("*.json") if p.name != "fixture_db.json"])


@pytest.mark.parametrize("name,minimum", MINIMUM.items())
def test_set_size(name, minimum):
    assert _count(name) >= minimum


@pytest.mark.parametrize("name", ["transform", "dedup", "attribution", "search"])
def test_baseline_report_matches_stored_outputs(name):
    stored = json.loads((ROOT / "docs" / "improvements" / "eval-2026-10-28" / f"{name}.json").read_text())
    fresh = getattr(eval_cli, f"score_{name}")(ROOT / "evals" / "baseline" / "2026-10-28")
    assert fresh["metrics"] == stored["metrics"]
