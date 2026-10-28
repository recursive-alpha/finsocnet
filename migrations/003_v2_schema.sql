-- Migration 003: FinSocNet v2 schema (docs/spec/01-database.md §2). SQLite only, FTS5, no vectors (ADR-001).
-- Generated from the spec DDL; executed by 003_v2_schema.py after the v1 tables were renamed to legacy_*.

-- 2.1 Runs
CREATE TABLE agent_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    skill         TEXT NOT NULL,
    goal          TEXT,
    harness       TEXT,
    model         TEXT,
    parent_run_id INTEGER REFERENCES agent_runs(id),
    started_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    finished_at   TEXT,
    outcome       TEXT CHECK (outcome IN ('success','partial','failed','aborted')),
    stats_json    TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(stats_json)),
    errors_json   TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(errors_json))
);

-- 2.2 Sources, contents, segments
CREATE TABLE sources (
    id               TEXT PRIMARY KEY,
    platform         TEXT NOT NULL,
    kind             TEXT NOT NULL,
    url              TEXT,
    title            TEXT,
    person_id        TEXT REFERENCES persons(id),
    requires_session INTEGER NOT NULL DEFAULT 0,
    crawl_cursor     TEXT,
    last_crawled_at  TEXT,
    status           TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','paused','blocked','gone','needs_review')),
    notes            TEXT,
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX idx_sources_platform ON sources(platform);
CREATE INDEX idx_sources_person   ON sources(person_id);

CREATE TABLE contents (
    id                 TEXT PRIMARY KEY,
    source_id          TEXT REFERENCES sources(id),
    platform           TEXT NOT NULL,
    content_type       TEXT NOT NULL,
    url                TEXT,
    title              TEXT,
    description        TEXT,
    author_handle      TEXT,
    author_platform_user_id TEXT,
    person_id          TEXT REFERENCES persons(id),
    published_at       TEXT,
    language           TEXT,
    duration_sec       INTEGER,
    metrics_json       TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metrics_json)),
    links_json         TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(links_json)),
    mentions_json      TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(mentions_json)),
    media_json         TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(media_json)),
    extra_json         TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(extra_json)),
    parent_content_id  TEXT REFERENCES contents(id),
    raw_path           TEXT,
    fetch_method       TEXT,
    fetched_at         TEXT,
    content_hash       TEXT,
    duplicate_of       TEXT REFERENCES contents(id),
    process_status     TEXT NOT NULL DEFAULT 'new' CHECK (process_status IN
                       ('metadata_only','new','processing','processed','failed','skipped_duplicate','needs_review')),
    processed_upto_seq INTEGER NOT NULL DEFAULT -1,
    cards_count        INTEGER NOT NULL DEFAULT 0,
    processed_with     TEXT,
    processed_at       TEXT,
    process_error      TEXT,
    summary            TEXT,
    created_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX idx_contents_source ON contents(source_id);
CREATE INDEX idx_contents_status ON contents(process_status);
CREATE INDEX idx_contents_hash   ON contents(content_hash);
CREATE INDEX idx_contents_person ON contents(person_id);

CREATE TABLE content_segments (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id     TEXT NOT NULL REFERENCES contents(id),
    seq            INTEGER NOT NULL,
    kind           TEXT NOT NULL,
    locator_json   TEXT NOT NULL CHECK (json_valid(locator_json)),
    author_handle  TEXT,
    person_id      TEXT REFERENCES persons(id),
    speaker_hint   TEXT,
    text           TEXT NOT NULL,
    UNIQUE (content_id, seq)
);
CREATE INDEX idx_segments_person ON content_segments(person_id);

CREATE VIRTUAL TABLE segments_fts USING fts5(
    text,
    content = 'content_segments', content_rowid = 'id',
    tokenize = "unicode61 remove_diacritics 2"
);
CREATE TRIGGER segments_ai AFTER INSERT ON content_segments BEGIN
  INSERT INTO segments_fts(rowid, text) VALUES (NEW.id, NEW.text);
