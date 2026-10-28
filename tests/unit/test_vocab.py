import pytest

from finsocnet.core import vocab
from finsocnet.core.output import CliError


def test_seed_loads_and_lookup_orders_matches(seeded):
    n = seeded.execute("SELECT COUNT(*) FROM vocabulary").fetchone()[0]
    assert n >= 250
    assert vocab.lookup(seeded, "ema_10")[0]["match"] == "exact_term"
    assert vocab.lookup(seeded, "stop loss")[0]["term"] == "stop_loss"
    hit = vocab.lookup(seeded, "cắt lỗ")
    assert hit and hit[0]["term"] == "stop_loss" and hit[0]["match"] == "exact_alias"
    assert vocab.lookup(seeded, "zzzz qqqq") == []


def test_add_rejects_duplicates_and_alias_clashes_listing_all(seeded, run_id):
    items = [{"term": "ema_10", "label": "x", "facet": "indicator", "aliases": []},
             {"term": "new_thing", "label": "new thing", "facet": "indicator", "aliases": ["cắt lỗ"], "broader": "nope"},
             {"term": "Bad-Term", "label": "bad", "facet": "indicator"}]
    with pytest.raises(CliError) as e:
        vocab.add(seeded, items, run_id)
    probs = " ".join(d["problem"] for d in e.value.details)
    assert "already exists" in probs and "owned by term 'stop_loss'" in probs and "invalid term key" in probs and "does not exist" in probs
    assert seeded.execute("SELECT COUNT(*) FROM vocabulary WHERE term = 'new_thing'").fetchone()[0] == 0


def test_add_with_broader_in_same_batch_and_fts_sync(seeded, run_id):
    vocab.add(seeded, [{"term": "launch_pad_x", "label": "launch pad x", "facet": "pattern", "broader": "launch_family"},
                       {"term": "launch_family", "label": "launch family", "facet": "pattern"}], run_id)
    assert seeded.execute("SELECT broader FROM vocabulary WHERE term = 'launch_pad_x'").fetchone()[0] == "launch_family"
    assert seeded.execute("SELECT term FROM vocabulary_fts WHERE vocabulary_fts MATCH '\"launch_pad_x\"'").fetchone()


def test_merge_rewrites_cards_and_suggest_follows_merge(seeded, run_id):
    from tests.conftest import make_card, make_decision
    from finsocnet.core import cards
    vocab.add(seeded, [{"term": "trail_stop_dup", "label": "trail stop dup", "facet": "order_type", "aliases": ["trail dup"]}], run_id)
    res = cards.commit_decisions(seeded, [make_decision()], run_id)
    assert res[0]["status"] == "committed"
    out = vocab.merge(seeded, "trailing_stop", "trail_stop_dup", run_id)
    assert out["cards_rewritten"] == 1
    assert "trail_stop_dup" in cards.card_row(seeded, 1)["terms"] and "trailing_stop" not in cards.card_row(seeded, 1)["terms"]
    assert vocab.suggest(seeded, "trailing_stop") == "trail_stop_dup"
    # FTS follows the rewrite
    assert seeded.execute("SELECT rowid FROM knowledge_cards_fts WHERE knowledge_cards_fts MATCH 'terms : \"trail_stop_dup\"'").fetchone()
