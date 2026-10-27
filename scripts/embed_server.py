#!/usr/bin/env python3
"""
Lightweight embedding worker for FinSocNet.
Communicates via JSON-RPC lines over stdin/stdout.
Uses sentence-transformers/all-MiniLM-L6-v2 (384 dimensions).
"""

import sys
import json
import os

def main():
    # Announce initializing
    sys.stdout.write(json.dumps({"status": "initializing"}) + "\n")
    sys.stdout.flush()

    try:
        from sentence_transformers import SentenceTransformer
        model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        model = SentenceTransformer(model_name)
        sys.stdout.write(json.dumps({"status": "ready", "dim": 384, "model": model_name}) + "\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stdout.write(json.dumps({"status": "error", "error": str(e)}) + "\n")
        sys.stdout.flush()
        sys.exit(1)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            action = req.get("action")
            req_id = req.get("id")

            if action == "embed":
                text = req.get("text", "")
                vec = model.encode(text, normalize_embeddings=True).tolist()
                res = {"id": req_id, "vector": vec}
                sys.stdout.write(json.dumps(res) + "\n")
                sys.stdout.flush()

            elif action == "embed_batch":
                texts = req.get("texts", [])
                if not texts:
                    res = {"id": req_id, "vectors": []}
                else:
                    vecs = model.encode(texts, normalize_embeddings=True, batch_size=32).tolist()
                    res = {"id": req_id, "vectors": vecs}
                sys.stdout.write(json.dumps(res) + "\n")
                sys.stdout.flush()

            elif action == "ping":
                sys.stdout.write(json.dumps({"id": req_id, "status": "pong"}) + "\n")
                sys.stdout.flush()

            elif action == "exit":
                break
        except Exception as e:
            sys.stdout.write(json.dumps({"id": req.get("id"), "error": str(e)}) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
