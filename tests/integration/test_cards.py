"""Card validation, retrieval determinism, commit per decision type, idempotency, CONFLICT, FTS triggers, undo."""

from __future__ import annotations

import copy
import json

import pytest

from finsocnet.core import cards
from finsocnet.core.output import CliError
from tests.conftest import make_card, make_decision


def codes(problems):
    return {p["code"] for p in problems}


# --- validation -------------------------------------------------------------------------------------------

def test_valid_card_passes_with_no_problems(seeded):
    probs, warns = cards.validate_card(seeded, make_card())
    assert probs == []


@pytest.mark.parametrize("kind,good,bad", [
    ("rule", "IF breakout THEN LONG on opening_range high", "Sell a third after a few days"),
    ("rule", "IF 3 consecutive losing days THEN SIZE down to 50%", "IF price > ema_10 THEN BUY"),
    ("observation", "gap_up stocks TENDS TO fade WHEN there is no catalyst", "Stocks go up"),
    ("mechanism", "rising real_yield CAUSES multiple_compression BECAUSE cash flows are discounted", "rates affect stocks"),
    ("definition", "adr_pct IS the average daily range as percent of price", "ADR% is the average range"),
    ("metric", "the setup HAS win_rate = 25-30% ON own trades", "win_rate = 30%"),
    ("practice", "reviewing every trade IMPROVES discipline FOR day traders", "reviewing trades is good"),
])
def test_grammar_per_kind(kind, good, bad):
    assert cards.GRAMMAR[kind].match(good)
    assert not cards.GRAMMAR[kind].match(bad)


def test_errors_are_all_reported_with_suggestions(seeded):
    bad = make_card(claim="Sell a third after a few days", terms=["ema10", "breakout"], action="LONG",
                    subject="see 12:40 here")
    bad["citation"]["quote"] = "completely different words not in the transcript"
    bad["citation"]["speaker"]["person_id"] = "nobody"
    probs, _ = cards.validate_card(seeded, bad)
    assert {"GRAMMAR_ERROR", "VOCAB_UNKNOWN", "QUOTE_NOT_FOUND", "VALIDATION_ERROR"} <= codes(probs)
    vocab_prob = next(p for p in probs if p["code"] == "VOCAB_UNKNOWN")
    assert vocab_prob["suggestion"] == "ema_10"


def test_action_must_match_first_then_keyword(seeded):
    probs, _ = cards.validate_card(seeded, make_card(action="EXIT"))
    assert any(p["path"] == "/action" for p in probs)
    probs, _ = cards.validate_card(seeded, make_card(kind="observation", claim="breakout TENDS TO fail WHEN market is choppy", action="LONG"))
    assert any(p["path"] == "/action" for p in probs)


def test_quote_check_ignores_case_punctuation_not_words(seeded):
    ok = make_card()
    ok["citation"]["quote"] = "ONCE ITS UP LIKE 3 4 DAYS AFTER THE BREAKOUT I SELL A THIRD"
    assert cards.validate_card(seeded, ok)[0] == []
    bad = make_card()
    bad["citation"]["quote"] = "once it is up like 3 4 days after the breakout I sell a third"
    assert "QUOTE_NOT_FOUND" in codes(cards.validate_card(seeded, bad)[0])
    spill = make_card()  # quote starting at seg 0 may continue into seg 1 (lookahead of 2)
    spill["citation"]["quote"] = "a quarter maybe, and then the rest I just trail with the 10-day"
    assert cards.validate_card(seeded, spill)[0] == []


def test_tag_stuffing_and_timestamps(seeded):
    probs, _ = cards.validate_card(seeded, make_card(terms=["vix"], claim="IF breakout position THEN EXIT_PARTIAL at 12:40", subject="partial profit rule"))
    assert any("tag stuffing" in p["problem"] for p in probs) and any("timestamps" in p["problem"] for p in probs)


def test_commenter_needs_handle_and_warnings(seeded):
    c = make_card()
    c["citation"]["speaker"] = {"person_id": None, "handle": None, "role": "commenter", "confidence": 1}
    assert any("handle" in p["problem"] for p in cards.validate_card(seeded, c)[0])
    _, warns = cards.validate_card(seeded, make_card(claim=make_card()["claim"] + " within 7 days", numbers={}))
    assert any("numbers in claim" in w for w in warns)


