import copy

from finsocnet.core.records import schema_errors

CARD = {
    "card_version": 1, "kind": "rule", "domain": "trading_strategy", "category": "trade_management",
    "subject": "partial profit then moving-average trailing exit after breakout",
    "claim": "IF breakout position AND 3-5 days since entry THEN EXIT_PARTIAL 1/4-1/3 of position THEN EXIT remainder UNTIL first tf_daily close below ma_10",
    "conditions": ["position entered on breakout"], "action": "EXIT_PARTIAL", "horizon": "swing_weeks", "instruments": ["equities"],
    "terms": ["breakout", "partial_profit", "ma_10"], "aliases": ["the 10-day"], "numbers": {"partial_after_days": "3-5"},
    "evidence_level": "claimed",
    "citation": {"content_id": "youtube:abc123def45", "segment_seq": 41,
                 "quote": "once it's up like 3, 4 days after the breakout I sell a third",
                 "speaker": {"person_id": "example-swing-trader", "handle": None, "role": "owner", "confidence": 0.95}},
}


def test_example_card_is_valid():
    assert schema_errors("card", CARD) == []


def test_card_problems_are_all_reported():
    bad = copy.deepcopy(CARD)
    bad["terms"] = ["EMA-10", "ok_term"]
    bad["kind"] = "idea"
    bad["citation"]["speaker"]["confidence"] = 2
    paths = {e["path"] for e in schema_errors("card", bad)}
    assert {"/terms/0", "/kind", "/citation/speaker/confidence"} <= paths


def test_decision_requires_target_for_same_and_refines():
    d = {"new_card": CARD, "candidate_ids": [41], "decision": "same", "rationale": "same rule as 41"}
    assert any("target_card_id" in e["problem"] for e in schema_errors("decision", d))
    d["target_card_id"] = 41
    assert schema_errors("decision", d) == []
    new = {"new_card": CARD, "candidate_ids": [], "decision": "new", "rationale": "no candidates"}
    assert schema_errors("decision", new) == []


def test_query_card_person_and_skill_schemas():
    q = {"intent": "find_rules", "subject": "holding overnight", "terms": ["overnight_hold"], "fts_queries": ["terms:(overnight_hold)"]}
    assert schema_errors("query_card", q) == []
    assert schema_errors("query_card", {"intent": "x", "subject": "s", "terms": []})
    person = {"id": "example-guest", "canonical_name": "Example Guest", "aliases": [{"alias": "@exampleg", "platform": "x"}]}
    assert schema_errors("person", person) == []
    skill = {"person_id": "p", "skill_name": "p-core", "category": "trade_management", "title": "t", "content_markdown": "m",
             "rules": [{"rule": "r", "card_ids": [41]}]}
    assert schema_errors("person_skill", skill) == []
    skill["rules"][0]["card_ids"] = []
    assert schema_errors("person_skill", skill)
