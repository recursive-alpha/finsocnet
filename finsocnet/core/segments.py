"""Helpers every adapter uses to build quotable segments (specs/00 §7.1)."""

from __future__ import annotations

import re
from typing import Any, Iterable

from finsocnet.core.normalize import clean_text

WINDOW_SEC = 45.0
WINDOW_CHARS = 600
URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")
HANDLE_RE = re.compile(r"(?<![\w/])@[A-Za-z0-9_.]{2,30}")
TICKER_RE = re.compile(r"(?<![\w$])\$[A-Z]{1,6}(?:\.[A-Z])?\b")
MIN_PARAGRAPH = 80


def transcript_windows(entries: Iterable[dict[str, Any]], speaker_hint: str | None = None) -> list[dict[str, Any]]:
    """Merge `{start, duration|end, text}` caption lines into windows of <= 45 s and <= 600 chars."""
    windows: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    for e in entries:
        text = " ".join(str(e.get("text", "")).split())
        if not text:
            continue
        start = float(e.get("start", 0) or 0)
        end = float(e["end"]) if "end" in e else start + float(e.get("duration", 0) or 0)
        if cur is not None and (end - cur["start"] > WINDOW_SEC or len(cur["text"]) + 1 + len(text) > WINDOW_CHARS):
            windows.append(cur)
            cur = None
        if cur is None:
            cur = {"start": start, "end": end, "text": text}
        else:
            cur["text"] += " " + text
            cur["end"] = max(cur["end"], end)
    if cur:
        windows.append(cur)
    return [{"seq": i, "kind": "transcript", "locator": {"start_sec": round(w["start"], 2), "end_sec": round(w["end"], 2)}, "text": clean_text(w["text"]),
             **({"speaker_hint": speaker_hint} if speaker_hint else {})} for i, w in enumerate(windows)]


def split_paragraphs(text: str, min_len: int = MIN_PARAGRAPH) -> list[str]:
    """Blank-line paragraphs; paragraphs shorter than `min_len` merge into the next one."""
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out: list[str] = []
    carry = ""
    for p in parts:
        cand = f"{carry}\n\n{p}" if carry else p
        if len(cand) < min_len:
            carry = cand
        else:
            out.append(cand)
            carry = ""
    if carry:
        if out:
            out[-1] += "\n\n" + carry
        else:
            out.append(carry)
    return out


def paragraph_segments(text: str, kind: str = "paragraph", start_seq: int = 0, extra_locator: dict[str, Any] | None = None, min_len: int = MIN_PARAGRAPH) -> list[dict[str, Any]]:
    return [{"seq": start_seq + i, "kind": kind, "locator": {"para": i, **(extra_locator or {})}, "text": clean_text(p)} for i, p in enumerate(split_paragraphs(text, min_len))]


def html_to_markdown(html: str) -> str:
    from markdownify import markdownify
    return clean_text(markdownify(html or "", heading_style="ATX", strip=["script", "style"]))


def html_paragraphs(html: str, kind: str = "paragraph", start_seq: int = 0) -> list[dict[str, Any]]:
    return paragraph_segments(html_to_markdown(html), kind, start_seq)


def code_segments(code: str, path: str | None = None, lines_per: int = 60, start_seq: int = 0) -> list[dict[str, Any]]:
    lines = code.splitlines()
    out = []
    for i in range(0, len(lines), lines_per):
        chunk = "\n".join(lines[i:i + lines_per]).strip("\n")
        if chunk.strip():
            loc: dict[str, Any] = {"line_start": i + 1, "line_end": min(i + lines_per, len(lines))}
            if path:
                loc["path"] = path
            out.append({"seq": start_seq + len(out), "kind": "code", "locator": loc, "text": chunk})
    return out


def renumber(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for i, s in enumerate(segments):
        s["seq"] = i
    return segments


def refs(text: str) -> dict[str, list[str]]:
    """URLs, @handles and $TICKERS found in a text, de-duplicated in order."""
    uniq = lambda xs: list(dict.fromkeys(xs))
    return {"links": uniq(u.rstrip(".,;") for u in URL_RE.findall(text or "")), "mentions": uniq(HANDLE_RE.findall(text or "") + TICKER_RE.findall(text or ""))}
