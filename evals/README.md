# Evaluation sets

Golden cases for `finsocnet eval` (docs/spec/06-explore-improve-eval.md). Cases are fictional and hand-checked.

| Set | Layout | Scoring |
|---|---|---|
| `transform/<case>/` | `input.json` (chunk_view, cast, platform, content_id), `expected.json` (`cards`: kind, category, action, terms, segment_seq; each may be a list of accepted values) | validity, recall, precision, no-card accuracy |
| `dedup/<case>.json` | `new_card`, `candidates` (full cards with ids), `expected_decision`, `expected_target` | accuracy, wrong-merge rate |
| `attribution/<case>.json` | `chunk_view`, `cast`, `expected` (`{seq: person_id}`) | accuracy |
| `search/<case>.json` | `question`, `expected_card_refs`, `must_not` over `search/fixture_db.sql` | recall@10, MRR |

Run: `finsocnet eval prepare <set> --out DIR`, let the agent write outputs following the *current* skill instructions
(`<case>.cards.json`, `<case>.decision.json`, `<case>.attribution.json`, `<case>.query_card.json`), then
`finsocnet eval score <set> --outputs DIR [--out report.json]`. Scripts never call an LLM (ADR-002).

Adding a case: copy an existing one, keep people and content ids fictional, never put a case in the same branch as the
instruction change it is meant to test, and have the user review it.

## Sizes and baseline

transform 30 · dedup 40 · search 30 (over `search/fixture_db.sql`, 68 cards) · attribution 15 (spec 06 §3.1 minimums).
`evals/baseline/2026-10-28/` holds the agent outputs for every case and `docs/improvements/eval-2026-10-28/*.json` the scores:
transform validity 1.0 / recall 1.0 / precision 1.0 · dedup accuracy 1.0 / wrong-merge 0.0 · attribution 1.0 · search recall@10 0.956, MRR 1.0.
The author of the agent outputs also wrote the cases, so this is a regression baseline, not independent evidence; `tests/unit/test_eval_sets.py` keeps both honest.
Regenerate: scratch generators live next to the sets (`search/gen_fixture.py`); transform/dedup cases were generated from a script and are plain JSON now.
