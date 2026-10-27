# FinSocNet: Multi-Platform Intelligence & User Skill Synthesizer

A modular framework and AI agent environment for exploring creators and communities across **YouTube, X (Twitter), Reddit, Medium, and the Web**, transcribing media (via API or local `openai/whisper-large-v3-turbo`), mining empirical trading hypotheses into a relational database and vector store (`knowledge.db` + Chroma), and synthesizing reusable [Agent Skills](https://agentskills.io).

## Quick Start

### 1. Requirements & Setup
- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/)
- `ffmpeg` (for local audio decoding and transcription)
- Playwright Chromium (`uv run playwright install chromium`)

```bash
# Setup environment
cp .env.example .env
uv sync
```

### 2. Available Skills in `.agents/skills/`

| Skill | Path | Description |
|---|---|---|
| **`youtube-extractor`** | `.agents/skills/youtube-extractor` | Fetch transcripts with timestamps, explore channel catalogs across all tabs (videos, shorts, streams) with Whisper fallback. |
| **`audio-transcriber`** | `.agents/skills/audio-transcriber` | Download audio tracks and transcribe locally using `openai/whisper-large-v3-turbo` (`int8`). |
| **`x-explorer`** | `.agents/skills/x-explorer` | Explore X (Twitter) profiles, search live posts/tickers, and extract tweet threads with browser session & password login. |
| **`reddit-explorer`** | `.agents/skills/reddit-explorer` | Discover and explore trading subreddits (`r/RealDayTrading`, `r/Daytrading`), search discussions, and read threads with comments. |
| **`medium-explorer`** | `.agents/skills/medium-explorer` | Explore Medium articles, quantitative finance publications, author profiles, and read full stories. |
| **`web-searcher`** | `.agents/skills/web-searcher` | Query DuckDuckGo without API keys for creators, profiles, and internet research with site-filtering. |
| **`web-reader`** | `.agents/skills/web-reader` | Render dynamic JS pages via Playwright, extract clean markdown/text, take screenshots, and inspect embedded videos and caption tracks. |
| **`annas-archive-explorer`** | `.agents/skills/annas-archive-explorer` | Search open books, research papers, and textbooks across Anna's Archive (https://annas-archive.gl) with mirror detection. |
| **`paper-code-explorer`** | `.agents/skills/paper-code-explorer` | Explore scientific research papers and code implementations across arXiv and Papers With Code (Hugging Face Papers). |
| **`knowledge-db`** | `.agents/skills/knowledge-db` | Relational SQLite database (`knowledge.db`) and Chroma vector store (`data/chroma_db`) with `sentence-transformers/all-MiniLM-L6-v2` across all sources. |
| **`hypothesis-miner`** | `.agents/skills/hypothesis-miner` | Mine empirical trading hypotheses, setups, holding periods, and verbatim quotes directly into the database. |
| **`user-skill-synthesizer`** | `.agents/skills/user-skill-synthesizer` | Transform extracted user rules across YouTube, X, Reddit, and Medium into production-ready Agent Skills conforming to [agentskills.io](https://agentskills.io). |

### 3. Agent Operating Guide
See **[AGENTS.md](AGENTS.md)** for instructions, workflow pipelines, and command references.
