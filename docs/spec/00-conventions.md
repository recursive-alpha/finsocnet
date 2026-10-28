# 00 — Conventions

Applies to every file in the repository. Read before writing any code.

---

## 1. Repository Layout (target)

```
finsocnet/                              # Python package (installed by `uv run`, editable)
  __init__.py
  cli.py                                # `finsocnet` entry point: kb, eval, session, explore, install, tui
  tui.py
  installer.py
  core/                                 # shared library — the ONLY code that touches the DB
    __init__.py
    config.py                           # env loading, paths (§6)
    db.py                               # connect(), transaction(), backup()
    migrations.py                       # runner for .sql and .py migrations (moved from finsocnet/migrations.py)
    output.py                           # envelope, emit(), fail(), exit codes (§3)
    ids.py                              # id builders and parsers (§4)
    normalize.py                        # text normalization, content_hash, quote matching (§5)
    records.py                          # ContentRecord, Segment, ItemRef, ProfileRecord dataclasses + validation (§7)
    content.py                          # add_content(), get_content(), chunks(), set_done()
    cards.py                            # validate_card(), candidates(), commit_decision(), search_cards()
    fts.py                              # FTS query building, sanitizing, RRF (03 §2)
    vocab.py                            # lookup(), add(), merge()
    persons.py                          # candidates(), upsert(), link_appearance(), aliases
    person_skills.py                    # upsert_skill(), render()
    queue.py                            # explore_queue, knowledge_gaps
    skill_install.py                    # skill-installer: resolve, fetch, scan, verify review, install, lock (07 §5)
    runs.py                             # agent_runs, lessons, feedback
    browser.py                          # attach(), new_page(), checkpoint check (04)
    budgets.py                          # budget accounting (04 §6)
    http.py                             # httpx client: retries, backoff, UA, proxy
    platform.py                         # PlatformAdapter protocol + run_platform_cli() (05 §1)
    sessions/                           # session-bridge internals (04)
      export_local.py  bundle.py  import_remote.py  formats.py  probes.py
    schemas/                            # JSON Schemas (draft 2020-12)
      content_record.schema.json
      card.schema.json
      query_card.schema.json
      decision.schema.json
      person.schema.json
      person_skill.schema.json
      eval_case.schema.json
      skill_review.schema.json
    kb_cli.py                           # `finsocnet kb …` (01 §6)
    eval_cli.py                         # `finsocnet eval …` (06)
.agents/skills/<skill>/
  SKILL.md
  scripts/<name>.py                     # thin: parse args, call finsocnet.core, emit envelope
  references/*.md|json                  # instructions, few-shot examples, seeds
config/
  platforms.yaml                        # per-platform domains, login probes, checkpoint patterns (04)
  budgets.yaml                          # per-platform rate budgets (04)
  forums.yaml                           # known forums and engines (05)
  skills.lock.json                      # third-party skills installed by skill-installer (07 §5); core skills are not listed
migrations/
  001_initial_schema.sql  002_add_skill_classification.sql  003_v2_schema.py  004_…
evals/
  transform/  dedup/  search/  attribution/   # golden cases (06)
tests/
  unit/  integration/  fixtures/<platform>/   # offline fixtures (HTML/JSON recorded responses)
docs/spec/                              # this spec
data/                                   # gitignored runtime data (§8)
```

Rules:
- Skill scripts never import each other via `sys.path` hacks. They import `finsocnet.core`. Existing `sys.path.insert` code is removed when a script is refactored.
- One concept, one module. Do not duplicate DB, envelope, ID or browser code inside skill scripts.

---

## 2. Python Conventions

