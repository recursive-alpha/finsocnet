---
description: "Show one knowledge card with citations and links"
argument-hint: "<card id>"
---

FinSocNet lives in `$FINSOCNET_HOME` (run every command with `uv run --project $FINSOCNET_HOME …`).

Run `uv run --project $FINSOCNET_HOME finsocnet kb card get $ARGUMENTS --citations --links --history` and present the claim, conditions, who said it (with role and confidence), quotes with source links (YouTube `?t=<start_sec>`), related and contradicting cards.
