"""
Semantic vector search and RAG retrieval using Chroma and open-source Hugging Face embeddings.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import vector store directly from knowledge-db skill
_KNOWLEDGE_SKILL_DIR = Path(__file__).resolve().parent.parent / ".agents" / "skills" / "knowledge-db" / "scripts"
if str(_KNOWLEDGE_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_KNOWLEDGE_SKILL_DIR))

try:
    from vector_store import search_content_chunks_vectors, search_hypotheses_vectors
except ImportError:
    search_hypotheses_vectors = None
    search_content_chunks_vectors = None


def vector_search(
    query: str,
    limit: int = 10,
    category: Optional[str] = None,
    direction: Optional[str] = None,
    platform: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Execute semantic vector search over trading hypotheses."""
    if search_hypotheses_vectors is None:
        return []
    try:
        return search_hypotheses_vectors(
            query=query,
            n_results=limit,
            category=category,
            direction=direction,
            platform=platform,
        )
    except Exception as e:
        print(f"[WARN] Vector search error: {e}", file=sys.stderr)
        return []


def rag_search(
    query: str,
    limit: int = 10,
    content_id: Optional[str] = None,
    platform: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Execute semantic RAG search across raw content and transcript chunks."""
    if search_content_chunks_vectors is None:
        return []
    try:
        return search_content_chunks_vectors(
            query=query,
            n_results=limit,
            content_id=content_id,
            platform=platform,
        )
    except Exception as e:
        print(f"[WARN] RAG search error: {e}", file=sys.stderr)
        return []
