# FinSocNet: Multi-Platform Financial Intelligence & Strategy Synthesizer

A modular framework, intelligence storage engine, and AI agent plugin for exploring trading creators across **YouTube, X (Twitter), Reddit, Medium, arXiv, and Anna's Archive**, transcribing media, mining empirical trading hypotheses into SQLite and Chroma, and synthesizing reusable [Agent Skills](https://agentskills.io).

---

## 1. Quick Installation

Install FinSocNet via a single command:

```bash
curl -fsSL https://raw.githubusercontent.com/recursive-alpha/finsocnet/main/install.sh | bash
```

Or install from a local clone:

```bash
git clone https://github.com/recursive-alpha/finsocnet.git
cd finsocnet
./install.sh
```

---

## 2. Multi-Harness AI Agent Integration

FinSocNet acts as a centralized trading knowledge storage and skill distribution engine for external AI agents. Register the plugin across your agent harnesses:

```bash
# Install / register across ALL supported harnesses:
finsocnet install all

# Or install for a specific agent:
finsocnet install claude      # Claude Code (~/.claude/commands/finsocnet.md)
finsocnet install omp         # OMP (~/.omp/agent/extensions/finsocnet.ts)
finsocnet install pi          # Pi Coding Agent (~/.pi/agent/extensions/finsocnet.ts)
finsocnet install hermes      # Hermes (~/.hermes/skills/research/finsocnet/)
finsocnet install codex       # OpenAI Codex (~/.codex/skills/finsocnet/)
finsocnet install openclaw    # OpenClaw (~/.openclaw/skills/finsocnet/)
```

### Slash Commands in AI Agents (Claude Code, OMP, etc.)
Once installed, use slash commands directly inside your AI coding assistant:

```bash
/finsocnet                             # Summary metrics across all platforms
/finsocnet:search "breakout momentum"  # Semantic vector search across all creators
/finsocnet:strategy minervini          # Load full VCP rulebook and risk parameters
/finsocnet:strategy qullamaggie        # Load Episodic Pivot & 10/20 EMA swing rules
/finsocnet:strategy lewis-kelly        # Load SMC market structure & M15/M1 execution
/finsocnet:strategy lance              # Load Right Side of the V capitulation rules
/finsocnet:explore youtube "@handle"   # Explore and catalog any new creator
/finsocnet:skills                      # Inspect System Skills vs Improved Strategy Skills
/finsocnet:rag "data cleaning"         # Retrieve raw transcript/content chunks
```

---

## 3. CLI & Terminal UI (TUI)

```bash
# Launch interactive Terminal UI
finsocnet

# Semantic vector search across all creators
finsocnet search "volatility contraction pattern VCP" --limit 3

# View full hypothesis card with exact verbatim quote & timestamp
finsocnet view 93

# Load creator strategy rulebook and checklists
finsocnet strategy minervini

# List cataloged creators across platforms
finsocnet creators --platform x

# Check database summary statistics
finsocnet stats
```

---

## 4. Available Skills in `.agents/skills/`

| Skill | Classification | Description |
|---|---|---|
| **`youtube-extractor`** | System | Fetch transcripts with timestamps, explore channel catalogs across all tabs (videos, shorts, streams) with Whisper fallback. |
| **`audio-transcriber`** | System | Download audio tracks and transcribe locally using `openai/whisper-large-v3-turbo` (`int8`). |
| **`x-explorer`** | System | Explore X (Twitter) profiles, search live posts/tickers, and extract tweet threads with browser session & password login. |
| **`reddit-explorer`** | System | Discover and explore trading subreddits (`r/RealDayTrading`, `r/Daytrading`), search discussions, and read threads with comments. |
| **`medium-explorer`** | System | Explore Medium articles, quantitative finance publications, author profiles, and read full stories. |
| **`web-searcher`** | System | Query DuckDuckGo without API keys for creators, profiles, and internet research with site-filtering. |
| **`web-reader`** | System | Render dynamic JS pages via Playwright, extract clean markdown/text, take screenshots, and inspect embedded videos and caption tracks. |
| **`annas-archive-explorer`** | System | Search open books, research papers, and textbooks across Anna's Archive (https://annas-archive.gl) with mirror detection. |
| **`paper-code-explorer`** | System | Explore scientific research papers and code implementations across arXiv and Papers With Code (Hugging Face Papers). |
| **`knowledge-db`** | System | Relational SQLite database (`knowledge.db`) and Chroma vector store (`data/chroma_db`) with `sentence-transformers/all-MiniLM-L6-v2`. |
| **`hypothesis-miner`** | System | Mine empirical trading hypotheses, setups, holding periods, and verbatim quotes directly into the database. |
| **`user-skill-synthesizer`** | System | Transform extracted user rules across YouTube, X, Reddit, and Medium into production-ready Agent Skills conforming to [agentskills.io](https://agentskills.io). |
| **`mark-minervini-vcp`** | Improved | Mark Minervini Volatility Contraction Pattern (VCP), 6 preservation rules, 1.25% equity risk. |
| **`qullamaggie-swing-strategy`** | Improved | Kristjan Qullamaggie Episodic Pivots (EP), High Tight Flags, 10/20 EMA trailing stops. |
| **`lance-breitstein-levels`** | Improved | Lance Breitstein liquidity dynamics, Right Side of the V, failed breakdown execution. |
| **`lewis-kelly-smc`** | Improved | Lewis Kelly Smart Money Concepts (SMC), M15 trend definition, M1 change of character entries. |
| **`humbled-trader-strategy`** | Improved | Humbled Trader momentum swing rules, ADR >= 4% filter, overnight long holding vs same-day short. |
| **`smb-capital-breakouts`** | Improved | SMB Capital prop desk breakout confirmation, relative volume surge, multi-timeframe alignment. |
| **`trader-dante-execution`** | Improved | Tom Dante institutional level mapping, pre-market preparation, unconditional stop discipline. |
| **`peter-brandt-classical`** | Improved | Peter Brandt 50-year classical factor charting, geometric supply/demand consolidation footprints. |
| **`chat-with-traders-defense`** | Improved | Tim Furey defense-first portfolio management, capital longevity, and drawdown truncation. |

---

## 5. Agent Operating Guide
See **[AGENTS.md](AGENTS.md)** for instructions, workflow pipelines, and command references.
