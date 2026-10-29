"""Static classifications for everything FinSocNet shows and filters by (people, cards, content, sources, skills, vocabulary).

One source of truth. Fixed lists with labels, groups and hints; a value that is not in a list is counted under the dimension's
`catch_all` (an `other` entry), it never creates a new class. Agents and the web UI read this through `kb taxonomy`; the schemas,
migrations and skills folder are checked against it by tests, so a new value must be added here on purpose."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from finsocnet.core import classes, config


def _e(id_: str, label: str | None = None, group: str = "", hint: str = "") -> dict[str, str]:
    return {"id": id_, "label": label or id_.replace("_", " ").capitalize(), "group": group, "hint": hint}


# ---- cards (values mirror card.schema.json and the DB CHECKs) ----
CARD_KIND = [_e("rule", hint="IF … THEN …"), _e("setup", hint="a named pattern with conditions"), _e("observation", hint="what tends to happen"),
             _e("mechanism", hint="why it happens"), _e("definition", hint="what a term means"), _e("metric", hint="a measured number"),
             _e("practice", hint="a habit or process")]
CARD_CATEGORY = [_e("setup_and_screening", "Setup & screening", "Trading"), _e("entry_and_execution", "Entry & execution", "Trading"),
                 _e("trade_management", "Trade management", "Trading"), _e("risk_and_sizing", "Risk & sizing", "Trading"),
                 _e("psychology_and_review", "Psychology & review", "Trading"), _e("market_dynamics", "Market dynamics", "Markets & economics"),
                 _e("concept", "Concept", "Markets & economics"), _e("research_method", "Research method", "Markets & economics")]
CARD_DOMAIN = [_e("trading_strategy"), _e("stock_market"), _e("market_microstructure"), _e("macro_economics"), _e("valuation"), _e("risk_management"),
               _e("psychology"), _e("quant_research"), _e("derivatives"), _e("crypto"), _e("forex"), _e("fixed_income"),
               _e("general_finance", "General finance", hint="catch-all")]
CARD_EVIDENCE = [_e("anecdotal", hint="one story"), _e("claimed", hint="stated, no data"), _e("backtested", hint="shown on data"), _e("audited", hint="verified record or peer-reviewed")]
CARD_HORIZON = [_e("intraday"), _e("overnight"), _e("swing_days", "Swing (days)"), _e("swing_weeks", "Swing (weeks)"), _e("position"), _e("n/a", "n/a")]
CARD_ACTION = [_e(a) for a in ("LONG", "SHORT", "ADD", "EXIT", "EXIT_PARTIAL", "AVOID", "HOLD", "SIZE", "NONE")]

# ---- content ----
CONTENT_STATUS = [_e("metadata_only", "Listed only", hint="inventory, text not fetched"), _e("new", "Fetched, not mined"), _e("processing", "Being mined"),
                  _e("processed", "Mined"), _e("failed"), _e("skipped_duplicate", "Duplicate"), _e("needs_review", "Needs review")]

# ---- medium: what a thing IS, independent of where it lives. Platforms come and go (they stay a free-text attribute, shown as a badge, never a class). ----
MEDIUM = [_e("video", "Video", "Watch", "long videos, shorts, live streams, lectures"), _e("audio", "Audio", "Watch", "podcast episodes, radio, recordings"),
          _e("article", "Article", "Read", "blog posts, newsletters, columns, news, web pages"), _e("social", "Social post", "Read", "short posts, threads, comments, chat"),
          _e("paper", "Paper", "Research", "papers, working papers, theses, reports"), _e("book", "Book", "Research", "books and long-form texts"),
          _e("code", "Code", "Other formats", "repositories, notebooks"), _e("document", "Document", "Other formats", "files, filings, slides, spreadsheets"),
          _e("other", "Other", "Other formats", "catch-all")]
# content_type (what the stored record says) -> medium. Unknown types are `other`.
TYPE_MEDIUM = {"video": "video", "short": "video", "stream": "video", "episode": "audio", "article": "article", "page": "article", "post": "social", "thread": "social",
               "comment": "social", "paper": "paper", "book": "book", "repo": "code", "file": "document", "filing": "document"}
CONTENT_TYPE = [_e(t, group=TYPE_MEDIUM[t]) for t in TYPE_MEDIUM] + [_e("other", group="other", hint="catch-all")]
# fallback medium of a source that has no content yet, from its kind
KIND_MEDIUM = {"channel": "video", "publication": "article", "feed": "article", "site": "article", "book": "book", "paper": "paper", "author": "paper", "user": "social", "group": "social"}
LINK_KIND = [_e(k) for k in ("website", "social", "video", "audio", "newsletter", "book", "course", "paper", "scholar", "wiki", "code", "store", "other")]


def _type_case(col: str = "content_type") -> str:
    whens = " ".join(f"WHEN '{t}' THEN '{f}'" for t, f in TYPE_MEDIUM.items())
    return f"CASE {col} {whens} ELSE 'other' END"


def _source_medium_expr() -> str:
    kind_case = "CASE kind " + " ".join(f"WHEN '{k}' THEN '{f}'" for k, f in KIND_MEDIUM.items()) + " ELSE 'other' END"
    top = (f"(SELECT {_type_case('c.content_type')} FROM contents c WHERE c.source_id = sources.id GROUP BY c.content_type ORDER BY COUNT(*) DESC LIMIT 1)")
    return f"COALESCE({top}, {kind_case})"


SOURCE_KIND = [_e("channel"), _e("feed"), _e("publication"), _e("user", "Account"), _e("author"), _e("group", "Group / community"), _e("site", "Website"), _e("book"), _e("paper"), _e("other", hint="catch-all")]
SOURCE_STATUS = [_e("active"), _e("paused"), _e("blocked"), _e("gone"), _e("needs_review", "Needs review")]

# ---- vocabulary facets (DB CHECK on vocabulary.facet) ----
VOCAB_FACET = [_e("indicator", group="Technical"), _e("pattern", group="Technical"), _e("setup", group="Technical"), _e("timeframe", group="Technical"),
               _e("order_type", group="Execution"), _e("metric", group="Measures"), _e("data", group="Measures"), _e("risk", group="Measures"),
               _e("concept", group="Ideas"), _e("psychology", group="Ideas"), _e("process", group="Ideas"), _e("event", group="Markets"), _e("market", group="Markets"),
               _e("instrument", group="Markets"), _e("asset_class", "Asset class", "Markets"), _e("tool", group="Tools")]

# ---- skills: every folder under .agents/skills belongs to exactly one group (a test enforces it) ----
SKILL_GROUP_ORDER = ["Knowledge core", "People", "Access", "Loop", "Video & audio", "Social", "Writing", "Web", "Research & code", "Unreadable data", "Other"]
SKILL_GROUP = {
    **{s: "Knowledge core" for s in ("knowledge-db", "knowledge-transformer", "knowledge-dedup", "knowledge-search", "market-idea-miner", "translator")},
    **{s: "People" for s in ("people-discoverer", "person-explorer", "person-profiler", "person-matcher", "person-skill-synthesizer", "person-skills-explorer")},
    **{s: "Access" for s in ("session-bridge", "agent-browser")},
    **{s: "Loop" for s in ("source-explorer", "self-improver", "skill-installer", "platform-skill-builder", "finsocnet")},
    **{s: "Video & audio" for s in ("youtube-extractor", "audio-transcriber", "podcast-explorer", "tiktok-explorer")},
    **{s: "Social" for s in ("x-explorer", "reddit-explorer", "bluesky-explorer", "threads-explorer", "instagram-explorer", "facebook-explorer", "linkedin-explorer",
                            "stocktwits-explorer", "discord-explorer", "telegram-explorer")},
    **{s: "Writing" for s in ("medium-explorer", "substack-explorer", "rss-explorer", "seekingalpha-explorer", "forum-explorer", "stackexchange-explorer",
                             "hackernews-explorer", "tradingview-explorer")},
    **{s: "Web" for s in ("web-searcher", "google-searcher", "web-reader", "document-reader")},
    **{s: "Research & code" for s in ("paper-code-explorer", "research-explorer", "annas-archive-explorer", "sec-edgar-explorer", "github-explorer")},
    **{s: "Unreadable data" for s in ("reverse-anything",)},
}
RULEBOOK_CATEGORY = CARD_CATEGORY + [_e("overview", group="Rulebook"), _e("checklists", group="Rulebook")]

DIMENSIONS: dict[str, dict[str, Any]] = {
    "people.class": {"entity": "people", "items": classes.CLASSES, "catch_all": "other", "table": "persons", "column": "COALESCE(profession, 'other')", "where": "status = 'active'"},
    "cards.kind": {"entity": "cards", "items": CARD_KIND, "catch_all": None, "table": "knowledge_cards", "column": "kind", "where": "status = 'active'"},
    "cards.category": {"entity": "cards", "items": CARD_CATEGORY, "catch_all": None, "table": "knowledge_cards", "column": "category", "where": "status = 'active'"},
    "cards.domain": {"entity": "cards", "items": CARD_DOMAIN, "catch_all": "general_finance", "table": "knowledge_cards", "column": "domain", "where": "status = 'active'"},
    "cards.evidence_level": {"entity": "cards", "items": CARD_EVIDENCE, "catch_all": None, "table": "knowledge_cards", "column": "evidence_level", "where": "status = 'active'"},
    "cards.horizon": {"entity": "cards", "items": CARD_HORIZON, "catch_all": "n/a", "table": "knowledge_cards", "column": "horizon", "where": "status = 'active'"},
    "cards.action": {"entity": "cards", "items": CARD_ACTION, "catch_all": "NONE", "table": "knowledge_cards", "column": "action", "where": "status = 'active'"},
    "content.medium": {"entity": "content", "items": MEDIUM, "catch_all": "other", "table": "contents", "column": _type_case(), "where": "1=1", "computed": True},
    "content.type": {"entity": "content", "items": CONTENT_TYPE, "catch_all": "other", "table": "contents", "column": "content_type", "where": "1=1"},
    "content.status": {"entity": "content", "items": CONTENT_STATUS, "catch_all": None, "table": "contents", "column": "process_status", "where": "1=1"},
    "sources.medium": {"entity": "sources", "items": MEDIUM, "catch_all": "other", "table": "sources", "column": _source_medium_expr(), "where": "1=1", "computed": True},
    "links.kind": {"entity": "links", "items": LINK_KIND, "catch_all": "other", "table": "person_links", "column": "kind", "where": "match_status != 'rejected'"},
    "sources.kind": {"entity": "sources", "items": SOURCE_KIND, "catch_all": "other", "table": "sources", "column": "kind", "where": "1=1"},
    "sources.status": {"entity": "sources", "items": SOURCE_STATUS, "catch_all": None, "table": "sources", "column": "status", "where": "1=1"},
    "vocab.facet": {"entity": "vocab", "items": VOCAB_FACET, "catch_all": None, "table": "vocabulary", "column": "facet", "where": "1=1"},
    "rulebooks.category": {"entity": "rulebooks", "items": RULEBOOK_CATEGORY, "catch_all": None, "table": "person_skills", "column": "category", "where": "1=1"},
}


def skills_on_disk() -> list[str]:
    root = config.repo_root() / ".agents" / "skills"
    return sorted(p.name for p in root.iterdir() if p.is_dir()) if root.exists() else []


def skill_group(name: str) -> str:
    return SKILL_GROUP.get(name, "Other")


def _counts(conn: sqlite3.Connection, d: dict[str, Any]) -> dict[str, int]:
    return {str(r[0]): r[1] for r in conn.execute(f"SELECT {d['column']}, COUNT(*) FROM {d['table']} WHERE {d['where']} GROUP BY 1")}


def build(conn: sqlite3.Connection, entity: str | None = None) -> dict[str, Any]:
    """Every dimension (or one entity's) as `{id, label, group, hint, count}` in a fixed order; counts of unlisted values are added to the catch-all."""
    out: dict[str, Any] = {}
    for key, d in DIMENSIONS.items():
        if entity and d["entity"] != entity:
            continue
        counts = _counts(conn, d)
        known = {i["id"] for i in d["items"]}
        extra = sum(n for v, n in counts.items() if v not in known)
        catch = d["catch_all"]
        items = [{**i, "count": counts.get(i["id"], 0) + (extra if i["id"] == catch else 0)} for i in d["items"]]
        out[key] = {"entity": d["entity"], "catch_all": catch, "items": items, "unlisted_values": sorted(v for v in counts if v not in known)}
        if key == "content.medium":  # what the dashboard needs: how much of each medium is only listed, fetched, mined
            for r in conn.execute(f"SELECT {d['column']} AS f, SUM(fetch_method IS NOT NULL AND process_status != 'metadata_only') AS fetched, SUM(process_status = 'processed') AS mined, "
                                  "SUM(cards_count) AS cards FROM contents GROUP BY 1"):
                for i in items:
                    if i["id"] == r["f"]:
                        i.update(fetched=r["fetched"] or 0, mined=r["mined"] or 0, cards=r["cards"] or 0)
    if not entity or entity == "skills":
        names = skills_on_disk()
        groups: dict[str, list[str]] = {}
        for n in names:
            groups.setdefault(skill_group(n), []).append(n)
        out["skills.group"] = {"entity": "skills", "catch_all": "Other", "unlisted_values": sorted(n for n in names if n not in SKILL_GROUP),
                               "items": [{"id": g, "label": g, "group": "", "hint": "", "count": len(groups.get(g, [])), "skills": groups.get(g, [])} for g in SKILL_GROUP_ORDER]}
    return out


def skill_groups() -> dict[str, str]:
    return {n: skill_group(n) for n in skills_on_disk()}


def clause(dim: str, column: str, value: str) -> tuple[str, list[str]]:
    """SQL for "column is `value`" in a static dimension; the catch-all (`other`) also matches every value that is not in the static list."""
    d = DIMENSIONS[dim]
    if d.get("computed"):  # a CASE expression that already maps every value to a listed one
        return f"({column}) = ?", [value]
    if value == d["catch_all"]:
        listed = [i["id"] for i in d["items"] if i["id"] != value]
        return f"({column} IS NULL OR {column} = ? OR {column} NOT IN ({','.join('?' * len(listed))}))", [value, *listed]
    return f"{column} = ?", [value]