END;
CREATE TRIGGER segments_ad AFTER DELETE ON content_segments BEGIN
  INSERT INTO segments_fts(segments_fts, rowid, text) VALUES ('delete', OLD.id, OLD.text);
END;
CREATE TRIGGER segments_au AFTER UPDATE OF text ON content_segments BEGIN
  INSERT INTO segments_fts(segments_fts, rowid, text) VALUES ('delete', OLD.id, OLD.text);
  INSERT INTO segments_fts(rowid, text) VALUES (NEW.id, NEW.text);
END;

-- 2.3 Persons
CREATE TABLE persons (
    id               TEXT PRIMARY KEY,
    canonical_name   TEXT NOT NULL,
    moniker          TEXT,
    bio              TEXT,
    avatar_url       TEXT,
    trading_style    TEXT,
    primary_markets  TEXT,
    verified_records TEXT,
    visibility       TEXT NOT NULL DEFAULT 'public' CHECK (visibility IN ('public','private_source')),
    status           TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','merged')),
    merged_into      TEXT REFERENCES persons(id),
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE person_aliases (
    alias_key  TEXT NOT NULL,
    alias      TEXT NOT NULL,
    platform   TEXT NOT NULL DEFAULT '',
    person_id  TEXT NOT NULL REFERENCES persons(id),
    PRIMARY KEY (alias_key, platform)
);
CREATE INDEX idx_alias_person ON person_aliases(person_id);

CREATE TABLE person_appearances (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id        TEXT NOT NULL REFERENCES persons(id),
    content_id       TEXT REFERENCES contents(id),
    source_id        TEXT REFERENCES sources(id),
    role             TEXT NOT NULL CHECK (role IN ('owner','guest','host','co_host','author','co_author',
                                                    'commenter','member','archive','mentioned')),
    match_confidence REAL NOT NULL DEFAULT 1.0,
    match_status     TEXT NOT NULL DEFAULT 'confirmed' CHECK (match_status IN ('confirmed','needs_review','rejected')),
    evidence         TEXT,
    run_id           INTEGER REFERENCES agent_runs(id),
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE (person_id, content_id, source_id, role)
);

CREATE VIRTUAL TABLE persons_fts USING fts5(person_id UNINDEXED, names, bio,
    tokenize = "unicode61 remove_diacritics 2");
CREATE TRIGGER persons_fts_ai AFTER INSERT ON persons BEGIN
  DELETE FROM persons_fts WHERE person_id = NEW.id;
  INSERT INTO persons_fts(person_id, names, bio)
  SELECT p.id,
         p.canonical_name || ' ' || COALESCE(p.moniker, '') || ' ' ||
           COALESCE((SELECT group_concat(alias, ' ') FROM person_aliases WHERE person_id = p.id), ''),
         COALESCE(p.bio, '')
  FROM persons p WHERE p.id = NEW.id;
END;
CREATE TRIGGER persons_fts_au AFTER UPDATE ON persons BEGIN
  DELETE FROM persons_fts WHERE person_id = OLD.id;
  DELETE FROM persons_fts WHERE person_id = NEW.id;
  INSERT INTO persons_fts(person_id, names, bio)
  SELECT p.id,
         p.canonical_name || ' ' || COALESCE(p.moniker, '') || ' ' ||
           COALESCE((SELECT group_concat(alias, ' ') FROM person_aliases WHERE person_id = p.id), ''),
         COALESCE(p.bio, '')
  FROM persons p WHERE p.id = NEW.id;
END;
CREATE TRIGGER persons_fts_ad AFTER DELETE ON persons BEGIN
  DELETE FROM persons_fts WHERE person_id = OLD.id;
END;
CREATE TRIGGER aliases_fts_ai AFTER INSERT ON person_aliases BEGIN
  DELETE FROM persons_fts WHERE person_id = NEW.person_id;
  INSERT INTO persons_fts(person_id, names, bio)
  SELECT p.id,
         p.canonical_name || ' ' || COALESCE(p.moniker, '') || ' ' ||
           COALESCE((SELECT group_concat(alias, ' ') FROM person_aliases WHERE person_id = p.id), ''),
         COALESCE(p.bio, '')
  FROM persons p WHERE p.id = NEW.person_id;
END;
CREATE TRIGGER aliases_fts_ad AFTER DELETE ON person_aliases BEGIN
  DELETE FROM persons_fts WHERE person_id = OLD.person_id;
  INSERT INTO persons_fts(person_id, names, bio)
  SELECT p.id,
         p.canonical_name || ' ' || COALESCE(p.moniker, '') || ' ' ||
           COALESCE((SELECT group_concat(alias, ' ') FROM person_aliases WHERE person_id = p.id), ''),
         COALESCE(p.bio, '')
  FROM persons p WHERE p.id = OLD.person_id;
END;

-- 2.4 Vocabulary
CREATE TABLE vocabulary (
    term          TEXT PRIMARY KEY CHECK (term GLOB '[a-z0-9]*' AND term NOT GLOB '*[^a-z0-9_]*'),
    label         TEXT NOT NULL,
    facet         TEXT NOT NULL CHECK (facet IN ('indicator','pattern','setup','order_type','timeframe','metric',
                                                  'concept','instrument','market','event','risk','psychology',
                                                  'process','asset_class','data','tool')),
    aliases_json  TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(aliases_json)),
    broader       TEXT REFERENCES vocabulary(term),
    definition    TEXT,
    status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','merged')),
    merged_into   TEXT REFERENCES vocabulary(term),
    run_id        INTEGER REFERENCES agent_runs(id),
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE VIRTUAL TABLE vocabulary_fts USING fts5(term, label, aliases, definition,
    tokenize = "unicode61 remove_diacritics 2 tokenchars '_'");
CREATE TRIGGER vocabulary_fts_ai AFTER INSERT ON vocabulary BEGIN
  INSERT INTO vocabulary_fts(rowid, term, label, aliases, definition)
  VALUES (NEW.rowid, NEW.term, NEW.label,
          COALESCE((SELECT group_concat(value, ' ; ') FROM json_each(NEW.aliases_json)), ''),
          COALESCE(NEW.definition, ''));
END;
CREATE TRIGGER vocabulary_fts_au AFTER UPDATE ON vocabulary BEGIN
  DELETE FROM vocabulary_fts WHERE rowid = OLD.rowid;
  INSERT INTO vocabulary_fts(rowid, term, label, aliases, definition)
  VALUES (NEW.rowid, NEW.term, NEW.label,
          COALESCE((SELECT group_concat(value, ' ; ') FROM json_each(NEW.aliases_json)), ''),
          COALESCE(NEW.definition, ''));
END;
CREATE TRIGGER vocabulary_fts_ad AFTER DELETE ON vocabulary BEGIN
  DELETE FROM vocabulary_fts WHERE rowid = OLD.rowid;
END;

-- 2.5 Knowledge cards
CREATE TABLE knowledge_cards (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    card_version         INTEGER NOT NULL,
    kind                 TEXT NOT NULL CHECK (kind IN ('rule','setup','observation','mechanism','definition','metric','practice')),
    domain               TEXT NOT NULL CHECK (domain IN ('trading_strategy','stock_market','market_microstructure',
                             'macro_economics','valuation','risk_management','psychology','quant_research',
                             'derivatives','crypto','forex','fixed_income','general_finance')),
    category             TEXT NOT NULL CHECK (category IN ('setup_and_screening','entry_and_execution','trade_management',
                             'risk_and_sizing','psychology_and_review','market_dynamics','concept','research_method')),
    subject              TEXT NOT NULL,
    claim                TEXT NOT NULL,
    conditions_json      TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(conditions_json)),
    action               TEXT CHECK (action IN ('LONG','SHORT','ADD','EXIT','EXIT_PARTIAL','AVOID','HOLD','SIZE','NONE')),
    horizon              TEXT CHECK (horizon IN ('intraday','overnight','swing_days','swing_weeks','position','n/a')),
    instruments_json     TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(instruments_json)),
    regime_json          TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(regime_json)),
    terms_json           TEXT NOT NULL CHECK (json_valid(terms_json) AND json_array_length(terms_json) >= 1),
    aliases_json         TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(aliases_json)),
    entities_json        TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(entities_json)),
    numbers_json         TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(numbers_json)),
    evidence_level       TEXT NOT NULL CHECK (evidence_level IN ('anecdotal','claimed','backtested','audited')),
    invalidation         TEXT,
    notes                TEXT,
    status               TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','merged','retired')),
    merged_into          INTEGER REFERENCES knowledge_cards(id),
    transformer_version  TEXT NOT NULL,
    produced_by          TEXT NOT NULL,
    run_id               INTEGER REFERENCES agent_runs(id),
    created_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX idx_cards_status   ON knowledge_cards(status);
