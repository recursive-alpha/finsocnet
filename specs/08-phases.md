# 08 — Implementation Phases

Implement in order. Each phase lists what to read, the tasks, and the acceptance tests. A phase is done only when every acceptance item passes and `uv run pytest` is green. Commit at the end of each phase (one branch per phase: `v2/phase-N-<name>`), tick the phase's items in [`09-checklist.md`](09-checklist.md), and stop for user review before the next phase.

---

## Phase 0 — Foundation and Cleanup

**Read:** specs/README.md, 00, 01 §1–§2, §5.

**Tasks**
1. Create `finsocnet/core/` modules: `config`, `db`, `output`, `ids`, `normalize`, `records`, `migrations` (moved + extended for `.py` migrations and auto-backup), `runs`.
2. Add JSON Schemas: `content_record`, `card`, `query_card`, `decision`, `person`, `person_skill`, `eval_case`.
3. Write `migrations/003_v2_schema.sql` (01 §2, all DDL including triggers and views) and `migrations/003_v2_schema.py` (01 §5.3).
4. Implement `kb` admin and content groups: `init`, `migrate`, `backup`, `doctor`, `stats`, `run start|end|list`, `lesson add|list|update`, `source …`, `content add|get|view|chunks|list|claim|done|fail|link-duplicate|search`.
5. `pyproject.toml`: remove `chromadb`, `sentence-transformers`, `duckduckgo-search`; add the v2 dependencies (00 §2); add optional groups `local`, `ocr`, `dev`.
6. Delete `knowledge-db/scripts/vector_store.py`, `knowledge-db/scripts/db.py`, `knowledge-db/scripts/ingest_idea.py`, `scripts/embed_server.py`, vector/RAG code in `finsocnet/search.py`; replace `knowledge-db/SKILL.md`.
7. `.gitignore`: whole `data/` except `.gitkeep` (00 §8). `.env.example`: 00 §6.
8. Test fixtures: a v1 fixture DB generator (`tests/fixtures/legacy/make_v1_db.py`) using the current v1 DDL and sample rows from 01 §5.2, plus two transcript JSON fixtures.

**Acceptance**
- `uv run finsocnet kb init` on an empty path creates the v2 schema; `kb doctor` reports OK.
- Migration tests in 01 §5.4 pass on the fixture DB.
- Run migration 003 on a **copy** of the real `data/knowledge.db`; report the summary to the user (do not touch the real DB until the user approves).
- `grep -rE "chromadb|sentence_transformers|SentenceTransformer|vector_store" finsocnet .agents scripts` → no matches.
- `kb content add` with a fixture ContentRecord → created; re-add with 2 more comments → `updated, segments_added: 2`; same text under another id → `duplicate`.
- FTS: `kb content search "<word from fixture>"` returns the segment.
- Every command prints exactly one JSON envelope; write commands without `--run` exit 2 `RUN_REQUIRED`.

---

## Phase 1 — Knowledge Core

**Read:** 02, 03 §1–§4, 01 §3, 06 §3.

**Tasks**
1. `finsocnet/core/vocab.py` + `kb vocab …`; write `vocabulary_seed.json` (02 §4.2, ≥ 250 terms) and load it.
2. `finsocnet/core/cards.py`: `validate_card` (all checks in 02 §2.2), `candidates`/`search_cards` (03 §2, deterministic), `commit_decision` (01 §3.2), `merge`/`retire`/`update`/`undo` (01 §3.3). `kb card …`, `kb citation attribute`, `kb decision list|review`.
3. Skills (SKILL.md + references, no scripts unless noted):
   - `knowledge-transformer` (02 §5–§7): `card_format.md`, `claim_grammar.md`, `examples.md` (E1–E16 complete), `query_examples.md`, `vocabulary_seed.json`.
   - `knowledge-dedup` (03 §3): `decision_examples.md` (≥ 10 cases).
   - `knowledge-search` (03 §4).
   - `market-idea-miner` (03 §1) — replaces `hypothesis-miner` (delete the old skill directory after the new one works).
