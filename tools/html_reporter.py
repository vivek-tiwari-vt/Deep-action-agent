#!/usr/bin/env python3
"""
HTML Reporter
Render a simple HTML report with sections, and optionally save.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from loguru import logger
from datetime import datetime


class HtmlReporter:
    def __init__(self, workspace_root: str = "workspace"):
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def render(self, title: str, sections: List[Dict[str, str]], output_path: Optional[str] = None) -> Dict[str, Any]:
        try:
            head = f"""
<!DOCTYPE html>
<html lang='en'>
<head>
  <meta charset='UTF-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1.0' />
  <title>{title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif; margin: 2rem; }}
    h1 {{ margin-bottom: 0.25rem; }}
    .date {{ color: #666; margin-bottom: 1.5rem; }}
    section {{ margin-bottom: 2rem; }}
    h2 {{ border-bottom: 1px solid #eee; padding-bottom: 0.25rem; }}
    pre {{ background: #f7f7f7; padding: 1rem; overflow-x: auto; }}
  </style>
  </head>
<body>
<h1>{title}</h1>
<div class='date'>Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
"""
            body_parts = []
            for s in sections or []:
                st = s.get('title', 'Section')
                sc = s.get('content', '')
                body_parts.append(f"<section><h2>{st}</h2><div>{sc}</div></section>")
            html = head + "\n".join(body_parts) + "\n</body></html>"

            path_written = None
            if output_path:
                out = Path(output_path)
                if not out.is_absolute():
                    out = self.workspace_root / out
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(html, encoding='utf-8')
                path_written = str(out)
            return {"success": True, "html": html, "path": path_written}
        except Exception as e:
            logger.error(f"HTML render failed: {e}")
            return {"success": False, "error": str(e)}


def get_html_reporter_tools() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "render_html_report",
                "description": "Render HTML report with sections and optional file output.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "sections": {"type": "array"},
                        "output_path": {"type": "string"}
                    },
                    "required": ["title", "sections"]
                }
            }
        }
    ]


html_reporter = HtmlReporter()

