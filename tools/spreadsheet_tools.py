#!/usr/bin/env python3
"""
Spreadsheet Tools
Read and write CSV/XLSX, do simple aggregations using pandas.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import pandas as pd
from loguru import logger
import json
import config


class SpreadsheetTools:
    def __init__(self, workspace_root: str = "workspace"):
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        return p if p.is_absolute() else (self.workspace_root / p)

    def read_table(self, file_path: str, sheet_name: Optional[str] = None) -> Dict[str, Any]:
        try:
            p = self._resolve(file_path)
            if not p.exists():
                return {"success": False, "error": f"File not found: {file_path}"}
            if p.suffix.lower() in [".xlsx", ".xlsm", ".xltx", ".xltm"]:
                df = pd.read_excel(p, sheet_name=sheet_name)
            else:
                df = pd.read_csv(p)
            return {"success": True, "rows": df.to_dict(orient="records"), "columns": list(df.columns)}
        except Exception as e:
            logger.error(f"read_table failed: {e}")
            return {"success": False, "error": str(e)}

    def write_table(self, file_path: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            p = self._resolve(file_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            df = pd.DataFrame(rows)
            if p.suffix.lower() in [".xlsx", ".xlsm", ".xltx", ".xltm"]:
                df.to_excel(p, index=False)
            else:
                df.to_csv(p, index=False)
            return {"success": True, "path": str(p)}
        except Exception as e:
            logger.error(f"write_table failed: {e}")
            return {"success": False, "error": str(e)}

    def aggregate(self, rows: List[Dict[str, Any]], group_by: List[str], metrics: Dict[str, str]) -> Dict[str, Any]:
        try:
            df = pd.DataFrame(rows)
            agg_df = df.groupby(group_by).agg(metrics).reset_index()
            return {"success": True, "rows": agg_df.to_dict(orient="records"), "columns": list(agg_df.columns)}
        except Exception as e:
            logger.error(f"aggregate failed: {e}")
            return {"success": False, "error": str(e)}


def get_spreadsheet_tools() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "read_table",
                "description": "Read CSV/XLSX into rows & columns",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "sheet_name": {"type": "string"}
                    },
                    "required": ["file_path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "write_table",
                "description": "Write rows to CSV/XLSX",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "rows": {"type": "array"}
                    },
                    "required": ["file_path", "rows"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "aggregate",
                "description": "Group by and aggregate rows",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "rows": {"type": "array"},
                        "group_by": {"type": "array"},
                        "metrics": {"type": "object"}
                    },
                    "required": ["rows", "group_by", "metrics"]
                }
            }
        }
    ]


spreadsheet_tools = SpreadsheetTools()

