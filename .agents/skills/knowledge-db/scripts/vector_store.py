#!/usr/bin/env python3
"""
Vector Store integration using Chroma and open-source Hugging Face embeddings
(sentence-transformers/all-MiniLM-L6-v2) for semantic search and RAG over user knowledge.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "data/chroma_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
HYPOTHESES_COLLECTION_NAME = "hypotheses"
CONTENT_CHUNKS_COLLECTION_NAME = "content_chunks"

_embedding_function = None
_chroma_client = None


def get_embedding_func():
    global _embedding_function
    if _embedding_function is None:
        _embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
    return _embedding_function


def get_chroma_client(persist_dir: str = CHROMA_PERSIST_DIR) -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=persist_dir)
    return _chroma_client


def get_hypotheses_collection(client: Optional[chromadb.PersistentClient] = None):
    if client is None:
        client = get_chroma_client()
    return client.get_or_create_collection(
        name=HYPOTHESES_COLLECTION_NAME,
        embedding_function=get_embedding_func(),
        metadata={"hnsw:space": "cosine"},
    )


def get_content_chunks_collection(client: Optional[chromadb.PersistentClient] = None):
    if client is None:
        client = get_chroma_client()
    return client.get_or_create_collection(
        name=CONTENT_CHUNKS_COLLECTION_NAME,
        embedding_function=get_embedding_func(),
        metadata={"hnsw:space": "cosine"},
    )


def format_hypothesis_document(h: dict[str, Any]) -> str:
    parts = [
        f"Title: {h.get('title', '')}",
        f"Direction: {h.get('direction', 'NEUTRAL')}",
        f"Category: {h.get('category', 'general')}",
        f"Platform: {h.get('platform', 'unknown')}",
        f"Statement: {h.get('hypothesis_statement', '')}",
    ]
    if h.get("setup_conditions"):
        parts.append(f"Setup Conditions: {h['setup_conditions']}")
    if h.get("holding_period"):
        parts.append(f"Holding Period: {h['holding_period']}")
    if h.get("statistical_claim"):
        parts.append(f"Statistical Evidence: {h['statistical_claim']}")
    if h.get("verbatim_quote"):
        parts.append(f"Quote: {h['verbatim_quote']}")
    return "\n".join(parts)


def index_hypothesis_in_vector_store(h: dict[str, Any]) -> None:
    col = get_hypotheses_collection()
    doc_id = f"hyp_{h['id']}"
    doc_text = format_hypothesis_document(h)
    meta = {
        "hypothesis_id": int(h["id"]),
        "content_id": str(h.get("content_id", "")),
        "user_id": str(h.get("user_id", "")),
        "platform": str(h.get("platform", "youtube")),
        "category": str(h.get("category", "")),
        "direction": str(h.get("direction", "")),
        "title": str(h.get("title", "")),
        "timestamp_formatted": str(h.get("timestamp_formatted", "")),
        "holding_period": str(h.get("holding_period", "")),
    }
    col.upsert(ids=[doc_id], documents=[doc_text], metadatas=[meta])


def index_content_chunks(
    content_id: str,
    user_id: str,
    platform: str,
    content_title: str,
    snippets: list[dict[str, Any]],
) -> int:
    col = get_content_chunks_collection()
    ids: list[str] = []
    docs: list[str] = []
    metas: list[dict[str, Any]] = []

    current_block: list[str] = []
    block_start = 0.0

    for i, s in enumerate(snippets):
        if not current_block:
            block_start = s.get("start", 0.0)
        current_block.append(s.get("text", ""))

        is_last = (i == len(snippets) - 1)
        next_start = snippets[i + 1].get("start", 0.0) if not is_last else s.get("start", 0.0)
        time_span = s.get("start", 0.0) + s.get("duration", 0.0) - block_start

        if is_last or time_span >= 30.0 or (next_start - (s.get("start", 0.0) + s.get("duration", 0.0))) > 2.5:
            text = " ".join(current_block).strip()
            mins = int(block_start // 60)
            secs = int(block_start % 60)
            ts_str = f"{mins:02d}:{secs:02d}"

            chunk_id = f"chunk_{content_id}_{int(block_start)}"
            doc = f"Content: {content_title} ({platform})\nTime: [{ts_str}]\nText: {text}"
            meta = {
                "content_id": content_id,
                "user_id": user_id,
                "platform": platform,
                "title": content_title,
                "timestamp_start": float(block_start),
                "timestamp_formatted": ts_str,
            }

            ids.append(chunk_id)
            docs.append(doc)
            metas.append(meta)
            current_block = []

    if ids:
        col.upsert(ids=ids, documents=docs, metadatas=metas)
    return len(ids)


def search_hypotheses_vectors(
    query: str,
    n_results: int = 5,
    category: Optional[str] = None,
    direction: Optional[str] = None,
    platform: Optional[str] = None,
) -> list[dict[str, Any]]:
    col = get_hypotheses_collection()
    filters = []
    if category:
        filters.append({"category": category})
    if direction:
        filters.append({"direction": direction.upper()})
    if platform:
        filters.append({"platform": platform.lower()})

    where_filter = None
    if len(filters) == 1:
        where_filter = filters[0]
    elif len(filters) > 1:
        where_filter = {"$and": filters}

    res = col.query(
        query_texts=[query],
        n_results=n_results,
        where=where_filter,
    )

    out = []
    if res and res["ids"] and res["ids"][0]:
        for i in range(len(res["ids"][0])):
            distance = res["distances"][0][i] if res.get("distances") else 0.0
            similarity = round(1.0 - distance, 4)
            out.append({
                "id": res["ids"][0][i],
                "score": similarity,
                "document": res["documents"][0][i],
                "metadata": res["metadatas"][0][i],
            })
    return out


def search_content_chunks_vectors(
    query: str,
    n_results: int = 5,
    content_id: Optional[str] = None,
    platform: Optional[str] = None,
) -> list[dict[str, Any]]:
    col = get_content_chunks_collection()
    filters = []
    if content_id:
        filters.append({"content_id": content_id})
    if platform:
        filters.append({"platform": platform.lower()})

    where_filter = None
    if len(filters) == 1:
        where_filter = filters[0]
    elif len(filters) > 1:
        where_filter = {"$and": filters}

    res = col.query(
        query_texts=[query],
        n_results=n_results,
        where=where_filter,
    )

    out = []
    if res and res["ids"] and res["ids"][0]:
        for i in range(len(res["ids"][0])):
            distance = res["distances"][0][i] if res.get("distances") else 0.0
            similarity = round(1.0 - distance, 4)
            out.append({
                "id": res["ids"][0][i],
                "score": similarity,
                "document": res["documents"][0][i],
                "metadata": res["metadatas"][0][i],
            })
    return out
