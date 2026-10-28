# Getting started

## Requirements

`uv`, Python ≥ 3.11, SQLite ≥ 3.38. Optional: Node ≥ 22 for the web UI and for REA ([Reverse anything](reverse-anything.md)), `ffmpeg` for transcription, Chrome/Chromium for browser-based platforms. About 0.5 GB of disk for the embedding model.

## Install

```bash
git clone <this repository> finsocnet && cd finsocnet
./install.sh                      # remote host: CLI + harness registration   (add --local on your own laptop: session export only)
# or by hand
uv sync
uv run finsocnet kb init          # creates data/knowledge.db, applies migrations 001-005, loads the vocabulary seed
uv run finsocnet install all      # slash commands and skill links for every harness it finds (Claude Code, OMP, Pi, Hermes, Codex, OpenClaw)
```

`finsocnet kb doctor` must print `"ok": true`.

## First run: one video, end to end

Every workflow starts with a **run** (an audit record) and passes it to every write.

```bash
R=$(uv run finsocnet kb run start --skill market-idea-miner --goal "mine one video" --harness claude-code --model <model> | jq -r .data.run_id)

# 1. fetch and store (any platform skill; --ingest stores it)
uv run .agents/skills/youtube-extractor/scripts/youtube.py fetch "https://www.youtube.com/watch?v=<id>" --ingest --run $R

# 2. tell the system what language it is (agent: skill translator) and mine it (agent: skill market-idea-miner)
#    -> Knowledge Cards written as JSON, validated, deduplicated, committed
uv run finsocnet kb card validate --file cards.json
uv run finsocnet kb card candidates --file cards.json
uv run finsocnet kb card commit --file decisions.json --run $R

# 3. make it searchable by meaning and ask
uv run finsocnet kb embed sync
uv run finsocnet search "when should I take profits on a breakout?" --ui

uv run finsocnet kb run end --run $R --outcome success --stats '{"cards": 5}'
```

In a harness you do not type these: `/finsocnet:mine <url>`, `/finsocnet:search <question>`, `/finsocnet:strategy <person>`, `/finsocnet:explore <seed>`. The skills carry the procedures.

## Explore on your own

```bash
uv run finsocnet explore add "pairs trading"                    # any topic, URL, @handle, person or query
uv run finsocnet explore add https://quant.stackexchange.com/questions/tagged/risk-management
# in the harness: /finsocnet:explore-step   (one step; /loop 30m /finsocnet:explore-step to keep going)
```

## Look at it

```bash
uv run finsocnet kb stats --ui
make web-install && make web-build && make web-start           # http://localhost:3000  (see Web UI)
```

Next: [Concepts](concepts.md).
