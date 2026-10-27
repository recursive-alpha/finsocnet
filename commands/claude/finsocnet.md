---
description: Explore mined trading hypotheses, search quotes, and view setup details via FinSocNet
---

Run the `finsocnet` command using the Bash tool based on `$ARGUMENTS`:
- If `$ARGUMENTS` is empty, execute: `finsocnet stats`
- If `$ARGUMENTS` contains `search` or `find`, execute: `finsocnet search <query>`
- If `$ARGUMENTS` contains `view`, execute: `finsocnet view <id>`
- If `$ARGUMENTS` contains `hypo` or `list`, execute: `finsocnet hypo <filter>`
- If `$ARGUMENTS` contains `creators`, execute: `finsocnet creators`
- If `$ARGUMENTS` contains `contents`, execute: `finsocnet contents`
- If `$ARGUMENTS` contains `skills`, execute: `finsocnet skills`
- Otherwise, execute: `finsocnet search "$ARGUMENTS"`

Present the output cleanly to the user with hypothesis IDs, creator attribution, empirical claims, setup conditions, holding periods, and timestamped quotes.