CREATE INDEX idx_cards_category ON knowledge_cards(category);

CREATE TABLE card_citations (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id                INTEGER NOT NULL REFERENCES knowledge_cards(id),
    content_id             TEXT NOT NULL REFERENCES contents(id),
    segment_seq            INTEGER,
    locator_json           TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(locator_json)),
    person_id              TEXT REFERENCES persons(id),
    author_handle          TEXT,
    speaker_role           TEXT CHECK (speaker_role IN ('owner','guest','host','co_host','author','co_author',
                                                        'commenter','member','unknown')),
    attribution_confidence REAL NOT NULL DEFAULT 1.0,
    quote                  TEXT NOT NULL,
    quote_verified         INTEGER NOT NULL DEFAULT 1,
    stance                 TEXT NOT NULL DEFAULT 'supports' CHECK (stance IN ('supports','refines')),
    run_id                 INTEGER REFERENCES agent_runs(id),
    added_at               TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE (card_id, content_id, segment_seq)
);
CREATE INDEX idx_citations_card    ON card_citations(card_id);
CREATE INDEX idx_citations_person  ON card_citations(person_id);
CREATE INDEX idx_citations_content ON card_citations(content_id);

CREATE TABLE card_links (
    from_card  INTEGER NOT NULL REFERENCES knowledge_cards(id),
    to_card    INTEGER NOT NULL REFERENCES knowledge_cards(id),
    relation   TEXT NOT NULL CHECK (relation IN ('related','contradicts','prerequisite','example_of','refines')),
    rationale  TEXT,
    run_id     INTEGER REFERENCES agent_runs(id),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    PRIMARY KEY (from_card, to_card, relation),
    CHECK (from_card <> to_card)
);

