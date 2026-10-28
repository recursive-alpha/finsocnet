# 05 — Platform and Content Skills

Every platform skill turns a platform into `ItemRef`, `ProfileRecord` and `ContentRecord` objects (00 §7). Platform skills never write knowledge cards; they only fetch and store content.

---

## 1. Platform Adapter Contract

### 1.1 Python interface (`finsocnet/core/platform.py`)

```python
class PlatformAdapter(Protocol):
    platform: str                       # platform key (00 §4)
    requires_session: bool              # True → check browser_sessions.login_state before browser work
    capabilities: frozenset[str]        # subset of {"search", "profile", "list", "fetch"} + extra subcommands

    def search(self, query: str, *, limit: int, since: str | None, **opts) -> list[ItemRef]: ...
    def profile(self, target: str) -> ProfileRecord: ...
    def list(self, source: str, *, limit: int, cursor: str | None, since: str | None, **opts) -> ListResult: ...
    def fetch(self, item: str, **opts) -> ContentRecord: ...

def run_platform_cli(adapter: PlatformAdapter, extra: dict[str, Callable] | None = None) -> None:
    """Builds argparse with the standard subcommands, handles --format/--run/--ingest/--limit/--since/--cursor,
    maps exceptions to error codes (00 §3.3), charges budgets, marks ItemRef.known, emits the envelope."""
```

### 1.2 Standard CLI

```
<script>.py search  "<query>" [--limit 20] [--since YYYY-MM-DD] [platform opts]
<script>.py profile <handle|url>  [--ingest]           # --ingest: kb source upsert + person candidates in output
<script>.py list    <source>      [--limit 50] [--cursor C] [--since D] [--save-cursor] [--enqueue]
<script>.py fetch   <item>        [--ingest] [platform opts]
```

- `--ingest` on `fetch` calls `kb content add` (requires `--run`) and returns its result inside `data.ingest`.
- `--enqueue` on `list` adds unknown items to `explore_queue` (`origin=source_refresh`, `action=fetch`).
- `--save-cursor` stores `next_cursor` in `sources.crawl_cursor`.
- Unsupported subcommand → exit 2 `UNSUPPORTED`.
- Every adapter saves the original response to `data/raw/<platform>/<native_id>.<json|html>` and sets `raw_path`.

### 1.3 Required tests per adapter

- Fixture test for each supported subcommand: recorded response(s) in `tests/fixtures/<platform>/` → expected JSON.
- `ContentRecord` passes the schema; segments are contiguous; locators have the right keys.
- Login/checkpoint fixture (for session platforms) → exit 3.
- One `@pytest.mark.live` smoke test per subcommand.

### 1.4 Directory per skill

```
.agents/skills/<skill>/
  SKILL.md                      # 00 §9 template
  scripts/<platform>.py         # adapter + run_platform_cli
  references/platform_notes.md  # endpoints, selectors, known breakages (updated by self-improver)
```

Old script names (`explore_channel.py`, `extract_transcript.py`, `explore_user.py`, `search_x.py`, `read_thread.py`, `explore_community.py`, `search_reddit.py`, `explore_tag.py`, `explore_author.py`, `read_article.py`, `read_page.py`, `inspect_video.py`, `search_web.py`) are kept as thin wrappers that call the new subcommands until Phase 8, then removed.

---

## 2. Priority 1 Skills

### 2.1 `youtube-extractor` — refactor

| | |
|---|---|
| Script | `scripts/youtube.py` |
| IDs | content `youtube:<videoId>`; source `youtube:channel:<UC…>` (`youtube:handle:<h>` only until resolved) |
| Session | none required; uses `data/sessions/cookies.txt` with yt-dlp `--cookies` when present (avoids "Sign in to confirm you're not a bot" on server IPs and allows members-only content) |
| search | yt-dlp `ytsearch<N>:<query>` (flat) → ItemRef; `--type video|channel` |
| profile | yt-dlp channel metadata (`https://www.youtube.com/@h/about` or `/channel/UC…`): title, description, links, subscriber count, channel id |
| list | yt-dlp `--flat-playlist` on `/videos`, `/shorts`, `/streams` (`--tab videos|shorts|streams|all`), newest first; cursor = last seen video id; `--since` by upload date |
| fetch | metadata via yt-dlp `-J`; captions via `youtube-transcript-api` (order: manual in original language → manual en → auto original → auto en); if none → `audio-transcriber` (Whisper) |
| content_type | `video`, `short`, `stream` |
| segments | merge caption lines into windows ≤ 45 s and ≤ 600 chars; `kind=transcript`, `locator={start_sec,end_sec}` |
| extra | `{"caption_source": "manual|auto|whisper", "caption_lang": "en", "chapters": [...]}`; chapters also become `links`-free metadata |
| mentions | from description: URLs (→ `links`), `@handles`, `$TICKERS` |
| notes | Live streams > 3 h: still fully transcribed (nothing ignored); mark `extra.long_form = true` |

