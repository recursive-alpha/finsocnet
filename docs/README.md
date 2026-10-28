# FinSocNet documentation

FinSocNet is an agent-operated knowledge network: scripts fetch, store, validate, search and score; **your AI harness is the only model** and does all reading, judging, translating and writing. Everything lives in one SQLite file.

| Read this | When you want to |
|---|---|
| [Getting started](getting-started.md) | install, create the database, run the first fetch → mine → search |
| [Concepts](concepts.md) | understand contents, Knowledge Cards, persons, the agent's role and the data flow |
| [CLI reference](cli.md) | find a command, read the JSON envelope, use `--ui`, understand exit codes |
| [Search](search.md) | search by keyword and meaning, filter by data type, translate questions and knowledge |
| [Exploring](exploring.md) | discover people, communities, channels and threads on **any topic**; visited tracking; add a new site |
| [People and pictures](persons.md) | persons, appearances, rulebooks, avatars and other images |
| [Skills and platforms](skills.md) | the catalogue of 48 skills and which platform needs a login |
| [Sessions and the agent browser](sessions.md) | log in locally, ship the session, run one Chrome on the server |
| [Reverse anything](reverse-anything.md) | read binaries, packaged apps, databases and captures with REA |
| [Web UI](web-ui.md) | run the Next.js UI: search with filters, cards, traders, content, operations |
| [Configuration](configuration.md) | `.env`, `config/*.yaml`, budgets, the embedding model |
| [Operations](operations.md) | backups, migrations, health checks, evaluation, self-improvement, installing skills |
| [Troubleshooting](troubleshooting.md) | exit codes in practice, common failures and what to do |

Design and decisions (the *why*, normative detail, acceptance tests): [`specs/`](../specs/README.md). Agent rules: [`AGENTS.md`](../AGENTS.md).

## Three rules to remember

1. **Scripts never call an LLM and never decide.** They fetch, store, validate, search, score. The agent reads and judges (ADR-002). Language detection and translation are the agent's job too ([`translator`](../.agents/skills/translator/SKILL.md)).
2. **One SQLite file.** Relational tables, FTS5 for keywords, a vectors table for meaning ([ADR-001, ADR-009](../specs/README.md)). Back it up with `finsocnet kb backup`.
3. **Nothing is ignored and nothing is deleted.** Everything fetched is stored; duplicates are linked, merged with history, never erased.