# --- commit -------------------------------------------------------------------------------------------------

def commit(conn, run_id, *decisions, legacy=False):
    return cards.commit_decisions(conn, list(decisions), run_id, legacy)


def second_card(**over):
    c = make_card(subject="trail the remainder with the 10-day moving average",
                  claim="IF position held after partial profit THEN HOLD remainder UNTIL tf_daily close below ma_10",
                  conditions=["partial profit taken"], action="HOLD", terms=["trailing_stop", "ma_10", "tf_daily", "partial_profit"],
                  numbers={"trail_ma": 10}, aliases=["the 20"])
    c["citation"].update(segment_seq=1, quote="and then the rest I just trail with the 10-day")
    c.update(over)
    return c


def test_new_creates_card_citation_decision_and_appearance(seeded, run_id):
    res = commit(seeded, run_id, make_decision())
    assert res[0]["status"] == "committed" and res[0]["result_card"] == 1
    card = cards.get_card(seeded, 1, citations=True)
    assert card["produced_by"] == "manual/test-model" and card["transformer_version"] == "kt-1.0"
    cit = card["citations"][0]
    assert cit["person_id"] == "example-swing-trader" and cit["locator"] == {"start_sec": 0, "end_sec": 20} and cit["quote_verified"] == 1
    assert seeded.execute("SELECT COUNT(*) FROM dedup_decisions").fetchone()[0] == 1
    assert seeded.execute("SELECT role FROM person_appearances WHERE person_id = 'example-swing-trader' AND content_id = 'youtube:abc123def45'").fetchone()[0] == "owner"


def test_recommit_is_idempotent(seeded, run_id):
    commit(seeded, run_id, make_decision())
    again = commit(seeded, run_id, make_decision())
    assert again[0]["status"] == "already_committed" and again[0]["result_card"] == 1
    assert seeded.execute("SELECT COUNT(*) FROM knowledge_cards").fetchone()[0] == 1
    assert seeded.execute("SELECT COUNT(*) FROM card_citations").fetchone()[0] == 1


def test_same_adds_citation_and_unions_aliases(seeded, run_id):
    commit(seeded, run_id, make_decision())
    other = make_card(aliases=["sell a third", "scale out"])
    other["citation"].update(segment_seq=1, quote="and then the rest I just trail with the 10-day")
    res = commit(seeded, run_id, make_decision(other, "same", [1], target=1))
    assert res[0]["status"] == "committed" and res[0]["result_card"] == 1
    c = cards.get_card(seeded, 1, citations=True, history=True)
    assert len(c["citations"]) == 2 and "scale out" in c["aliases"] and len(c["history"]) == 1
    assert seeded.execute("SELECT COUNT(*) FROM knowledge_cards").fetchone()[0] == 1


def test_refines_applies_updates_snapshot_and_stance(seeded, run_id):
    commit(seeded, run_id, make_decision())
    new = make_card(aliases=["the 20"])
    new["citation"].update(segment_seq=1, quote="On slower names I use the 20")
    upd = {"conditions_add": ["slower stocks use ma_20"], "numbers_set": {"trail_ma_slow": 20}, "aliases_add": ["the 20"],
           "terms_add": ["ma_20"], "notes_append": "Variant: ma_20 for slower stocks.", "evidence_level_upgrade": "backtested",
           "invalidation_set": "close above the trailing average"}
    res = commit(seeded, run_id, make_decision(new, "refines", [1], target=1, updates=upd))
    assert res[0]["status"] == "committed", res
    c = cards.get_card(seeded, 1, citations=True)
    assert "ma_20" in c["terms"] and c["numbers"]["trail_ma_slow"] == 20 and c["evidence_level"] == "backtested"
    assert c["invalidation"] and "Variant" in c["notes"]
    assert {x["stance"] for x in c["citations"]} == {"supports", "refines"}
    # the FTS index follows the refinement
    assert seeded.execute("SELECT rowid FROM knowledge_cards_fts WHERE knowledge_cards_fts MATCH 'terms : \"ma_20\"'").fetchone()


