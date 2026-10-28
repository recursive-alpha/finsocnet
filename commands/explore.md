---
description: "Add a seed to the exploration queue and run one explore step"
argument-hint: "<url | @handle | person | query>"
---

FinSocNet lives in `$FINSOCNET_HOME` (run every command with `uv run --project $FINSOCNET_HOME …`).

Run `uv run --project $FINSOCNET_HOME finsocnet explore add "$ARGUMENTS"`, then use the `source-explorer` skill for one step restricted to that item. Report what was fetched and mined.
