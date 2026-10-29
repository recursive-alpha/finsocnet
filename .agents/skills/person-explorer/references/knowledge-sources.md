# Knowledge sweep: where a person's knowledge lives and how to get all of it

Goal: **every kind of thing the person published or said**, not only the channel the user gave you: articles, newspaper and magazine pieces, interviews, books, talks and lectures, videos (long and short), podcasts, papers and working papers, letters, filings, social posts. You do the sweep with skills; `kb person coverage <id>` tells you what is still missing (its `gaps` list is your to-do) and when you are done.

## The loop

1. `kb person coverage <id>` → read `content_by_type` (listed / fetched / mined) and `gaps`.
2. For each gap, run the recipe below for the person's **class** (`kb person get <id>` → `profession`; static list in `kb person classes`; `other` = use the generic recipe).
3. Fetch with the platform skill (`--ingest --run R`), mine with `market-idea-miner`, commit cards.
4. `kb person coverage <id>` again. Stop when `gaps` is empty, or every remaining gap is **blocked** (record platform + exit code + hint) or **searched without result** (record the queries you tried: `kb run end --stats '{"searched_no_result": ["books: annas.py search \"<name>\" → 0"]}'`).
5. Budgets per person and round: 12 fetched contents unless the first ones keep producing cards; YouTube ≤ 15 requests per run.

## Search recipes by content type (use the skill, read its SKILL.md first)

| Type | How to find it | Fetch with |
|---|---|---|
| **Articles & blog posts** | their site/blog (`rss.py discover <site>`, `web.py discover`), Substack/Medium (`substack.py search/list`, `medium.py list`), `web_search.py search "\"<name>\" article|essay|column"`, `google.py search "\"<name>\" site:<their site>"` | `substack.py fetch`, `medium.py fetch`, `rss.py fetch`, `web.py fetch` |
| **Newspaper & magazine pieces** (by or about them) | `web_search.py search "\"<name>\" interview|profile|op-ed site:ft.com OR site:wsj.com OR site:bloomberg.com OR site:reuters.com OR site:economist.com OR site:nytimes.com OR site:forbes.com OR site:barrons.com OR site:project-syndicate.org"`; for non-English use local outlets (vnexpress.net, nikkei.com, caixin.com, elpais.com, ...); prefer pieces **by** the person or interviews (their own words) | `web.py fetch` (paywalled → note it, use the archive/open version only if the skill supports it, else `blocked: paywall`) |
| **Books** | `annas.py search "<title or name>"`, the person's site/Amazon/Goodreads page (titles only; text from Anna's), `web_search.py "\"<name>\" book"`; `research.py search` for monographs | `annas.py download` → `document.py fetch --ingest` (full text, 8000-char chunks); blocked → `blocked: ddos-guard`, queue |
| **Talks & lectures** | `youtube.py search "<name> lecture|keynote|talk|interview" --type video` (mind the budget), conference sites (`web.py fetch` on speaker pages), university channels, TED, Nobel lectures (nobelprize.org), central-bank speech pages | `youtube.py fetch` (transcript), `document.py fetch` for PDF/slides/transcripts, `transcribe.py` only if no text and the item is short |
| **Videos (long, shorts, streams)** | `youtube.py list <channel> --tab all --catalog` (whole inventory as metadata), then top by views and by teaching titles | `youtube.py fetch` |
| **Podcasts** | `podcast.py search "<name>"` (their show and shows they guested on), the show's own site for transcripts | `podcast.py fetch`, `web.py fetch` of transcript pages, `transcribe.py` last |
| **Papers & working papers** | `research.py search "<name>"` / `research.py profile` (OpenAlex id), `papers.py search` (arXiv), their homepage's papers page, SSRN/NBER/RePEc pages via `web.py`, `github.py` for code | `research.py fetch --pdf --ingest`, `papers.py fetch`, `document.py fetch` |
| **Lecture notes & course material** | their university page, MIT OCW / Yale Open Courses / Coursera pages (`web_search.py "\"<name>\" lecture notes pdf"`) | `document.py fetch` |
| **Letters, filings, reports** | fund/firm site (annual or shareholder letters), `sec.py` for 13F/10-K/proxy of their firm, central-bank and agency publication pages | `sec.py fetch`, `document.py fetch`, `web.py fetch` |
| **Social posts** | X (`x.py list`), Reddit (`reddit.py`), LinkedIn (`linkedin.py`), Bluesky (`bluesky.py list`), Threads, StockTwits, TradingView ideas (`tradingview.py list`) | each skill's `fetch`; exit 3 → `blocked: needs session`, tell the user the export |
| **Mentions in other people's content** | `kb content search "<name>"` (our own full text), guests/hosts lists | already stored: mine the segments where they speak |

## By class: what usually exists (check these first)

| Class | Look first for |
|---|---|
| trader, investor | their channel/stream, newsletter, podcast appearances, books, courses (public pages only), X threads, forum posts, interviews |
| portfolio_manager, strategist, analyst | fund letters, quarterly notes, conference talks, interviews (Bloomberg/CNBC/podcasts), 13F via `sec.py`, books |
| executive, founder | shareholder/annual letters, earnings-call remarks, keynote talks, books, interviews, company blog, podcasts |
| economist, central_banker, regulator | speeches and testimony on the institution's site (bis.org speech archive, federalreserve.gov, ecb.europa.eu, boj.or.jp, ...), working papers, press conferences (transcripts), books, op-eds |
| academic, researcher | papers (OpenAlex/SSRN/NBER/arXiv), lecture notes and syllabi, course videos, textbooks, Nobel/prize lectures, op-eds, podcasts |
| author, journalist | their books (Anna's), columns and articles (their outlet's author page), newsletters, interviews |
| educator | course pages (public), YouTube/podcast, books, newsletters |
| other | start from what made them in scope (`relevance`) and follow it |

## Quality bar per fetched item

- Prefer **their own words** over text about them. Text about them is fine for identity and context (`person_links`, `bio`), and for cards only if it quotes them.
- Full text, not abstract/snippet. Paywalled or truncated pieces are recorded (`blocked: paywall`), never reconstructed.
- Each card is attributed to the right speaker (host vs guest vs author), quote verbatim.
- Duplicates: `kb seen check`, `kb content claim`, and the dedup judgment (`knowledge-dedup`) keep the database from filling with copies.

## Diversity check (after each person)

Different content types, different years (oldest and newest), at least two platforms, and at least one primary source. If a person has 40 cards from one YouTube channel only, the sweep is not done: search books, papers, articles and interviews next.
