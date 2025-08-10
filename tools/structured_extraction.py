#!/usr/bin/env python3
"""
Structured Extraction Tools
Lightweight pattern-based extraction into JSON given regex patterns per field.
"""

from typing import Dict, Any, List
import re
from loguru import logger


class StructuredExtraction:
    def extract_with_patterns(self, text: str, patterns: Dict[str, str]) -> Dict[str, Any]:
        try:
            result: Dict[str, Any] = {}
            for field, pattern in (patterns or {}).items():
                try:
                    m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
                    result[field] = m.group(1).strip() if m and m.groups() else (m.group(0).strip() if m else None)
                except re.error as rex:
                    result[field] = None
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"extract_with_patterns failed: {e}")
            return {"success": False, "error": str(e)}


def get_structured_extraction_tools() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "extract_with_patterns",
                "description": "Extract fields from text using regex patterns per field. Use non-greedy groups.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "patterns": {"type": "object"}
                    },
                    "required": ["text", "patterns"]
                }
            }
        }
    ]


structured_extraction = StructuredExtraction()

