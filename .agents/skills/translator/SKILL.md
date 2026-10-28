---
name: translator
description: Detect the language of stored content and of user questions, and translate everything that is not English into English so it can be embedded and searched. Use whenever a content has no language yet (`kb translate detect-pending`), a non-English content needs English text for semantic search (`kb translate pending`), or a user question is not in English and must become an English Query Card before `kb card search`. The agent does all detecting and translating by reading; scripts only store the verdicts.
license: MIT
compatibility: Requires the FinSocNet repository (finsocnet kb CLI). No scripts of its own.
metadata:
  author: finsocnet
  version: "1.0.0"
  priority: "P1"
  status: ready
  phase: "9"
  spec: specs/10-semantic-search.md
---

# Translator

Semantic search embeds **English** text only (config/embedding.yaml). Cards are already English by contract; this skill makes the rest of the knowledge reachable: it decides the language of every content, translates non-English segments, and turns non-English questions into English ones. You do it by reading and writing; `kb` stores the result. Never use a language-detection library or a translation API.

## 1. Detect the language of contents

1. `kb run start --skill translator --goal "detect languages" …` → `R`.
2. `kb translate detect-pending --limit 20` → contents with `language` unset and a sample (first 3 segments, 700 chars each) of their text.
3. For each content, read the sample and decide:
   - one BCP-47 tag for the main language: `en`, `vi`, `es`, `pt-BR`, `zh-Hans`, `ja`, `ar`…;
   - `mixed` when segments clearly differ (a bilingual podcast, a thread where replies switch language). Mixed contents are resolved per segment in step 2.
   - Code, tickers and numbers only (a Pine script, a table) → the language of its comments or title; if none, `en`.
   - Do not guess from a single word or a name. If the sample is too short to tell, look at more of it: `kb content view <id> --from-seq 0 --to-seq 10`.
4. Write `data/work/R/languages.json` → `[{"content_id": "…", "language": "vi"}]`, then `kb translate set-language --file … --run R`. Until a content has a language it is **not embedded**.

## 2. Translate what is not English

1. `kb translate pending --limit 50` (optionally `--content <id>`) → segments of contents whose language is not English and that have no English text yet.
2. Translate each segment into English **faithfully**:
   - keep numbers, tickers, units, indicator names and percentages exactly (`MA20` stays `MA20`, `2R` stays `2R`);
   - keep the speaker's meaning and register, do not summarize, do not add advice, do not "improve" a rule;
   - keep slang you cannot translate in quotes with a short gloss: `"no-brainer" (an obvious trade)`;
   - leave a quote that is already English as it is.
3. Write `data/work/R/translations.json`:
   ```json
   [{"content_id": "forum:f319.com:123", "seq": 4, "source_lang": "vi", "text_en": "I always cut the loss when the price closes below the 20 day average."},
    {"content_id": "podcast:abc:ep1", "seq": 9, "source_lang": "en"}]
   ```
   For a `mixed` content mark the segments that are already English with `"source_lang": "en"` and **no** `text_en` (the original text is recorded).
4. `kb translate put --file … --run R`. Fix every problem it lists and send again; the call is idempotent.
5. `kb embed sync --kinds segment` embeds the translated segments; `kb embed status` shows what is pending.

The **original text is never replaced**: quotes in cards keep the source language (specs/02 §English cards), the translation is only a search aid. Do not translate inside `content_segments`.

## 3. Translate a question (search time)

Used by `knowledge-search` before it writes the Query Card:

1. Read the question. If it is not English, translate it to a plain English statement of what the user wants to know. Keep names (people, tickers) as written.
2. Write the **Query Card** in English from that statement (subject, vocabulary terms, English aliases) — see `knowledge-transformer/references/query_examples.md`.
3. Answer in the language of the user's question; quotes stay as the source wrote them, with your translation after them in brackets.

## Errors and edge cases

| Situation | Do |
|---|---|
| `VALIDATION_ERROR` from `translate put` | `error.details` lists each segment; fix and resend. |
| A content is wrongly tagged | Set it again with `set-language`; translations already stored stay (re-run `pending` to see what is missing). |
| 5000 untranslated segments | Work per content, most-cited or newest first (`--content`); translation is incremental, search works with what is embedded. |
| The text is unreadable (OCR garbage, binary) | Set `language` to `und` and skip it; for binaries use `reverse-anything`. |

## References

- `references/glossary_vi_es_zh.md` — how to render recurring trading terms, so translations stay consistent.