@pytest.mark.parametrize("upd,problem", [
    ({"numbers_set": {"partial_after_days": "9"}}, "already"),
    ({"terms_add": ["not_a_term"]}, "unknown term"),
    ({"evidence_level_upgrade": "anecdotal"}, "raised"),
    ({"conditions_add": [f"c{i}" for i in range(12)]}, "12 conditions"),
])
def test_refines_rules_reject(seeded, run_id, upd, problem):
    commit(seeded, run_id, make_decision())
    new = make_card()
    new["citation"].update(segment_seq=1, quote="and then the rest I just trail with the 10-day")
    res = commit(seeded, run_id, make_decision(new, "refines", [1], target=1, updates=upd))
    assert res[0]["status"] == "error" and problem in res[0]["error"]["details"][0]["problem"]
    assert cards.get_card(seeded, 1)["stats"]["citations"] == 1  # savepoint rolled the decision back


def test_related_and_contradicts_require_matching_link(seeded, run_id):
    commit(seeded, run_id, make_decision())
    no_link = commit(seeded, run_id, make_decision(second_card(), "related", [1]))
    assert no_link[0]["status"] == "error" and "link" in no_link[0]["error"]["message"]
    ok = commit(seeded, run_id, make_decision(second_card(), "related", [1], links=[{"to_card": 1, "relation": "related", "rationale": "same setup"}]))
    assert ok[0]["status"] == "committed" and ok[0]["result_card"] == 2
    assert seeded.execute("SELECT relation FROM card_links WHERE from_card = 2 AND to_card = 1").fetchone()[0] == "related"
    opposite = make_card(claim="IF breakout position THEN HOLD overnight UNTIL ma_10 breaks", action="HOLD", subject="hold winners overnight")
    opposite["citation"].update(segment_seq=2, quote="I never hold a loser overnight hoping it comes back")
    res = commit(seeded, run_id, make_decision(opposite, "contradicts", [1], links=[{"to_card": 1, "relation": "contradicts"}]))
    assert res[0]["status"] == "committed"
    assert cards.get_card(seeded, 1)["stats"]["contradictions"] == 1


def test_conflict_when_target_merged_and_batch_isolation(seeded, run_id):
    commit(seeded, run_id, make_decision())
    commit(seeded, run_id, make_decision(second_card(), "new", []))
    cards.merge_cards(seeded, 2, 1, "test", run_id)
    other = make_card()
    other["citation"].update(segment_seq=2, quote="that is how accounts blow up")
    fresh = make_card(subject="never hold a loser overnight", claim="IF position is losing THEN AVOID overnight_hold",
                      action="AVOID", terms=["overnight_hold"], conditions=["losing position"], numbers={}, horizon="overnight")
    fresh["citation"].update(segment_seq=2, quote="I never hold a loser overnight hoping it comes back")
    batch = commit(seeded, run_id, make_decision(other, "same", [2], target=2), make_decision(fresh, "new", []))
    assert batch[0]["status"] == "error" and batch[0]["error"]["code"] == "CONFLICT"
    assert batch[1]["status"] == "committed"


def test_legacy_commit_allows_null_segment_for_textless_content(seeded, run_id):
    from finsocnet.core import content
    content.add_content(seeded, {"id": "youtube:legacy000001", "platform": "youtube", "content_type": "video", "segments": []}, run_id)
    legacy = make_card()
    legacy["citation"].update(content_id="youtube:legacy000001", segment_seq=None, locator={"start_sec": 760})
    assert cards.commit_decisions(seeded, [make_decision(legacy)], run_id)[0]["status"] == "error"
    res = cards.commit_decisions(seeded, [make_decision(legacy)], run_id, legacy=True)
    assert res[0]["status"] == "committed"
    cit = cards.get_card(seeded, res[0]["result_card"], citations=True)["citations"][0]
    assert cit["segment_seq"] is None and cit["quote_verified"] == 0 and cit["locator"] == {"start_sec": 760}
    # content with segments cannot use the legacy escape hatch
    bad = make_card()
    bad["citation"]["segment_seq"] = None
    assert cards.commit_decisions(seeded, [make_decision(bad)], run_id, legacy=True)[0]["status"] == "error"


# --- retrieval ------------------------------------------------------------------------------------------------