### 2.2 `audio-transcriber` — refactor

| | |
|---|---|
| Script | `scripts/transcribe.py` (not a platform adapter; standard envelope) |
| Commands | `transcribe <url-or-path> [--language auto] [--content-id ID] [--diarize]` → `{segments:[{start_sec,end_sec,text}], language, model, duration_sec}` |
| Input | local file or any yt-dlp-supported URL (YouTube, Twitch VOD, Vimeo, Rumble, Kick, X video, TikTok, podcast enclosure) |
| Engine | `faster-whisper` model `WHISPER_MODEL`, `compute_type` `WHISPER_COMPUTE_TYPE`, VAD filter on, `word_timestamps=False` |
| Cache | `data/transcripts/<sha256(audio)[:16]>.json`; same audio → no re-transcription |
| Output use | caller builds segments (≤ 45 s windows) into its own ContentRecord |
| `--diarize` | optional later (whisperX/pyannote); fills `speaker_hint`; not required in v2 |

### 2.3 `podcast-explorer` — new

| | |
|---|---|
| Script | `scripts/podcast.py` |
| IDs | source `podcast:feed:<sha1(feed_url)[:12]>`; content `podcast:<sha1(feed_url)[:12]>:<sha1(guid)[:12]>` |
| search | iTunes Search API `https://itunes.apple.com/search?media=podcast&entity=podcast&term=<q>&limit=<n>` (shows) and `entity=podcastEpisode` (`--episodes`) |
| profile | show metadata from the RSS channel (title, author, description, links, image) |
| list | `feedparser` on the feed URL (or iTunes `lookup?id=` → `feedUrl`); items newest first; cursor = last guid |
| fetch | 1) Podcasting 2.0 `<podcast:transcript>` (VTT/SRT/JSON) if present → segments; 2) else look for the same episode on YouTube (`youtube.py search` title + show name; match when duration within ±3% and title similarity high) → if found, fetch that and `kb content link-duplicate`; 3) else download enclosure → `audio-transcriber` |
| content_type | `episode`; segments `transcript` |
| extra | `{"guests_hint": [...names parsed by regex from title/description: "with X", "ft. X", "feat. X"], "show": "…"}` — hints only; the agent confirms persons |
| notes | Spotify-exclusive shows are DRM-protected → out of scope; record the show as a source with `status='blocked'` and a note |

### 2.4 `x-explorer` — refactor

| | |
|---|---|
| Script | `scripts/x.py` |
| IDs | content `x:<tweet_id>` (thread = root tweet id); source `x:user:<handle lowercase>` |
| Session | required (`x`) |
| Method | agent browser; capture GraphQL JSON (`/i/api/graphql/*/(SearchTimeline|UserTweets|UserTweetsAndReplies|TweetDetail|UserByScreenName)`) with `capture_json` while scrolling; DOM parsing only as fallback |
| search | `https://x.com/search?q=<q>&f=live` (or `f=top` with `--top`); supports operators (`from:`, `since:`, `min_faves:`, `$TICKER`) |
| profile | `UserByScreenName` → bio, links, followers, verified, created_at |
| list | `https://x.com/<handle>` (`--with-replies` → `/with_replies`); scroll until `--limit` or `--since`; cursor = oldest tweet id |
| fetch | `https://x.com/<handle>/status/<id>` → `TweetDetail`; build the **author's self-thread** (consecutive replies by the same author) as segments; other people's replies as `reply` segments (cap `--max-replies 100`, sorted by likes) |
| content_type | `post` (single) or `thread` |
| segments | each tweet: `kind=post|reply`, `locator={tweet_id}`, author per segment; long-form "note tweets" full text; quoted tweet text appended in `extra.quoted` and as a separate `reply`-kind segment with `locator.quoted_id` |
| media | images/videos URLs; videos with speech → optional `audio-transcriber` when `--transcribe-video` |
| budget | `x` in budgets.yaml |

