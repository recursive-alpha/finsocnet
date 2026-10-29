

def test_audit_reports_cards_without_fetched_source(seeded, run_id):
    from finsocnet.core import audit
    from tests.conftest import make_decision
    from tests.integration.test_cards import commit
    commit(seeded, run_id, make_decision())
    seeded.execute("UPDATE contents SET fetch_method = NULL")
    a = audit.run(seeded)
    assert a["cards"]["unsourced_active"] == a["cards"]["active"] > 0
    assert a["contents"]["without_provenance"] >= 1 and any("no fetched content" in t for t in a["todo"])
    seeded.execute("UPDATE contents SET fetch_method = 'api'")
    assert audit.run(seeded)["cards"]["unsourced_active"] == 0
