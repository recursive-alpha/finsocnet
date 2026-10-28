---
description: "Show a person: profile, aliases, appearances, stats"
argument-hint: "<person id or name>"
---

FinSocNet lives in `$FINSOCNET_HOME` (run every command with `uv run --project $FINSOCNET_HOME …`).

Use the `person-matcher` skill: `kb person candidates --name "$ARGUMENTS"` if the id is unknown, then `kb person get <id>` and `kb person cards <id>`. Show aliases per platform, appearances by role, card count per category, and `needs_review` items.
