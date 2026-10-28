"""Semantic search over the knowledge base (specs/10-semantic-search.md, ADR-009 supersedes the embedding part of ADR-001).

Vectors are float32 BLOBs in the `embeddings` table (one row per kind/ref/model) and are scored by brute force with numpy: the
corpus is cards, not billions of chunks. Scripts never call an LLM: the embedding model is a local ONNX encoder (fastembed), and
translation into English is done by the agent (skill `translator`) before anything is embedded.
"""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
from functools import lru_cache
from typing import Any, Iterable

import numpy as np
import yaml

from finsocnet.core import config
from finsocnet.core.db import loads, transaction
from finsocnet.core.output import CliError

KINDS = ("card", "segment", "person", "skill")
HASH_DIM = 512


# --- settings and providers -----------------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _file_settings() -> dict[str, Any]:
    p = config.repo_root() / "config" / "embedding.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}


def settings() -> dict[str, Any]:
    s = dict(_file_settings())
    s["provider"] = os.getenv("FINSOCNET_EMBED_PROVIDER", s.get("provider", "fastembed"))
    s["model"] = os.getenv("FINSOCNET_EMBED_MODEL", s.get("model", "snowflake/snowflake-arctic-embed-m"))
    s.setdefault("batch_size", 32)
    s.setdefault("max_chars", 2000)
    s.setdefault("query_prefix", "")
    s.setdefault("doc_prefix", "")
    return s


def model_id() -> str:
    s = settings()
    return f"hashing-{HASH_DIM}" if s["provider"] == "hashing" else s["model"]


_TOKEN = re.compile(r"[a-z0-9_]+")


def _hash_vec(text: str) -> np.ndarray:
    """Signed feature hashing over unigrams and bigrams: deterministic, offline, no model download."""
    v = np.zeros(HASH_DIM, dtype=np.float32)
    toks = _TOKEN.findall(text.lower().replace("_", " "))
    grams = toks + [f"{a} {b}" for a, b in zip(toks, toks[1:])]
    for g in grams:
        h = int.from_bytes(hashlib.blake2b(g.encode(), digest_size=8).digest(), "big")
        v[h % HASH_DIM] += 1.0 if (h >> 63) & 1 else -1.0
    return v


@lru_cache(maxsize=2)
def _fastembed(model: str, cache_dir: str | None) -> Any:
    try:
        from fastembed import TextEmbedding
    except ImportError as e:  # pragma: no cover - dependency is declared
        raise CliError("UNSUPPORTED", "fastembed is not installed", "run `uv sync`, or set FINSOCNET_EMBED_PROVIDER=hashing") from e
    try:
        return TextEmbedding(model_name=model, cache_dir=str(config.resolve_path(cache_dir)) if cache_dir else None)
    except Exception as e:  # noqa: BLE001 - download/ONNX errors
        raise CliError("UNSUPPORTED", f"cannot load embedding model {model}: {str(e).splitlines()[0][:200]}",
                       "check network and disk space, pick a smaller model in config/embedding.yaml, or set FINSOCNET_EMBED_PROVIDER=hashing") from e


