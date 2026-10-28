# 01 — Database (`data/knowledge.db`)

SQLite only (ADR-001). This document is the normative schema. Migration `003_v2_schema` creates it from the current v1 database.

---

## 1. Connection Rules

`finsocnet.core.db.connect()` must, on every connection:

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 10000;
PRAGMA synchronous = NORMAL;
```

- `row_factory = sqlite3.Row`.
- `transaction(conn)` context manager uses `BEGIN IMMEDIATE` so concurrent writers wait instead of failing mid-transaction.
- JSON columns are TEXT holding valid JSON (`json_valid()` CHECK constraints below). Read with `json.loads`, write with `json.dumps(ensure_ascii=False, separators=(",", ":"))`.
- SQLite ≥ 3.38 is required (JSON functions built in, FTS5 enabled). `kb doctor` checks this.

---

## 2. Schema (normative DDL)

The DDL below is stored as `migrations/003_v2_schema.sql` and executed by `migrations/003_v2_schema.py` (§5).

### 2.1 Runs (written first; everything references them)

```sql
CREATE TABLE agent_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    skill         TEXT NOT NULL,
    goal          TEXT,
    harness       TEXT,                    -- 'claude-code','codex','hermes','pi','omp','openclaw','manual'
    model         TEXT,                    -- 'claude-opus-5-5'
    parent_run_id INTEGER REFERENCES agent_runs(id),
    started_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    finished_at   TEXT,
    outcome       TEXT CHECK (outcome IN ('success','partial','failed','aborted')),
    stats_json    TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(stats_json)),
    errors_json   TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(errors_json))
);
```

`produced_by` everywhere below is derived as `<harness>/<model>` from the run.

### 2.2 Sources, contents, segments

```sql
CREATE TABLE sources (
    id               TEXT PRIMARY KEY,                 -- '<platform>:<kind>:<native>'
    platform         TEXT NOT NULL,
    kind             TEXT NOT NULL,                    -- channel, handle, user, subreddit, group, page, publication, feed,
                                                       -- server, channel_chat, site, forum, repo, query, playlist
    url              TEXT,
    title            TEXT,
    person_id        TEXT REFERENCES persons(id),      -- owner when the source belongs to one person
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
    id                 TEXT PRIMARY KEY,               -- '<platform>:<native_id>'
    source_id          TEXT REFERENCES sources(id),
    platform           TEXT NOT NULL,
    content_type       TEXT NOT NULL,                  -- video, short, stream, episode, post, thread, chat_window, article,
                                                       -- paper, book, filing, page, question, repo, file, idea, script
    url                TEXT,
    title              TEXT,
    description        TEXT,
    author_handle      TEXT,
    author_platform_user_id TEXT,
    person_id          TEXT REFERENCES persons(id),    -- main author/owner once matched
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
    processed_upto_seq INTEGER NOT NULL DEFAULT -1,    -- last segment seq the miner finished
    cards_count        INTEGER NOT NULL DEFAULT 0,
    processed_with     TEXT,                           -- transformer version, e.g. 'kt-1.0'
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
    kind           TEXT NOT NULL,                      -- transcript, post, comment, reply, message, paragraph, page, code,
                                                       -- caption, question, answer
    locator_json   TEXT NOT NULL CHECK (json_valid(locator_json)),
    author_handle  TEXT,
    person_id      TEXT REFERENCES persons(id),        -- set by attribution
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
```

### 2.3 Persons

```sql
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
    alias_key  TEXT NOT NULL,       -- normalized: casefold, strip leading '@' / 'u/', remove diacritics, collapse spaces
    alias      TEXT NOT NULL,       -- display form
    platform   TEXT NOT NULL DEFAULT '',   -- '' = any platform
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

-- Standalone FTS (aggregates aliases), maintained by triggers.
CREATE VIRTUAL TABLE persons_fts USING fts5(person_id UNINDEXED, names, bio,
    tokenize = "unicode61 remove_diacritics 2");
-- Triggers: persons AFTER INSERT/UPDATE/DELETE and person_aliases AFTER INSERT/DELETE
-- delete the row WHERE person_id = X and re-insert:
--   names = canonical_name || ' ' || COALESCE(moniker,'') || ' ' || (SELECT group_concat(alias,' ') FROM person_aliases WHERE person_id = X)
--   bio   = COALESCE(bio,'')
```

### 2.4 Vocabulary

```sql
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
-- Triggers on vocabulary AFTER INSERT/UPDATE/DELETE keep vocabulary_fts in sync (rowid = vocabulary.rowid;
-- aliases = group_concat over json_each(aliases_json) separated by ' ; ').
```

### 2.5 Knowledge cards

```sql
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
    entities_json        TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(entities_json)),   -- '$NVDA', 'SPY', 'FOMC'
    numbers_json         TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(numbers_json)),
    evidence_level       TEXT NOT NULL CHECK (evidence_level IN ('anecdotal','claimed','backtested','audited')),
    invalidation         TEXT,
    notes                TEXT,
    status               TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','merged','retired')),
    merged_into          INTEGER REFERENCES knowledge_cards(id),
    transformer_version  TEXT NOT NULL,                 -- 'kt-1.0'
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
    segment_seq            INTEGER,                    -- NULL only for legacy citations (quote_verified = 0)
    locator_json           TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(locator_json)),   -- copied from the segment
    person_id              TEXT REFERENCES persons(id),
    author_handle          TEXT,                       -- when no person yet (e.g. anonymous commenter)
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

