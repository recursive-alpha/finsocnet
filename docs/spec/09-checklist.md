# 09 — Status Checklist (done / missing)

> **Last checked:** 2026-10-28, branch `v2/phase-0-foundation` (Phase 0 done; Phases 1–8 not started).
> **Who updates it:** the implementing agent ticks items at the end of each phase (same branch as the phase) and updates the date; the reviewer checks the ticks against the acceptance tests in `08-phases.md`.
> Legend: `[x]` done and verified · `[~]` partly done (note says what is left) · `[ ]` missing.

## Summary

| Phase | Spec | SKILL.md + references | Code | Tests / acceptance |
|---|---|---|---|---|
| 0 Foundation and cleanup | [x] | [x] knowledge-db | [x] | [~] 30 tests green; migration 003 run on a copy, real DB awaiting your approval |
| 1 Knowledge core | [x] | [x] transformer, dedup, search, miner | [ ] | [ ] |
| 2 Persons and legacy conversion | [x] | [x] matcher, synthesizer, explorer | [~] v1 `match_person.py` only | [ ] |
| 3 Agent browser and session bridge | [x] | [x] agent-browser, session-bridge | [ ] | [ ] |
| 4 P1 platform skills (15) | [x] | [x] all 15 | [~] v1 scripts in 9 skills | [ ] |
| 5 Explore, self-improve, eval, skill installer | [x] | [x] source-explorer, self-improver, skill-installer | [ ] | [ ] |
| 6 P2 platform skills (11) | [x] | [x] all 11 | [ ] | [ ] |
| 7 P3 platform skills (7) | [x] | [x] all 7 | [ ] | [ ] |
| 8 Harness integration and docs | [x] | [x] finsocnet | [~] v1 installer and commands | [ ] |

Bottom line: the **spec and every skill's instructions are written** (45 skills); **Phase 0 code exists** (`finsocnet/core`, `kb` admin/run/lesson/feedback/source/content, migration 003). Phases 1–8 are not implemented. The real `data/knowledge.db` is still on the v1 schema (migration waits for your approval); v1 platform scripts still run except their `--ingest-db` paths, which called the removed `knowledge-db/scripts/db.py` and return in Phase 4.

---

## 1. Done

### 1.1 Specification
- [x] `SPEC.md`: goals, principles P1–P10, ADR-001…008 (incl. why SQLite only, no Chroma), never-do / always-do rules, skill inventory, architecture, config, open questions.
- [x] `docs/spec/00`–`08`: conventions, database DDL + migration 003 mapping + `kb` CLI, Knowledge Cards, pipelines, sessions and browser, platform skills, explore/improve/eval, harness integration + skill installer, phases.
- [x] Spec self-checks: claim-grammar regex fixed (non-greedy `THEN`) and verified on all examples; example cards validate against grammar and vocabulary.

### 1.2 Skills (`.agents/skills/`, 45 folders, every SKILL.md has valid frontmatter, name = folder, description ≤ 1024 chars, all referenced files exist)
- [x] Core: `knowledge-db`, `knowledge-transformer`, `knowledge-dedup`, `knowledge-search`, `market-idea-miner`, `person-matcher`, `person-skill-synthesizer`, `person-skills-explorer`, `session-bridge`, `agent-browser`, `source-explorer`, `self-improver`, `skill-installer`, `finsocnet`.
- [x] Platform P1 (15): `youtube-extractor`, `audio-transcriber`, `podcast-explorer`, `x-explorer`, `reddit-explorer`, `medium-explorer`, `substack-explorer`, `web-searcher`, `google-searcher`, `web-reader`, `document-reader`, `annas-archive-explorer`, `paper-code-explorer` (+ v1 skills rewritten with a *Legacy commands* section).
- [x] Platform P2 (11): `discord-explorer`, `telegram-explorer`, `stackexchange-explorer`, `forum-explorer`, `tradingview-explorer`, `facebook-explorer`, `rss-explorer`, `sec-edgar-explorer`, `research-explorer`, `github-explorer`, `bluesky-explorer`.
- [x] Platform P3 (7): `stocktwits-explorer`, `tiktok-explorer`, `instagram-explorer`, `threads-explorer`, `linkedin-explorer`, `seekingalpha-explorer`, `hackernews-explorer`.
- [x] References: `knowledge-transformer/references/{card_format, claim_grammar, examples (E1–E16), query_examples (Q1–Q9), vocabulary_seed.json (344 terms, validated)}`; `knowledge-dedup/references/decision_examples.md` (D1–D12); `source-explorer/references/dispatch.md`; `skill-installer/references/{link_formats, review_checklist}.md`; `references/platform_notes.md` in all 31 platform skills.

