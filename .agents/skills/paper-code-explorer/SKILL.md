---
name: paper-code-explorer
description: Explore scientific research papers and open-source code implementations across arXiv and Papers With Code (Hugging Face Papers). Search quantitative finance, ML trading algorithms, and market microstructure, and retrieve GitHub code repositories and PDFs.
license: MIT
metadata:
  version: "1.0.0"
  author: "finsocnet"
---

# Paper & Code Explorer (arXiv & Papers With Code)

Research tool for scientific papers and open-source code implementations across arXiv and Papers With Code (Hugging Face Papers index). Discovers quantitative finance algorithms, market microstructure research, deep learning trading models, and verified GitHub repositories.

## Capabilities
1. **Search Papers with Open-Source Code:** Search arXiv literature and filter exclusively for papers with public GitHub code implementations (`--has-code`).
2. **Paper Details & PDF Downloads:** Retrieve full abstracts, AI summaries, author lists, linked models/datasets, and download open-access PDFs (`data/papers/<arxiv_id>.pdf`).
3. **Trending AI & Quant Research:** Inspect daily upvoted papers across machine learning and algorithmic trading.
4. **Knowledge DB Integration:** Automatically ingests papers, abstracts, and code links into `data/knowledge.db` (`platform='arxiv'`, `content_type='paper'`).

## Usage

### 1. Search Papers with Open-Source Code Repositories
```bash
uv run .agents/skills/paper-code-explorer/scripts/search_papers.py "market microstructure trading" --has-code --ingest-db
```

### 2. Inspect Paper and Download Open-Access PDF
```bash
uv run .agents/skills/paper-code-explorer/scripts/get_paper.py "2610.34467" --auto-download --ingest-db
```

### 3. Explore Daily Trending Papers
```bash
uv run .agents/skills/paper-code-explorer/scripts/explore_trending.py --limit 5 --has-code
```

## References
See [references/qfin_categories.md](references/qfin_categories.md) for arXiv quantitative finance taxonomy (`q-fin.TR`, `q-fin.PM`, `q-fin.RM`).
