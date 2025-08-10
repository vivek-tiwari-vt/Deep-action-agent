#!/usr/bin/env python3
"""
Lightweight Vector-like Memory
File-backed naive memory with simple embeddings via hashing placeholder.
Replace later with a real vector DB (FAISS/Chroma).
"""

from __future__ import annotations
from typing import Dict, Any, List
from pathlib import Path
import json
import hashlib
from datetime import datetime
from loguru import logger
import os
import config


class Memory:
    def __init__(self, base_dir: str = None):
        base = base_dir or os.path.join(config.WORKSPACE_BASE, "memory")
        self.base_path = Path(base)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.index_file = self.base_path / "index.jsonl"
        if not self.index_file.exists():
            self.index_file.touch()

    def _embed(self, text: str) -> str:
        # Placeholder: deterministic hash as pseudo-embedding ID
        return hashlib.sha256((text or "").encode("utf-8")).hexdigest()

    def remember(self, namespace: str, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            item = {
                "id": self._embed(f"{namespace}:{content}"),
                "namespace": namespace,
                "content": content,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat()
            }
            with open(self.index_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(item) + "\n")
            return {"success": True, "item": item}
        except Exception as e:
            logger.error(f"Memory remember failed: {e}")
            return {"success": False, "error": str(e)}

    def search(self, namespace: str, query: str, top_k: int = 5) -> Dict[str, Any]:
        try:
            # Naive scoring by substring count; replace with vector similarity later
            results: List[Dict[str, Any]] = []
            with open(self.index_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    if item.get("namespace") != namespace:
                        continue
                    content = item.get("content", "")
                    score = content.lower().count(query.lower())
                    if score > 0:
                        results.append({"item": item, "score": score})
            results.sort(key=lambda x: x["score"], reverse=True)
            return {"success": True, "results": results[:top_k]}
        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return {"success": False, "error": str(e)}


def get_memory_tools() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "memory_remember",
                "description": "Store a memory entry in a namespace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "namespace": {"type": "string"},
                        "content": {"type": "string"},
                        "metadata": {"type": "object"}
                    },
                    "required": ["namespace", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "memory_search",
                "description": "Search memory by namespace and query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "namespace": {"type": "string"},
                        "query": {"type": "string"},
                        "top_k": {"type": "integer", "default": 5}
                    },
                    "required": ["namespace", "query"]
                }
            }
        }
    ]


# Global instance
memory = Memory()

