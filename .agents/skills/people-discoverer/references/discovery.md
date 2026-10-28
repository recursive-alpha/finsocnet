# Finding candidates

Every query is free text in any language; run several and keep the names that appear more than once. Use `--run R` and `--new-only` on platform skills, and mark rejected results `skipped` so you do not meet them again.

| Seed | Where to look |
|---|---|
| "leading <field> traders / PMs / CEOs" | `web_search.py search "best <field> hedge fund managers"`, `"<field> interview series"`, Wikipedia list pages, fund-ranking articles, conference line-ups (`"<conference> speakers"`) |
| professors / researchers | `research.py search "<topic>" --source openalex --limit 25` (authors with several works), `research.py profile "<name>"`, university department staff pages (`web_search.py search "<university> finance faculty"`), SSRN/NBER author lists |
| economists, central bankers, regulators | institution speaker pages (`site:federalreserve.gov speeches`, `site:ecb.europa.eu`, `site:bis.org`), working-paper series |
| executives, founders | shareholder letters (`"annual letter to shareholders"`), SEC filings via `sec.py`, interviews, books |
| authors, journalists | book lists (`annas.py search`, publisher pages), column archives, podcast guests |
| traders, investors | YouTube / X / Reddit / Substack authors who recur (`youtube.py search "<topic>" --type channel`), prop-firm and fund blogs, interview podcasts |
| people already in the database | `kb person list`, guests found by `person-matcher` (`role: guest`), authors of stored papers (`kb content search`), names in `explore_queue` with `origin=mention` |

## What to record per candidate before creating

`name`, `profession`, one fact with its source URL, `relevance` (one sentence), 1–3 platform places. Candidates that fail the gate go in the run stats (`skipped`), not in the database.
