import json
import re
from pathlib import Path

from finsocnet.core import classes, taxonomy

ROOT = Path(__file__).resolve().parents[2]


def ids(items):
    return [i["id"] for i in items]


def test_card_lists_match_the_card_schema():
    props = json.loads((ROOT / "finsocnet/core/schemas/card.schema.json").read_text())["properties"]
    for dim, items in (("kind", taxonomy.CARD_KIND), ("category", taxonomy.CARD_CATEGORY), ("domain", taxonomy.CARD_DOMAIN), ("evidence_level", taxonomy.CARD_EVIDENCE),
                       ("horizon", taxonomy.CARD_HORIZON), ("action", taxonomy.CARD_ACTION)):
        assert ids(items) == props[dim]["enum"], dim


def test_vocab_facets_and_content_status_match_the_migration():
    sql = (ROOT / "migrations/003_v2_schema.sql").read_text()
    facets = re.search(r"facet\s+TEXT NOT NULL CHECK \(facet IN \((.*?)\)\)", sql, re.S).group(1)
    assert set(re.findall(r"'(\w+)'", facets)) == set(ids(taxonomy.VOCAB_FACET))
    status = re.search(r"process_status\s+TEXT NOT NULL DEFAULT 'new' CHECK \(process_status IN\s*\((.*?)\)\)", sql, re.S).group(1)
    assert set(re.findall(r"'(\w+)'", status)) == set(ids(taxonomy.CONTENT_STATUS))


def test_every_skill_folder_has_a_group_and_every_group_is_listed():
    on_disk = set(taxonomy.skills_on_disk())
    assert on_disk - set(taxonomy.SKILL_GROUP) == set(), "add the new skill to taxonomy.SKILL_GROUP"
    assert set(taxonomy.SKILL_GROUP) - on_disk == set()
    assert set(taxonomy.SKILL_GROUP.values()) <= set(taxonomy.SKILL_GROUP_ORDER)


def test_every_dimension_has_unique_ids_and_unlisted_values_fall_into_the_catch_all(conn, run_id):
    for key, d in taxonomy.DIMENSIONS.items():
        assert len(ids(d["items"])) == len(set(ids(d["items"]))), key
        assert d["catch_all"] is None or d["catch_all"] in ids(d["items"]), key
    assert ids(classes.CLASSES)[-1] == "other"
    conn.execute("INSERT INTO sources (id, platform, kind) VALUES ('x:1', 'brand-new-platform', 'mystery-kind')")
    t = taxonomy.build(conn, "sources")
    kinds = {i["id"]: i["count"] for i in t["sources.kind"]["items"]}
    assert kinds["other"] == 1 and t["sources.kind"]["unlisted_values"] == ["mystery-kind"]
    # a new platform is not a class: it never shows up in any list, the source is classified by what it publishes
    assert all("brand-new-platform" not in json.dumps(d["items"]) for d in t.values())
    assert {i["id"]: i["count"] for i in t["sources.medium"]["items"]}["other"] == 1


def test_medium_comes_from_the_content_type_not_the_platform(conn):
    conn.execute("INSERT INTO sources (id, platform, kind) VALUES ('s:1', 'whatever', 'channel')")
    for i, t in enumerate(("video", "short", "episode")):
        conn.execute("INSERT INTO contents (id, source_id, platform, content_type, process_status) VALUES (?, 's:1', 'whatever', ?, 'metadata_only')", (f"c:{i}", t))
    m = {i["id"]: i["count"] for i in taxonomy.build(conn, "content")["content.medium"]["items"]}
    assert (m["video"], m["audio"]) == (2, 1)
    assert {i["id"]: i["count"] for i in taxonomy.build(conn, "sources")["sources.medium"]["items"]}["video"] == 1  # majority of its contents
