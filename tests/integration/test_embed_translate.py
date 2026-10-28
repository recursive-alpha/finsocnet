"""Semantic search plumbing with the offline hashing provider (no model download), translation bookkeeping and the search modes."""

from __future__ import annotations

import pytest

from finsocnet.core import cards, embed, translate
from finsocnet.core.output import CliError
from tests.conftest import make_card, make_decision
from tests.integration.test_cards import commit, second_card


@pytest.fixture
def hashing(monkeypatch):
    monkeypatch.setenv("FINSOCNET_EMBED_PROVIDER", "hashing")


def test_sync_is_incremental_and_status_counts(seeded, run_id, hashing):
    commit(seeded, run_id, make_decision())
    commit(seeded, run_id, make_decision(second_card(), "new", []))
    assert embed.status(seeded)["kinds"]["card"] == {"embedded": 0, "pending": 2}
    assert embed.sync(seeded, ["card"])["kinds"]["card"] == {"embedded": 2, "remaining": 0}
    assert embed.sync(seeded, ["card"])["kinds"]["card"]["embedded"] == 0  # nothing changed: nothing re-embedded
    cards.update_card(seeded, 1, {"notes_append": "x", "aliases_add": ["peel off a third into strength"]}, "alias", run_id)
    assert embed.status(seeded)["kinds"]["card"]["pending"] == 1  # alias is part of the embedded text
    assert embed.model_id() == "hashing-512"


def test_vector_search_ranks_the_closest_card_first(seeded, run_id, hashing):
    commit(seeded, run_id, make_decision())
    commit(seeded, run_id, make_decision(second_card(), "new", []))
    embed.sync(seeded, ["card"])
    hits = embed.vector_search(seeded, cards_text(seeded, 2), ["card"], 5)
    assert hits[0]["ref"] == "2" and hits[0]["score"] > hits[1]["score"]


def cards_text(conn, cid):
    return embed.card_text(cards.card_row(conn, cid))


def test_modes_auto_degrades_and_explicit_warns(seeded, run_id, hashing):
    commit(seeded, run_id, make_decision())
    r = cards.search_cards(seeded, None, "trail the remainder", 5)
    assert r["mode"] == "lexical" and not r["warnings"]  # auto without vectors stays lexical, silently
    r = cards.search_cards(seeded, None, "trail the remainder", 5, "semantic")
    assert r["mode"] == "lexical" or r["results"] == [] or r["warnings"]
    assert any("kb embed sync" in w for w in r["warnings"])
    embed.sync(seeded, ["card"])
    r = cards.search_cards(seeded, None, "partial profit after a breakout", 5)
    assert r["mode"] == "hybrid" and r["results"][0]["score_debug"].get("vec") == 1
    with pytest.raises(CliError):
        cards.search_cards(seeded, None, "x", 5, "nope")


def test_vectors_are_per_model(seeded, run_id, hashing, monkeypatch):
    commit(seeded, run_id, make_decision())
    embed.sync(seeded, ["card"])
    monkeypatch.setenv("FINSOCNET_EMBED_PROVIDER", "fastembed")
    monkeypatch.setenv("FINSOCNET_EMBED_MODEL", "some/other-model")
    assert embed.status(seeded)["kinds"]["card"] == {"embedded": 0, "pending": 1}
    assert embed.status(seeded)["other_models"][0]["model"] == "hashing-512"


# --- language and translation (decided by the agent, stored by the scripts) ---------------------------------------------

VI = "Mình luôn cắt lỗ khi giá đóng cửa dưới MA20, không chần chừ, giữ lại hy vọng là chết."


def _segment(conn, text, seq=5):
    cid = conn.execute("SELECT content_id FROM content_segments LIMIT 1").fetchone()[0]
    conn.execute("INSERT INTO content_segments (content_id, seq, kind, locator_json, text) VALUES (?, ?, 'paragraph', '{}', ?)", (cid, seq, text))
    return cid


def test_unknown_language_blocks_embedding_until_the_agent_decides(seeded, run_id, hashing):
    cid = _segment(seeded, VI)
    seeded.execute("UPDATE contents SET language = NULL WHERE id = ?", (cid,))
    det = translate.detect_pending(seeded)
    assert det and det[0]["content_id"] == cid and det[0]["sample"]
    embed.sync(seeded, ["segment"])
    assert seeded.execute("SELECT COUNT(*) FROM embeddings WHERE kind='segment'").fetchone()[0] == 0
    translate.set_language(seeded, [{"content_id": cid, "language": "en"}], run_id)
    assert not any(d["content_id"] == cid for d in translate.detect_pending(seeded))
    with pytest.raises(CliError):
        translate.set_language(seeded, [{"content_id": "nope", "language": "en"}], run_id)
    with pytest.raises(CliError):
        translate.set_language(seeded, [{"content_id": cid, "language": ""}], run_id)


def test_pending_put_get_and_embedding_uses_the_translation(seeded, run_id, hashing):
    cid = _segment(seeded, VI)
    translate.set_language(seeded, [{"content_id": cid, "language": "vi"}], run_id)
    assert [p["seq"] for p in translate.pending(seeded, content_id=cid)] == [0, 1, 5] or 5 in [p["seq"] for p in translate.pending(seeded, content_id=cid)]
    embed.sync(seeded, ["segment"])
    assert seeded.execute("SELECT COUNT(*) FROM embeddings WHERE kind='segment' AND ref = ?", (f"{cid}#5",)).fetchone()[0] == 0  # not before translation
    with pytest.raises(CliError):
        translate.put(seeded, [{"content_id": cid, "seq": 5, "source_lang": "vi"}], run_id)  # text_en required
    translate.put(seeded, [{"content_id": cid, "seq": 5, "source_lang": "vi", "text_en": "I always cut the loss when the price closes below the 20 day average, without hesitation."}], run_id)
    assert 5 not in [p["seq"] for p in translate.pending(seeded, content_id=cid)]
    embed.sync(seeded, ["segment"])
    assert seeded.execute("SELECT COUNT(*) FROM embeddings WHERE kind='segment' AND ref = ?", (f"{cid}#5",)).fetchone()[0] == 1
    assert translate.get(seeded, cid, 5)[0]["source_lang"] == "vi"


def test_english_segment_inside_a_mixed_content_is_marked_without_text(seeded, run_id, hashing):
    cid = _segment(seeded, "I sell a third after three days.", seq=7)
    translate.set_language(seeded, [{"content_id": cid, "language": "mixed"}], run_id)
    assert 7 in [p["seq"] for p in translate.pending(seeded, content_id=cid)]
    translate.put(seeded, [{"content_id": cid, "seq": 7, "source_lang": "en"}], run_id)
    assert translate.get(seeded, cid, 7)[0]["text_en"] == "I sell a third after three days."