CREATE TABLE card_history (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id       INTEGER NOT NULL REFERENCES knowledge_cards(id),
    snapshot_json TEXT NOT NULL CHECK (json_valid(snapshot_json)),
    reason        TEXT NOT NULL,
    run_id        INTEGER REFERENCES agent_runs(id),
    at            TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE dedup_decisions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint        TEXT NOT NULL UNIQUE,
    new_card_json      TEXT NOT NULL CHECK (json_valid(new_card_json)),
    candidate_ids_json TEXT NOT NULL CHECK (json_valid(candidate_ids_json)),
    decision           TEXT NOT NULL CHECK (decision IN ('same','refines','related','contradicts','new')),
    target_card        INTEGER REFERENCES knowledge_cards(id),
    result_card        INTEGER NOT NULL REFERENCES knowledge_cards(id),
    rationale          TEXT NOT NULL,
    produced_by        TEXT NOT NULL,
    run_id             INTEGER REFERENCES agent_runs(id),
    reviewed           TEXT CHECK (reviewed IN ('agreed','overturned')),
    review_note        TEXT,
    created_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE VIRTUAL TABLE knowledge_cards_fts USING fts5(
    subject, claim, conditions, terms, aliases, entities, quotes,
    tokenize = "porter unicode61 remove_diacritics 2 tokenchars '_'"
);
CREATE TRIGGER cards_fts_ai AFTER INSERT ON knowledge_cards BEGIN
  INSERT INTO knowledge_cards_fts(rowid, subject, claim, conditions, terms, aliases, entities, quotes)
  SELECT k.id, k.subject, k.claim,
    COALESCE((SELECT group_concat(value, ' ; ') FROM json_each(k.conditions_json)), ''),
    COALESCE((SELECT group_concat(value, ' ')   FROM json_each(k.terms_json)), ''),
    COALESCE((SELECT group_concat(value, ' ; ') FROM json_each(k.aliases_json)), ''),
    COALESCE((SELECT group_concat(value, ' ')   FROM json_each(k.entities_json)), ''),
    COALESCE((SELECT group_concat(quote, ' ; ') FROM card_citations WHERE card_id = k.id), '')
  FROM knowledge_cards k WHERE k.id = NEW.id;
END;
CREATE TRIGGER cards_fts_au AFTER UPDATE ON knowledge_cards BEGIN
  DELETE FROM knowledge_cards_fts WHERE rowid = OLD.id;
  INSERT INTO knowledge_cards_fts(rowid, subject, claim, conditions, terms, aliases, entities, quotes)
  SELECT k.id, k.subject, k.claim,
    COALESCE((SELECT group_concat(value, ' ; ') FROM json_each(k.conditions_json)), ''),
    COALESCE((SELECT group_concat(value, ' ')   FROM json_each(k.terms_json)), ''),
    COALESCE((SELECT group_concat(value, ' ; ') FROM json_each(k.aliases_json)), ''),
    COALESCE((SELECT group_concat(value, ' ')   FROM json_each(k.entities_json)), ''),
    COALESCE((SELECT group_concat(quote, ' ; ') FROM card_citations WHERE card_id = k.id), '')
  FROM knowledge_cards k WHERE k.id = NEW.id;
END;
CREATE TRIGGER cards_fts_ad AFTER DELETE ON knowledge_cards BEGIN
  DELETE FROM knowledge_cards_fts WHERE rowid = OLD.id;
END;
CREATE TRIGGER citations_fts_ai AFTER INSERT ON card_citations BEGIN
  DELETE FROM knowledge_cards_fts WHERE rowid = NEW.card_id;
  INSERT INTO knowledge_cards_fts(rowid, subject, claim, conditions, terms, aliases, entities, quotes)
  SELECT k.id, k.subject, k.claim,
    COALESCE((SELECT group_concat(value, ' ; ') FROM json_each(k.conditions_json)), ''),
    COALESCE((SELECT group_concat(value, ' ')   FROM json_each(k.terms_json)), ''),
    COALESCE((SELECT group_concat(value, ' ; ') FROM json_each(k.aliases_json)), ''),
    COALESCE((SELECT group_concat(value, ' ')   FROM json_each(k.entities_json)), ''),
    COALESCE((SELECT group_concat(quote, ' ; ') FROM card_citations WHERE card_id = k.id), '')
  FROM knowledge_cards k WHERE k.id = NEW.card_id;
END;
CREATE TRIGGER citations_fts_au AFTER UPDATE OF card_id, quote ON card_citations BEGIN
  DELETE FROM knowledge_cards_fts WHERE rowid IN (OLD.card_id, NEW.card_id);
  INSERT INTO knowledge_cards_fts(rowid, subject, claim, conditions, terms, aliases, entities, quotes)
  SELECT k.id, k.subject, k.claim,
    COALESCE((SELECT group_concat(value, ' ; ') FROM json_each(k.conditions_json)), ''),
    COALESCE((SELECT group_concat(value, ' ')   FROM json_each(k.terms_json)), ''),
    COALESCE((SELECT group_concat(value, ' ; ') FROM json_each(k.aliases_json)), ''),
    COALESCE((SELECT group_concat(value, ' ')   FROM json_each(k.entities_json)), ''),
    COALESCE((SELECT group_concat(quote, ' ; ') FROM card_citations WHERE card_id = k.id), '')
  FROM knowledge_cards k WHERE k.id = OLD.card_id;
  INSERT INTO knowledge_cards_fts(rowid, subject, claim, conditions, terms, aliases, entities, quotes)
  SELECT k.id, k.subject, k.claim,
    COALESCE((SELECT group_concat(value, ' ; ') FROM json_each(k.conditions_json)), ''),
    COALESCE((SELECT group_concat(value, ' ')   FROM json_each(k.terms_json)), ''),
    COALESCE((SELECT group_concat(value, ' ; ') FROM json_each(k.aliases_json)), ''),
    COALESCE((SELECT group_concat(value, ' ')   FROM json_each(k.entities_json)), ''),
    COALESCE((SELECT group_concat(quote, ' ; ') FROM card_citations WHERE card_id = k.id), '')
  FROM knowledge_cards k WHERE k.id = NEW.card_id;
END;

-- 2.6 Person skills
CREATE TABLE person_skills (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id            TEXT NOT NULL REFERENCES persons(id),
    skill_name           TEXT NOT NULL,
    category             TEXT NOT NULL CHECK (category IN ('overview','setup_and_screening','entry_and_execution',
                             'trade_management','risk_and_sizing','psychology_and_review','checklists')),
    title                TEXT NOT NULL,
    summary              TEXT,
    content_markdown     TEXT NOT NULL,
    rules_json           TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(rules_json)),
    source_card_ids_json TEXT NOT NULL CHECK (json_valid(source_card_ids_json)),
    produced_by          TEXT NOT NULL,
    run_id               INTEGER REFERENCES agent_runs(id),
    updated_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE (person_id, skill_name, category)
);
CREATE VIRTUAL TABLE person_skills_fts USING fts5(skill_name, category, title, summary, content_markdown,
    content = 'person_skills', content_rowid = 'id',
    tokenize = "porter unicode61 remove_diacritics 2 tokenchars '_'");
