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
