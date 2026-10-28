---
description: "Start from a person's profile URL and let the agent discover and complete everything"
argument-hint: "<profile url>"
---

FinSocNet lives in `$FINSOCNET_HOME` (run every command with `uv run --project $FINSOCNET_HOME …`).

Run `uv run --project $FINSOCNET_HOME finsocnet explore add "$ARGUMENTS" --person`, then use the `person-explorer` skill on that URL: resolve the profile, create or match the person, find and verify their other places, list everything they published, mine the most important content, and report what is complete and what is blocked.
