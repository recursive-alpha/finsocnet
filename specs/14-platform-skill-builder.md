# 14 — Platform skill builder

Code: `finsocnet/adapters/site_recipe.py` (adapter), `site_tools.py` (probe, check, scaffold), skill `platform-skill-builder` (`scripts/site.py`). Config: `config/sites/<name>.yaml` (one recipe per custom platform).

## 1. Idea

"Add xyz.org" becomes: **probe → decide with the user → recipe → live check → scaffold**. A recipe declares where lists and texts are (CSS selectors, JSON paths or a feed); one generic adapter turns it into the standard platform contract (`search`, `profile`, `list`, `fetch`, `--ingest`, `--enqueue`, `--save-cursor`, `--new-only`, budgets, visited tracking). Hand-written adapters remain possible for sites a recipe cannot express (the skill says when and what changes).

## 2. Custom platforms in the core

A file `config/sites/<name>.yaml` makes `<name>` a known platform for: content ids (`ids.known_platforms`), ContentRecord validation (the `platform` enum became a pattern plus a runtime check), `finsocnet explore add` dispatch (`dispatch.custom_rules`: the recipe's `dispatch:` rules, then a catch-all for the domain), and skill/platform config (`config/platforms.yaml`, `config/budgets.yaml` blocks written by scaffold). Content ids may contain dashes in the platform part.

## 3. Recipe

See `.agents/skills/platform-skill-builder/references/recipe.md`. Required: `name`, `base_url`, `mode` (`http` | `browser` | `api` | `feed`) and at least one operation. Validation reports every problem at once with JSON paths (`VALIDATION_ERROR`).

## 4. Probe (plain HTTP, never logs in)

Reports reachability, bot wall, server, generator, text size, login form, JS-rendered hint, feeds (`<link rel=alternate>` and common paths), engines (forum engines via `forum.detect_engine`, WordPress/Discourse/Mastodon/Lemmy/Ghost JSON endpoints), candidate item selectors (repeating blocks), `robots.txt` as it applies to `User-agent: *` (grouped correctly; `blocks_everything`, `crawl_delay`, `content_signals`), the existing skill that `dispatch.classify` already routes the URL to, and a `strategy`: `existing` · `api` · `feed` · `http` · `browser` · `blocked`. **`blocked` (robots disallow everything) means: no scraper; ask the user.** Probe requests use their own budget (`probe`).

## 5. Check and scaffold

`site.py check <name> [--query Q] [--source S] [--item U] [--target T]` runs each defined operation against the live site and reports per operation: items found, with title / author / date, a sample, and `problems` (no items, no titles, little text from `fetch.body`, no title). `site.py scaffold <name> [--force]` writes `.agents/skills/<name>-explorer/{SKILL.md, scripts/<name>.py, references/platform_notes.md}` and appends `config/platforms.yaml` / `config/budgets.yaml` blocks; it refuses to overwrite (`CONFLICT`) without `--force` and never touches other files.

## 6. Acceptance

Fixture tests for html, api and feed modes, selector errors, check problems, custom platform in ids/dispatch/schema, scaffold output and conflict, probe (feeds, robots blocking). Live demonstration: probe → recipe → `check` → scaffold for `simonwillison.net` (Atom feed + page body), run in a scratch root; the verified recipe is shipped as `references/examples/blog-feed.yaml`. The probe of `lobste.rs` correctly reports `blocked`.