4. Eval framework: `finsocnet eval prepare|score` for `transform` and `dedup`; initial sets: transform 10, dedup 15 (from the 16 existing transcripts and fictional cases).
5. Tests: grammar regex per kind (good/bad examples from `claim_grammar.md`), vocabulary checks, quote check with punctuation/case differences, candidate retrieval determinism, commit for each decision type, idempotent re-commit, CONFLICT on merged target, FTS triggers (insert/update/citation add/citation move), undo of a merge.

**Acceptance**
- An agent run of `market-idea-miner` on 3 legacy transcripts (one solo video, one interview, one reddit thread) completes; every committed card passes validation; `dedup_decisions` has one row per card.
- Re-running the miner on the same content creates no duplicates (`already_committed` or `same` decisions).
- `knowledge-search` answers 5 sample questions with cited cards; one unanswerable question creates a gap.
- Eval: transform validity 100%; dedup wrong-merge rate ≤ 0.03 on the initial set.

---

## Phase 2 — Persons and Legacy Conversion

**Read:** 03 §5–§7, 01 §5.3 step 9.

**Tasks**
1. `finsocnet/core/persons.py`, `person_skills.py`; `kb person …`, `kb skill …`.
2. Skills: `person-matcher` (rewrite), `person-skill-synthesizer` (replaces `skill-curator` and `user-skill-synthesizer`), `person-skills-explorer` (replaces `skill-explorer`).
3. Legacy conversion (agent work, one run per person, tracked with `kb run`):
   - For each of the 66 `legacy_hypotheses`: find the quote in the content's segments (`kb content search`); if found → normal transform + dedup with that segment; if not found (content has no text) → card with a legacy citation (`segment_seq = NULL`, `quote_verified = 0`, `locator_json = {start_sec}` from the legacy timestamp). Requires a `--legacy` flag on `kb card commit` that relaxes only the quote check.
   - For each of the 9 person folders: read `SKILL.md` and `references/*.md`; every rule that is not yet a card becomes a card citing the original content (legacy citation if needed); then run `person-skill-synthesizer` for the person.
   - Compare the new rulebook with the old folder; list rules lost or changed in `specs/improvements/legacy-conversion.md`.
4. After the user approves the comparison: delete `legacy/person-skills/` (the 9 folders), `legacy/meta-skills/` (`hypothesis-miner`, `skill-curator`, `user-skill-synthesizer`, `skill-explorer`) and `legacy/scripts/` (`rebuild_all_person_skills.py`, `rebuild_skills_data.py`, …), and repoint or remove `finsocnet strategy`; migration `004_drop_legacy.sql` drops `legacy_hypotheses`, `legacy_skills`, `legacy_users`, `legacy_contents`, `legacy_persons`, `legacy_person_appearances` (keep `legacy_id_map`).

**Acceptance**
- `kb skill get <person> --render markdown` works for all 9 persons; every rule references active card ids that cite that person; no timestamps in rulebooks.
- `specs/improvements/legacy-conversion.md` lists 0 lost rules (or each loss is explained and approved).
- `ls .agents/skills` contains no person folders.
- Attribution eval set (≥ 10 cases) created; accuracy ≥ 0.85.

---

## Phase 3 — Agent Browser and Session Bridge

**Read:** 04 (all), 00 §6, §10 (secret-leak test).

