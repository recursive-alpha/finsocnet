# Troubleshooting

Always read `error.hint` in the JSON envelope first; `--ui` shows it in a red panel.

| You see | Cause | Do |
|---|---|---|
| exit 2 `RUN_REQUIRED` | a write without a run | `kb run start …`, pass `--run <id>` (or `FINSOCNET_RUN_ID`) |
| exit 2 `UNSUPPORTED` "REA is not installed" | `rea` not on `PATH` | `npm install --global rea-agents` ([Reverse anything](reverse-anything.md)) |
| exit 3 `LOGIN_REQUIRED` / `CHECKPOINT` | platform needs your session, or a captcha | stop that platform; `finsocnet session export && finsocnet session push`; solve a check once with `agent_browser.py vnc` |
| exit 4 `RATE_LIMITED` | a budget or the site said slow down | wait `retry_after_sec`; the explore queue defers the item. `web_search.py` maps a failing search backend to this too |
| exit 5 "cannot reach … ERR_NAME_NOT_RESOLVED" | the host does not resolve | check the URL |
| exit 6 `VALIDATION_ERROR` | cards, recipes, translations or records failed validation | `error.details` lists every problem with its JSON path; fix them all, then resend (commits are idempotent) |
| exit 7 browser unavailable | agent Chrome not running | `agent_browser.py start [--headless]`, retry once |
| exit 8 `CONFLICT` | target merged/retired, skill folder exists, run already claimed | re-run candidates for that card; `--force` for scaffold; stop if another run has the content |
| search finds nothing by meaning | no embeddings yet, or the content has no language | `kb embed status`; `kb embed sync`; `kb translate detect-pending --by-source` |
| warning "no card embeddings for model …" | model changed or never synced | `kb embed sync` (the old model's vectors stay) |
| first semantic query is slow | the ONNX model loads once per process | expected; the web UI keeps nothing between calls, so the first call of a cold server is slowest |
| model download fails | no network or disk | free ~0.5 GB, set `FINSOCNET_EMBED_PROVIDER=hashing` meanwhile (keyword-like, offline) |
| `no such table: seen_items` / `no such column: avatar_url` | database not migrated | `finsocnet kb migrate` (backup is taken first) |
| Reddit `CHECKPOINT` on lists | Reddit blocks JSON from server IPs | the adapter falls back to RSS automatically; expect partial comments |
| `kb card commit` item `error` | e.g. a `related` decision without `links` | read every `results[].status`, fix, commit again; only then `kb content done` |
| platform returns empty lists after a site change | selectors went stale | for your own sites: `site.py check <name>`, fix `config/sites/<name>.yaml`; record it as a `platform_change` lesson |
| avatars missing for someone | no own profile was ingested, or X needs a session | `profile <handle> --ingest`, link the source to the person, `kb person avatar fetch` |
| web UI shows "Failed to execute CLI command" | `uv` not on the server's `PATH`, or no database | start the UI from the repo root; `finsocnet kb doctor` |

Tests: `uv run pytest` (offline; real headless Chromium is used by the browser tests, `-m live` for real sites). A failing test that passes alone under load is the real-browser test racing a busy machine; re-run it.
