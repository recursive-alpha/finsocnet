-- Migration 001: Initial Multi-Platform Schema

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    handle TEXT,
    platform TEXT NOT NULL DEFAULT 'youtube', -- youtube, x, reddit, medium, annas_archive, arxiv, podcast, web
    profile_url TEXT,
    topics TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contents (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'youtube',
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    content_type TEXT DEFAULT 'video', -- video, short, stream, post, thread, article, book, paper
    duration INTEGER DEFAULT 0,
    published_date TEXT,
    view_count INTEGER DEFAULT 0,
    description TEXT,
    transcript_path TEXT,
    raw_text TEXT,
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS hypotheses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL, -- holding_period, stock_selection, execution, risk_management, edge
    direction TEXT NOT NULL, -- LONG, SHORT, NEUTRAL, BOTH
    instrument TEXT DEFAULT 'equities',
    hypothesis_statement TEXT NOT NULL,
    setup_conditions TEXT,
    holding_period TEXT,
    statistical_claim TEXT,
    invalidation_risk TEXT,
    timestamp_start REAL DEFAULT 0.0,
    timestamp_end REAL DEFAULT 0.0,
    timestamp_formatted TEXT,
    verbatim_quote TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(content_id) REFERENCES contents(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_name TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'youtube',
    skill_dir TEXT NOT NULL,
    description TEXT,
    hypotheses_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_contents_user ON contents(user_id);
CREATE INDEX IF NOT EXISTS idx_contents_platform ON contents(platform);
CREATE INDEX IF NOT EXISTS idx_hypotheses_content ON hypotheses(content_id);
CREATE INDEX IF NOT EXISTS idx_hypotheses_user ON hypotheses(user_id);
CREATE INDEX IF NOT EXISTS idx_hypotheses_category ON hypotheses(category);
CREATE INDEX IF NOT EXISTS idx_hypotheses_direction ON hypotheses(direction);