**Tasks**
1. `finsocnet/core/browser.py`, `budgets.py`, `config/platforms.yaml`, `config/budgets.yaml`.
2. Skill `agent-browser`: `agent_browser.py start|stop|status|open|vnc` (Xvfb handling, PID file, idempotent start, proxy, egress IP in status).
3. `finsocnet/core/sessions/`: readers for every format in 04 §3.1, bundle create/encrypt (pyrage), push (scp/ssh), import, reapply, verify, purge.
4. Skill `session-bridge` (remote commands) and `finsocnet session init-local|export|push` (local).
5. Spike: method A on Linux/macOS/Windows; fill 04 §9. Verify cookie names in `platforms.yaml` for x, reddit, facebook, google, medium, substack, discord, telegram.
6. Remove password/credential paths from `login_x.py`, `login_reddit.py`, `login_medium.py` (delete those scripts once adapters use the agent browser in Phase 4); remove credential keys from `.env.example`.

**Acceptance**
- From a fixture `cookies.txt` + Cookie-Editor JSON + storage_state folder: `import` → cookies present in the agent browser (checked via CDP `Storage.getCookies` count per domain), `browser_sessions` rows correct.
- Secret-leak test passes (00 §10).
- `agent_browser.py stop && start` → session cookies restored by `reapply`.
- Real check with the user: export locally, push, import, `verify --all` shows `logged_in` for the platforms the user is logged into.
- A logged-out fixture page makes `check_page` raise exit 3.
- Budgets: exhausting a fixture budget returns exit 4 with `retry_after_sec`.

---

## Phase 4 — Priority 1 Platform Skills

**Read:** 05 §1–§2, 00 §7, 04 §6.

**Tasks** — one sub-branch per skill, in this order:
1. `finsocnet/core/platform.py` (`PlatformAdapter`, `run_platform_cli`), `http.py`.
2. `youtube-extractor`, `audio-transcriber`, `document-reader`, `web-reader`, `web-searcher`, `google-searcher`.
3. `reddit-explorer`, `x-explorer`, `medium-explorer`, `substack-explorer`, `podcast-explorer`.
4. `annas-archive-explorer`, `paper-code-explorer` alignment.
5. Old script names kept as wrappers (05 §1.4).

**Acceptance (per skill)**
- Fixture tests for every supported subcommand pass; ContentRecords validate.
- Live smoke test run once with the user's sessions; results noted in `references/platform_notes.md`.
- `fetch --ingest` → content in DB → `market-idea-miner` processes it end to end.
- No `chromium.launch(` / `new_context(` in any skill script: `grep -rn "chromium.launch\|new_context(" .agents/skills` → no matches.

---

## Phase 5 — Explore, Self-Improve, Evaluate

**Read:** 06 (all), 07 §3 (`/finsocnet:explore-step`, `/finsocnet:improve`).

**Tasks**
1. `finsocnet/core/queue.py`; `kb queue|gap|history|feedback …`.
2. Skill `source-explorer` with `references/dispatch.md` (06 §1.3) and priority guidance.
3. Skill `self-improver` (06 §2) including the re-dedup sweep and the proposal workflow.
4. Eval sets to minimum sizes (06 §3.1); `evals/search/fixture_db.sql`; `eval prepare|score` for all sets.
5. `finsocnet explore add`, `finsocnet persons review`, `finsocnet feedback`.
6. Skill `skill-installer` (07 §5): `finsocnet/core/skill_install.py`, `skill_installer.py`, `skill_review.schema.json`, `config/skills.lock.json`, `finsocnet/skills.py` core/installed split, fixtures in 07 §5.6. Depends only on Phase 0; may be built earlier.

**Acceptance**
- From one seed person, 10 explore steps run unattended: queue items processed, contents mined, mentions enqueued, no item stuck `in_progress` after the run.
- A gap created by a search is filled after exploration and re-checked (`status = filled`, `filled_by_cards_json` non-empty).
- One `self-improver` run produces at least one applied `data_fix` and one branch proposal with before/after eval tables.
- Eval targets in 06 §3.4 met, or the shortfall is listed in a lesson with a plan.
- `skill-installer`: installs a clean skill from a GitHub folder link, a repo with several skills, and a `.zip`; refuses every block fixture; refuses install with an incomplete `review.json`; `outdated` detects an upstream commit and a local edit; no staged file is ever executed (test-enforced).

