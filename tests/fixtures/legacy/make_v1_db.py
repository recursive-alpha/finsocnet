"""Build a v1 fixture database (the DDL of the current production DB + the sample rows of specs/01-database.md §5.2).

Usage in tests: `make_v1_db(path)`. Transcript files are expected under `<root>/data/transcripts/` (see conftest).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

V1_DDL = """
CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE users (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, handle TEXT, platform TEXT NOT NULL DEFAULT 'youtube',
    profile_url TEXT, topics TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE contents (
    id TEXT PRIMARY KEY, user_id TEXT NOT NULL, platform TEXT NOT NULL DEFAULT 'youtube', title TEXT NOT NULL,
    url TEXT NOT NULL, content_type TEXT DEFAULT 'video', duration INTEGER DEFAULT 0, published_date TEXT,
    view_count INTEGER DEFAULT 0, description TEXT, transcript_path TEXT, raw_text TEXT, summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE hypotheses (
    id INTEGER PRIMARY KEY AUTOINCREMENT, content_id TEXT NOT NULL, user_id TEXT NOT NULL, title TEXT NOT NULL,
    category TEXT NOT NULL, direction TEXT NOT NULL, instrument TEXT DEFAULT 'equities',
    hypothesis_statement TEXT NOT NULL, setup_conditions TEXT, holding_period TEXT, statistical_claim TEXT,
    invalidation_risk TEXT, timestamp_start REAL DEFAULT 0.0, timestamp_end REAL DEFAULT 0.0, timestamp_formatted TEXT,
    verbatim_quote TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, person_id TEXT,
    FOREIGN KEY(content_id) REFERENCES contents(id) ON DELETE CASCADE,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT, skill_name TEXT UNIQUE NOT NULL, user_id TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'youtube', skill_dir TEXT NOT NULL, description TEXT, hypotheses_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, skill_type TEXT DEFAULT 'improved', version TEXT DEFAULT '1.0.0',
    author TEXT DEFAULT 'finsocnet', person_id TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE persons (
    id TEXT PRIMARY KEY, canonical_name TEXT NOT NULL, moniker TEXT, bio TEXT, avatar_url TEXT, trading_style TEXT,
    verified_records TEXT, primary_markets TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE person_appearances (
    id INTEGER PRIMARY KEY AUTOINCREMENT, person_id TEXT NOT NULL, platform TEXT NOT NULL, platform_id TEXT,
    handle_or_name TEXT, role TEXT, content_id TEXT, content_title TEXT, notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(person_id) REFERENCES persons(id));
CREATE TABLE person_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT, person_id TEXT NOT NULL REFERENCES persons(id), skill_name TEXT NOT NULL,
    category TEXT NOT NULL, title TEXT NOT NULL, summary TEXT, content_markdown TEXT NOT NULL, rules_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(person_id, category, skill_name));
CREATE TABLE market_ideas (
    id INTEGER PRIMARY KEY AUTOINCREMENT, person_id TEXT REFERENCES persons(id), content_id TEXT,
    domain TEXT NOT NULL DEFAULT 'trading_strategy', category TEXT NOT NULL DEFAULT 'market_dynamics',
    direction TEXT DEFAULT 'BOTH', instrument TEXT DEFAULT 'equities', title TEXT NOT NULL, idea_statement TEXT NOT NULL,
    setup_conditions TEXT, holding_period TEXT, statistical_claim TEXT, invalidation_risk TEXT, verbatim_quote TEXT NOT NULL,
    alternative_resources TEXT DEFAULT '[]', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE vector_embeddings (
    id TEXT PRIMARY KEY, collection TEXT NOT NULL, entity_id TEXT NOT NULL, person_id TEXT, document TEXT NOT NULL,
    metadata_json TEXT NOT NULL, embedding BLOB NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE VIRTUAL TABLE market_ideas_fts USING fts5(title, idea_statement, setup_conditions, verbatim_quote,
    content='market_ideas', content_rowid='id');
CREATE VIRTUAL TABLE person_skills_fts USING fts5(skill_name, category, title, summary, content_markdown,
    content='person_skills', content_rowid='id');
CREATE INDEX idx_contents_user ON contents(user_id);
CREATE INDEX idx_contents_platform ON contents(platform);
CREATE INDEX idx_hypotheses_content ON hypotheses(content_id);
"""

CHANNEL = "UC" + "a" * 22

USERS = [
    (CHANNEL, "Example Swing Trader", "@ExampleSwing", "youtube", "https://youtube.com/channel/" + CHANNEL),
    ("UC_lewis_kelly_8", "Lewis Kelly", "@Lewiskelly8", "youtube", "https://youtube.com/@Lewiskelly8"),
    ("x_qullamaggie", "Qullamaggie", "@Qullamaggie", "x", "https://x.com/Qullamaggie"),
    ("x_x_trader", "Unrelated Zhihu Page", "@x_trader", "x", "https://x.com/x_trader"),
    ("reddit_HSeldon2020", "HSeldon2020", "u/HSeldon2020", "reddit", "https://reddit.com/user/HSeldon2020"),
    ("medium_ztraderdorian", "Dorian", "@ztraderdorian", "medium", "https://medium.com/@ztraderdorian"),
    ("annas_archive", "Anna's Archive", None, "annas_archive", None),
    ("arxiv_org", "arXiv", None, "arxiv", None),
    ("system", "System", None, "system", None),
]

LONG_RAW = (
    "First paragraph about data cleaning in trading and why it matters a lot for every backtest you will ever run.\n\n"
    "short\n\n"
    "Second paragraph explains survivorship bias and how delisted stocks silently inflate the results of naive tests.\n\n"
    "Third paragraph: look-ahead bias happens when the model sees information that was not available at the time of the trade."
)

CONTENTS = [
    # id, user_id, platform, title, url, type, duration, published, views, description, transcript_path, raw_text
    ("abc123def45", CHANNEL, "youtube", "Selling into strength", "https://youtu.be/abc123def45", "video", 600, "20260902", 1200, "desc", "data/transcripts/abc123def45.json", None),
    ("zzz999yyy88", CHANNEL, "youtube", "Risk first", "https://youtu.be/zzz999yyy88", "video", 400, "20260903", 300, None, "data/transcripts/zzz999yyy88.json", None),
    ("catalog0001", CHANNEL, "youtube", "Catalog only video", "https://youtu.be/catalog0001", "video", 100, "20260101", 5, None, None, None),
    ("catalog0002", "UC_lewis_kelly_8", "youtube", "Another catalog entry", "https://youtu.be/catalog0002", "short", 30, None, 0, None, None, None),
    ("reddit_1xg9xq1", "reddit_HSeldon2020", "reddit", "How I size positions", "https://reddit.com/r/x/comments/1xg9xq1", "thread", 0, "2026-09-14", 412, None, None, LONG_RAW),
    ("x_1851234567890123456", "x_qullamaggie", "x", "A short post", "https://x.com/Qullamaggie/status/1851234567890123456", "post", 0, None, 0, None, None, "tiny stub text"),
    ("medium_data-cleaning-00f164ca71a0", "medium_ztraderdorian", "medium", "What is data cleaning", "https://medium.com/@z/data-cleaning-00f164ca71a0", "article", 0, None, 0, None, None, LONG_RAW),
    ("arxiv_2610_34467", "arxiv_org", "arxiv", "A paper", "https://arxiv.org/abs/2610.34467", "paper", 0, None, 0, "Abstract", None, LONG_RAW),
    ("aa_87377793416593215", "annas_archive", "annas_archive", "A book", "https://annas-archive.gl/md5/x", "book", 0, None, 0, "Description", None, "Book description that is quite short"),
]

PERSONS = [
    ("kristjan-qullamaggie", "Kristjan Kullamägi", "Qullamaggie", "Swing trader"),
    ("example-swing-trader", "Example Swing Trader", "ExampleSwing", "Fictional trader"),
    ("lewis-kelly", "Lewis Kelly", None, "SMC trader"),
]

APPEARANCES = [
    ("kristjan-qullamaggie", "x", "x_qullamaggie", "@Qullamaggie", "owner", None, None, None),
    ("kristjan-qullamaggie", "youtube", CHANNEL, "@Qullamaggie", "owner", "abc123def45", "Selling into strength", "owner of channel"),
    ("example-swing-trader", "youtube", CHANNEL, "@ExampleSwing", "owner", "zzz999yyy88", "Risk first", None),
    ("lewis-kelly", "youtube", "UC_lewis_kelly_8", "@Lewiskelly8", "guest", None, None, None),
    ("lewis-kelly", "annas_archive", "annas_archive", "Lewis Kelly", "archive", None, None, None),
]


def make_v1_db(path: str | Path, with_migrations_001_002: bool = True) -> Path:
    path = Path(path)
    conn = sqlite3.connect(path)
    conn.executescript(V1_DDL)
    if with_migrations_001_002:
        conn.executemany("INSERT INTO schema_migrations (version, name) VALUES (?, ?)", [(1, "initial_schema"), (2, "add_skill_classification")])
    conn.executemany("INSERT INTO users (id, name, handle, platform, profile_url) VALUES (?, ?, ?, ?, ?)", USERS)
    conn.executemany(
        """INSERT INTO contents (id, user_id, platform, title, url, content_type, duration, published_date, view_count,
                                 description, transcript_path, raw_text) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        CONTENTS,
    )
    conn.executemany("INSERT INTO persons (id, canonical_name, moniker, bio) VALUES (?, ?, ?, ?)", PERSONS)
    conn.executemany(
        """INSERT INTO person_appearances (person_id, platform, platform_id, handle_or_name, role, content_id, content_title, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        APPEARANCES,
    )
    conn.execute(
        """INSERT INTO hypotheses (content_id, user_id, title, category, direction, hypothesis_statement, verbatim_quote, person_id)
           VALUES ('abc123def45', ?, 'Trail with the 10-day', 'execution', 'LONG', 'Trail the rest with the 10-day', 'trail with the 10-day', 'example-swing-trader')""",
        (CHANNEL,),
    )
    conn.commit()
    conn.close()
    return path
