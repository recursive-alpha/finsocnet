---
description: "Load a person's rulebook"
argument-hint: "<person> [category] [--rebuild]"
---

FinSocNet lives in `$FINSOCNET_HOME` (run every command with `uv run --project $FINSOCNET_HOME …`).

Use the `person-skills-explorer` skill for: $ARGUMENTS
`kb skill get <person> --render markdown` (or `--category`). With `--rebuild`, first run `person-skill-synthesizer`. Never invent rules: every rule must show its card ids.
