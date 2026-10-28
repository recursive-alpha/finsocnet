---
description: "Show the FinSocNet knowledge base status"
argument-hint: ""
---

FinSocNet lives in `$FINSOCNET_HOME` (run every command with `uv run --project $FINSOCNET_HOME …`).

Run `uv run --project $FINSOCNET_HOME finsocnet kb stats` and `uv run --project $FINSOCNET_HOME finsocnet kb gap list --status open --limit 5`, then summarize in a short table: persons, sources, contents by status, cards, citations, top 10 persons by cards, open gaps, queue by status, and session health per platform (`session_bridge.py status`). Mention anything stuck (contents `processing`, queue `in_progress`, sessions logged out).
