---
name: web-reader
description: Read any web page through the agent browser (JavaScript rendered, with the user's sessions) and extract clean article text, tables and comments; discover a site's RSS feeds, outbound links, PDFs and embedded videos or caption tracks; take screenshots. Use for any URL no specialised platform skill handles — blogs, personal trader sites, news, course pages — or to inspect a page for media.
license: MIT
compatibility: FinSocNet repository, agent-browser running, trafilatura.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P1"
  status: ready
  phase: "4"
  spec: docs/spec/05-platform-skills.md
---

# Web Reader

The fallback reader. Attaches to the agent browser (never launches its own Chromium), extracts with trafilatura, and hands PDFs to `document-reader`.

## When to use

- Any URL without a dedicated platform skill (see source-explorer dispatch).
- "Read this page", "what's on this site", "find the videos/feeds on this site".

## Before you start

- Agent browser running.

## Commands

```bash
S=.agents/skills/web-reader/scripts/web.py
uv run $S fetch <url> [--screenshot PATH] [--ingest]
uv run $S discover <url>
uv run $S (inspect_media.py) <url>
```

| Command | Returns |
|---|---|
| `fetch <url>` | ContentRecord (paragraphs); PDFs delegated to document-reader |
| `discover <url>` | ItemRefs: RSS/Atom feeds, sitemap, outbound links, PDFs, embedded YouTube/Vimeo, `<video>`, `.vtt/.srt` tracks |
| `(inspect_media.py) <url>` | embedded media and caption tracks (former inspect_video.py) |

Common flags (docs/spec/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

## Procedure

1. `uv run finsocnet kb run start --skill web-reader --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. Unknown site: `discover` first → enqueue feeds (rss-explorer), videos (youtube/audio), PDFs (document-reader) → `fetch --ingest --run R` the page itself.
3. Short extraction (< 200 chars) → the DOM fallback runs automatically; if still empty, take a screenshot and look at it.
4. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
5. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| content id | `web:<sha1(canonical_url)[:16]>` |
| source id | `web:site:<host>` |
| content_type | `page` |
| segments | paragraphs `{para}`; tables as text; page comments as `comment` |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 3 `LOGIN_REQUIRED` / `CHECKPOINT` | follow session-bridge *exit code 3*; for optional sessions continue with public data and say what was not readable |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 7 `BROWSER_UNAVAILABLE` | `agent_browser.py start`, retry once |
| 1 `INTERNAL` | `kb lesson add --skill web-reader --kind script_bug …` with the error, then report |

## Notes

- Canonical URL removes tracking params (`utm_*`, `fbclid`, `gclid`, …) — see docs/spec/00 §4.

## Legacy commands (v1 names; thin wrappers until Phase 8)

```bash
uv run .agents/skills/web-reader/scripts/read_page.py "<url>" [--screenshot data/screenshots/x.png]
uv run .agents/skills/web-reader/scripts/inspect_video.py "<url>"
```

The v1 names call the v2 adapter (`--ingest-db` maps to `--ingest`); use the new subcommands in new work.

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
