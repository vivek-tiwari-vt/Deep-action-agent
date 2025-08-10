#!/usr/bin/env python3
"""
GitHub Connector (minimal)
Create issues/comments using GitHub REST API.
"""

from typing import Dict, Any
import os
import requests
from loguru import logger


class GitHubConnector:
    def _headers(self):
        token = os.getenv("GITHUB_TOKEN")
        return {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}

    def create_issue(self, owner: str, repo: str, title: str, body: str = "") -> Dict[str, Any]:
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/issues"
            resp = requests.post(url, headers=self._headers(), json={"title": title, "body": body}, timeout=30)
            return {"success": resp.ok, "status": resp.status_code, "body": resp.json()}
        except Exception as e:
            logger.error(f"GitHub create_issue failed: {e}")
            return {"success": False, "error": str(e)}

    def comment_issue(self, owner: str, repo: str, issue_number: int, body: str) -> Dict[str, Any]:
        try:
            url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"
            resp = requests.post(url, headers=self._headers(), json={"body": body}, timeout=30)
            return {"success": resp.ok, "status": resp.status_code, "body": resp.json()}
        except Exception as e:
            logger.error(f"GitHub comment_issue failed: {e}")
            return {"success": False, "error": str(e)}


def get_github_tools():
    return [
        {
            "type": "function",
            "function": {
                "name": "github_create_issue",
                "description": "Create a GitHub issue.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "title": {"type": "string"},
                        "body": {"type": "string"}
                    },
                    "required": ["owner", "repo", "title"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "github_comment_issue",
                "description": "Comment on a GitHub issue.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "issue_number": {"type": "integer"},
                        "body": {"type": "string"}
                    },
                    "required": ["owner", "repo", "issue_number", "body"]
                }
            }
        }
    ]


github_connector = GitHubConnector()

