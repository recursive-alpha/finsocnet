# 11 — Visited items and open-topic exploration

Code: `finsocnet/core/seen.py`, hooks in `finsocnet/core/platform.py`, `kb seen …`. Migration `004` (`seen_items`). Skills: `source-explorer` (discovery recipe), every platform skill (`--new-only`, `--no-track`).

## 1. Visited-item tracking

**Problem.** `known` only told whether an item had been *stored*. Items that were looked at and rejected, failed, or are still queued reappeared in every search and list.

**Table `seen_items`** — one row per canonical item id (`key`, e.g. `youtube:abc`, `reddit:1xg9`, `web:<hash>`): `platform, kind, url, title, source_id, status, note, times_seen, first_seen, last_seen, run_id`.

| Status | Set by | Meaning |
|---|---|---|
| `seen` | `search`, `list` (with a run) | shown to the agent |
| `queued` | `list --enqueue` | in the explore queue |
| `fetched` | `fetch --ingest` | stored as content |
| `skipped` | `kb seen mark --status skipped --note why` | judged irrelevant; never offered again |
| `failed` | `kb seen mark --status failed` | could not be fetched |

A later `seen` never lowers a status (`fetched > skipped > failed > queued > seen`).

**Behavior in every platform skill** (shared `run_platform_cli`):
- When the call has a run (`--run` or `FINSOCNET_RUN_ID`) the returned items are recorded; ad-hoc looks leave no trace; `--no-track` disables recording.
- Items carry `visited` (`null` or a status) and `seen_count`; `known` is true for stored contents and for `fetched` / `skipped` items.
- `search --new-only` and `list --new-only` drop known items and report `hidden_known`.
- `list --enqueue` queues only items that are neither known nor already `queued`, and marks them `queued`.

**Commands:** `kb seen check KEY…` · `kb seen mark --key K --status S [--note N]` · `kb seen list [--platform --status --source]` · `kb seen stats`.

**Acceptance:** (tests) no run → no rows; second sighting → `times_seen` 2, `visited: "seen"`; skipped items vanish under `--new-only` and survive later sightings; fetched items are not re-queued.

## 2. No topic limit

Exploration is topic-agnostic. Finance is the miner's interest, not a filter on discovery.

- No adapter restricts by topic by default (the GitHub `algorithmic-trading` topic default and the Anna's Archive English default were removed; Stack Exchange accepts any site slug; forums are detected from the page).
- Skill descriptions state "any topic"; finance communities are examples.
- `source-explorer` carries a **discovery recipe** (per platform: search for communities/channels/threads on a free-text topic, enqueue the live ones, `kb seen mark … skipped` the dead ones).
- Everything fetched is stored (ADR-007). `market-idea-miner` writes cards only where there is finance knowledge; non-finance content remains searchable by its text (`kb search --types contents`, semantic once translated/embedded).
- Unknown sites are handled by `platform-skill-builder` (14).
