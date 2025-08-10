#!/usr/bin/env python3
"""
Vector Memory (Chroma)
Lightweight vector memory using Chroma and sentence-transformers.
"""

from typing import Dict, Any, List
from pathlib import Path
try:
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer
    _VECTOR_DEPS = True
except Exception:
    chromadb = None
    Settings = None
    SentenceTransformer = None
    _VECTOR_DEPS = False
import os
from loguru import logger
import uuid
import config


class VectorMemory:
    def __init__(self, base_dir: str = None, model_name: str = None):
        base = base_dir or os.path.join(config.WORKSPACE_BASE, "vector_memory")
        Path(base).mkdir(parents=True, exist_ok=True)
        if not _VECTOR_DEPS:
            raise RuntimeError("Vector dependencies not installed")
        self.client = chromadb.Client(Settings(persist_directory=base))
        self.embedder = SentenceTransformer(model_name or os.getenv("EMBEDDINGS_MODEL", "all-MiniLM-L6-v2"))

    def _get_collection(self, namespace: str):
        return self.client.get_or_create_collection(namespace)

    def upsert(self, namespace: str, texts: List[str], metadatas: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            col = self._get_collection(namespace)
            ids = [str(uuid.uuid4()) for _ in texts]
            embeddings = self.embedder.encode(texts, show_progress_bar=False).tolist()
            col.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
            return {"success": True, "count": len(ids), "ids": ids}
        except Exception as e:
            logger.error(f"vector upsert failed: {e}")
            return {"success": False, "error": str(e)}

    def query(self, namespace: str, query_text: str, top_k: int = 5) -> Dict[str, Any]:
        try:
            col = self._get_collection(namespace)
            emb = self.embedder.encode([query_text], show_progress_bar=False).tolist()
            res = col.query(query_embeddings=emb, n_results=top_k)
            return {"success": True, "results": res}
        except Exception as e:
            logger.error(f"vector query failed: {e}")
            return {"success": False, "error": str(e)}


def get_vector_memory_tools() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "vector_upsert",
                "description": "Upsert texts into a vector memory namespace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "namespace": {"type": "string"},
                        "texts": {"type": "array"},
                        "metadatas": {"type": "array"}
                    },
                    "required": ["namespace", "texts"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "vector_query",
                "description": "Query most similar entries from a vector memory namespace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "namespace": {"type": "string"},
                        "query_text": {"type": "string"},
                        "top_k": {"type": "integer", "default": 5}
                    },
                    "required": ["namespace", "query_text"]
                }
            }
        }
    ]


try:
    vector_memory = VectorMemory()
except Exception:
    class _Noop:
        def upsert(self, *args, **kwargs):
            return {"success": False, "error": "vector memory unavailable"}
        def query(self, *args, **kwargs):
            return {"success": False, "error": "vector memory unavailable"}
    vector_memory = _Noop()

