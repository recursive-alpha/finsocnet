---
description: FinSocNet Multi-Platform Financial Intelligence, Strategy Rulebooks & Hypothesis Search
---

You have direct access to the FinSocNet intelligence and trading strategy storage engine.
Execute the `finsocnet` CLI tool via Bash based on the user's intent or arguments:

- **Search Hypotheses:** `finsocnet search "<query>"` (semantic vector search across all creators)
- **Get Creator Strategy Rulebook:** `finsocnet strategy <creator_or_strategy>` (e.g. minervini, qullamaggie, lance, smb, lewis-kelly, humbled, dante, brandt, furey)
- **View Full Hypothesis Card:** `finsocnet view <id>` (verbatim quotes, exact timestamps, setup filters)
- **Explore Creators & Content:** `finsocnet explore <youtube|x|reddit|medium|arxiv|annas_archive> "<target>"`
- **List Skills:** `finsocnet skills` (shows System Skills vs Improved Strategy Skills)
- **RAG Content Chunks:** `finsocnet rag "<query>"`
- **Database Stats:** `finsocnet stats`

If the user invokes subcommands like `/finsocnet:search <query>`, `/finsocnet:strategy <name>`, or `/finsocnet:explore <platform> <target>`, parse the arguments and execute the matching CLI command above.

Always present output with clear creator attribution, setup conditions, holding periods, and verbatim citations.
