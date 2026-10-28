# FinSocNet: Multi-Platform Financial Intelligence & Strategy Network

FinSocNet is an agent-operated financial intelligence framework and skill distribution engine. It discovers traders, investors, and quantitative researchers across **31 platforms** (video, podcasts, newsletters, social networks, chat communities, forums, code repositories, academic papers, and SEC filings), captures their content into a single SQLite database, transforms insights into structured **Knowledge Cards**, deduplicates claims using agent reasoning, and delivers executable trading rulebooks and semantic search to AI coding harnesses.

Adheres strictly to the open [Agent Skills Specification](https://agentskills.io).

---

## 1. Core Principles (v2 Architecture)

- **Harness-Native Intelligence:** Agents read, analyze, judge, and transform financial knowledge using explicit instructions, claim grammar, and few-shot examples. Deterministic scripts handle fetch, storage, validation, and search.
- **Pure SQLite Storage:** Single local file (`data/knowledge.db`) using relational tables, vector embeddings (BLOBs), and FTS5 full-text search. Zero external daemon or Chroma dependency.
- **Structured Knowledge Cards:** Knowledge is stored in a canonical schema with strict claim grammar (`WHEN ... IF ... THEN ... WITH CONFIDENCE ...`) and controlled vocabulary.
- **Agent-Judged Deduplication:** Candidates are retrieved algorithmically, but the agent determines whether a claim is identical, refining, related, contradicting, or novel.
- **Person-Centric Attribution:** Knowledge belongs to individual practitioners, not media channels. Every citation records who claimed it, their role, and the exact content anchor.
- **Remote-First Session Bridge:** Secure transfer of authenticated browser sessions from local machines to dedicated agent browser profiles—no plain-text passwords or cookies stored in `.env`.

Full design specifications live in [`SPEC.md`](SPEC.md) and [`docs/spec/`](docs/spec/).

---

## 2. Quick Installation

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

## 3. Multi-Harness AI Agent Integration

FinSocNet serves as a centralized knowledge base and strategy distribution engine for AI coding harnesses:

```bash
# Install / register across ALL supported harnesses:
finsocnet install all

# Or install for a specific agent harness:
finsocnet install claude      # Claude Code (~/.claude/commands/finsocnet.md)
finsocnet install omp         # OMP (~/.omp/agent/extensions/finsocnet.ts)
finsocnet install pi          # Pi Coding Agent (~/.pi/agent/extensions/finsocnet.ts)
finsocnet install hermes      # Hermes (~/.hermes/skills/research/finsocnet/)
finsocnet install codex       # OpenAI Codex (~/.codex/skills/finsocnet/)
finsocnet install openclaw    # OpenClaw (~/.openclaw/skills/finsocnet/)
```

### Slash Commands in AI Agents
Once registered, interact with FinSocNet directly inside your AI harness:

| Command | Action |
|---|---|
| `/finsocnet` | Summary metrics across platforms, creators, and hypotheses |
| `/finsocnet:search <query>` | Cited search across all indexed trading knowledge |
| `/finsocnet:strategy <name>` | Load full trader rulebooks (e.g. `minervini`, `qullamaggie`, `lance`, `dante`) |
| `/finsocnet:explore <platform> <target>` | Explore and catalog a new creator or channel |
| `/finsocnet:skills` | Inspect installed system skills and strategy rulebooks |
| `/finsocnet:rag <query>` | Retrieve verbatim content chunks with source citations |
| `/finsocnet:view <id>` | Inspect an exact hypothesis card with quote and metadata |

---

## 4. CLI & Terminal UI (TUI)

```bash
# Launch interactive Terminal UI
finsocnet

# Semantic vector & keyword search across all indexed knowledge
finsocnet search "volatility contraction pattern VCP" --limit 3

# View full hypothesis card with exact verbatim quote & timestamp
finsocnet view 93

# Load trader strategy rulebook and actionable checklists
finsocnet strategy minervini

# List cataloged creators across platforms
finsocnet creators --platform x

# Check database summary statistics
finsocnet stats
```

---

## 5. Skill Catalog (`.agents/skills/`)

FinSocNet provides 45 standardized skills adhering to [agentskills.io](https://agentskills.io):

### A. Core Knowledge Engine
| Skill | Role | Description |
|---|---|---|
| **`knowledge-db`** | Storage | Database CLI (`finsocnet kb`) over SQLite (`data/knowledge.db`), FTS5, and vector search. |
| **`knowledge-transformer`** | Extraction | Transforms raw transcripts and texts into validated Knowledge Cards using claim grammar and vocabulary. |
| **`knowledge-dedup`** | Deduplication | Evaluates candidate cards to decide `same`, `refines`, `relates`, or `contradicts`. |
| **`knowledge-search`** | Retrieval | Answers trading questions with cited Knowledge Cards, consensus, and contradiction checks. |
| **`market-idea-miner`** | Pipeline | Orchestrates end-to-end mining of a content item into segmented citations and cards. |
| **`person-matcher`** | Attribution | Resolves creators, guests, and authors to canonical person entities across platforms. |
| **`person-skill-synthesizer`** | Synthesis | Synthesizes a trader's Knowledge Cards into modular rulebooks (screening, execution, risk). |
| **`person-skills-explorer`** | Inspection | Lists, searches, and compares synthesized trader rulebooks. |

### B. Orchestration, Browsing & Self-Improvement
| Skill | Role | Description |
|---|---|---|
| **`agent-browser`** | Browser | Persistent, authenticated Chromium browser over Chrome DevTools Protocol (CDP). |
| **`session-bridge`** | Auth | Exports local browser cookies/storage states and imports them into remote agent profiles. |
| **`source-explorer`** | Discovery | Autonomous exploration loop processing queued discovery seeds and knowledge gaps. |
| **`self-improver`** | Evolution | Diagnoses failed runs and gaps to synthesize skill improvements under human evaluation. |
| **`skill-installer`** | Extensions | Installs external skills from GitHub, local paths, or URLs with automated security audits. |
| **`finsocnet`** | Root Entry | Central entry point for platform metrics, rulebooks, and unified intelligence queries. |

### C. Platform Exploration Adapters (31 Platforms)
| Priority | Platforms | Covered Sources |
|---|---|---|
| **P1: Core Media & Web** | `youtube-extractor`, `audio-transcriber`, `podcast-explorer`, `x-explorer`, `reddit-explorer`, `medium-explorer`, `substack-explorer`, `web-searcher`, `google-searcher`, `web-reader`, `document-reader`, `annas-archive-explorer`, `paper-code-explorer` | YouTube (videos/shorts/streams), local Whisper (`large-v3-turbo`), Apple/Spotify podcasts, X/Twitter, Reddit (`r/RealDayTrading`, etc.), Medium, Substack, DuckDuckGo, Google, Playwright dynamic web, PDF/EPUB/DOCX, Anna's Archive, arXiv & Papers With Code. |
| **P2: Communities & Markets** | `discord-explorer`, `telegram-explorer`, `stackexchange-explorer`, `forum-explorer`, `tradingview-explorer`, `facebook-explorer`, `rss-explorer`, `sec-edgar-explorer`, `research-explorer`, `github-explorer`, `bluesky-explorer` | Discord trading servers, Telegram channels, Quant Stack Exchange, Elite Trader / Forex Factory forums, TradingView ideas/scripts, Facebook groups, RSS/Atom feeds, SEC EDGAR 10-K/8-K filings, OpenAlex / Semantic Scholar, GitHub repos, Bluesky fintwit. |
| **P3: Secondary Social** | `stocktwits-explorer`, `tiktok-explorer`, `instagram-explorer`, `threads-explorer`, `linkedin-explorer`, `seekingalpha-explorer`, `hackernews-explorer` | StockTwits ticker streams, TikTok creators, Instagram trading posts/reels, Meta Threads, LinkedIn articles, Seeking Alpha analyses, Hacker News fintech/quant threads. |

---

## 6. Verified Trader Rulebooks (`finsocnet strategy <name>`)

Synthesized rulebooks and actionable checklists for legendary practitioners:
- **Mark Minervini (`minervini`):** Volatility Contraction Pattern (VCP), SEPA analysis, trend templates, 1.25% equity risk limit.
- **Kristjan Qullamaggie (`qullamaggie`):** Episodic Pivots, High Tight Flags, ORB execution, 10/20 EMA trailing stops.
- **Lance Breitstein (`lance`):** Liquidity dynamics, Right Side of the V, failed breakdown reclamation, asymmetric risk sizing.
- **Lewis Kelly (`lewis-kelly`):** Smart Money Concepts (SMC), multi-timeframe structural alignment (M15 to M1), change of character.
- **Tom Dante (`dante`):** Institutional S/R liquidity sweeps, pre-market plan sheets, -2R daily circuit breaker.
- **SMB Capital (`smb`):** Prop desk breakout confirmation, relative volume surges, Reading the Tape.
- **Peter Brandt (`brandt`):** Classical factor charting, 50-year geometric consolidation footprints, factor rules.
- **Humbled Trader (`humbled`):** Momentum swing execution, ADR ≥ 4% filter, strict overnight holding protocols.
- **Tim Furey (`furey`):** Defense-first capital preservation, risk-of-ruin minimization, drawdown truncation.

---

## 7. Documentation & Guides

- **[`SPEC.md`](SPEC.md):** Complete architectural specification and design decisions.
- **[`docs/spec/`](docs/spec/):** In-depth guides on database schemas, knowledge cards, pipelines, sessions, and platform adapters.
- **[`AGENTS.md`](AGENTS.md):** Operational guidelines for AI agents executing FinSocNet pipelines.
