#!/usr/bin/env python3
"""
Document Ingestion Tools
Parse PDF, DOCX, and HTML into plain text chunks with basic metadata.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from loguru import logger
from bs4 import BeautifulSoup
from pypdf import PdfReader
import docx


def _read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: List[str] = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(parts).strip()


def _read_docx(path: Path) -> str:
    d = docx.Document(str(path))
    return "\n".join(p.text for p in d.paragraphs).strip()


def _read_html(path: Path) -> str:
    html = path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")
    # remove scripts/styles
    for tag in soup(["script", "style"]):
        tag.extract()
    return soup.get_text(" ", strip=True)


class DocIngestion:
    def __init__(self, workspace_root: str = "workspace"):
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, file_path: str) -> Path:
        p = Path(file_path)
        return p if p.is_absolute() else (self.workspace_root / p)

    def ingest(self, file_path: str) -> Dict[str, Any]:
        try:
            p = self._resolve(file_path)
            if not p.exists():
                return {"success": False, "error": f"File not found: {file_path}"}
            ext = p.suffix.lower()
            if ext == ".pdf":
                text = _read_pdf(p)
            elif ext in [".docx"]:
                text = _read_docx(p)
            elif ext in [".html", ".htm"]:
                text = _read_html(p)
            else:
                # Fallback: treat as text
                text = p.read_text(encoding="utf-8", errors="ignore")
            return {"success": True, "text": text, "length": len(text)}
        except Exception as e:
            logger.error(f"ingest failed: {e}")
            return {"success": False, "error": str(e)}


def get_doc_ingestion_tools() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "ingest",
                "description": "Ingest a document (PDF/DOCX/HTML/TXT) into plain text",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"}
                    },
                    "required": ["file_path"]
                }
            }
        }
    ]


doc_ingestion = DocIngestion()