---

## Phase 6 — Priority 2 Platform Skills

**Read:** 05 §3.

Order: `stackexchange-explorer`, `rss-explorer`, `forum-explorer` (Discourse first, then XenForo), `telegram-explorer` (public mode), `discord-explorer` (user mode, then bot mode), `tradingview-explorer`, `facebook-explorer`, `sec-edgar-explorer`, `research-explorer`, `github-explorer`, `bluesky-explorer`.

**Acceptance:** per skill as in Phase 4; Discord and Facebook only after the user has answered SPEC §9 Q2.

---

## Phase 7 — Priority 3 Platform Skills

**Read:** 05 §4. Order: `hackernews-explorer`, `stocktwits-explorer`, `tiktok-explorer`, `instagram-explorer`, `threads-explorer`, `seekingalpha-explorer`, `linkedin-explorer`. Acceptance as in Phase 4.

---

## Phase 8 — Harness Integration and Documentation

**Read:** 07.

**Tasks**
1. `commands/` slash command sources and installer rendering for all harnesses (07 §2–§3); remove obsolete commands.
2. `finsocnet tui` updated to v2 data.
3. Rewrite `AGENTS.md`, `README.md`, `.env.example`; every SKILL.md matches the template.
4. Remove old script-name wrappers.
5. Final acceptance checklist (below).

---

## Phase 9 — Semantic search, open exploration, images, REA, skill builder, UI

**Read:** 10–15.

**Tasks**
1. Migrations `004`, `005`; `core/embed.py`, `translate.py`, `search.py`, `seen.py`, `media.py`; `kb embed|translate|seen|search`, `kb person avatar`, `card link|unlink`.
2. Skills: `translator`, `reverse-anything`, `platform-skill-builder`; updates to `knowledge-search`, `market-idea-miner`, `knowledge-db`, `person-matcher`, `source-explorer`, all explorers (topic-free).
3. `--ui` (`core/ui.py`); web `/search`, `/api/search|embed|media`, avatars.
4. Root `README.md`, `docs/` (platform documentation), cover image and demo GIF.

**Acceptance:** see each spec's acceptance section; `uv run pytest` green; `tsc`, `eslint` (new files) and `next build` green.

---

## Final Acceptance Checklist (v2 done)

- [ ] **SQLite only:** no `chromadb`, `sentence-transformers`, vector tables, or embedding code; `data/chroma_db` absent (ADR-001).
- [ ] **No LLM SDK** in any script (ADR-002); Whisper is the only model run by scripts.
- [ ] **Cards:** every active card validates; every citation's quote is found in its segment (except `quote_verified = 0` legacy citations).
- [ ] **Agent dedup:** every card insert/merge has a `dedup_decisions` row; eval wrong-merge rate ≤ 3%.
- [ ] **Nothing ignored:** no code path deletes contents; caps produce warnings; session import includes all domains.
- [ ] **Person-centric:** citations carry person or handle and role; review queue works.
- [ ] **No person skill folders** in `.agents/skills/`.
- [ ] **Session bridge:** no credentials in `.env`; secret-leak test passes; re-export protocol works.
- [ ] **Agent browser:** no `chromium.launch`/`new_context` in skills; budgets and checkpoints enforced.
- [ ] **Explore → gap → fill** loop demonstrated.
- [ ] **Self-improver** proposals arrive only as branches with eval reports.
- [ ] **Rulebooks** are timestamp-free; citations keep locators.
- [ ] **agentskills.io:** every skill has valid frontmatter, description ≤ 1024 chars, procedures that reference existing commands.
- [ ] **Skill installs:** every folder in `.agents/skills/` is either a core skill or has a `config/skills.lock.json` entry whose file hashes match (or is reported `locally_modified`).
- [ ] **Docs:** AGENTS.md and README.md describe v2 only.
