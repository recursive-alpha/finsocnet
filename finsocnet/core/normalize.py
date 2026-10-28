"""Text normalization (specs/00-conventions.md §5)."""

from __future__ import annotations

import hashlib
import re
import unicodedata

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_NON_ALNUM_SPACE = re.compile(r"[^\w\s]|_", re.UNICODE)
_NON_ALNUM = re.compile(r"[^\w]|_", re.UNICODE)
_WS = re.compile(r"\s+")


def clean_text(s: str) -> str:
    """NFC, strip control characters, unify line endings, collapse >2 blank lines."""
    s = unicodedata.normalize("NFC", s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = _CONTROL.sub("", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def hash_text(s: str) -> str:
    """sha256 of NFKC → casefold → letters/digits/space only → collapsed whitespace."""
    t = unicodedata.normalize("NFKC", s).casefold()
    t = _NON_ALNUM_SPACE.sub("", t)
    t = _WS.sub(" ", t).strip()
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def strip_diacritics(s: str) -> str:
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))


def quote_key(s: str) -> str:
    """NFKC → casefold → remove diacritics → keep letters/digits → collapse spaces.

    Punctuation is dropped without leaving a space, so "it's" and "its" match, but a changed word does not.
    """
    t = unicodedata.normalize("NFKC", s).casefold()
    t = strip_diacritics(t)
    t = re.sub(r"[^\w\s]|_", "", t, flags=re.UNICODE)
    return _WS.sub(" ", t).strip()


def quote_in(quote: str, text: str) -> bool:
    k = quote_key(quote)
    return bool(k) and k in quote_key(text)


def alias_key(alias: str) -> str:
    """Casefold, strip leading '@' / 'u/', remove diacritics, collapse spaces."""
    t = unicodedata.normalize("NFKC", alias).strip().casefold()
    t = re.sub(r"^(@|u/|/u/)", "", t)
    t = strip_diacritics(t)
    return _WS.sub(" ", t).strip()
