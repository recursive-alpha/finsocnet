#!/usr/bin/env python3
"""
Pure SQLite Vector & Full-Text Search Store for FinSocNet.
Replaces Chroma with self-contained, embedded SQLite vector storage (float32 BLOBs)
and SQLite FTS5 for full-text search. No external daemon or Chroma required.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from dotenv import load_dotenv

load_dotenv()

DEFAULT_DB_PATH = Path(os.getenv("KNOWLEDGE_DB_PATH", "data/knowledge.db"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

_model = None


def get_embedding_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def encode_text(text: str) -> np.ndarray:
    """Encode text to 384-dim unit-normalized float32 vector."""
    model = get_embedding_model()
    vec = model.encode(text, normalize_embeddings=True)
    return vec.astype(np.float32)


def upsert_vector_embedding(
    conn: sqlite3.Connection,
    collection: str,
    entity_id: str,
    document: str,
    metadata: dict[str, Any],
    person_id: Optional[str] = None,
) -> str:
    """Embed and store a document in the vector_embeddings SQLite table."""
    vec = encode_text(document)
    vec_blob = vec.tobytes()
    doc_id = f"{collection}_{entity_id}"
    meta_json = json.dumps(metadata, ensure_ascii=False)

    conn.execute(
        """
        INSERT INTO vector_embeddings (id, collection, entity_id, person_id, document, metadata_json, embedding)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            document = excluded.document,
            metadata_json = excluded.metadata_json,
            embedding = excluded.embedding,
            person_id = excluded.person_id;
        """,
        (doc_id, collection, str(entity_id), person_id, document, meta_json, vec_blob),
    )
    conn.commit()
    return doc_id


def search_vector_sqlite(
    conn: sqlite3.Connection,
    collection: str,
    query_text: str,
    limit: int = 5,
    person_id: Optional[str] = None,
    filter_metadata: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """
    Search embeddings in SQLite using exact dot product cosine similarity.
    Blazing fast matrix-vector dot product in numpy directly from SQLite BLOBs.
    """
    query_vec = encode_text(query_text)

    sql = "SELECT id, entity_id, person_id, document, metadata_json, embedding FROM vector_embeddings WHERE collection = ?"
    params: list[Any] = [collection]
    if person_id:
        sql += " AND person_id = ?"
        params.append(person_id)

    rows = conn.execute(sql, params).fetchall()
    if not rows:
        return []

    ids = []
    entity_ids = []
    person_ids = []
    docs = []
    metas = []
    vectors = []

    for r in rows:
        meta = json.loads(r["metadata_json"])
        if filter_metadata:
            match = True
            for k, v in filter_metadata.items():
                if meta.get(k) != v:
                    match = False
                    break
            if not match:
                continue

        ids.append(r["id"])
        entity_ids.append(r["entity_id"])
        person_ids.append(r["person_id"])
        docs.append(r["document"])
        metas.append(meta)
        vec = np.frombuffer(r["embedding"], dtype=np.float32)
        vectors.append(vec)

    if not vectors:
        return []

    matrix = np.vstack(vectors)  # shape (N, 384)
    scores = np.dot(matrix, query_vec)  # Cosine similarity for unit vectors

    top_indices = np.argsort(scores)[::-1][:limit]

    results = []
    for idx in top_indices:
        results.append({
            "id": ids[idx],
            "entity_id": entity_ids[idx],
            "person_id": person_ids[idx],
            "score": round(float(scores[idx]), 4),
            "document": docs[idx],
            "metadata": metas[idx],
        })

    return results


def search_fts_sqlite(
    conn: sqlite3.Connection,
    table_name: str,
    query_text: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Full-text search using SQLite FTS5."""
    # Sanitize FTS5 query terms
    clean_terms = [re.sub(r"[^\w*]", "", w) for w in query_text.split() if w]
    if not clean_terms:
        return []
    fts_query = " OR ".join(clean_terms)

    try:
        sql = f"""
        SELECT rowid, rank, * FROM {table_name}
        WHERE {table_name} MATCH ?
        ORDER BY rank
        LIMIT ?
        """
        rows = conn.execute(sql, (fts_query, limit)).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        # Fallback to empty if FTS syntax error
        return []


def hybrid_search_ideas(
    conn: sqlite3.Connection,
    query_text: str,
    limit: int = 5,
    person_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Hybrid Search combining Vector similarity and FTS5 BM25 text match.
    Uses Reciprocal Rank Fusion (RRF) to score and rank results.
    """
    vec_results = search_vector_sqlite(conn, collection="market_ideas", query_text=query_text, limit=limit * 2, person_id=person_id)
    fts_results = search_fts_sqlite(conn, table_name="market_ideas_fts", query_text=query_text, limit=limit * 2)

    rrf_scores: dict[int, float] = {}
    doc_lookup: dict[int, dict[str, Any]] = {}

    k = 60.0
    for rank, r in enumerate(vec_results):
        try:
            e_id = int(r["entity_id"])
            rrf_scores[e_id] = rrf_scores.get(e_id, 0.0) + (1.0 / (k + rank + 1))
            doc_lookup[e_id] = r
        except Exception:
            continue

    for rank, r in enumerate(fts_results):
        e_id = r["rowid"]
        rrf_scores[e_id] = rrf_scores.get(e_id, 0.0) + (1.0 / (k + rank + 1))
        if e_id not in doc_lookup:
            # Fetch from market_ideas
            row = conn.execute("SELECT * FROM market_ideas WHERE id = ?", (e_id,)).fetchone()
            if row:
                doc_lookup[e_id] = {
                    "id": f"market_ideas_{e_id}",
                    "entity_id": str(e_id),
                    "person_id": row["person_id"],
                    "document": f"{row['title']}\n{row['idea_statement']}",
                    "metadata": dict(row),
                }

    sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[:limit]
    final_results = []
    for e_id in sorted_ids:
        item = doc_lookup[e_id]
        item["rrf_score"] = round(rrf_scores[e_id], 4)
        final_results.append(item)

    return final_results