### 2.5 `reddit-explorer` — refactor

| | |
|---|---|
| Script | `scripts/reddit.py` |
| IDs | content `reddit:<post_id36>`; source `reddit:subreddit:<name lowercase>` / `reddit:user:<name lowercase>` |
| Session | optional (improves access; required for NSFW/quarantined/private subs) |
| Method | Reddit JSON endpoints loaded through the agent browser (`page.goto` on `.json` URLs → `JSON.parse(document.body.innerText)`), so cookies and proxy apply. Remove the old `--host-resolver-rules` hack. |
| search | `https://www.reddit.com/search.json?q=<q>&sort=relevance&t=all&limit=100` or `/r/<sub>/search.json?restrict_sr=1&q=` (`--subreddit`); `--type sr` → `/subreddits/search.json` |
| profile | `/user/<name>/about.json` or `/r/<sub>/about.json` |
| list | `/r/<sub>/<sort>.json?limit=100&after=<cursor>` (`--sort hot|new|top|rising`, `--t day|week|month|year|all`); `/user/<name>/submitted.json` and `/comments.json` (`--kind posts|comments`) |
| fetch | `/comments/<id>.json?limit=500&depth=10&sort=top&raw_json=1`; expand `more` stubs with `/api/morechildren.json` until `--max-comments` (default 500, sorted by score) — log a warning when the cap is hit |
| content_type | `thread` |
| segments | post: `kind=post`, `locator={comment_id:"t3_<id>"}`; comments: `kind=comment`, `locator={comment_id:"t1_<id>", parent_id, score, depth}`, author per segment; deleted/removed comments kept with text `[deleted]` (not quotable) |
| links | outbound URLs from post/comments → `links` |

### 2.6 `medium-explorer` — refactor

| | |
|---|---|
| Script | `scripts/medium.py` |
| IDs | content `medium:<post_id hex>` (the 12-hex suffix of the URL); source `medium:user:<handle>` / `medium:publication:<slug>` / `medium:tag:<tag>` |
| Session | optional (member-only stories need a member session) |
| search | `https://medium.com/search?q=<q>` via agent browser (DOM) |
| profile | `https://medium.com/@<handle>/about` via browser |
| list | RSS: `https://medium.com/feed/@<handle>`, `/feed/<publication>`, `/feed/tag/<tag>` (RSS returns only recent items; for full history scroll the profile page in the browser with `--full`) |
| fetch | agent browser on the article URL; extract `article` with trafilatura on the rendered HTML; paragraphs → segments |
| content_type | `article`; segments `paragraph` `{para}`; code blocks `code` |
| extra | `{"member_only": true|false, "claps": N, "reading_time_min": N}`; if member-only and not logged in → warning `truncated: true` (still stored) |

### 2.7 `substack-explorer` — new