def test_candidates_find_related_card_and_are_deterministic(seeded, run_id):
    commit(seeded, run_id, make_decision())
    commit(seeded, run_id, make_decision(second_card(), "new", []))
    probe = make_card(subject="sell part of the position then trail with the 10 day", aliases=["sell a third"])
    first, _ = cards.candidates(seeded, [probe], limit=10)
    second, _ = cards.candidates(seeded, [probe], limit=10)
    ids = [c["card"]["id"] for c in first[0]["candidates"]]
    assert ids == [c["card"]["id"] for c in second[0]["candidates"]] and ids[0] == 1 and set(ids) == {1, 2}
    top = first[0]["candidates"][0]
    assert top["score_debug"] and top["citations"] and top["stats"]["citations"] == 1
    assert cards.candidates(seeded, [make_card(terms=["vix"], subject="zzz qqq", claim="IF zzz THEN LONG qqq", aliases=[], conditions=[])], limit=5)[0][0]["candidates"] == []


def test_siblings_from_same_run_and_segment_are_separated(seeded, run_id):
    commit(seeded, run_id, make_decision())
    entry, _ = cards.candidates(seeded, [make_card()], limit=10, run_id=run_id)
    assert entry[0]["candidates"] == [] and [s["card"]["id"] for s in entry[0]["siblings"]] == [1]


def test_search_with_query_card_text_and_filters(seeded, run_id):
    commit(seeded, run_id, make_decision())
    commit(seeded, run_id, make_decision(second_card(), "new", []))
    q = {"intent": "find_rules", "question": "how do I trail a stop after a breakout?", "subject": "trailing a stop after breakout",
         "terms": ["trailing_stop", "breakout"], "aliases": ["trail with the 10-day"], "filters": {"category": ["trade_management"]},
         "fts_queries": ["terms:(ma_10)", "terms:(((broken"]}
    res = cards.search_cards(seeded, q)
    assert {r["card"]["id"] for r in res["results"]} == {1, 2} and any("FTS syntax error" in w for w in res["warnings"])
    q["filters"] = {"evidence_level_min": "backtested"}
    assert cards.search_cards(seeded, q)["results"] == []
    q["filters"] = {"person_id": ["example-swing-trader"], "kind": ["rule"]}
    assert len(cards.search_cards(seeded, q)["results"]) == 2
    r = cards.search_cards(seeded, text="stop loss trailing ma 10")
    assert r["results"] and "stop_loss" in r["terms_used"] or "ma_10" in r["terms_used"]
    with pytest.raises(CliError):
        cards.search_cards(seeded, {"intent": "nope", "subject": "s", "terms": []})


# --- FTS triggers -----------------------------------------------------------------------------------------------

def fts_hit(conn, expr):
    return [r[0] for r in conn.execute("SELECT rowid FROM knowledge_cards_fts WHERE knowledge_cards_fts MATCH ?", (expr,))]


def test_fts_triggers_insert_update_citation_add_and_move(seeded, run_id):
    commit(seeded, run_id, make_decision())
    commit(seeded, run_id, make_decision(second_card(), "new", []))
    assert fts_hit(seeded, "quotes : \"sell\"") == [1]  # citation quote indexed on insert
    other = make_card()
    other["citation"].update(segment_seq=2, quote="that is how accounts blow up")
    commit(seeded, run_id, make_decision(other, "same", [1], target=1))
    assert fts_hit(seeded, "quotes : \"accounts\"") == [1]  # citation add re-indexes
    seeded.execute("UPDATE knowledge_cards SET claim = 'IF zebra THEN LONG yak' WHERE id = 1")
    assert fts_hit(seeded, "claim : \"zebra\"") == [1] and fts_hit(seeded, "claim : \"IF\"") != []
    seeded.execute("UPDATE card_citations SET card_id = 2 WHERE quote LIKE '%accounts%'")  # citation move
    assert fts_hit(seeded, "quotes : \"accounts\"") == [2]
    assert seeded.execute("SELECT COUNT(*) FROM knowledge_cards_fts").fetchone()[0] == 2
    seeded.execute("INSERT INTO knowledge_cards (id, card_version, kind, domain, category, subject, claim, terms_json, evidence_level, transformer_version, produced_by) "
                   "VALUES (99, 1, 'rule', 'trading_strategy', 'concept', 's', 'c', '[\"vix\"]', 'claimed', 'kt-1.0', 't/t')")
    assert fts_hit(seeded, "terms : \"vix\"") == [99]
    seeded.execute("DELETE FROM knowledge_cards WHERE id = 99")
    assert fts_hit(seeded, "terms : \"vix\"") == []


