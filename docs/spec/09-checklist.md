# 09 — Status Checklist (done / missing)

> **Last checked:** 2026-10-28, branch `v2/phase-0-foundation` (Phase 0 done; Phases 1–8 not started).
> **Who updates it:** the implementing agent ticks items at the end of each phase (same branch as the phase) and updates the date; the reviewer checks the ticks against the acceptance tests in `08-phases.md`.
> Legend: `[x]` done and verified · `[~]` partly done (note says what is left) · `[ ]` missing.

## Summary

| Phase | Spec | SKILL.md + references | Code | Tests / acceptance |
|---|---|---|---|---|
| 0 Foundation and cleanup | [x] | [x] knowledge-db | [x] | [~] 30 tests green; migration 003 run on a copy, real DB awaiting your approval |
| 1 Knowledge core | [x] | [x] transformer, dedup, search, miner | [x] | [~] 69 tests green; agent acceptance runs happen with the legacy conversion (Phase 2) |
| 2 Persons and legacy conversion | [x] | [x] matcher, synthesizer, explorer | [x] | [~] conversion done; deleting the legacy folders waits for your approval of `docs/improvements/legacy-conversion.md` |
| 3 Agent browser and session bridge | [x] | [x] agent-browser, session-bridge | [x] | [~] 15 tests incl. a real headless Chromium; live check with your accounts pending |
| 4 P1 platform skills (15) | [x] | [x] all 15 | [x] | [~] fixture tests for every adapter; live checks with your accounts pending (see platform notes) |
| 5 Explore, self-improve, eval, skill installer | [x] | [x] source-explorer, self-improver, skill-installer | [x] | [~] eval sets below the spec minimum (see 2.6); unattended explore run not demonstrated |
| 6 P2 platform skills (11) | [x] | [x] all 11 | [x] | [~] 5 verified against live APIs/pages, 6 hand-written fixtures only |
| 7 P3 platform skills (7) | [x] | [x] all 7 | [x] | [~] hackernews verified live, the rest hand-written fixtures |
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
- [x] Skill docs and references (see 1.2); statuses set to `ready`.
- [x] `finsocnet/core/vocab.py`, `cards.py`, `fts.py`; `kb vocab|card|citation|decision …`; the 344-term seed loads on `kb init`.
- [x] `--legacy` flag on `kb card commit` and `kb card validate` (relaxes only the quote check, only for contents without text).
- [x] `evals/transform` (10 cases), `evals/dedup` (15 cases), `evals/README.md`; `finsocnet eval prepare|score|run` for transform, dedup, attribution and search (search needs `evals/search/fixture_db.sql`, Phase 5).
- [x] Tests: grammar per kind, vocabulary (add/merge/lookup), quote check, candidate determinism, siblings, commit for every decision type, idempotent re-commit, CONFLICT and batch isolation, FTS triggers (insert, update, citation add/move, delete), merge/undo, legacy commit, eval scoring, CLI flow.
- [~] Acceptance: all 14 of 15 spec example cards validate (the 15th, E12, adds its own vocabulary term first). Initial eval run by the same agent that wrote the cases: transform validity 1.0 / recall 1.0 / precision 1.0, dedup accuracy 1.0 / wrong-merge 0.0 (not independent evidence; the user should review the golden cases). The `market-idea-miner` run on 3 legacy transcripts, the re-run without duplicates, and the 5 cited answers + 1 gap are done with the Phase 2 conversion on the migrated DB.

Deviations to review: (a) the tag-stuffing check also looks at `subject` (spec example E8 only passes that way); (b) `card.schema.json` allows an optional `citation.locator` (needed for legacy citations); (c) `kb card commit` exits 0 with per-item `status: error` entries and a warning per failed decision, instead of a non-zero exit; (d) `kb card candidates` also returns `siblings`.

### 2.3 Phase 2 — Persons and legacy conversion
- [x] Skill docs; the v1 `match_person.py` is removed (`kb person candidates` replaces it).
- [x] `finsocnet/core/persons.py`, `person_skills.py`; `kb person|skill …`.
- [x] The real `data/knowledge.db` is migrated to v2 (backup: `data/backups/knowledge-20261028T034532Z-pre-003.db`); vocabulary seed (344 terms) plus 7 terms added during the conversion.
- [x] Legacy conversion: 58 cards (66 hypotheses: 46 converted, 11 duplicates, 9 not converted), 9 rulebooks in `person_skills`; `docs/improvements/legacy-conversion.md`. `finsocnet strategy <name>` now reads `person_skills`.
- [ ] **Waiting on you:** approve the comparison (lost rules, hypotheses that the source does not support), then delete `legacy/person-skills/`, `legacy/meta-skills/`, `legacy/scripts/` and apply migration `004_drop_legacy.sql` (not written yet; it needs your OK first).
- [x] `evals/attribution` (12 cases); agent accuracy 1.0 on the set (author-scored, not independent).

Deviation to review: the spec asks for a card for every legacy rule, "with a legacy citation if needed". Where the stored source text contradicts or does not contain the rule, I created no card, because a citation would attribute an unsupported claim to a real person. Details and the list of dropped rules are in the conversion document. The two arXiv stub cards (11, 12) use `--legacy` and are stored with `quote_verified = 0`.