CREATE TRIGGER person_skills_ai AFTER INSERT ON person_skills BEGIN
  INSERT INTO person_skills_fts(rowid, skill_name, category, title, summary, content_markdown)
  VALUES (NEW.id, NEW.skill_name, NEW.category, NEW.title, NEW.summary, NEW.content_markdown);
END;
CREATE TRIGGER person_skills_ad AFTER DELETE ON person_skills BEGIN
  INSERT INTO person_skills_fts(person_skills_fts, rowid, skill_name, category, title, summary, content_markdown)
  VALUES ('delete', OLD.id, OLD.skill_name, OLD.category, OLD.title, OLD.summary, OLD.content_markdown);
END;
CREATE TRIGGER person_skills_au AFTER UPDATE ON person_skills BEGIN
  INSERT INTO person_skills_fts(person_skills_fts, rowid, skill_name, category, title, summary, content_markdown)
  VALUES ('delete', OLD.id, OLD.skill_name, OLD.category, OLD.title, OLD.summary, OLD.content_markdown);
  INSERT INTO person_skills_fts(rowid, skill_name, category, title, summary, content_markdown)
  VALUES (NEW.id, NEW.skill_name, NEW.category, NEW.title, NEW.summary, NEW.content_markdown);
END;

-- 2.7 Exploration, sessions, budgets, learning
CREATE TABLE explore_queue (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    target          TEXT NOT NULL,
    target_kind     TEXT NOT NULL CHECK (target_kind IN ('url','handle','source','content','query','person','book','paper')),
    platform        TEXT NOT NULL DEFAULT '',
    action          TEXT NOT NULL DEFAULT 'fetch' CHECK (action IN ('fetch','list','profile','search','crawl_source')),
    origin          TEXT NOT NULL CHECK (origin IN ('user','mention','gap','history','citation','person_crosslink',
                                                    'search_result','source_refresh','retry')),
    origin_ref      TEXT,
    reason          TEXT,
    priority        REAL NOT NULL DEFAULT 0.5 CHECK (priority BETWEEN 0 AND 1),
    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','in_progress','done','failed','deferred','skipped')),
    attempts        INTEGER NOT NULL DEFAULT 0,
    not_before      TEXT,
    last_error      TEXT,
    run_id          INTEGER REFERENCES agent_runs(id),
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE (target, platform, action)
);

