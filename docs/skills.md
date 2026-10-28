# Skills and platforms

Every capability is a skill in [`.agents/skills/`](../.agents/skills/) (the open [Agent Skills](https://agentskills.io) format). Platform skills share one contract (`search`, `profile`, `list`, `fetch`, `--ingest`, `--enqueue`, `--save-cursor`, `--new-only`; see [Exploring](exploring.md)); their code is in `finsocnet/adapters/`. **Login** says whether the user's imported session matters ([Sessions](sessions.md)). This page was generated from the skills' own descriptions on 2026-10-28; the SKILL.md of a skill is always the source of truth.

## Knowledge core

| Skill | What it does | Login |
|---|---|---|
| [`knowledge-db`](../.agents/skills/knowledge-db/SKILL.md) | The FinSocNet database CLI (`finsocnet kb`) over the single SQLite file data/knowledge.db | — |
| [`knowledge-transformer`](../.agents/skills/knowledge-transformer/SKILL.md) | Rewrite financial and trading knowledge from any text (video transcripts, podcasts, posts, comments, chat messages, articles, books, papers, filings, Pine Script or code) into canonical Know | — |
| [`knowledge-dedup`](../.agents/skills/knowledge-dedup/SKILL.md) | Decide whether a new Knowledge Card is the same as, refines, relates to, or contradicts existing cards, and commit the decision atomically so the knowledge base keeps exactly one card per id | — |
| [`knowledge-search`](../.agents/skills/knowledge-search/SKILL.md) | Answer trading and finance questions from the FinSocNet knowledge base with cited Knowledge Cards | — |
| [`market-idea-miner`](../.agents/skills/market-idea-miner/SKILL.md) | Mine one stored content item (video, podcast episode, thread, chat window, article, book, paper, filing, code) end to end | — |
| [`translator`](../.agents/skills/translator/SKILL.md) | Detect the language of stored content and of user questions, and translate everything that is not English into English so it can be embedded and searched. Use whenever a content has no langu | — |

## People

| Skill | What it does | Login |
|---|---|---|
| [`people-discoverer`](../.agents/skills/people-discoverer/SKILL.md) | Discover and create the people who publish markets and economics knowledge (traders, PMs, investors, CEOs, economists, professors, authors, regulators) before crawling their content, then find and queue their channels, accounts, sites and papers | — |
| [`person-explorer`](../.agents/skills/person-explorer/SKILL.md) | Start from one profile URL of a person and complete everything: identify and match the person, find and verify all their places, list every long and short video/post/paper, mine the best content, report what is complete and what is blocked | — |
| [`person-profiler`](../.agents/skills/person-profiler/SKILL.md) | Build the full profile of one person: find and verify website, social accounts, newsletters, podcasts, courses, books, code, papers and scholar/Wikipedia pages, match each with evidence and confidence, store them as links, aliases and sources | — |
| [`person-matcher`](../.agents/skills/person-matcher/SKILL.md) | Resolve who is speaking or writing — match channel owners, podcast hosts and guests, authors, commenters and handles across YouTube, X, Reddit, Discord, Substack, forums, books and papers to | — |
| [`person-skill-synthesizer`](../.agents/skills/person-skill-synthesizer/SKILL.md) | Build or rebuild a person's trading rulebook (overview, setup and screening, entry and execution, trade management, risk and sizing, psychology and review, checklists) from the Knowledge Car | — |
| [`person-skills-explorer`](../.agents/skills/person-skills-explorer/SKILL.md) | Read, list and compare people's rulebooks stored in the FinSocNet database | — |

## Access

| Skill | What it does | Login |
|---|---|---|
| [`session-bridge`](../.agents/skills/session-bridge/SKILL.md) | Move the user's logged-in browser sessions from their local machine to the remote FinSocNet host | — |
| [`agent-browser`](../.agents/skills/agent-browser/SKILL.md) | Start, check and debug the single Chrome browser that all FinSocNet platform skills attach to over CDP on the remote host | — |

## Loop and growth

| Skill | What it does | Login |
|---|---|---|
| [`source-explorer`](../.agents/skills/source-explorer/SKILL.md) | Run the FinSocNet exploration loop — take the next items from the explore queue (user seeds, knowledge gaps, people and books mentioned in content, browser history, cross-platform links, sea | — |
| [`self-improver`](../.agents/skills/self-improver/SKILL.md) | Improve FinSocNet from its own run history | — |
| [`skill-installer`](../.agents/skills/skill-installer/SKILL.md) | Install a new agent skill into FinSocNet from a link the user pastes | — |
| [`platform-skill-builder`](../.agents/skills/platform-skill-builder/SKILL.md) | Create a new platform skill for a website, forum, blog, community, API or feed that FinSocNet has no skill for. Given a URL or a name ("add xyz.org"), it probes the site (robots.txt, feeds | — |
| [`finsocnet`](../.agents/skills/finsocnet/SKILL.md) | Entry point to FinSocNet, the financial social intelligence system | — |

## Video and audio

| Skill | What it does | Login |
|---|---|---|
| [`youtube-extractor`](../.agents/skills/youtube-extractor/SKILL.md) | Catalog YouTube channels (videos, shorts, live streams), read video metadata and full transcripts with timestamps (manual or auto captions, local Whisper fallback), search YouTube, and store | — |
| [`audio-transcriber`](../.agents/skills/audio-transcriber/SKILL.md) | Transcribe speech to timestamped text with local Whisper (openai/whisper-large-v3-turbo, int8) from a local audio/video file or any yt-dlp-supported URL | — |
| [`podcast-explorer`](../.agents/skills/podcast-explorer/SKILL.md) | Find and ingest podcasts on any topic (finance examples such as Chat With Traders, Market Wizards-style interviews, macro shows) | — |
| [`tiktok-explorer`](../.agents/skills/tiktok-explorer/SKILL.md) | Explore TikTok creators on any topic — list a profile's videos, read captions and descriptions, transcribe speech with local Whisper — and store videos as FinSocNet content | no |

## Social networks

| Skill | What it does | Login |
|---|---|---|
| [`x-explorer`](../.agents/skills/x-explorer/SKILL.md) | Explore X (Twitter) through the agent browser with the user's imported session | x |
| [`reddit-explorer`](../.agents/skills/reddit-explorer/SKILL.md) | Explore any Reddit community or user, on any topic (finance examples such as r/RealDayTrading, r/Daytrading, r/algotrading, r/options, r/vietnamstocks) | browser; RSS fallback |
| [`bluesky-explorer`](../.agents/skills/bluesky-explorer/SKILL.md) | Explore Bluesky (fintwit traders who moved from X) | — |
| [`threads-explorer`](../.agents/skills/threads-explorer/SKILL.md) | Explore Threads (Meta) — trader profiles and posts with replies — through the agent browser and store them as FinSocNet content | optional |
| [`instagram-explorer`](../.agents/skills/instagram-explorer/SKILL.md) | Explore Instagram creators on any topic with the user's imported session | instagram |
| [`facebook-explorer`](../.agents/skills/facebook-explorer/SKILL.md) | Read Facebook groups and pages on any topic through the agent browser with the user's imported session | facebook |
| [`linkedin-explorer`](../.agents/skills/linkedin-explorer/SKILL.md) | Read LinkedIn posts and articles of known fund managers, analysts and traders with the user's imported session, and store them as FinSocNet content. Use for linkedin.com/in, /posts or /pulse | linkedin |
| [`stocktwits-explorer`](../.agents/skills/stocktwits-explorer/SKILL.md) | Read StockTwits symbol streams and user streams and store messages as FinSocNet content. Use for stocktwits.com links, $TICKER sentiment streams, or StockTwits users. Most messages yield no | — |
| [`discord-explorer`](../.agents/skills/discord-explorer/SKILL.md) | Read Discord servers on any topic — list servers and channels, read text, forum and announcement channels and threads by day, search a server, and store messages as FinSocNet content — eithe | discord |
| [`telegram-explorer`](../.agents/skills/telegram-explorer/SKILL.md) | Read Telegram channels and groups on any topic | private channels |

## Writing and communities

| Skill | What it does | Login |
|---|---|---|
| [`medium-explorer`](../.agents/skills/medium-explorer/SKILL.md) | Explore Medium on any topic (trading, quant and finance writing included) | member stories |
| [`substack-explorer`](../.agents/skills/substack-explorer/SKILL.md) | Explore Substack newsletters on any topic (trading, macro and investing included) | paid posts |
| [`rss-explorer`](../.agents/skills/rss-explorer/SKILL.md) | Follow any RSS or Atom feed on any topic — trader blogs, Ghost/WordPress/Beehiiv newsletters, news sites (CafeF, Vietstock, Reuters sections), YouTube channel feeds — discover a site's feeds | — |
| [`seekingalpha-explorer`](../.agents/skills/seekingalpha-explorer/SKILL.md) | Read Seeking Alpha articles, author profiles and comments (premium articles with the user's subscription session) and store them as FinSocNet content. Use for seekingalpha.com article or aut | premium articles |
| [`forum-explorer`](../.agents/skills/forum-explorer/SKILL.md) | Read forums of any engine and any topic — finance examples Elite Trader, BabyPips, Futures.io, Forex Factory, Trade2Win, F319 (Vietnam), and any Discourse, XenForo, vBulletin or phpBB forum | — |
| [`stackexchange-explorer`](../.agents/skills/stackexchange-explorer/SKILL.md) | Search and read Stack Exchange Q&A — Quantitative Finance (quant), Personal Finance & Money (money), Stack Overflow (backtesting, pandas, trading APIs), Economics, Cross Validated (stats) an | — |
| [`hackernews-explorer`](../.agents/skills/hackernews-explorer/SKILL.md) | Search Hacker News stories and read full comment trees on any topic (quant, market structure, fintech and trading-system discussions included) via the Algolia HN API, and store them as FinSo | — |
| [`tradingview-explorer`](../.agents/skills/tradingview-explorer/SKILL.md) | Explore TradingView — trade ideas with descriptions, symbol, timeframe and long/short labels, open-source Pine Script indicators and strategies with their code, author profiles and comments | optional |

## Web

| Skill | What it does | Login |
|---|---|---|
| [`web-searcher`](../.agents/skills/web-searcher/SKILL.md) | Search the open web with DuckDuckGo (no API key) to find traders, their profiles on other platforms, interviews, articles, forums and PDFs, with site filters, regions, time limits and news m | — |
| [`google-searcher`](../.agents/skills/google-searcher/SKILL.md) | Search Google (web and news) through the agent browser with the user's Google session, using advanced operators (site:, inurl:, intitle:, filetype:, date ranges) to find creator discussions | google (session helps) |
| [`web-reader`](../.agents/skills/web-reader/SKILL.md) | Read any web page through the agent browser (JavaScript rendered, with the user's sessions) and extract clean article text, tables and comments; discover a site's RSS feeds, outbound links | — |
| [`document-reader`](../.agents/skills/document-reader/SKILL.md) | Read local or downloaded documents — PDF books and papers (with OCR for scanned pages), EPUB, DOCX, HTML, Markdown and text, including chat exports from Zalo/WhatsApp/Telegram saved as text | — |

## Research and code

| Skill | What it does | Login |
|---|---|---|
| [`paper-code-explorer`](../.agents/skills/paper-code-explorer/SKILL.md) | Search arXiv (q-fin, stat.ML, cs.LG) and Hugging Face / Papers With Code for papers on any topic with open-source code (quantitative finance and trading included), read abstracts and AI summ | — |
| [`research-explorer`](../.agents/skills/research-explorer/SKILL.md) | Search academic and practitioner research on any topic beyond arXiv | — |
| [`annas-archive-explorer`](../.agents/skills/annas-archive-explorer/SKILL.md) | Search Anna's Archive for books, textbooks and papers on any topic (finance examples such as Market Wizards, Reminiscences, quant textbooks), read book details and mirrors by MD5, and downlo | — |
| [`sec-edgar-explorer`](../.agents/skills/sec-edgar-explorer/SKILL.md) | Read SEC EDGAR filings — company and fund filings index by CIK, full-text search, 10-K/10-Q/8-K text, 13F-HR holdings of fund managers, N-CSR fund letters — and store them as FinSocNet conte | — |
| [`github-explorer`](../.agents/skills/github-explorer/SKILL.md) | Explore GitHub repositories on any topic (trading strategies, backtests and quant research included) | — |

## Unreadable data

| Skill | What it does | Login |
|---|---|---|
| [`reverse-anything`](../.agents/skills/reverse-anything/SKILL.md) | Read what an agent cannot read — compiled binaries, packaged desktop/Electron apps, APKs, SQLite databases, packet captures, model files (GGUF, safetensors), firmware, .pyc, plists, crash re | — |

## Your own platforms

`platform-skill-builder` adds a `<name>-explorer` skill for any site from a declarative recipe in `config/sites/<name>.yaml`; see [Exploring → New sites](exploring.md#new-sites-platform-skill-builder).

Skills from other people go through `skill-installer` (quarantine, scan, review of every file, your confirmation, lock file `config/skills.lock.json`); see [Operations](operations.md#installing-third-party-skills).
