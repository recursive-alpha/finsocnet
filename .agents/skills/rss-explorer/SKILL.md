---
name: rss-explorer
description: Follow any RSS or Atom feed — trader blogs, Ghost/WordPress/Beehiiv newsletters, news sites (CafeF, Vietstock, Reuters sections), YouTube channel feeds — discover a site's feeds, list new entries since the last check, and fetch full entries (from the feed or via web-reader) as FinSocNet content. Use for blogs and news sites, "follow this blog", cheap new-upload checks, or forwarding email newsletters through a feed.
license: MIT
compatibility: FinSocNet repository with feedparser; web-reader for entries without full content.
metadata:
  author: finsocnet
  version: "2.0.0"
  priority: "P2"
  status: ready
  phase: "6"
  spec: specs/05-platform-skills.md
---

# RSS Explorer

Items share ids with web-reader (`web:<sha1(url)>`), so the same article found twice is the same content.

## When to use

- Blog/news/newsletter sites with feeds; source refresh of many sites.

## Before you start

- None.

## Commands

```bash
S=.agents/skills/rss-explorer/scripts/rss.py
uv run $S profile <site url|feed url> [--ingest]
uv run $S list <feed url> [--limit 100] [--save-cursor] [--enqueue]
uv run $S fetch <entry url> [--ingest]
```

| Command | Returns |
|---|---|
| `profile <site url|feed url>` | feed title, link, description (runs discovery when given a site) |
| `list <feed url>` | entries newest first |
| `fetch <entry url>` | full content from the feed, else web-reader |

Common flags (specs/00-conventions.md §3): `--ingest --run R` stores the record (writes require a run id); `--enqueue --run R` adds unseen items to the explore queue; `--save-cursor` stores the paging position in `sources.cursor_json` so the next `list` continues where it stopped; `--cursor C` overrides it. Output is always the JSON envelope `{ok, command, data, warnings, meta}`.

Implements only `list,fetch,profile` of the adapter contract; other subcommands exit 2 `UNSUPPORTED`.

## Procedure

1. `uv run finsocnet kb run start --skill rss-explorer --goal "<goal>" --harness <h> --model <m>` → `R`. If a parent skill (source-explorer, knowledge-search) already started a run, reuse its `R`.
2. Site: `profile <site> --ingest` (finds the feed) → `list --enqueue --save-cursor --run R`.
3. Read `warnings` in every envelope (`truncated`, `cap_reached`, `partial`) and pass them on to the user or the queue item; nothing is dropped silently.
4. `uv run finsocnet kb run end --run R --outcome success|partial|failed --stats '{…}'` when you started the run.

## Stored as

| Field | Value |
|---|---|
| source id | `rss:feed:<sha1(feed_url)[:12]>` |
| content id | `web:<sha1(canonical_url)[:16]>` |
| content_type | `article` |

## Errors

| Exit · code | Do |
|---|---|
| 2 `USAGE` / `RUN_REQUIRED` / `UNSUPPORTED` | fix the call; writes need `--run R` |
| 4 `RATE_LIMITED` / `BUDGET_EXHAUSTED` | stop this platform; queue item → `deferred` with `retry_after_sec` |
| 5 `NOT_FOUND` / `GONE` | queue item → `failed`; already stored content stays (status `gone`) |
| 1 `INTERNAL` | `kb lesson add --skill rss-explorer --kind script_bug …` with the error, then report |

## Notes

- Discovery: `<link rel=alternate type=application/rss+xml|atom+xml>`, `/feed`, `/rss`, `/atom.xml`, `/index.xml`.

## References

- `references/platform_notes.md` — endpoints, selectors and open items to verify; record platform changes here.