CREATE TABLE card_history (            -- snapshot BEFORE every update/merge/retire; enables undo
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id       INTEGER NOT NULL REFERENCES knowledge_cards(id),
    snapshot_json TEXT NOT NULL CHECK (json_valid(snapshot_json)),
    reason        TEXT NOT NULL,
    run_id        INTEGER REFERENCES agent_runs(id),
    at            TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE dedup_decisions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint        TEXT NOT NULL UNIQUE,       -- sha1(quote_key(claim) | content_id | segment_seq): makes commits idempotent
    new_card_json      TEXT NOT NULL CHECK (json_valid(new_card_json)),
    candidate_ids_json TEXT NOT NULL CHECK (json_valid(candidate_ids_json)),
    decision           TEXT NOT NULL CHECK (decision IN ('same','refines','related','contradicts','new')),
    target_card        INTEGER REFERENCES knowledge_cards(id),   -- existing card for same/refines
    result_card        INTEGER NOT NULL REFERENCES knowledge_cards(id),  -- card that now holds the citation
    rationale          TEXT NOT NULL,
    produced_by        TEXT NOT NULL,
    run_id             INTEGER REFERENCES agent_runs(id),
    reviewed           TEXT CHECK (reviewed IN ('agreed','overturned')),
    review_note        TEXT,
    created_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

-- Standalone FTS: columns are derived from JSON and from citations, so it is NOT an external-content table.
CREATE VIRTUAL TABLE knowledge_cards_fts USING fts5(
    subject, claim, conditions, terms, aliases, entities, quotes,
    tokenize = "porter unicode61 remove_diacritics 2 tokenchars '_'"
);
```

**FTS triggers for cards (must be implemented exactly; tests in `tests/integration/test_card_fts.py`).**

```sql
-- Helper expression used by every trigger, written out in full each time (SQLite has no procedures):
-- INSERT INTO knowledge_cards_fts(rowid, subject, claim, conditions, terms, aliases, entities, quotes)
-- SELECT k.id, k.subject, k.claim,
--   COALESCE((SELECT group_concat(value, ' ; ') FROM json_each(k.conditions_json)), ''),
--   COALESCE((SELECT group_concat(value, ' ')   FROM json_each(k.terms_json)), ''),
--   COALESCE((SELECT group_concat(value, ' ; ') FROM json_each(k.aliases_json)), ''),
--   COALESCE((SELECT group_concat(value, ' ')   FROM json_each(k.entities_json)), ''),
--   COALESCE((SELECT group_concat(quote, ' ; ') FROM card_citations WHERE card_id = k.id), '')
-- FROM knowledge_cards k WHERE k.id = <ID>;

CREATE TRIGGER cards_fts_ai AFTER INSERT ON knowledge_cards BEGIN
  <helper with ID = NEW.id>;
END;
CREATE TRIGGER cards_fts_au AFTER UPDATE ON knowledge_cards BEGIN
  DELETE FROM knowledge_cards_fts WHERE rowid = OLD.id;
  <helper with ID = NEW.id>;
END;
CREATE TRIGGER cards_fts_ad AFTER DELETE ON knowledge_cards BEGIN
  DELETE FROM knowledge_cards_fts WHERE rowid = OLD.id;
END;
CREATE TRIGGER citations_fts_ai AFTER INSERT ON card_citations BEGIN
  DELETE FROM knowledge_cards_fts WHERE rowid = NEW.card_id;
  <helper with ID = NEW.card_id>;
END;
CREATE TRIGGER citations_fts_au AFTER UPDATE OF card_id, quote ON card_citations BEGIN
  DELETE FROM knowledge_cards_fts WHERE rowid IN (OLD.card_id, NEW.card_id);
  <helper with ID = OLD.card_id>;
  <helper with ID = NEW.card_id>;
END;
```

Why `tokenchars '_'`: vocabulary keys such as `ema_10` must stay one token. Without it, FTS splits `ema_10` into `ema` and `10` and term matching becomes noisy.
Why `remove_diacritics 2`: Vietnamese and other accented text must match with or without accents.

### 2.6 Person skills

```sql
CREATE TABLE person_skills (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id            TEXT NOT NULL REFERENCES persons(id),
    skill_name           TEXT NOT NULL,             -- '<person-id>-core' or a named methodology, e.g. 'minervini-vcp'
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
-- Standard external-content triggers (ai / ad / au) as for segments_fts.
```

### 2.7 Exploration, sessions, budgets, learning

```sql
CREATE TABLE explore_queue (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    target          TEXT NOT NULL,              -- URL, handle, content id, query text, person id
    target_kind     TEXT NOT NULL CHECK (target_kind IN ('url','handle','source','content','query','person','book','paper')),
    platform        TEXT NOT NULL DEFAULT '',   -- '' = unknown; the agent decides
    action          TEXT NOT NULL DEFAULT 'fetch' CHECK (action IN ('fetch','list','profile','search','crawl_source')),
    origin          TEXT NOT NULL CHECK (origin IN ('user','mention','gap','history','citation','person_crosslink',
                                                    'search_result','source_refresh','retry')),
    origin_ref      TEXT,
    reason          TEXT,
    priority        REAL NOT NULL DEFAULT 0.5 CHECK (priority BETWEEN 0 AND 1),
    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','in_progress','done','failed','deferred','skipped')),
    attempts        INTEGER NOT NULL DEFAULT 0,
    not_before      TEXT,                       -- set on RATE_LIMITED / LOGIN_REQUIRED
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

CREATE TABLE browser_sessions (         -- METADATA ONLY. Never cookie values.
    domain          TEXT PRIMARY KEY,   -- registrable domain, e.g. 'x.com'
    platform        TEXT,               -- from config/platforms.yaml, NULL for unknown domains
    cookie_count    INTEGER NOT NULL,
    earliest_expiry TEXT,               -- NULL = session cookies only
    has_local_storage INTEGER NOT NULL DEFAULT 0,
    bundle_id       TEXT NOT NULL,
    imported_at     TEXT NOT NULL,
    verified_at     TEXT,
    login_state     TEXT NOT NULL DEFAULT 'unknown' CHECK (login_state IN ('logged_in','logged_out','checkpoint','unknown'))
);

CREATE TABLE budget_usage (
    platform     TEXT NOT NULL,
    window_kind  TEXT NOT NULL CHECK (window_kind IN ('minute','hour','day')),
    window_start TEXT NOT NULL,         -- UTC, truncated to the window
    count        INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (platform, window_kind, window_start)
);

CREATE TABLE lessons (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER REFERENCES agent_runs(id),
    skill       TEXT NOT NULL,
    kind        TEXT NOT NULL CHECK (kind IN ('data_fix','vocabulary','few_shot','instruction','script_bug','platform_change','other')),
    observation TEXT NOT NULL,
    evidence    TEXT,               -- ids, error text, example
    proposal    TEXT,
    status      TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','applied','proposed','rejected','duplicate')),
    ref         TEXT,               -- branch / commit / PR / card ids
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
```

### 2.8 Views

```sql
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
```

---

## 3. Write Semantics (implemented in `finsocnet.core`, exposed by `kb`)

### 3.1 `add_content(record, run_id)`

1. Validate against `content_record.schema.json`. Upsert `sources` row from `record.source` (insert if missing; update `title`/`url` if changed).
2. If `contents.id` does not exist: insert content + all segments. Compute `content_hash = hash_text(concat(segment texts))`.
   - If another content with the same hash exists and total text ≥ 500 chars: set `duplicate_of`, `process_status = 'skipped_duplicate'`. Return `status: "duplicate"`.
   - Else `process_status = 'new'` (or `'metadata_only'` when there are zero segments). Return `status: "created"`.
3. If it exists (re-fetch):
   - Update metadata columns and `metrics_json`, `fetched_at`.
   - Segments are **append-only**. Match incoming segments to stored ones by `locator_json` identity key (`comment_id`, `message_id`, `start_sec`, `page`, `para`). Matched: if text differs and no citation references that `seq`, update text; if cited, keep stored text and add warning. Unmatched: append with next `seq`.
   - If segments were appended and status was `processed`, set status back to `new` (miner resumes from `processed_upto_seq + 1`). Return `status: "updated"`, `segments_added: N`.
4. `metadata_only` contents (catalog entries without text) become `new` when a later fetch adds segments.

### 3.2 `commit_decision(decision, run_id)` — atomic per decision

Runs inside one `BEGIN IMMEDIATE` transaction (batch files: one SAVEPOINT per decision; a failed decision rolls back only itself).

1. Validate `decision.schema.json`; validate `new_card` with `validate_card` (schema, grammar, vocabulary, quote check against `content_segments(content_id, segment_seq)` and the next 2 segments).
2. Compute `fingerprint`. If it exists in `dedup_decisions` → return `status: "already_committed"` with the stored result (idempotent retry).
3. By `decision`:
   - `same`: target must be `active` (else `CONFLICT`). Insert citation (stance `supports`). Union `aliases` and `entities` from new card into target (snapshot to `card_history` first if changed).
   - `refines`: target must be `active`. Snapshot target to `card_history`. Apply `updates` (only fields allowed in 03 §3.4). Insert citation (stance `refines`).
   - `related` / `contradicts`: insert new card + citation; insert every entry of `links` (at least one link required whose relation equals the decision).
   - `new`: insert new card + citation; insert `links` if any.
   - For `same` / `refines`, any `links` in the decision are inserted with `from_card = target` (e.g. the new citation's card also contradicts another card).
4. Insert `dedup_decisions` row with `result_card`.
5. If the citation's `person_id` is set, ensure a `person_appearances` row (`role = speaker_role`) exists for (person, content).

### 3.3 Merges and retirements (self-improver, `kb card merge|retire`)

- `merge --from A --into B`: snapshot both; move A's citations to B (`UPDATE card_citations SET card_id = B` — skip rows that would violate the UNIQUE key and record them in the result); repoint `card_links` (drop self-links); `A.status = 'merged', A.merged_into = B`; union aliases/entities/terms into B.
- `retire --id A`: snapshot; `status = 'retired'`; citations stay (history).
- `undo --history-id H`: restore snapshot H (fields only; citations moved by merge are moved back using the snapshot's `citation_ids`).

---

## 4. Retention

- Never delete: `contents`, `content_segments`, `card_citations`, `dedup_decisions`, `card_history`, `agent_runs`.
- May prune: `data/audio/` files older than 30 days whose content is `processed`; `budget_usage` rows older than 7 days; `data/work/<run_id>/` older than 90 days (`kb prune --dry-run` first).

---

## 5. Migration `003_v2_schema` (from the current v1 database)

### 5.1 Runner changes (`finsocnet/core/migrations.py`)

- Discover `migrations/NNN_name.sql` **and** `migrations/NNN_name.py`. A `.py` migration defines `def up(conn: sqlite3.Connection) -> None`.
- Before applying any pending migration: `kb backup` to `data/backups/knowledge-<UTC>-pre-NNN.db` (SQLite backup API). Abort if the backup fails.
- Each migration runs in one transaction with `PRAGMA foreign_keys = OFF` during the migration and `PRAGMA foreign_key_check` before commit (fail on any violation).
- Record in `schema_migrations(version, name, applied_at)` (existing table).
- Note: in the current DB, `persons`, `person_appearances`, `market_ideas`, `person_skills`, `vector_embeddings` exist without a migration file. `003` must check existence with `sqlite_master` before touching each table.

### 5.2 Current v1 data (snapshot 2026-10-28)

| Table | Rows | Notes |
|---|---|---|
| `contents` | 5636 | youtube 5608 (≈5572 catalog-only, no text), x 11, arxiv 10, annas_archive 3, medium 2, reddit 2 |
| `users` | 22 | channel/profile registry; some bad rows (`x_x_trader` title is an unrelated Zhihu page; `UC_lewis_kelly_8` is not a real channel id) |
| `hypotheses` | 66 | legacy ideas with timestamps |
| `persons` | 9 | keep |
| `person_appearances` | 18 | keep, remap ids |
| `skills` | 22 | registry of the folders being removed |
| `market_ideas`, `person_skills`, `vector_embeddings` | 0 | drop |
| transcript files | `data/transcripts/<videoId>.json` = `{"metadata": {…}, "transcript": [{"start", "duration", "text"}]}` |

### 5.3 Steps of `003_v2_schema.py`

1. Abort with a clear error if `market_ideas`, `person_skills` or `vector_embeddings` has rows (they are expected to be empty).
2. Rename v1 tables: `contents → legacy_contents`, `users → legacy_users`, `hypotheses → legacy_hypotheses`, `skills → legacy_skills`, `persons → legacy_persons`, `person_appearances → legacy_person_appearances`. Drop `market_ideas`, `market_ideas_fts*`, `person_skills`, `person_skills_fts*`, `vector_embeddings`.
3. Execute `003_v2_schema.sql` (all DDL in §2).
4. Insert one `agent_runs` row: `skill='migration', harness='manual', goal='003_v2_schema'`; use its id as `run_id` below.
5. `legacy_persons → persons` (copy columns; `visibility='public'`).
6. `legacy_users → sources`:
   | legacy row | source id | kind |
   |---|---|---|
   | platform `youtube`, id matches `^UC[0-9A-Za-z_-]{22}$` | `youtube:channel:<id>` | channel |
   | platform `youtube`, other id | `youtube:handle:<handle without @, lowercase>`, `status='needs_review'` | handle |
   | id `x_<h>` | `x:user:<h>` | user |
   | id `reddit_<u>` | `reddit:user:<u lowercase>` | user |
   | id `medium_<u>` | `medium:user:<u>` | user |
   | `annas_archive`, `arxiv_org`, `system` | no source | — |
   | `x_x_trader` | `x:user:x_trader`, `status='needs_review'`, note "title looks unrelated" | user |
   Keep `title = name`, `url = profile_url`. Write a mapping table `legacy_id_map(kind, old_id, new_id)`.
7. `legacy_contents → contents`:
   | legacy id pattern | new id | content_type |
   |---|---|---|
   | youtube 11-char id | `youtube:<id>` | legacy `content_type` (default `video`) |
   | `reddit_<x>` | `reddit:<x>` | thread |
   | `x_<n>` | `x:<n>` | post |
   | `medium_<slug>` | `medium:<slug>` | article |
   | `arxiv_<a>_<b>` | `arxiv:<a>.<b>` | paper |
   | `aa_<n>` | `book:aa-<n>`, `process_status='needs_review'` (not an md5) | book |
   Map `user_id` via `legacy_id_map` to `source_id`; `published_date → published_at`; `duration → duration_sec`; `view_count → metrics_json.views`; keep `description`, `summary`.
   Segments:
   - if `transcript_path` file exists: load `transcript[]`, merge consecutive entries into windows of ≤ 45 s and ≤ 600 chars → segments `kind='transcript'`, `locator={start_sec,end_sec}` (rounded to 0.01).
   - else if `raw_text` is non-empty: split on blank lines into paragraphs (merge paragraphs < 80 chars with the next) → `kind='paragraph'`, `locator={para: i}`.
   - else: no segments, `process_status='metadata_only'`.
   - Rows with raw_text ≤ 150 chars (stubs) → `process_status='needs_review'`.
   `content_hash` computed as in §3.1. Write mapping rows into `legacy_id_map`.
8. `legacy_person_appearances → person_appearances`: map `content_id` (via `legacy_id_map`, NULL if unmapped) and `platform_id → source_id`; role `archive` stays `archive`; for every `handle_or_name`, insert `person_aliases(alias_key, alias, platform, person_id)` (ignore conflicts). Set `sources.person_id` for `role='owner'`.
9. Keep `legacy_hypotheses` and `legacy_skills` unchanged for Phase 2 (the agent converts hypotheses into cards; see `08-phases.md`). They are dropped by migration `005` after conversion.
10. `PRAGMA foreign_key_check`; commit. Print a summary (counts per mapping, rows flagged `needs_review`).

### 5.4 Migration acceptance tests

- A fixture DB built from the v1 DDL with the sample rows of §5.2 migrates without error.
- `contents` count = legacy count; every `youtube:` id has 11-char suffix; `metadata_only` count equals legacy rows without text.
- A content with `data/transcripts/<id>.json` has transcript segments whose concatenated text equals the legacy transcript text (after `clean_text`).
- `persons` = 9 rows; aliases contain `qullamaggie` for `kristjan-qullamaggie`.
- Running the migration twice is a no-op (runner skips applied versions).
- A pre-migration backup file exists.

---

## 6. `kb` CLI Reference

`uv run finsocnet kb <group> <command> …` (wrapper: `.agents/skills/knowledge-db/scripts/kb.py`). All output uses the envelope. `W` = write command, requires `--run`.

### 6.1 Admin
| Command | Data returned |
|---|---|
| `kb init` | creates DB, runs migrations → `{applied: [...]}` |
| `kb migrate [--dry-run]` | `{pending: [...], applied: [...]}` |
| `kb backup [--to PATH]` | `{path}` |
| `kb doctor` | `{sqlite_version, integrity, fts_integrity: {table: ok}, orphans: {...}, warnings}` |
| `kb stats` | counts per table and status, cards by category, top persons, open gaps, queue by status, sessions summary |
| `kb prune [--dry-run]` | files/rows to prune (§4) |

### 6.2 Runs, lessons, feedback
| Command | |
|---|---|
| `kb run start --skill S --goal G --harness H --model M [--parent RUN]` | `{run_id}` |
| `kb run end --run R --outcome O [--stats JSON] [--errors JSON]` | `{run_id}` |
| `kb run list [--skill] [--since] [--limit]` | runs |
| `kb lesson add --skill S --kind K --observation T [--evidence] [--proposal]` W | `{lesson_id}` |
| `kb lesson list [--status open] [--skill]` / `kb lesson update ID --status --ref` W | |
| `kb feedback add --target-type T --target-id ID --rating -1|0|1 [--comment]` | `{feedback_id}` |
| `kb feedback list [--status open]` / `kb feedback handle ID` W | |

### 6.3 Sources and contents
| Command | |
|---|---|
| `kb source upsert --file F` W / `kb source get ID` / `kb source list [--platform] [--person] [--status]` | |
| `kb source cursor ID --set CURSOR` W | |
| `kb content add --file F|-` W | `{id, status: created|updated|duplicate, segments_added, duplicate_of}` |
| `kb content get ID [--meta-only]` | content row + segment count |
| `kb content view ID [--from-seq A] [--to-seq B]` | `{text}` rendered for the agent (03 §1.2) |
| `kb content chunks ID [--max-chars 12000] [--overlap 2]` | `[{chunk, from_seq, to_seq, chars}]` starting at `processed_upto_seq + 1` |
| `kb content list [--status] [--platform] [--source] [--person] [--limit]` | |
| `kb content claim ID` W | sets `processing` (fails with `CONFLICT` if another run holds it < 2 h) |
| `kb content done ID --upto-seq N --cards N [--transformer kt-X.Y]` W | sets `processed` (or keeps `new` if more segments remain) |
| `kb content fail ID --error TEXT` W | sets `failed` |
| `kb content link-duplicate ID --of OTHER` W | |
| `kb content search "<text>" [--platform] [--person] [--content ID] [--limit 20]` | segment hits with `content_id, seq, locator, snippet` (segments_fts) |

### 6.4 Vocabulary
| Command | |
|---|---|
| `kb vocab lookup "<phrase>" [--limit 5]` | `[{term, label, facet, aliases, broader, match: exact_term|exact_alias|label|fts}]` |
| `kb vocab add --file F` W | array of `{term,label,facet,aliases,broader,definition}`; rejects existing terms and aliases already owned by another term |
| `kb vocab update TERM --file F` W / `kb vocab merge --from A --into B` W | merge rewrites `terms_json` of all cards (FTS triggers reindex) |
| `kb vocab list [--facet]` / `kb vocab export --out F` | |

### 6.5 Cards
| Command | |
|---|---|
| `kb card validate --file F` | `{valid: [i…], errors: [{index, details:[…]}]}` |
| `kb card candidates --file F [--index I] [--limit 10]` | `[{index, candidates: [{card, citations: [≤2], stats, score_debug}]}]` |
| `kb card commit --file F [--legacy]` W | `[{index, status: committed|already_committed|error, decision, result_card, error?}]`; `--legacy` (Phase 2 only) allows `segment_seq: null` with `quote_verified = 0` when the content has no segments |
| `kb card search --query-card F [--limit 30]` / `kb card search --text "<q>"` | ranked cards with stats and top citations |
| `kb card get ID [--citations] [--links] [--history]` | |
| `kb card list [--person] [--category] [--status] [--since] [--limit]` | |
| `kb card update ID --file PATCH --reason R` W | snapshot + patch (allowed fields: 03 §3.4 + `kind`,`category`,`domain`,`claim`,`subject`) |
| `kb card merge --from A --into B --reason R` W / `kb card retire ID --reason R` W / `kb card undo --history-id H` W | |
| `kb citation attribute ID --person P --role R --confidence C` W | fixes speaker attribution |

### 6.6 Persons and person skills
| Command | |
|---|---|
| `kb person candidates [--name] [--handle] [--platform] [--context TEXT]` | `[{person, score, reasons}]` (03 §5) |
| `kb person upsert --file F` W | person.schema.json |
| `kb person alias add --person P --alias A [--platform X]` W | |
| `kb person appearance add --file F` W | |
| `kb person get ID` / `kb person list [--needs-review]` / `kb person cards ID [--category]` | |
| `kb person merge --from A --into B` W | moves aliases, appearances, citations, sources, skills |
| `kb skill upsert --file F` W | person_skill.schema.json |
| `kb skill get PERSON [--skill-name] [--category] [--render markdown]` / `kb skill list` | |

### 6.7 Exploration
| Command | |
|---|---|
| `kb queue add --target T --target-kind K [--platform] [--action] --origin O [--origin-ref] [--reason] [--priority]` W (or `--file` array) | duplicates are ignored (UNIQUE) and returned as `existing` |
| `kb queue next [--limit 5] [--platform]` | marks returned items `in_progress`; skips `not_before` in future, platforms with exhausted budget, and platforms needing a session whose `login_state` ≠ `logged_in` |
| `kb queue update ID --status S [--error] [--retry-after SEC]` W / `kb queue list [--status]` | |
| `kb gap add --query Q [--query-card F] --verdict V` W | increments `asked_count` if the same normalized query is open |
| `kb gap list [--status open]` / `kb gap update ID --status S [--filled-by 1,2]` W | |
| `kb history pending [--limit 200]` / `kb history mark URL… --triage T` W | |
| `kb decision list [--since] [--reviewed none]` / `kb decision review ID --verdict agreed|overturned [--note]` W | |