CREATE TABLE knowledge_gaps (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    query                TEXT NOT NULL,
    query_card_json      TEXT CHECK (query_card_json IS NULL OR json_valid(query_card_json)),
    verdict              TEXT NOT NULL CHECK (verdict IN ('no_answer','weak_answer','conflicting')),
    status               TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','exploring','filled','wont_fill')),
    filled_by_cards_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(filled_by_cards_json)),
    asked_count          INTEGER NOT NULL DEFAULT 1,
    run_id               INTEGER REFERENCES agent_runs(id),
    created_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE history_entries (
    url           TEXT PRIMARY KEY,
    title         TEXT,
    visit_count   INTEGER,
    last_visit_at TEXT,
    bundle_id     TEXT,
    triage        TEXT NOT NULL DEFAULT 'pending' CHECK (triage IN ('pending','queued','not_relevant'))
);

CREATE TABLE browser_sessions (
    domain          TEXT PRIMARY KEY,
    platform        TEXT,
    cookie_count    INTEGER NOT NULL,
    earliest_expiry TEXT,
    has_local_storage INTEGER NOT NULL DEFAULT 0,
    bundle_id       TEXT NOT NULL,
    imported_at     TEXT NOT NULL,
    verified_at     TEXT,
    login_state     TEXT NOT NULL DEFAULT 'unknown' CHECK (login_state IN ('logged_in','logged_out','checkpoint','unknown'))
);

