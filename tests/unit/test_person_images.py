

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


def test_static_classes_match_schema_and_other_catches_the_rest(conn, run_id):
    import json
    from pathlib import Path
    from finsocnet.core import classes, persons
    schema = json.loads((Path(__file__).resolve().parents[2] / "finsocnet/core/schemas/person.schema.json").read_text())
    assert set(schema["properties"]["profession"]["enum"]) - {None} == set(classes.IDS) and classes.IDS[-1] == "other"
    persons.upsert(conn, {"id": "a-person", "canonical_name": "A Person"}, run_id)  # no class given
    counts = {c["id"]: c["count"] for c in classes.with_counts(conn)}
    assert counts["other"] == 1 and sum(counts.values()) == 1


def test_query_is_read_only_and_schema_lists_tables(conn):
    import pytest
    from finsocnet.core import dbtools
    from finsocnet.core.output import CliError
    assert dbtools.query("SELECT COUNT(*) AS n FROM persons")["rows"] == [{"n": 0}]
    for bad in ("DELETE FROM persons", "SELECT 1; SELECT 2", "PRAGMA writable_schema = 1"):
        with pytest.raises(CliError):
            dbtools.query(bad)
    assert "persons" in dbtools.schema()["tables"] and dbtools.schema("persons")["tables"]["persons"]["columns"][0]["name"] == "id"


def test_coverage_gaps_and_removals(seeded, run_id):
    from finsocnet.core import persons
    from finsocnet.core.output import CliError
    import pytest
    persons.upsert(seeded, {"id": "jane", "canonical_name": "Jane", "profession": "academic"}, run_id)
    persons.link_add(seeded, {"person_id": "jane", "url": "https://jane.example/", "kind": "website", "evidence": "her own site"}, run_id)
    cov = persons.coverage(seeded, "jane")
    assert cov["class"] == "academic" and not cov["complete"]
    assert any("profile field missing: bio" in g for g in cov["gaps"]) and any("no book" in g for g in cov["gaps"]) and "no active card" in cov["gaps"]
    assert persons.link_remove(seeded, "jane", "https://jane.example/")["removed"] == 1
    persons.alias_add(seeded, "jane", "@jane", "x")
    assert persons.alias_remove(seeded, "jane", "@jane", "x")["removed"] == 1
    assert persons.remove(seeded, "jane", "created by mistake")["removed"] is True
    with pytest.raises(CliError):
        persons.coverage(seeded, "jane")