### 1.3 Cleanup
- [x] 9 person rulebook folders moved to `legacy/person-skills/` (not deleted: they had uncommitted edits).
- [x] `hypothesis-miner`, `user-skill-synthesizer`, `skill-curator`, `skill-explorer` moved to `legacy/meta-skills/`.
- [x] `scripts/{batch_pipeline, deep_crawl, rebuild_skills_data}.py`, `data/rebuild_all_person_skills.py`, old guides and v1 schema docs moved to `legacy/`; `legacy/README.md` explains each.
- [x] `finsocnet strategy <name>` reads `legacy/person-skills/` (verified: `uv run finsocnet strategy dante`).

### 1.4 v1 that still runs (verified 2026-10-28 unless noted)
- [x] `uv run finsocnet stats`, `strategy`, `skills` (but see 2.0 #3), `match_person.py list`.
- [~] v1 platform scripts present, not re-run in this review: `youtube-extractor` (2), `audio-transcriber` (2), `x-explorer` (3), `reddit-explorer` (4), `medium-explorer` (4), `web-searcher` (1), `web-reader` (2), `annas-archive-explorer` (3), `paper-code-explorer` (3).
- [x] Data in `data/knowledge.db` (v1 schema, migrations 001–002): contents 5636, users 22, hypotheses 66, skills 22, persons 9, person_appearances 18; `data/transcripts/` 16 files. No `data/chroma_db/`.

---

## 2. Missing

### 2.0 Known problems in the current tree (fix in the phase shown)
1. [x] **Vector code removed** (ADR-001): `finsocnet/search.py`, `knowledge-db/scripts/{db.py, vector_store.py, ingest_idea.py}`, `scripts/embed_server.py` deleted in Phase 0 (the tree was clean, so no uncommitted work was lost; they stay in git history). Side effect: the v1 `search`/`rag` CLI commands and the TUI's semantic search are gone, and `--ingest-db` in 6 v1 platform scripts is broken until Phase 4.
2. [x] **`pyproject.toml`** v2 dependencies; `chromadb`, `sentence-transformers`, `duckduckgo-search` removed; groups `local`, `ocr`, `dev`. `ccl_chromium_reader` is not on PyPI and is left out of `local` (decide in Phase 3, 04 §9).
3. [ ] **`finsocnet skills` misclassifies** new core skills (agent-browser, discord-explorer, …) as `IMPROVED`, because `finsocnet/skills.py` `SYSTEM_SKILL_NAMES` is the v1 list — Phase 5 task 6 (core vs installed).
4. [ ] **38 `chromium.launch` / `new_context(` calls** in v1 skill scripts (ADR-006) — Phase 4.
5. [ ] **Password login scripts** `login_x.py`, `login_reddit.py`, `login_medium.py` still present (ADR-005) — Phase 3/4. Still the only v1 login path, so they stay until session-bridge works.
6. [ ] **Stale docs**: `README.md`, `AGENTS.md` (Chroma, hypothesis-miner, password login, `vector-search`/`rag-search`), `commands/claude/finsocnet.md` — Phase 8.
7. [ ] **v1 CLI commands to remove**: `search` (vector), `rag`, `view`, `list` (hypotheses) — Phase 8 (07 §1).
8. [x] **`.gitignore`** ignores all of `data/` except `.gitkeep`. Files already tracked under `data/` (channels, hypotheses, persons, reddit) stay tracked; untrack them with `git rm --cached` if you want them out of the repo.
9. [x] Spec paths for legacy files fixed: 08 Phase 2 task 4 and 00 §8 now point to `legacy/`.

### 2.1 Phase 0 — Foundation
- [x] `finsocnet/core/`: `config`, `db`, `output`, `ids`, `normalize`, `records`, `migrations`, `runs`, plus `content`, `fts`, `kb_cli`.
- [x] JSON Schemas: `content_record`, `card`, `query_card`, `decision`, `person`, `person_skill`, `eval_case` (`skill_review` comes with Phase 5).
- [x] `migrations/003_v2_schema.sql` + `003_v2_schema.py`.
- [x] `kb` admin and content commands (`init, migrate, backup, doctor [--repair-fts], stats, prune, run, lesson, feedback, source, content …`).
- [x] `pyproject.toml` deps + optional groups.
- [x] `.env.example` (00 §6), `.gitignore`.
- [x] `tests/`: v1 fixture DB generator, two transcript fixtures, migration, content, envelope, schema and normalization tests (30).
- [~] Migration 003 run on a **copy** of `data/knowledge.db` (result below); **the real DB is not migrated** until you approve.

Migration 003 on the copy of the real DB (2026-10-28): 9 persons, 19 sources (2 `needs_review`: `youtube:handle:lewiskelly8`, `x:user:x_trader`), 5636 contents (27 `new`, 5600 `metadata_only`, 9 `needs_review`: 3 books with non-md5 ids, 5 arXiv stubs, 1 X stub), 404 transcript/paragraph segments, 18 appearances, 15 aliases, `legacy_hypotheses` and `legacy_skills` kept. `kb doctor` OK. 57 foreign-key orphans exist in `legacy_hypotheses`/`legacy_skills` before the migration (their `user_id` holds person ids); they are left untouched and go away with the legacy tables in Phase 2.

Deviations to review: (a) the runner ignores FK violations in `legacy_*` tables because of those orphans; (b) a brand-new database gets no pre-migration backups; (c) `kb content claim` stores its claim in `contents.extra_json._claim` (no column exists) and has a `--reprocess` flag; (d) `kb content done` keeps `processing` while more segments remain, instead of resetting to `new`, so the claim survives between chunks.

### 2.2 Phase 1 — Knowledge core
- [x] Skill docs and references (see 1.2).
- [ ] `finsocnet/core/vocab.py`, `cards.py`, `fts.py`; `kb vocab|card|citation|decision …`; seed loaded into the DB.
- [ ] `--legacy` flag on `kb card commit`.
- [ ] `evals/` (does not exist yet): transform ≥ 10, dedup ≥ 15 cases; `finsocnet eval prepare|score`.
- [ ] Tests: grammar, vocabulary, quote check, candidate determinism, commit per decision type, idempotency, CONFLICT, FTS triggers, undo.
- [ ] Acceptance: miner on 3 legacy transcripts; re-run creates no duplicates; 5 cited answers + 1 gap; eval targets.

### 2.3 Phase 2 — Persons and legacy conversion
- [x] Skill docs (see 1.2).
- [~] `person-matcher`: v1 `match_person.py list|get|match` works; v2 `kb person …` missing.
- [ ] `finsocnet/core/persons.py`, `person_skills.py`; `kb person|skill …`.
- [ ] Convert 66 legacy hypotheses and 9 legacy rulebooks to cards + `person_skills`; `docs/improvements/legacy-conversion.md`.
- [ ] After user approval: delete `legacy/person-skills/`, `legacy/meta-skills/`; migration `004_drop_legacy.sql`.
- [ ] Attribution eval ≥ 10 cases, accuracy ≥ 0.85.

### 2.4 Phase 3 — Agent browser and session bridge
- [x] Skill docs (see 1.2).
- [ ] `config/` (does not exist yet): `platforms.yaml`, `budgets.yaml`.
- [ ] `finsocnet/core/browser.py`, `budgets.py`, `sessions/`.
- [ ] `agent_browser.py`, `session_bridge.py`; local `finsocnet session init-local|export|push`.
- [ ] Spike table 04 §9 filled (export method A on Linux/macOS/Windows; cookie names per platform).
- [ ] Secret-leak test; reapply after restart; real export → push → import → `verify --all` with the user.

### 2.5 Phase 4 — P1 platform skills
- [ ] `finsocnet/core/platform.py`, `http.py`.
- [ ] v2 adapters (fixtures + one live smoke test each): `youtube.py`, `transcribe.py`, `document.py`, `web.py`, `web_search.py`, `google.py`, `reddit.py`, `x.py`, `medium.py`, `substack.py`, `podcast.py`, `annas.py`, `papers.py`.
- [ ] Old script names as wrappers (05 §1.4).
- [ ] `grep -rn "chromium.launch\|new_context(" .agents/skills` → 0 (today: 38).

### 2.6 Phase 5 — Explore, self-improve, eval, skill installer
- [x] Skill docs (see 1.2).
- [ ] `finsocnet/core/queue.py`; `kb queue|gap|history|feedback …`.
- [ ] Full eval sets (06 §3.1) incl. `evals/search/fixture_db.sql`.
- [ ] `finsocnet explore add`, `persons review`, `feedback`.
- [ ] `finsocnet/core/skill_install.py`, `skill_installer.py`, `config/skills.lock.json`, `skills.py` core/installed split, fixtures (07 §5.6).
- [ ] Acceptance: 10 unattended explore steps; gap filled; one self-improver run with a data fix + branch proposal; skill-installer fixtures.

### 2.7 Phase 6 — P2 platform skills (code)
- [ ] `stackexchange.py` · [ ] `rss.py` · [ ] `forum.py` + `config/forums.yaml` · [ ] `telegram.py` · [ ] `discord.py` · [ ] `tradingview.py` · [ ] `facebook.py` · [ ] `sec.py` · [ ] `research.py` · [ ] `github.py` · [ ] `bluesky.py`

### 2.8 Phase 7 — P3 platform skills (code)
- [ ] `hackernews.py` · [ ] `stocktwits.py` · [ ] `tiktok.py` · [ ] `instagram.py` · [ ] `threads.py` · [ ] `seekingalpha.py` · [ ] `linkedin.py`

### 2.9 Phase 8 — Harness integration and docs
- [~] `finsocnet install <harness>` exists (v1); needs v2 slash commands (07 §3) and symlinks for all core + installed skills.
- [ ] `commands/` sources for all slash commands, rendered per harness.
- [ ] `finsocnet tui` on v2 data.
- [ ] Rewrite `AGENTS.md`, `README.md`.
- [ ] Remove old script-name wrappers and v1 CLI commands.
- [ ] Final acceptance checklist in `08-phases.md`.

---

## 3. Waiting on user decisions

| # | Question | Blocks |
|---|---|---|
| Q1 | All-domain cookie import: accept, or default denylist for banking/payment domains? (SPEC §9) | Phase 3 |
| Q2 | Accept ToS/ban risk for Discord, Facebook, LinkedIn, Instagram (per platform)? | Phase 6–7 for those skills |
| Q3 | Private-group members as `private_source` persons, excluded from exports? | Phase 2 |
| Q4 | No user-agent spoofing by default? | Phase 3 |
| Q5 | Card language: English cards with source-language quotes, or Vietnamese cards for Vietnamese sources? | Phase 1 |
| Q6 | Pin one model for transformation? | Phase 1 |
| Q7 | Bulk ingest cost: books now or after the core is stable? | Phase 4 (`document-reader` books) |
| Q8 | Skill installer: lighter review for trusted publishers, or full review always (current spec)? | Phase 5 |
| Q9 | Move `login_*.py` to `legacy/` now, or keep until session-bridge works (current choice: keep)? | — |
| Q10 | Delete or keep your uncommitted `vector_store.py` / `ingest_idea.py` changes? | Phase 0 |
| Q11 | Build `skill-installer` before Phase 5 (it only needs Phase 0)? | scheduling |