CREATE TABLE budget_usage (
    platform     TEXT NOT NULL,
    window_kind  TEXT NOT NULL CHECK (window_kind IN ('minute','hour','day')),
    window_start TEXT NOT NULL,
    count        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (platform, window_kind, window_start)
);

CREATE TABLE lessons (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER REFERENCES agent_runs(id),
    skill       TEXT NOT NULL,
    kind        TEXT NOT NULL CHECK (kind IN ('data_fix','vocabulary','few_shot','instruction','script_bug','platform_change','other')),
    observation TEXT NOT NULL,
    evidence    TEXT,
    proposal    TEXT,
    status      TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','applied','proposed','rejected','duplicate')),
    ref         TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type TEXT NOT NULL CHECK (target_type IN ('card','answer','person_match','dedup','person_skill','gap')),
    target_id   TEXT NOT NULL,
    rating      INTEGER NOT NULL CHECK (rating IN (-1,0,1)),
    comment     TEXT,
    status      TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','handled')),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- 2.8 Views
CREATE VIEW card_stats AS
SELECT k.id AS card_id,
       COUNT(c.id)                         AS citations,
       COUNT(DISTINCT c.person_id)         AS persons,
       COUNT(DISTINCT c.content_id)        AS contents,
       (SELECT COUNT(*) FROM card_links l
         WHERE l.relation = 'contradicts' AND (l.from_card = k.id OR l.to_card = k.id)) AS contradictions
FROM knowledge_cards k LEFT JOIN card_citations c ON c.card_id = k.id
GROUP BY k.id;

CREATE VIEW person_stats AS
SELECT p.id AS person_id,
       (SELECT COUNT(DISTINCT card_id) FROM card_citations WHERE person_id = p.id) AS cards,
       (SELECT COUNT(*) FROM person_appearances WHERE person_id = p.id AND match_status = 'confirmed') AS appearances,
       (SELECT COUNT(*) FROM sources WHERE person_id = p.id) AS sources
FROM persons p WHERE p.status = 'active';
