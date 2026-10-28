"""FTS5 query building and sanitizing (specs/03-pipelines.md §2)."""

from __future__ import annotations

import re

STOPWORDS = frozenset(
    """a an and are as at be but by for from has have he her his i if in into is it its of on or our she so
    than that the their them then there these they this to was we were what when which who will with you your
    about after again all also any been before being between both can could did does doing down during each
    few how just me more most my no nor not now off once only other out over own same should some such too
    under until up very while would""".split()
)
GRAMMAR_KEYWORDS = frozenset(
    "IF THEN AND OR WHEN TENDS TO CAUSES BECAUSE IS HAS IMPROVES HURTS WITHIN UNTIL LONG SHORT ADD EXIT EXIT_PARTIAL AVOID HOLD SIZE NONE".split()
)

_WORD = re.compile(r"[\w']+", re.UNICODE)


def quote_token(token: str) -> str:
    """Quote one token for FTS5: `"token"` with internal quotes doubled."""
    return '"' + token.replace('"', '""') + '"'


def tokens(text: str) -> list[str]:
    return [t.strip("'") for t in _WORD.findall(text) if t.strip("'")]


def significant_words(text: str, limit: int | None = None) -> list[str]:
    """Tokens that are neither stopwords nor claim-grammar keywords, length >= 3, in order of first appearance."""
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens(text):
        low = t.lower()
        if len(low) < 3 or low in STOPWORDS or t in GRAMMAR_KEYWORDS or low in seen:
            continue
        seen.add(low)
        out.append(low)
        if limit and len(out) >= limit:
            break
    return out


def match_any(words: list[str], column: str | None = None) -> str | None:
    """`col : ("a" OR "b")`; None when there is nothing to search."""
    words = [w for w in words if w]
    if not words:
        return None
    expr = " OR ".join(quote_token(w) for w in words)
    return f"{column} : ({expr})" if column else f"({expr})"


def match_text(text: str, mode: str = "and") -> str | None:
    """Turn free text into a safe FTS5 expression (every token quoted)."""
    toks = tokens(text)
    if not toks:
        return None
    joiner = " OR " if mode == "or" else " "
    return joiner.join(quote_token(t) for t in toks)
