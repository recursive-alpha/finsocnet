"""Unified search (specs/10-semantic-search.md §5): types, filters, modes, merged ranking, facets."""

from __future__ import annotations

import pytest

from finsocnet.core import embed, search
from finsocnet.core.output import CliError
from tests.conftest import make_decision
from tests.integration.test_cards import commit, second_card


@pytest.fixture
def kb(seeded, run_id, monkeypatch):
    monkeypatch.setenv("FINSOCNET_EMBED_PROVIDER", "hashing")
    commit(seeded, run_id, make_decision())
    commit(seeded, run_id, make_decision(second_card(), "new", []))
    cid = seeded.execute("SELECT content_id FROM content_segments LIMIT 1").fetchone()[0]
    seeded.execute("UPDATE contents SET language = 'en', title = 'Trailing stops walkthrough', published_at = '2026-09-02' WHERE id = ?", (cid,))
    seeded.execute("INSERT OR IGNORE INTO persons (id, canonical_name, trading_style, primary_markets) VALUES ('example-owner', 'Example Owner', 'swing breakout trader', 'equities')")
    seeded.execute("INSERT INTO person_skills (person_id, skill_name, category, title, summary, content_markdown, source_card_ids_json, produced_by) VALUES "
                   "('example-owner', 'example-owner', 'trade_management', 'Example Owner: trade management', 'sell a third then trail with the ten day average', '# Trade management\\nTrail the rest.', '[1]', 't/t')")
    embed.sync(seeded, ["card", "segment", "person", "skill"])
    return seeded


def test_all_types_are_searched_and_ranked_together(kb):
    r = search.search(kb, "trail the remainder after selling a third", limit=20)
    assert r["mode"] == "hybrid" and set(r["facets"]) == {"cards", "contents", "persons", "skills"} and r["facets"]["cards"] >= 1
    assert r["results"][0]["relevance"] == pytest.approx(max(h["relevance"] for h in r["results"])) and r["results"][0]["type"] in ("cards", "skills", "contents")
    types = {h["type"] for h in r["results"]}
    assert {"cards", "contents", "skills"} <= types
    card = next(h for h in r["results"] if h["type"] == "cards")
    assert card["snippet"].startswith("IF ") and "vec" in card["ranks"] and card["meta"]["kind"] in ("rule", "setup")


def test_types_and_modes(kb):
    only = search.search(kb, "trail the remainder", types=["cards"])
    assert {h["type"] for h in only["results"]} == {"cards"} and list(only["facets"]) == ["cards"]
    lex = search.search(kb, "trail remainder", types=["contents", "skills"], mode="lexical")
    assert lex["mode"] == "lexical" and all("vec" not in h["ranks"] for h in lex["results"])
    sem = search.search(kb, "trail the remainder", types=["contents"], mode="semantic")
    assert sem["results"] and all(set(h["ranks"]) == {"vec"} for h in sem["results"])
    hit = next(h for h in lex["results"] if h["type"] == "contents")
    assert "«" in hit["snippet"] and hit["meta"]["platform"]


def test_filters_per_type_and_ignored_filters_warn(kb):
    assert search.search(kb, "trail the remainder", types=["cards"], filters={"kind": ["rule"]})["total"] >= 1
    assert search.search(kb, "trail the remainder", types=["cards"], filters={"kind": ["metric"]})["total"] == 0
    assert search.search(kb, "trail the remainder", types=["contents"], filters={"platform": ["youtube"], "since": "2026-09-01"})["total"] >= 1
    assert search.search(kb, "trail the remainder", types=["contents"], filters={"since": "2026-10-01"})["total"] == 0
    assert search.search(kb, "trail", types=["skills"], filters={"person_id": ["someone-else"]})["total"] == 0
    r = search.search(kb, "trail", types=["persons"], filters={"platform": "x"})
    assert any("do not apply" in w for w in r["warnings"])


def test_without_embeddings_it_is_lexical_and_explicit_modes_warn(seeded, run_id, monkeypatch):
    monkeypatch.setenv("FINSOCNET_EMBED_PROVIDER", "hashing")
    commit(seeded, run_id, make_decision())
    r = search.search(seeded, "trail the remainder")
    assert r["mode"] == "lexical" and r["facets"]["cards"] >= 1
    w = search.search(seeded, "trail the remainder", mode="semantic")["warnings"]
    assert any("kb embed sync" in x for x in w)


def test_bad_input(seeded):
    for kw in ({"query": " "}, {"query": "x", "types": ["nope"]}, {"query": "x", "mode": "fuzzy"}):
        q = kw.pop("query")
        with pytest.raises(CliError) as e:
            search.search(seeded, q, **kw)
        assert e.value.code == "USAGE"