def _normalize(m: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(m, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return (m / n).astype(np.float32)


def embed_texts(texts: list[str], *, query: bool = False) -> np.ndarray:
    """L2-normalised float32 matrix, one row per text. `query=True` applies the model's query prefix."""
    s = settings()
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)
    prefix = s["query_prefix"] if query else s["doc_prefix"]
    texts = [(prefix + t)[: int(s["max_chars"]) + len(prefix)] for t in texts]
    if s["provider"] == "hashing":
        return _normalize(np.stack([_hash_vec(t) for t in texts]))
    model = _fastembed(s["model"], s.get("cache_dir"))
    out: list[np.ndarray] = []
    bs = int(s["batch_size"])
    for i in range(0, len(texts), bs):
        out.extend(np.asarray(v, dtype=np.float32) for v in model.embed(texts[i:i + bs]))
    return _normalize(np.stack(out))


def embed_query(text: str) -> np.ndarray:
    return embed_texts([text], query=True)[0]


# --- the English text that gets embedded ---------------------------------------------------------------------------

def _nat(term: str) -> str:
    return term.replace("_", " ")


def card_text(card: dict[str, Any]) -> str:
    """Canonical English form of a card: subject, claim, conditions, aliases, terms in words."""
    parts = [card.get("subject") or "", card.get("claim") or ""]
    if card.get("conditions"):
        parts.append("Conditions: " + "; ".join(card["conditions"]))
    if card.get("aliases"):
        parts.append("Also said as: " + "; ".join(card["aliases"]))
    if card.get("terms"):
        parts.append("Topics: " + ", ".join(_nat(t) for t in card["terms"]))
    return ". ".join(p.strip().rstrip(".") for p in parts if p and p.strip())


def query_text(query_card: dict[str, Any]) -> str:
    """The English knowledge query (a Query Card) as one string."""
    parts = [query_card.get("subject") or ""]
    if query_card.get("aliases"):
        parts.append("Also said as: " + "; ".join(query_card["aliases"]))
    if query_card.get("terms"):
        parts.append("Topics: " + ", ".join(_nat(t) for t in query_card["terms"]))
    return ". ".join(p.strip().rstrip(".") for p in parts if p and p.strip())


def _h(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


# --- store -----------------------------------------------------------------------------------------------------------

def _pending(conn: sqlite3.Connection, kind: str, model: str) -> Iterable[tuple[str, str]]:
    """(ref, english text) for rows of `kind` that have no up-to-date vector for `model`."""
    have = {r[0]: r[1] for r in conn.execute("SELECT ref, text_hash FROM embeddings WHERE kind = ? AND model = ?", (kind, model))}
    if kind == "card":
        from finsocnet.core import cards
        for r in conn.execute("SELECT id FROM knowledge_cards WHERE status = 'active' ORDER BY id"):
            c = cards.card_row(conn, r[0])
            t = card_text(c)
            if have.get(str(c["id"])) != _h(t):
                yield str(c["id"]), t
    elif kind == "segment":
        # English only: the segment's translation, or its own text when the agent set the content's language to English.
        from finsocnet.core import translate
        q = """SELECT s.content_id, s.seq, s.text, c.language, t.text_en FROM content_segments s
               JOIN contents c ON c.id = s.content_id LEFT JOIN segment_translations t ON t.content_id = s.content_id AND t.seq = s.seq
               WHERE c.process_status != 'skipped_duplicate' ORDER BY s.content_id, s.seq"""
        for r in conn.execute(q):
            text = r["text_en"] or (r["text"] if translate.is_english_tag(r["language"]) else None)
            ref = f"{r['content_id']}#{r['seq']}"
            if text and have.get(ref) != _h(text):
                yield ref, text
    elif kind == "person":
        # name and the agent-written profile fields (English by contract); the free-text bio is in any language, so it is not embedded
        for r in conn.execute("SELECT id, canonical_name, moniker, trading_style, primary_markets FROM persons WHERE status = 'active' ORDER BY id"):
            t = ". ".join(x for x in (r["canonical_name"], r["moniker"] or "", r["trading_style"] or "", r["primary_markets"] or "") if x)
            if have.get(r["id"]) != _h(t):
                yield r["id"], t
    elif kind == "skill":
        for r in conn.execute("SELECT id, title, summary, content_markdown FROM person_skills ORDER BY id"):
            t = ". ".join(x for x in (r["title"], r["summary"] or "", (r["content_markdown"] or "")[:1500]) if x)
            if have.get(str(r["id"])) != _h(t):
                yield str(r["id"]), t


def sync(conn: sqlite3.Connection, kinds: Iterable[str] = ("card", "person", "skill"), limit: int | None = None) -> dict[str, Any]:
    """Embed every row without an up-to-date vector for the current model. Idempotent and resumable."""
    model, report = model_id(), {}
    for kind in kinds:
        if kind not in KINDS:
            raise CliError("USAGE", f"unknown kind {kind!r}", f"one of {', '.join(KINDS)}")
        todo = list(_pending(conn, kind, model))
        if limit is not None:
            todo = todo[:limit]
        done = 0
        for i in range(0, len(todo), 256):
            chunk = todo[i:i + 256]
            vecs = embed_texts([t for _, t in chunk])
            with transaction(conn):
                for (ref, text), v in zip(chunk, vecs):
                    conn.execute("INSERT INTO embeddings (kind, ref, model, dim, text_hash, vector) VALUES (?, ?, ?, ?, ?, ?) "
                                 "ON CONFLICT(kind, ref, model) DO UPDATE SET dim = excluded.dim, text_hash = excluded.text_hash, vector = excluded.vector, "
                                 "created_at = strftime('%Y-%m-%dT%H:%M:%SZ','now')", (kind, ref, model, int(v.shape[0]), _h(text), v.tobytes()))
            done += len(chunk)
        report[kind] = {"embedded": done, "remaining": len(todo) - done}
    _cache.clear()
    return {"model": model, "kinds": report}


def status(conn: sqlite3.Connection) -> dict[str, Any]:
    model = model_id()
    out: dict[str, Any] = {"model": model, "provider": settings()["provider"], "kinds": {}}
    for kind in KINDS:
        n = conn.execute("SELECT COUNT(*) FROM embeddings WHERE kind = ? AND model = ?", (kind, model)).fetchone()[0]
        pend = sum(1 for _ in _pending(conn, kind, model))
        out["kinds"][kind] = {"embedded": n, "pending": pend}
    out["other_models"] = [dict(r) for r in conn.execute("SELECT model, kind, COUNT(*) AS n FROM embeddings WHERE model != ? GROUP BY model, kind", (model,))]
    return out


_cache: dict[tuple[str, str, int], tuple[list[str], np.ndarray]] = {}


def _matrix(conn: sqlite3.Connection, kind: str, model: str) -> tuple[list[str], np.ndarray]:
    n = conn.execute("SELECT COUNT(*) FROM embeddings WHERE kind = ? AND model = ?", (kind, model)).fetchone()[0]
    key = (kind, model, n)
    if key in _cache:
        return _cache[key]
    rows = conn.execute("SELECT ref, dim, vector FROM embeddings WHERE kind = ? AND model = ? ORDER BY ref", (kind, model)).fetchall()
    refs = [r["ref"] for r in rows]
    m = np.stack([np.frombuffer(r["vector"], dtype=np.float32) for r in rows]) if rows else np.zeros((0, 0), dtype=np.float32)
    _cache[key] = (refs, m)
    return refs, m


def vector_search(conn: sqlite3.Connection, query: str, kinds: Iterable[str] = ("card",), limit: int = 50) -> list[dict[str, Any]]:
    """Cosine ranking of `query` (English) against stored vectors of the current model. Empty when nothing is embedded yet."""
    model = model_id()
    kinds = list(kinds)
    mats = [(k, *_matrix(conn, k, model)) for k in kinds]
    if not any(len(r) for _, r, _ in mats):
        return []
    q = embed_query(query)
    hits: list[dict[str, Any]] = []
    for kind, refs, m in mats:
        if not refs or m.shape[1] != q.shape[0]:
            continue
        sims = m @ q
        top = np.argsort(-sims)[:limit]
        hits.extend({"kind": kind, "ref": refs[i], "score": float(sims[i])} for i in top)
    hits.sort(key=lambda h: -h["score"])
    return hits[:limit]


def card_vector_ranks(conn: sqlite3.Connection, query: str, limit: int = 50) -> dict[int, int]:
    """{card_id: rank} for the RRF fusion in `cards.retrieve` (rank 1 = closest)."""
    return {int(h["ref"]): i for i, h in enumerate(vector_search(conn, query, ("card",), limit), 1)}


def has_vectors(conn: sqlite3.Connection, kind: str = "card") -> bool:
    return conn.execute("SELECT 1 FROM embeddings WHERE kind = ? AND model = ? LIMIT 1", (kind, model_id())).fetchone() is not None