# --- merge / retire / update / undo ---------------------------------------------------------------------------

def test_merge_moves_citations_and_undo_restores(seeded, run_id):
    commit(seeded, run_id, make_decision())
    commit(seeded, run_id, make_decision(second_card(), "new", [], ))
    res = cards.merge_cards(seeded, 2, 1, "duplicates", run_id)
    assert res["citations_moved"] == 1
    assert cards.card_row(seeded, 2)["status"] == "merged" and cards.card_row(seeded, 2)["merged_into"] == 1
    assert fts_hit(seeded, "quotes : \"trail\"") == [1]
    hist = [h for h in cards.get_card(seeded, 2, history=True)["history"]]
    cards.undo(seeded, hist[0]["id"], run_id)
    assert cards.card_row(seeded, 2)["status"] == "active"
    assert seeded.execute("SELECT card_id FROM card_citations WHERE quote LIKE '%trail with the 10-day' ").fetchone()[0] == 2
    assert 2 in fts_hit(seeded, "quotes : \"trail\"")


def test_retire_update_and_citation_attribution(seeded, run_id):
    commit(seeded, run_id, make_decision())
    out = cards.update_card(seeded, 1, {"claim": "IF breakout position THEN EXIT_PARTIAL one third", "notes_append": "fixed wording"}, "tighten claim", run_id)
    assert out["claim"].endswith("one third") and "fixed wording" in out["notes"]
    with pytest.raises(CliError) as e:
        cards.update_card(seeded, 1, {"claim": "sell some stock soon"}, "bad", run_id)
    assert e.value.code == "GRAMMAR_ERROR"
    with pytest.raises(CliError):
        cards.update_card(seeded, 1, {"status": "retired"}, "not allowed", run_id)
    seeded.execute("INSERT INTO persons (id, canonical_name) VALUES ('p2', 'P Two')")
    cards.attribute_citation(seeded, 1, "p2", "guest", 0.8, run_id)
    assert seeded.execute("SELECT person_id, speaker_role FROM card_citations WHERE id = 1").fetchone()[:] == ("p2", "guest")
    cards.retire_card(seeded, 1, "obsolete", run_id)
    assert cards.card_row(seeded, 1)["status"] == "retired"
    with pytest.raises(CliError):
        cards.retire_card(seeded, 1, "again", run_id)
    assert cards.list_cards(seeded) == []
    d = cards.list_decisions(seeded, reviewed="none")
    assert d and cards.review_decision(seeded, d[0]["id"], "agreed", "ok")["reviewed"] == "agreed"


def test_link_and_unlink_are_snapshotted_and_idempotent(seeded, run_id):
    commit(seeded, run_id, make_decision())
    commit(seeded, run_id, make_decision(second_card(), "new", [], ))
    assert cards.link_cards(seeded, 2, 1, "related", "same topic", run_id)["status"] == "created"
    assert cards.link_cards(seeded, 2, 1, "related", "same topic", run_id)["status"] == "exists"
    assert [(l["from_card"], l["to_card"], l["relation"]) for l in cards.get_card(seeded, 2, links=True)["links"]] == [(2, 1, "related")]
    hist = cards.get_card(seeded, 2, history=True)["history"]
    assert any("link related -> 1" in h["reason"] for h in hist)
    with pytest.raises(CliError):
        cards.link_cards(seeded, 2, 2, "related", "self", run_id)
    with pytest.raises(CliError):
        cards.link_cards(seeded, 2, 1, "likes", "bad relation", run_id)
    assert cards.unlink_cards(seeded, 2, 1, "related", "wrong", run_id)["status"] == "removed"
    with pytest.raises(CliError) as e:
        cards.unlink_cards(seeded, 2, 1, "related", "again", run_id)
    assert e.value.code == "NOT_FOUND"


def test_citation_to_text_nobody_fetched_is_refused(seeded):
    from finsocnet.core import cards
    seeded.execute("UPDATE contents SET fetch_method = NULL")
    problems = cards.validate_cards(seeded, [make_card()])
    assert "no fetch provenance" in json.dumps(problems)
