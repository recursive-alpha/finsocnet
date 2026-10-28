# CLI reference

Entry point: `finsocnet` (`uv run finsocnet …`). Platform skills are scripts in `.agents/skills/*/scripts/` with the same conventions. **The CLI is the only interface**: there is no Python HTTP API; the [web UI](web-ui.md) calls the CLI.

## Output

Every command prints **exactly one JSON object** on stdout:

```json
{"ok": true,  "command": "kb.card.search", "data": {...}, "warnings": [], "meta": {"elapsed_ms": 31}}
{"ok": false, "command": "kb.card.get", "error": {"code": "NOT_FOUND", "message": "card 999 not found", "hint": "...", "retry_after_sec": null}, "warnings": [], "meta": {...}}
```

Logs go to stderr. Read `error.hint` before retrying; `error.details` lists every problem of a validation error at once.

| Exit | Meaning |
|---|---|
| 0 | ok |
| 1 | internal error: record a `script_bug` lesson |
| 2 | usage, `RUN_REQUIRED`, `UNSUPPORTED` (e.g. REA not installed) |
| 3 | `LOGIN_REQUIRED` / `CHECKPOINT`: stop that platform and ask the user to redo a session export |
| 4 | `RATE_LIMITED` / `BUDGET_EXHAUSTED`: wait `retry_after_sec` |
| 5 | not found (also: host does not resolve) |
| 6 | validation failed (cards, recipes, translations…) |
| 7 | agent browser unavailable |
| 8 | conflict (merged target, existing skill folder, …) |

## `--ui`: a terminal view for people

Add `--ui` to **any** command to draw the same data as tables and panels instead of JSON (exit codes stay the same). `FINSOCNET_UI=1` makes it the default for a shell session.

```bash
finsocnet search "why do options lose value" --ui
finsocnet kb card get 8 --ui
finsocnet kb person get tom-dante --ui
finsocnet kb stats --ui
.agents/skills/reddit-explorer/scripts/reddit.py list r/Daytrading --limit 5 --ui
```

## Runs and writes

`kb run start` returns a run id; every write command takes `--run <id>` (or `FINSOCNET_RUN_ID`); without it: exit 2 `RUN_REQUIRED`. End with `kb run end --run R --outcome success|partial|failed --stats '{…}'`.

## `finsocnet kb …`

| Group | Commands |
|---|---|
| database | `init`, `migrate [--dry-run]`, `backup [--to]`, `doctor [--repair-fts]`, `stats`, `prune` |
| `run` | `start`, `end`, `list` |
| `content` | `add`, `get`, `view`, `chunks`, `list`, `claim`, `done`, `fail`, `link-duplicate`, `search` |
| `source` | `upsert`, `get`, `list`, `cursor` |
| `vocab` | `lookup`, `add`, `update`, `merge`, `list`, `export` |
| `card` | `validate`, `candidates`, `commit`, `search [--mode]`, `get`, `list`, `update`, `merge`, `link`, `unlink`, `retire`, `undo` |
| `citation`, `decision` | `citation attribute`; `decision list`, `decision review` |
| `person` | `candidates`, `upsert`, `alias add`, `appearance add`, `get`, `list`, `cards`, `merge`, `avatar add|fetch|list` |
| `skill` | `upsert`, `get [--render markdown]`, `list` (person rulebooks) |
| `queue`, `gap`, `history` | the exploration loop: `queue add|next|update|list`, `gap add|list|update` |
| `seen` | `check`, `mark`, `list`, `stats` — visited items ([Exploring](exploring.md)) |
| `embed`, `translate` | `embed status|sync|query`; `translate detect-pending|set-language|pending|put|get` ([Search](search.md)) |
| `search` | unified search over cards, content, persons, rulebooks |
| `lesson`, `feedback` | the improvement loop ([Operations](operations.md)) |

Use `finsocnet kb <group> --help` for flags. Files passed with `--file` may be `-` for stdin.

## Other commands

| Command | Where | Purpose |
|---|---|---|
| `finsocnet search "<english text>" [flags]` | server | alias of `kb search` |
| `finsocnet eval prepare|score|run` | server | golden sets: `eval score search --search-mode lexical|semantic|hybrid` |
| `finsocnet explore add <url|@handle|person|query>` | server | seed the exploration queue; the right skill is chosen by `core/dispatch.py` (including your own sites in `config/sites/`) |
| `finsocnet persons review`, `finsocnet feedback` | server | resolve uncertain person matches; rate an answer or card |
| `finsocnet session init-local|export|push` | **your machine** | session bridge ([Sessions](sessions.md)) |
| `finsocnet install <harness|all> [--uninstall]` | where a harness runs | slash commands and skill links |
| `finsocnet stats`, `skills`, `strategy <person>`, `tui` | server | summaries, a person's rulebook, a Textual TUI |

## Platform skill scripts

Same contract everywhere (details: [Exploring](exploring.md)):

```bash
S=.agents/skills/<skill>/scripts/<script>.py
uv run $S search "<query>" [--limit N] [--since YYYY-MM-DD] [--new-only] [--run R]
uv run $S profile <handle-or-url> [--ingest --run R]          # avatars are downloaded with --ingest
uv run $S list <source> [--limit N] [--cursor C] [--save-cursor] [--enqueue] [--new-only] --run R
uv run $S fetch <url-or-id> [--ingest --run R] [--full]
```

`--no-track` leaves the visited table alone; `--format text` pretty-prints the JSON.