| | |
|---|---|
| Script | `scripts/substack.py` |
| IDs | content `substack:<pub_subdomain>:<post_id>`; source `substack:publication:<subdomain>` (custom domains map to the subdomain from the API's `publication.subdomain`) |
| Session | optional (`substack`; paid posts need a subscribed account) |
| Method | Substack JSON endpoints via the agent browser (`page.request` shares cookies). Endpoints are unofficial — verify in Phase 4 and record in `references/platform_notes.md`. |
| search | publications: `https://substack.com/api/v1/publication/search?query=<q>&page=0&limit=<n>`; posts: `https://substack.com/api/v1/post/search?query=<q>` (verify) or Google `site:substack.com` fallback via `google-searcher` |
| profile | `https://substack.com/api/v1/user/<handle>/public_profile` (author) or `https://<pub>/api/v1/publication` (verify) |
| list | `https://<pub>/api/v1/archive?sort=new&offset=<cursor>&limit=50` |
| fetch | `https://<pub>/api/v1/posts/<slug>` → `body_html` (markdownify → paragraphs); `audience` field: `everyone|only_paid|founding`; if paid and body truncated → warning `truncated: true`; comments `https://<pub>/api/v1/post/<id>/comments?all_comments=true&sort=best_first` → `comment` segments; podcast posts (`podcast_url`) → `audio-transcriber` |
| content_type | `article` (or `episode` for podcast posts) |
| notes | Substack Notes (`--notes`): `https://substack.com/api/v1/reader/feed/profile/<user_id>` (verify) → each note a `post` content |

### 2.8 `web-searcher` — keep

| | |
|---|---|
| Script | `scripts/web_search.py` |
| search | `ddgs` text search: `--region`, `--timelimit d|w|m|y`, `--site <domain>` (adds `site:`), `--news` |
| Output | ItemRef with `id = web:<sha1(canonical_url)[:16]>`; no `fetch` (use `web-reader`) |

### 2.9 `google-searcher` — new

| | |
|---|---|
| Script | `scripts/google.py` |
| Session | optional (`google`); works logged-out but logged-in reduces CAPTCHAs |
| search | agent browser `https://www.google.com/search?q=<q>&num=<n≤50>&hl=en` (`--news` → `tbm=nws`, `--since` → `tbs=cdr:1,cd_min:MM/DD/YYYY`); parse organic results (title, url, snippet, date if shown); ignore ads; support all operators in the query |
| Checkpoint | `/sorry/` or "unusual traffic" → exit 3 `CHECKPOINT` |
| Budget | strict (`google` in budgets.yaml) |
| fetch | not supported (use `web-reader`) |

### 2.10 `web-reader` — refactor

| | |
|---|---|
| Scripts | `scripts/web.py` (adapter: `fetch`, `discover`), `scripts/inspect_media.py` (former `inspect_video.py`) |
| IDs | content `web:<sha1(canonical_url)[:16]>`; source `web:site:<host>` |
| fetch | agent browser → wait `networkidle` (cap `BROWSER_TIMEOUT_MS`) → `trafilatura.extract(html, output_format="markdown", include_comments=True, include_tables=True)` → paragraphs; fallback to readability-style DOM extraction when trafilatura returns < 200 chars |
| discover | `discover <url>`: RSS/Atom links, sitemap, outbound links, embedded media (YouTube/Vimeo iframes, `<video>`, `.vtt/.srt` tracks), PDF links → returned as ItemRefs for the agent to enqueue |
| PDFs | URLs ending in `.pdf` or with `Content-Type: application/pdf` → download to `data/papers/` and delegate to `document-reader` |
| content_type | `page` |

### 2.11 `document-reader` — new

| | |
|---|---|
| Script | `scripts/document.py` |
| IDs | `book:<md5>` when the file came from Anna's Archive (md5 known); `arxiv:<id>` for arXiv PDFs; else `file:<sha256(file)[:16]>` |
| Commands | `fetch <path-or-url> [--title] [--author] [--source-id] [--ocr auto|force|off]`, `scan [--dir data/inbox/documents]` (ingest every new file in the drop folder; moves processed files to `data/inbox/documents/done/`) |
| PDF | PyMuPDF text per page → `page` segments `{page}` (1-based); page with < 50 chars of text and `--ocr auto` → OCR with `ocrmypdf` (optional dependency group `ocr`); tables kept as text |
| EPUB | `ebooklib` → chapters → paragraphs `{chapter, para}` |
| DOCX / HTML / MD / TXT | paragraphs `{para}` |
| Audio / video (mp3, m4a, wav, mp4, mkv, webm…) | `audio-transcriber transcribe <path>` → `transcript` segments `{start_sec,end_sec}` (≤ 45 s windows); `content_type` `recording` — so a webinar or course recording the user drops is never ignored |
| Metadata | title/author from file metadata or args; `content_type`: `book` (> 80 pages or EPUB), `paper`, `recording`, `file` |
| notes | Large books are fine (nothing ignored); the miner uses 8000-char chunks |

### 2.12 `annas-archive-explorer` — keep, extend

| | |
|---|---|
| Script | `scripts/annas.py` (wraps existing `search_archive.py`, `get_book_details.py`, `session_manager.py` logic) |
| search | existing search with `--ext pdf|epub`, `--lang`; ItemRef `id = book:<md5>` |
| fetch | details by md5 (title, author, year, description, mirrors) → `metadata_only` content (description as one paragraph segment) |
| download | new subcommand `download <md5> [--mirror N]` → `data/books/<md5>.<ext>` → `document-reader fetch` |
| Session | DDoS-Guard clearance is now handled by the agent browser profile (remove separate `session_manager.py` storage once the browser path works) |
| notes | Downloading copyrighted books may be illegal in the user's jurisdiction; the skill downloads only on explicit `download` calls. |

### 2.13 `paper-code-explorer` — keep, align

| | |
|---|---|
| Script | `scripts/papers.py` |
| IDs | `arxiv:<id>` (no version suffix; version in `extra.version`) |
| search | arXiv API `http://export.arxiv.org/api/query?search_query=…` + HF Papers; `--has-code` filters to papers with repos |
| fetch | metadata + abstract (`metadata_only`) or `--pdf` → download → `document-reader` |
| trending | `trending [--limit] [--has-code]` (existing) |
| links | GitHub repo URLs → `links` (picked up by `github-explorer` via the queue) |

---

## 3. Priority 2 Skills

### 3.1 `discord-explorer` — new

| | |
|---|---|
| Script | `scripts/discord.py` |
| IDs | content `discord:<channel_id>:<YYYY-MM-DD>` (one content per channel per UTC day; threads: `discord:<thread_id>:<YYYY-MM-DD>`); source `discord:server:<guild_id>`, `discord:channel:<channel_id>` |
| Modes | `--mode user` (default): agent browser on discord.com with the imported session (token in localStorage). `--mode bot`: official Bot API with `DISCORD_BOT_TOKEN`, only for servers where the user added the bot (fully allowed by Discord). |
| ToS | Automating a user account violates Discord's terms ("self-bots") and can get the account banned. Use a secondary account, keep budgets low, read only. See SPEC §9 Q2. |
| Method (user mode) | open `https://discord.com/channels/<guild>/<channel>`; scroll up; capture the client's own REST responses `GET /api/v9/channels/<id>/messages?before=…&limit=50` with `capture_json`. The script never sends its own API requests with the token. |
| list | `list servers` → guild ids/names from the sidebar DOM; `list <guild_id>` → text, forum and announcement channels (DOM); `list <channel_id> --since D` → day windows available |
| search | in-app search UI per guild (`--guild`): type query, capture `/guilds/<id>/messages/search` responses |
| profile | user popout data for `<user_id>` when visible; mostly persons come from message authors |
| fetch | `fetch <channel_id> --since D [--until D] [--max-messages 2000]` → one ContentRecord per day window; `fetch <message_link>` → the day window containing it |
| segments | each message `kind=message`, `locator={message_id, reply_to?}`, author `{handle: username, platform_user_id: id}`; attachments → `media`; embeds' text appended |
| incremental | re-fetch appends new messages (01 §3.1) |
| visibility | persons created from Discord authors get `visibility='private_source'` unless also public elsewhere |

### 3.2 `telegram-explorer` — new

| | |
|---|---|
| Script | `scripts/telegram.py` |
| IDs | public channel posts: content `telegram:<channel>:<msg_id>`; groups/private chats (browser mode): `telegram:<chat_id>:<YYYY-MM-DD>`; source `telegram:channel:<name>` |
| Public mode (no login) | `https://t.me/s/<channel>` HTML preview; paginate with `?before=<msg_id>`; parse `.tgme_widget_message` (text, date, views, media, forwarded-from) |
| Browser mode | Telegram Web (`https://web.telegram.org/k/`) with imported localStorage session; DOM scroll; for groups and private channels |
| search | public: `https://t.me/s/<channel>?q=<q>`; global channel discovery via `web-searcher --site t.me` |
| profile | channel title, description, subscriber count from the preview header |
| segments | `kind=post|message`, `locator={msg_id}` |

### 3.3 `stackexchange-explorer` — new (covers Stack Overflow)

| | |
|---|---|
| Script | `scripts/stackexchange.py` |
| Sites | `--site` key: `quant` (Quantitative Finance), `money` (Personal Finance & Money), `stackoverflow`, `economics`, `stats` (Cross Validated), `datascience`; default `quant` |
| IDs | content `stackexchange:<site>:<question_id>`; source `stackexchange:site:<site>` / `stackexchange:user:<site>:<user_id>`; tag sources `stackexchange:tag:<site>:<tag>` |
| API | `https://api.stackexchange.com/2.3/…` with `site=<site>`, `filter=withbody`, optional `key=STACKEXCHANGE_KEY`; honour `backoff` and `quota_remaining` (stop at < 10) |
| search | `/search/advanced?q=<q>&sort=votes&order=desc&pagesize=<n>` (`--tagged`, `--accepted`) |
| profile | `/users/<id>` (+ `/users/<id>/top-answer-tags`) |
| list | `/questions?tagged=<tag>&sort=votes` or `/users/<id>/answers?sort=votes` |
| fetch | `/questions/<id>?filter=withbody` + `/questions/<id>/answers?filter=withbody&sort=votes&pagesize=100` + comments (`/posts/<ids>/comments?filter=withbody`, `--comments`) |
| segments | question `kind=question` `{post_id}`; answers `kind=answer` `{post_id, score, accepted}`; code blocks inside bodies kept as `code` segments `{post_id, block}`; HTML → markdown (markdownify) |
| persons | high-reputation answerers become persons only when they state knowledge (normal miner rules) |

### 3.4 `forum-explorer` — new (generic trading forums)

| | |
|---|---|
| Script | `scripts/forum.py` |
| Config | `config/forums.yaml`: `{host, name, engine, language, requires_session, notes}`; initial entries (engines to verify): `elitetrader.com` (xenforo), `forums.babypips.com` (discourse), `futures.io` (custom/generic), `forexfactory.com` (custom/generic, Cloudflare), `trade2win.com` (xenforo), `f319.com` (xenforo, vi) |
| IDs | content `forum:<host>:<thread_id>`; source `forum:board:<host>:<board_id>` / `forum:user:<host>:<user_id>` |
| detect | `detect <url>` → engine by `<meta name="generator">`, HTML markers (`data-template` XenForo, `discourse` meta, vBulletin/phpBB markers) |
| Engines | **discourse**: JSON — `/latest.json`, `/c/<slug>/<id>.json`, `/t/<id>.json` (+ `/t/<id>/posts.json?post_ids[]=…` for > 20 posts), `/search.json?q=`, `/u/<user>.json`. **xenforo**: HTML — `/forums/<slug>.<id>/page-N`, `/threads/<slug>.<id>/page-N`, posts `article.message` (`data-content="post-<id>"`, `data-author`), `.bbWrapper` body, quotes stripped into `extra`. **vbulletin/phpbb**: HTML selectors in `references/engines.md`. **generic**: `web-reader` per page + agent-guided pagination. |
| fetch | all pages of a thread (nothing ignored), cap `--max-pages 200` with warning |
| segments | each post `kind=post|reply`, `locator={post_id, page}`, author per post |
| Method | agent browser for every engine (Cloudflare-protected sites need it); Discourse JSON loaded through the browser too |

### 3.5 `tradingview-explorer` — new

| | |
|---|---|
| Script | `scripts/tradingview.py` |
| IDs | ideas `tradingview:idea:<id>`; scripts `tradingview:script:<id>`; source `tradingview:user:<username>` |
| search | `https://www.tradingview.com/ideas/search/<q>/` and scripts `https://www.tradingview.com/scripts/search/<q>/` (verify URLs), via browser |
| profile | `https://www.tradingview.com/u/<user>/` (bio, followers, reputation) |
| list | user ideas (`/u/<user>/#published-charts`), user scripts; symbol ideas `/symbols/<EXCH>-<SYM>/ideas/` |
| fetch idea | title, description text → paragraphs; symbol, timeframe, direction label (Long/Short) → `extra`; chart snapshot image URL → `media`; comments → `comment` segments |
| fetch script | description → paragraphs; open-source Pine code (when visible) → `code` segments split by ~60 lines `{line_start, line_end}`; protected/invite-only scripts → description only, `extra.code_visible=false` |
| content_type | `idea`, `script` |

### 3.6 `facebook-explorer` — new

| | |
|---|---|
| Script | `scripts/facebook.py` |
| Session | required (`facebook`). Strict budget. Recommend a secondary account. |
| IDs | content `facebook:<group_or_page_id>:<post_id>`; source `facebook:group:<id>`, `facebook:page:<id>` |
| search | `https://www.facebook.com/search/groups/?q=` and `/search/posts/?q=` via browser (DOM) |
| profile | group about (name, members, privacy, description) / page about |
| list | group/page feed: scroll, collect post permalinks (`/groups/<id>/posts/<post_id>/` or `/permalink/`) |
| fetch | open the permalink; capture GraphQL responses (`/api/graphql/`) where possible, DOM fallback; expand "See more" and up to `--max-comments 200` comments ("View more comments" clicks with pauses) |
| segments | post `kind=post`; comments `kind=comment` `{comment_id, parent_id?}`; video posts with speech → `--transcribe-video` uses yt-dlp with `cookies.txt` + Whisper |
| visibility | authors in private groups → `private_source` |

### 3.7 `rss-explorer` — new

| | |
|---|---|
| Script | `scripts/rss.py` |
| IDs | source `rss:feed:<sha1(feed_url)[:12]>`; items use `web:<sha1(canonical_url)[:16]>` (same id as `web-reader`, so content dedup is natural) |
| discover | `discover <site_url>` → `<link rel="alternate" type="application/rss+xml|atom+xml">`, common paths (`/feed`, `/rss`, `/atom.xml`, `/index.xml`) |
| list | feedparser; cursor = newest entry id seen |
| fetch | entry with full `content:encoded` → use it; else `web-reader fetch` on the link |
| Use | blogs, Ghost/WordPress/Beehiiv newsletters, news sites (CafeF, Vietstock, Reuters sections), YouTube channel feeds (`/feeds/videos.xml?channel_id=`) for cheap new-upload checks |

### 3.8 `sec-edgar-explorer` — new

| | |
|---|---|
| Script | `scripts/sec.py` |
| Requirement | `SEC_USER_AGENT` header (company/name + email) on every request; ≤ 10 req/s |
| IDs | content `sec:<accession_no>`; source `sec:cik:<cik10>` |
| search | full-text search `https://efts.sec.gov/LATEST/search-index?q="<q>"&forms=10-K,13F-HR` (verify) |
| profile | `https://data.sec.gov/submissions/CIK<cik10>.json` (name, tickers, filings index) |
| list | filings from submissions JSON (`--forms 10-K,10-Q,8-K,13F-HR,N-CSR`) |
| fetch | primary document HTML/TXT → paragraphs (`{section?, para}`); 13F: `informationTable` XML → `extra.holdings` + a generated paragraph per top-20 holding (quotable) |
| Use | fund manager persons: 13F holdings as `verified_records` evidence; fund letters (N-CSR) as knowledge; `evidence_level: audited` for filed numbers |

### 3.9 `research-explorer` — new

| | |
|---|---|
| Script | `scripts/research.py` |
| IDs | `paper:doi:<doi>` or `paper:openalex:<W…>`; arXiv papers keep `arxiv:<id>`; SSRN `paper:ssrn:<abstract_id>` |
| search | OpenAlex `https://api.openalex.org/works?search=<q>&filter=…&mailto=OPENALEX_MAILTO`; Semantic Scholar `https://api.semanticscholar.org/graph/v1/paper/search?query=<q>&fields=title,abstract,authors,year,openAccessPdf,externalIds`; `--ssrn` → SSRN search via browser |
| profile | author: OpenAlex `/authors/<id>` / S2 `/author/<id>` |
| fetch | metadata + abstract → `metadata_only`; `--pdf` when an open-access PDF exists → `document-reader` |
| Use | academic evidence for cards (`evidence_level: backtested` when a paper tests the claim) |

### 3.10 `github-explorer` — new

| | |
|---|---|
| Script | `scripts/github.py` |
| IDs | repo `github:<owner>/<repo>`; file `github:<owner>/<repo>:<path>@<sha7>` |
| API | `https://api.github.com` with optional `GITHUB_TOKEN`; honour `X-RateLimit-Remaining` / `Retry-After` |
| search | `/search/repositories?q=<q>+topic:algorithmic-trading&sort=stars` (`--topic`, `--language`) |
| profile | `/users/<user>` |
| list | `tree <repo>` → file list (`/git/trees/<branch>?recursive=1`) with sizes, for the agent to choose files |
| fetch | `fetch <repo>` → README as paragraphs; `fetch <repo>:<path>` → file as `code` segments (≤ 60 lines each) |
| Use | strategy logic in code → `setup`/`rule` cards (`evidence_level: claimed`, or `backtested` if the repo includes reproducible backtest results) |

### 3.11 `bluesky-explorer` — new

| | |
|---|---|
| Script | `scripts/bluesky.py` |
| IDs | content `bluesky:<did>:<rkey>`; source `bluesky:user:<handle>` |
| API | public AppView `https://public.api.bsky.app/xrpc/` — `app.bsky.actor.getProfile`, `app.bsky.feed.getAuthorFeed`, `app.bsky.feed.getPostThread`, `app.bsky.feed.searchPosts` (verify whether search needs auth; fallback: browser on `bsky.app/search`) |
| fetch | thread: author's self-replies as `post` segments, others as `reply` (cap 100) |

---

## 4. Priority 3 Skills

| Skill | Script | IDs | Method | Notes |
|---|---|---|---|---|
| `stocktwits-explorer` | `stocktwits.py` | `stocktwits:<message_id>`; source `stocktwits:symbol:<SYM>`, `stocktwits:user:<name>` | `https://api.stocktwits.com/api/2/streams/symbol/<SYM>.json` and `/streams/user/<name>.json` (verify public access; else browser) | High noise: content is stored per message; most yield no cards, which is expected |
| `tiktok-explorer` | `tiktok.py` | `tiktok:<video_id>`; source `tiktok:user:<handle>` | list via browser profile scroll; fetch via yt-dlp with `cookies.txt` → `audio-transcriber`; caption from description | Session optional |
| `instagram-explorer` | `instagram.py` | `instagram:<shortcode>`; source `instagram:user:<handle>` | browser (session required); reels via yt-dlp with `cookies.txt` → Whisper; captions + comments as segments | Strict budget |
| `threads-explorer` | `threads.py` | `threads:<post_id>`; source `threads:user:<handle>` | browser; capture GraphQL where possible | |
| `linkedin-explorer` | `linkedin.py` | `linkedin:<activity_urn>`; articles `linkedin:article:<slug>` | browser (session required); only profiles of known persons (`profile`, `list` their posts, `fetch` post/article) | Strictest budget; high ban risk |
| `seekingalpha-explorer` | `seekingalpha.py` | `seekingalpha:<article_id>`; source `seekingalpha:author:<slug>` | browser (session for premium); PerimeterX "Press & Hold" → exit 3 | Articles + comments |
| `hackernews-explorer` | `hackernews.py` | `hn:<item_id>` | Algolia `https://hn.algolia.com/api/v1/search?query=&tags=story` and `/items/<id>` (full comment tree) | No session |

---

## 5. Sources Not Covered (and why)

| Source | Reason | Workaround |
|---|---|---|
| Spotify-exclusive podcasts | DRM audio | none; record as blocked source |
| Zalo groups, WhatsApp groups | no web reader, closed apps | user exports chats to a file → `document-reader` (TXT) |
| Paid courses / Patreon videos | membership + DRM in many cases | if accessible in the browser with the user's session, `web-reader` + `audio-transcriber` on downloadable media |
| Email newsletters | inbox access | forward to a feed (Kill the Newsletter / Substack RSS) → `rss-explorer`, or save as files → `document-reader` |

---

## 6. Adding a New Platform (checklist for implementing agents)

1. Add the platform key to 00 §4 and to `config/platforms.yaml` (+ `budgets.yaml` if it needs its own budget).
2. Create `.agents/skills/<platform>-explorer/` from the template (§1.4) with a SKILL.md whose description contains the platform name and typical user phrases.
3. Implement the adapter: at least `fetch`; `list`/`search`/`profile` when the platform supports them.
4. Record fixtures and write tests (§1.3).
5. Add the skill to SPEC.md §5.2 and to this document.
6. Add a `source-explorer` dispatch rule (06 §1.3) mapping URL patterns to the new skill.