### 2.4 Phase 3 — Agent browser and session bridge
- [x] `config/platforms.yaml`, `config/budgets.yaml`.
- [x] `finsocnet/core/browser.py`, `browser_proc.py`, `budgets.py`, `sessions/{formats, bundle, import_remote, export_local, probes}.py`.
- [x] `agent_browser.py start|stop|status|open|vnc`, `session_bridge.py keygen|import|status|verify|reapply|purge`, local `finsocnet session init-local|export|push`.
- [x] Spike table (04 §9): method A verified on Linux; macOS, Windows, cookie names per platform and Discord/Telegram keys are **not verified** (need your machine and accounts).
- [x] Acceptance in tests: fixture `cookies.txt` + Cookie-Editor JSON + storage_state + HAR + Firefox DB imported; cookies present in a real headless Chromium (count per domain via CDP); `stop && start` then `reapply` restores them; secret-leak test (stdout, stderr, logs, DB file, `data/work`, `store.age`) passes; logged-out/checkpoint pages raise exit 3; an exhausted budget raises exit 4 with `retry_after_sec`.
- [ ] **Needs you:** real export on your machine -> `push` -> `verify --all` shows `logged_in` for your platforms; SPEC §9 Q1 (banking denylist) and Q4 (no UA spoofing; implemented as specified: no override).
- [ ] Removal of `login_x.py`, `login_reddit.py`, `login_medium.py` happens in Phase 4 together with the adapters that replace them (they are still the only v1 login path).

Notes: `session_bridge.py keygen` was run once while testing and created `~/.config/finsocnet/age_identity.txt` on this machine (chmod 600); reuse or delete it. Chrome hangs on the first cookie operation when no desktop keyring exists, so the agent browser passes `--password-store=basic --use-mock-keychain` on Linux.

### 2.5 Phase 4 — P1 platform skills
- [x] `finsocnet/core/platform.py` (adapter contract, standard CLI: `--ingest`, `--enqueue`, `--save-cursor`, `known`, session guard), `http.py` (budgeted client), `segments.py`, `legacy.py`.
- [x] Adapters in `finsocnet/adapters/` (the skill scripts are thin wrappers; deviation from the spec's "adapter inside the script"): `youtube, web_search, web, google, document, annas, papers, reddit, x, medium, substack, podcast` and `core/transcribe.py`.
- [x] Old script names kept as wrappers (`core/legacy.py`); the password-login scripts `login_x/reddit/medium.py` and `session_manager.py` are deleted (ADR-005). `grep -rn "chromium.launch\|new_context(\|launch_persistent_context" .agents finsocnet` -> 0 matches outside `core/browser*`.
- [x] Fixture tests for every supported subcommand; ContentRecords validate. Real recordings for hackernews, stackexchange, bluesky, github, openalex, itunes + podcast feed, rss, telegram preview, substack, sec; hand-written fixtures (documented shape, not recorded) for reddit, x, google, medium, annas, and every session-gated platform.
- [~] **Not done:** the "live smoke test with your sessions" and `fetch --ingest -> market-idea-miner` end-to-end per skill. Plain HTTP to reddit.com, stocktwits.com and medium.com feeds was refused from this network, so those adapters rely on the agent browser and were not run against the real sites.

### 2.6 Phase 5 — Explore, self-improve, eval, skill installer
- [x] `core/queue.py` and `kb queue|gap|history`, `kb feedback`; `finsocnet explore add|show`, `finsocnet persons review`, `finsocnet feedback`; URL dispatch rules (`core/dispatch.py`, 06 §1.3).
- [x] `evals/search/fixture_db.sql` (68 fictional cards) and `eval prepare|score` for transform, dedup, search and attribution; `kb ... --since 7d` accepted.
- [x] Skill installer: `core/skill_install.py` (B1-B6, H1-H8, M1-M4 scanner, safe archive extraction, review verification, lock file, update/remove/outdated), `skill_installer.py`, `skill_review.schema.json`, `config/skills.lock.json`, `finsocnet/skills.py` core/installed split, 18 offline tests (no staged file is ever passed to a subprocess; test-enforced).
- [~] Eval sets are **below the minimum** of 06 §3.1: transform 10 (30), dedup 15 (40), search 15 (30), attribution 15 (15 ok). Results from the author of the cases: transform validity 1.0, recall 1.0; dedup accuracy 1.0, wrong-merge 0.0; search recall@10 1.0; attribution 1.0. They are not independent evidence. Plan: have the user review and extend the golden cases before trusting the numbers.
- [ ] **Not demonstrated:** 10 unattended explore steps, a gap filled by exploration, and a self-improver run with a branch proposal. These need real content from the platforms and the user's review.

### 2.7 Phase 6 — P2 platform skills
- [x] `stackexchange, rss, forum (discourse/xenforo/generic), telegram (public), discord (user/bot), tradingview, facebook, sec, research, github, bluesky`.
- Discord and Facebook ship with the ToS warnings; enabling them for real use waits for your answer to SPEC §9 Q2.

### 2.8 Phase 7 — P3 platform skills
- [x] `hackernews, stocktwits, tiktok, instagram, threads, seekingalpha, linkedin`.

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
