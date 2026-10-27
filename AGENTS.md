# Agent Operating Guide: Multi-Platform Intelligence & User Skill Synthesis

Welcome to **FinSocNet**. This repository provides an end-to-end framework for AI agents to discover creators across platforms (**YouTube, X/Twitter, Reddit, Medium, and the Web**), transcribe media (via API or local `openai/whisper-large-v3-turbo`), mine empirical trading hypotheses directly into a database and vector store (`knowledge.db` + Chroma), and synthesize production-ready **User Agent Skills** conforming to the [agentskills.io](https://agentskills.io) specification.

---

## 1. Skill Architecture (`.agents/skills/`)

All skills adhere strictly to the open [Agent Skills Specification](https://agentskills.io/specification.md) with YAML frontmatter, documentation, and executable scripts.

| Skill | Directory | Primary Role |
|---|---|---|
| **`youtube-extractor`** | `.agents/skills/youtube-extractor` | Fetch transcripts with timestamps, video metadata, and catalog uploads across all tabs (videos, shorts, streams) with Whisper fallback. |
| **`audio-transcriber`** | `.agents/skills/audio-transcriber` | Download audio tracks from YouTube or local media and transcribe with local `openai/whisper-large-v3-turbo` (int8 quantized). |
| **`x-explorer`** | `.agents/skills/x-explorer` | Explore X profiles, search live posts/cashtags, and extract tweet threads with browser session & password login. |
| **`reddit-explorer`** | `.agents/skills/reddit-explorer` | Discover and explore trading subreddits (`r/RealDayTrading`, `r/Daytrading`), search discussions, and read threads with comments. |
| **`medium-explorer`** | `.agents/skills/medium-explorer` | Explore Medium articles, quantitative finance publications, author profiles, and read full stories. |
| **`web-searcher`** | `.agents/skills/web-searcher` | Query DuckDuckGo without API keys for creators, profiles, and internet research with site-filtering. |
| **`web-reader`** | `.agents/skills/web-reader` | Render dynamic JS pages via Playwright, extract clean markdown/text, take screenshots, and inspect embedded videos and caption tracks. |
| **`annas-archive-explorer`** | `.agents/skills/annas-archive-explorer` | Search open books, research papers, and textbooks across Anna's Archive (https://annas-archive.gl) with mirror detection. |
| **`paper-code-explorer`** | `.agents/skills/paper-code-explorer` | Explore scientific papers and open-source code implementations across arXiv and Papers With Code (Hugging Face Papers). |
| **`knowledge-db`** | `.agents/skills/knowledge-db` | Manage SQLite database (`knowledge.db`) and Chroma vector store (`data/chroma_db`) with `sentence-transformers/all-MiniLM-L6-v2`. |
| **`hypothesis-miner`** | `.agents/skills/hypothesis-miner` | Extract structured trading hypotheses, setup filters, holding periods, win rates, and quotes directly into the database. |
| **`user-skill-synthesizer`** | `.agents/skills/user-skill-synthesizer` | Package mined user/creator rules across platforms (YouTube, X, Reddit, Medium, etc.) into standardized, reusable Agent Skills. |

---

## 2. Environment & Configuration

Environment variables are loaded from `.env` (configured via `.env.example`):

```bash
# Database & Vector Store Configuration
KNOWLEDGE_DB_PATH=data/knowledge.db
CHROMA_PERSIST_DIR=data/chroma_db
EMBEDDING_PROVIDER=hf
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Local Whisper Transcription Configuration
WHISPER_MODEL=openai/whisper-large-v3-turbo
WHISPER_DEVICE=auto
WHISPER_COMPUTE_TYPE=int8
AUDIO_DOWNLOAD_DIR=data/audio

# Social Network Browser Sessions & Credentials (Optional)
X_AUTH_TOKEN=
X_USERNAME=
X_PASSWORD=
X_SESSION_FILE=data/sessions/x_session.json

REDDIT_USERNAME=
REDDIT_PASSWORD=
REDDIT_SESSION_FILE=data/sessions/reddit_session.json

MEDIUM_SID=
MEDIUM_UID=
MEDIUM_SESSION_FILE=data/sessions/medium_session.json

# Web & Playwright Browser Configuration
HEADLESS_BROWSER=true
BROWSER_TIMEOUT_MS=30000
```

---

## 3. Browser Session & Credential Storage

For social networks (X, Reddit, Medium), authenticated sessions are stored directly as browser storage state in `data/sessions/`:
- **X (Twitter):** `data/sessions/x_session.json`
- **Reddit:** `data/sessions/reddit_session.json`
- **Medium:** `data/sessions/medium_session.json`

You can authenticate using cookies/tokens OR username and password:

```bash
# X (Twitter)
uv run .agents/skills/x-explorer/scripts/login_x.py --token "<AUTH_TOKEN>"
uv run .agents/skills/x-explorer/scripts/login_x.py --user "<USERNAME>" --password "<PASSWORD>"
uv run .agents/skills/x-explorer/scripts/login_x.py --interactive

# Reddit
uv run .agents/skills/reddit-explorer/scripts/login_reddit.py --user "<USERNAME>" --password "<PASSWORD>"
uv run .agents/skills/reddit-explorer/scripts/login_reddit.py --interactive

# Medium
uv run .agents/skills/medium-explorer/scripts/login_medium.py --sid "<SID_COOKIE>" --uid "<UID_COOKIE>"
uv run .agents/skills/medium-explorer/scripts/login_medium.py --interactive
```

---

## 4. Multi-Platform Operational Pipelines

### A. YouTube Pipeline
```bash
# 1. Catalog channel across all tabs (videos, shorts, streams)
uv run .agents/skills/youtube-extractor/scripts/explore_channel.py "@Lewiskelly8" --tab all --save-json data/channels/lewis_kelly_full.json

# 2. Extract transcript with automatic local Whisper fallback
uv run .agents/skills/youtube-extractor/scripts/extract_transcript.py "<VIDEO_URL_OR_ID>"

# 3. Ingest content & auto-index chunks into Chroma
uv run .agents/skills/knowledge-db/scripts/db.py ingest-content data/transcripts/<ID>.json --platform youtube

# 4. Mine hypotheses directly into knowledge.db
uv run .agents/skills/hypothesis-miner/scripts/extract_hypotheses.py data/transcripts/<ID>.json --ingest-db --platform youtube
```

### B. X (Twitter) Pipeline
```bash
# 1. Explore user profile, bio, and recent posts
uv run .agents/skills/x-explorer/scripts/explore_user.py "@Qullamaggie" --ingest-db

# 2. Search posts, cashtags ($SPY, $NVDA), and topics on X
uv run .agents/skills/x-explorer/scripts/search_x.py "breakout trading $NVDA" --limit 5
```

### C. Reddit Community Pipeline
```bash
# 1. Explore subreddit hot/top posts
uv run .agents/skills/reddit-explorer/scripts/explore_community.py "RealDayTrading" --sort hot --limit 5

# 2. Search discussions across Reddit for creators or setups
uv run .agents/skills/reddit-explorer/scripts/search_reddit.py "Qullamaggie 10 EMA strategy" --limit 5

# 3. Read full thread with top community comments and ingest into database
uv run .agents/skills/reddit-explorer/scripts/read_thread.py "<REDDIT_THREAD_URL>" --ingest-db
```

### D. Medium Pipeline
```bash
# 1. Explore topic tag (e.g. algorithmic-trading, trading, quantitative-finance)
uv run .agents/skills/medium-explorer/scripts/explore_tag.py "algorithmic-trading" --limit 5

# 2. Explore author profile
uv run .agents/skills/medium-explorer/scripts/explore_author.py "@ztraderai" --ingest-db

# 3. Read full article and ingest into knowledge.db
uv run .agents/skills/medium-explorer/scripts/read_article.py "<MEDIUM_ARTICLE_URL>" --ingest-db
```

### E. Web Search & Dynamic Page Reading
```bash
# 1. Search the web via DuckDuckGo without API keys
uv run .agents/skills/web-searcher/scripts/search_web.py "Kristjan Qullamaggie setups" --limit 5

# 2. Render dynamic JS page and extract clean reader markdown
uv run .agents/skills/web-reader/scripts/read_page.py "https://qullamaggie.com"

# 3. Inspect page for embedded videos and caption tracks (.vtt/.srt)
uv run .agents/skills/web-reader/scripts/inspect_video.py "https://qullamaggie.com"
```

### F. Anna's Archive Pipeline (Books & Research Papers)
```bash
# 1. Search Anna's Archive for trading books or textbooks (auto-ingests into knowledge.db)
uv run .agents/skills/annas-archive-explorer/scripts/search_archive.py "Market Wizards" --ext pdf --ingest-db

# 2. Inspect book description and download mirrors by MD5
uv run .agents/skills/annas-archive-explorer/scripts/get_book_details.py "<MD5_HASH>"

# 3. (Optional) Save DDoS-Guard clearance session
uv run .agents/skills/annas-archive-explorer/scripts/session_manager.py --interactive
```

### G. arXiv & Papers With Code Pipeline
```bash
# 1. Search scientific papers with open-source GitHub code
uv run .agents/skills/paper-code-explorer/scripts/search_papers.py "market microstructure trading" --has-code --ingest-db

# 2. Inspect paper details, AI summary, and download PDF to data/papers/
uv run .agents/skills/paper-code-explorer/scripts/get_paper.py "2610.34467" --auto-download --ingest-db

# 3. Explore daily trending research papers
uv run .agents/skills/paper-code-explorer/scripts/explore_trending.py --limit 5 --has-code
```
---

## 5. Semantic Vector Search & RAG Across Platforms

Perform natural language queries across all ingested platforms:

```bash
# Semantic vector search over trading hypotheses
uv run .agents/skills/knowledge-db/scripts/db.py vector-search "should I hold overnight or close same day?" --limit 3

# Filter hypotheses by platform (youtube, x, reddit, medium)
uv run .agents/skills/knowledge-db/scripts/db.py vector-search "SMC change of character" --platform youtube

# Semantic RAG search across raw content and transcript chunks
uv run .agents/skills/knowledge-db/scripts/db.py rag-search "data cleaning in backtesting" --platform medium

# Check database distribution across platforms and categories
uv run .agents/skills/knowledge-db/scripts/db.py stats
```

---

## 6. Synthesizing User Agent Skills

Transform any creator's mined hypotheses from YouTube, X, Reddit, or Medium into a modular Agent Skill:

```bash
# From YouTube content
uv run .agents/skills/user-skill-synthesizer/scripts/synthesize_skill.py "lewis-kelly-smc" \
  --content-id "B1ALxAVtFfI" --platform youtube

# From X user
uv run .agents/skills/user-skill-synthesizer/scripts/synthesize_skill.py "x-breakout-strategy" \
  --user-id "@alphatrader" --platform x

# From Reddit user/community
uv run .agents/skills/user-skill-synthesizer/scripts/synthesize_skill.py "real-day-trading-mindset" \
  --content-id "reddit_1xg9xq1" --platform reddit

# From Medium author
uv run .agents/skills/user-skill-synthesizer/scripts/synthesize_skill.py "quant-data-cleaning" \
  --content-id "<MEDIUM_CONTENT_ID>" --platform medium
```
