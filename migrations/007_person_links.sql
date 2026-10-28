-- 007: the places and facts of a person (specs/16): website, social accounts, newsletters, channels, papers, profiles, courses.
-- One row per URL per person; every row says how sure the match is and why.
CREATE TABLE person_links (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id     TEXT NOT NULL REFERENCES persons(id),
    url           TEXT NOT NULL,
    kind          TEXT NOT NULL CHECK (kind IN ('website','social','video','audio','newsletter','code','paper','scholar','wiki','course','book','store','other')),
    platform      TEXT NOT NULL DEFAULT '',
    handle        TEXT,
    label         TEXT,
    confidence    REAL NOT NULL DEFAULT 1.0 CHECK (confidence BETWEEN 0 AND 1),
    match_status  TEXT NOT NULL DEFAULT 'confirmed' CHECK (match_status IN ('confirmed','needs_review','rejected')),
    evidence      TEXT,
    source_id     TEXT REFERENCES sources(id),
    run_id        INTEGER REFERENCES agent_runs(id),
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE (person_id, url)
);
CREATE INDEX idx_person_links_person ON person_links(person_id);
CREATE INDEX idx_person_links_platform ON person_links(platform);
