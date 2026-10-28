---
description: "Answer a trading/finance question from the knowledge base, with citations"
argument-hint: "<question>"
---

FinSocNet lives in `$FINSOCNET_HOME` (run every command with `uv run --project $FINSOCNET_HOME …`).

Use the `knowledge-search` skill for: $ARGUMENTS
Translate the question to English when needed, transform it into a Query Card, run `kb card search` (hybrid BM25 + semantic), answer only from cards with quote, person, source and a timestamped URL, show consensus and contradictions, and log a gap if the answer is weak.