- Python ≥ 3.11, run everything with `uv run`. Dependencies in `pyproject.toml`; optional groups: `local` (session export on the user's machine: `rookiepy`, `ccl_chromium_reader`), `ocr` (`ocrmypdf`), `dev` (`pytest`, `pytest-recording` or `respx`).
- Required dependencies after v2: `yt-dlp`, `youtube-transcript-api`, `faster-whisper`, `playwright` (CDP client only), `httpx`, `jsonschema`, `pyyaml`, `python-dotenv`, `ddgs`, `feedparser`, `trafilatura`, `markdownify`, `pymupdf`, `ebooklib`, `python-docx`, `pyrage`, `textual`, `prompt-toolkit`.
- Removed: `chromadb`, `sentence-transformers`, `duckduckgo-search`.
- `from __future__ import annotations` at the top of every module; type hints on public functions; dataclasses for records.
- Logging goes to **stderr** (`logging`, level from `FINSOCNET_LOG_LEVEL`, default `INFO`). Stdout is reserved for the envelope.
- Time: store UTC ISO-8601 strings with `Z` (`2026-10-28T09:15:00Z`). Use `datetime.now(timezone.utc)`.
- Paths: `pathlib.Path`, resolved relative to the repo root from `config.REPO_ROOT`, never relative to the current directory.
- Never `print()` secrets; `finsocnet.core.sessions` exposes only redacted views.

---

## 3. Script Contract

### 3.1 Invocation

```
uv run .agents/skills/<skill>/scripts/<name>.py <subcommand> [args] [--format json|text] [--run <run_id>]
uv run finsocnet kb <group> <command> [args]
```

- Default `--format json`. `text` is for humans and may be a table; it is never parsed by agents.
- `--run <run_id>` (or env `FINSOCNET_RUN_ID`) is **required** for every command that writes to the DB. Missing → exit 2, code `RUN_REQUIRED`.
- Input files: `--file path.json` or `-` for stdin.

### 3.2 Envelope (stdout, exactly one JSON object)

Success:
```json
{
  "ok": true,
  "command": "reddit.fetch",
  "data": { },
  "warnings": ["comment cap 500 reached; 132 comments not fetched"],
  "meta": {"elapsed_ms": 1840, "run_id": 17, "budget": {"platform": "reddit", "remaining_hour": 112}}
}
```

Failure:
```json
{
  "ok": false,
  "command": "x.fetch",
  "error": {
    "code": "LOGIN_REQUIRED",
    "message": "x.com redirected to /i/flow/login",
    "hint": "Re-export your local session: finsocnet session export … && finsocnet session push …",
    "retry_after_sec": null
  },
  "warnings": [],
  "meta": {"elapsed_ms": 920}
}
```

Implement with `finsocnet.core.output.emit(command, data, warnings)` and `fail(command, code, message, hint=None, retry_after_sec=None)`; `fail` exits with the mapped code.

### 3.3 Exit codes and error codes

| Exit | Error codes | Meaning | Agent action |
|---|---|---|---|
| 0 | — | success | continue |
| 1 | `INTERNAL` | unexpected exception (traceback on stderr) | log lesson `script_bug`, skip item |
| 2 | `USAGE`, `RUN_REQUIRED`, `UNSUPPORTED` | bad arguments / subcommand not supported by this platform | fix the call |
| 3 | `LOGIN_REQUIRED`, `CHECKPOINT` | session missing/expired, CAPTCHA, security checkpoint | follow re-export protocol (04 §5), stop this platform |
| 4 | `RATE_LIMITED`, `BUDGET_EXHAUSTED` | remote rate limit or local budget used up | requeue with `retry_after_sec` |
| 5 | `NOT_FOUND`, `GONE` | item deleted/private | mark item failed with reason |
| 6 | `VALIDATION_ERROR`, `VOCAB_UNKNOWN`, `QUOTE_NOT_FOUND`, `GRAMMAR_ERROR`, `REVIEW_INCOMPLETE` | agent JSON failed validation | fix the JSON and retry |
| 6 | `SKILL_INVALID`, `BLOCKED` | staged skill fails the agentskills.io format or a block rule (07 §5) | report; not installable |
| 7 | `BROWSER_UNAVAILABLE` | agent Chrome not running / CDP unreachable | run `agent_browser.py start` |
| 8 | `CONFLICT` | target card merged/retired since candidates were fetched; or skill name already taken | re-run candidates; or install under another name |

Validation errors list every problem at once in `error.details`: `[{"path": "/terms/2", "problem": "unknown term 'ema10'", "suggestion": "ema_10"}]`.

---

## 4. Identifier Formats

All IDs are strings unless noted. Builders live in `finsocnet.core.ids`; never hand-format IDs.

| Entity | Format | Examples |
|---|---|---|
| Content | `<platform>:<native_id>` | `youtube:B1ALxAVtFfI`, `reddit:1xg9xq1`, `x:1851234567890123456`, `substack:example:139876543`, `stackexchange:quant:12345`, `forum:elitetrader.com:385123`, `discord:1100000000000000000:2026-10-27`, `book:<md5>`, `arxiv:2401.01234`, `web:<sha1(canonical_url)[:16]>`, `file:<sha256[:16]>` |
| Source | `<platform>:<kind>:<native>` | `youtube:channel:UCxxxx`, `x:user:qullamaggie`, `reddit:subreddit:realdaytrading`, `discord:channel:1100…`, `rss:feed:<sha1(url)[:12]>`, `web:site:example.com` |
| Person | lowercase ASCII slug of canonical name; collisions get `-2`, `-3` | `lance-breitstein`, `tom-dante` |
| Handle-only person | `<platform>-<handle-slug>` | `reddit-example-dt` |
| Card | integer autoincrement | `41` |
| Run | integer autoincrement | `17` |
| Bundle | `b-<UTC yyyymmddHHMMSS>-<4 hex>` | `b-20261028091500-a1f3` |

Rules:
- Platform keys (lowercase): `youtube, podcast, x, reddit, medium, substack, web, google, file, book, arxiv, paper, discord, telegram, stackexchange, forum, tradingview, facebook, rss, sec, github, bluesky, stocktwits, tiktok, instagram, threads, linkedin, seekingalpha, hackernews`.
- Subreddit, X handle, host names: lowercase in IDs; original casing is kept in `title`/`handle` fields.
- Canonical URL for `web:` ids: lowercase scheme+host, remove fragment, remove tracking params (`utm_*`, `fbclid`, `gclid`, `ref`, `ref_src`, `s` on x.com), remove trailing slash except root.

---

## 5. Text Normalization

`finsocnet.core.normalize`:

| Function | Behaviour | Used for |
|---|---|---|
| `clean_text(s)` | Unicode NFC, strip control chars, unify line endings, collapse >2 blank lines | storing segment text |
| `hash_text(s)` | `sha256` of: NFKC → casefold → remove all chars except letters/digits/space → collapse whitespace | `contents.content_hash` |
| `quote_key(s)` | NFKC → casefold → remove diacritics → remove all except letters/digits → collapse spaces | quote matching |
| `quote_in(quote, text)` | `quote_key(quote) in quote_key(text)` | `QUOTE_NOT_FOUND` check |

The quote check accepts punctuation and case differences (auto-captions have no punctuation) but not changed words.

---

## 6. Environment (`.env`)

| Key | Default | Notes |
|---|---|---|
| `KNOWLEDGE_DB_PATH` | `data/knowledge.db` | |
| `FINSOCNET_LOG_LEVEL` | `INFO` | |
| `FINSOCNET_RUN_ID` | — | alternative to `--run` |
| `WHISPER_MODEL` | `openai/whisper-large-v3-turbo` | |
| `WHISPER_DEVICE` | `auto` | |
| `WHISPER_COMPUTE_TYPE` | `int8` | |
| `CDP_URL` | `http://127.0.0.1:9222` | agent Chrome |
| `BROWSER_PROFILE_DIR` | `data/browser-profile` | |
| `CHROME_BIN` | auto-detect | `google-chrome`, `chromium`, `brave-browser` |
| `XVFB_DISPLAY` | `:99` | used when `DISPLAY` is unset |
| `FINSOCNET_PROXY` | — | e.g. `socks5://127.0.0.1:1080` |
| `AGE_IDENTITY_FILE` | `~/.config/finsocnet/age_identity.txt` | remote host private key, outside repo |
| `SEC_USER_AGENT` | — | required by `sec-edgar-explorer` |
| `STACKEXCHANGE_KEY`, `GITHUB_TOKEN`, `OPENALEX_MAILTO` | — | optional rate-limit keys |

Removed: `X_AUTH_TOKEN`, `X_USERNAME`, `X_PASSWORD`, `X_SESSION_FILE`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`, `REDDIT_SESSION_FILE`, `MEDIUM_SID`, `MEDIUM_UID`, `MEDIUM_SESSION_FILE`, `CHROMA_PERSIST_DIR`, `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `HEADLESS_BROWSER`.

---

## 7. Shared Record Schemas

JSON Schemas live in `finsocnet/core/schemas/`. The shapes below are normative.

### 7.1 `ContentRecord` (output of every platform `fetch`, input of `kb content add`)

```json
{
  "id": "reddit:1xg9xq1",
  "platform": "reddit",
  "content_type": "thread",
  "source": {"id": "reddit:subreddit:realdaytrading", "kind": "subreddit", "title": "r/RealDayTrading", "url": "https://www.reddit.com/r/RealDayTrading/"},
  "url": "https://www.reddit.com/r/RealDayTrading/comments/1xg9xq1/…/",
  "title": "How I size positions after a losing streak",
  "author": {"handle": "u/example_dt", "display_name": null, "platform_user_id": "t2_abc", "profile_url": "https://www.reddit.com/user/example_dt"},
  "published_at": "2026-09-14T13:02:11Z",
  "language": "en",
  "description": null,
  "segments": [
    {"seq": 0, "kind": "post",    "locator": {"comment_id": "t3_1xg9xq1"}, "author": {"handle": "u/example_dt"}, "text": "…"},
    {"seq": 1, "kind": "comment", "locator": {"comment_id": "t1_k1", "parent_id": "t3_1xg9xq1", "score": 87}, "author": {"handle": "u/other"}, "text": "…"}
  ],
  "metrics": {"score": 412, "comments": 96, "views": null, "likes": null},
  "links": ["https://example.com/sizing.pdf"],
  "mentions": ["u/someone", "$SPY", "@handle"],
  "media": [{"kind": "image", "url": "https://i.redd.it/…"}],
  "parent_content_id": null,
  "raw_path": "data/raw/reddit/1xg9xq1.json",
  "fetched_at": "2026-10-28T09:15:00Z",
  "fetch_method": "json_endpoint",
  "extra": {}
}
```

Rules:
- `segments` are ordered, `seq` starts at 0 and is contiguous. Each segment is a **quotable unit**: a transcript window (≤ 45 s or ≤ 600 chars), a post, a comment, a message, a paragraph, a page.
- Segment `kind`: `transcript, post, comment, reply, message, paragraph, page, code, caption, answer, question`.
- Segment `locator` by kind: transcript `{start_sec, end_sec}`; comment/message `{comment_id|message_id, parent_id?}`; page `{page}`; paragraph `{chapter?, para}`; code `{path?, line_start, line_end}`.
- `author` on a segment overrides the content author (threads, chats).
- `speaker_hint` (optional, transcripts): e.g. `"SPEAKER_0"` from diarization; null otherwise.
- `raw_path`: the original API/HTML/transcript response saved under `data/raw/<platform>/`, so content can be re-parsed without re-fetching.
- `extra`: platform-specific fields that have no column (e.g. TradingView symbol, 13F period).

### 7.2 `ItemRef` (output of `search` and `list`)

```json
{"ref": "https://www.reddit.com/r/…/comments/1xg9xq1/", "id": "reddit:1xg9xq1", "kind": "thread",
 "title": "…", "author_handle": "u/example_dt", "published_at": "2026-09-14T13:02:11Z",
 "snippet": "first 300 chars…", "metrics": {"score": 412}, "known": false}
```
`known` is true when `id` already exists in `contents` (scripts check this so the agent can skip).

`list` returns `{"items": [ItemRef…], "next_cursor": "t3_abc" | null, "source": {…}}`.

### 7.3 `ProfileRecord` (output of `profile`)

```json
{"platform": "x", "source_id": "x:user:example", "handle": "@example", "display_name": "Example Trader",
 "bio": "…", "links": ["https://youtube.com/@example"], "followers": 120000, "verified": true,
 "avatar_url": "…", "profile_url": "https://x.com/example", "location": null, "joined_at": "2015-03-01",
 "known_person_id": "example-trader" }
```
`known_person_id` is filled when `person_aliases` already maps this handle.

---

## 8. Data Directory (`data/`, gitignored)

```
data/
  knowledge.db (+ -wal, -shm)
  backups/knowledge-<UTC>.db
  raw/<platform>/…              # original responses
  audio/                        # downloaded audio (cache, may be pruned)
  transcripts/                  # Whisper outputs
  books/  papers/               # downloaded documents
  inbox/documents/              # user drop folder for documents (document-reader watches)
  sessions/
    inbox/                      # pushed bundles / dropped cookie folders (deleted after import)
    store.age                   # encrypted normalized cookies + localStorage (re-applied on browser start)
    cookies.txt                 # Netscape format for yt-dlp (chmod 600, regenerated on import)
    storage/<platform>.json     # Playwright storage_state for legacy needs (chmod 600)
  browser-profile/              # agent Chrome user-data-dir
  work/<run_id>/                # agent work files: chunk inputs, cards, decisions (kept for audit)
  screenshots/
  skill-staging/<staging_id>/   # quarantined skill downloads; never executed; pruned after 7 days (07 §5)
  skill-backups/<name>-<UTC>/   # replaced or removed installed skills
```

`.gitignore` must include `data/` entirely except `data/.gitkeep`. Remove the current per-subfolder rules. (`data/rebuild_all_person_skills.py` was already moved to `legacy/scripts/`; it is deleted in Phase 2.)

---

## 9. SKILL.md Template

```markdown
---
name: <skill-name>                      # = directory name, lowercase-hyphen
description: <≤1024 chars: what it does AND when to use it, with trigger words>
license: MIT
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
---

# <Title>

## When to use
- bullet triggers

## Prerequisites
- e.g. agent browser running (`agent_browser.py status`), session for <domain> (`session_bridge.py status`)

## Commands
| Command | What it returns |
|---|---|
| `uv run .agents/skills/<skill>/scripts/<name>.py search "<q>" --limit 20` | ItemRef[] |

## Procedure
1. numbered steps the agent follows, including which kb commands to call and when to stop

## Output handling
- what to do with each error code

## References
- references/<file>.md — purpose
```

Rules: the description must contain the trigger words a user would type ("Discord", "server", "channel", …). Procedures are imperative and numbered. Every command shown must exist and be covered by a test.

---

## 10. Testing

- `uv run pytest` runs offline tests only (default marker expression `not live`).
- Every platform adapter has fixture tests: recorded HTML/JSON in `tests/fixtures/<platform>/` → parsed `ContentRecord` compared to an expected JSON file.
- Every `kb` command has an integration test against a temp DB created by running all migrations.
- Secret-leak test: import a fake bundle with known cookie values, run `session_bridge.py import/status`, assert none of the values appear in stdout, stderr, the DB file, or `data/work/`.
- Migration test: copy of a fixture legacy DB (built from current schema, see 01 §5) → run migrations → assert row mappings.
- Live tests (`@pytest.mark.live`) hit real platforms; run manually with `uv run pytest -m live -k <platform>`.
