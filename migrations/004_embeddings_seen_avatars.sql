-- 004: semantic search (embeddings + translations), visited-item tracking, person images.
-- ADR-009 (embeddings in SQLite): vectors live in this SQLite file as float32 BLOBs, scored by brute force (specs/10-semantic-search.md).

-- One row per (kind, ref, model). `ref` is the card id, "content_id#seq" for a segment, or the person id.
-- `text_hash` is the sha1 of the English text that was embedded, so unchanged rows are never re-embedded.
CREATE TABLE embeddings (
    kind       TEXT NOT NULL CHECK (kind IN ('card','segment','person','skill')),
    ref        TEXT NOT NULL,
    model      TEXT NOT NULL,
    dim        INTEGER NOT NULL,
    text_hash  TEXT NOT NULL,
    vector     BLOB NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    PRIMARY KEY (kind, ref, model)
);
CREATE INDEX idx_embeddings_model ON embeddings(model, kind);

-- English text of a segment that is not written in English (written by the agent with the `translator` skill).
CREATE TABLE segment_translations (
    content_id TEXT NOT NULL REFERENCES contents(id),
    seq        INTEGER NOT NULL,
    source_lang TEXT,
    text_en    TEXT NOT NULL,
    run_id     INTEGER REFERENCES agent_runs(id),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    PRIMARY KEY (content_id, seq)
);

-- Every item key an explorer has looked at, whether or not it was fetched (specs/11-explore-visited-open-topics.md).
-- `key` is the canonical item id (youtube:abc, reddit:1xg9, web:<hash>, ...).
CREATE TABLE seen_items (
    key         TEXT PRIMARY KEY,
    platform    TEXT NOT NULL,
    kind        TEXT,
    url         TEXT,
    title       TEXT,
    source_id   TEXT,
    status      TEXT NOT NULL DEFAULT 'seen' CHECK (status IN ('seen','queued','fetched','skipped','failed')),
    note        TEXT,
    times_seen  INTEGER NOT NULL DEFAULT 1,
    first_seen  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    last_seen   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    run_id      INTEGER REFERENCES agent_runs(id)
);
CREATE INDEX idx_seen_platform ON seen_items(platform, status);
CREATE INDEX idx_seen_source ON seen_items(source_id);

-- Pictures of a person (avatar, banner, ...) stored as files under data/media/persons/.
CREATE TABLE person_images (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id   TEXT NOT NULL REFERENCES persons(id),
    kind        TEXT NOT NULL DEFAULT 'avatar' CHECK (kind IN ('avatar','banner','photo','logo')),
    platform    TEXT,
    source_url  TEXT NOT NULL,
    path        TEXT NOT NULL,
    sha256      TEXT NOT NULL,
    mime        TEXT,
    width       INTEGER,
    height      INTEGER,
    bytes       INTEGER,
    fetched_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    run_id      INTEGER REFERENCES agent_runs(id),
    UNIQUE (person_id, sha256)
);
CREATE INDEX idx_person_images_person ON person_images(person_id, kind);

ALTER TABLE persons ADD COLUMN avatar_path TEXT;
ALTER TABLE persons ADD COLUMN avatar_sha256 TEXT;
ALTER TABLE persons ADD COLUMN avatar_mime TEXT;
ALTER TABLE persons ADD COLUMN avatar_fetched_at TEXT;
