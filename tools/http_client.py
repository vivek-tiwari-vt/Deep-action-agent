#!/usr/bin/env python3
"""
HTTP Client Tool
Safe HTTP(S) request tool with domain allowlist and timeouts.
"""

from typing import Dict, Any, Optional, List
import os
import re
import json
import requests
from urllib.parse import urlparse
from loguru import logger
import config


def _load_allowed_domains() -> List[str]:
    # Comma-separated list of allowed domains; if empty, default to none unless ALLOW_ALL_HTTP=true
    raw = os.getenv("HTTP_ALLOWED_DOMAINS", "").strip()
    allowed = [d.strip().lower() for d in raw.split(',') if d.strip()]
    return allowed


def _is_domain_allowed(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ["http", "https"]:
            return False
        host = (parsed.netloc or "").lower()
        allowed = _load_allowed_domains()
        if os.getenv("ALLOW_ALL_HTTP", "false").lower() == "true":
            return True
        for domain in allowed:
            if host == domain or host.endswith("." + domain):
                return True
        return False
    except Exception:
        return False


class HttpClient:
    def http_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        if not _is_domain_allowed(url):
            return {"success": False, "error": f"URL not allowed by policy: {url}"}

        method = (method or "GET").upper()
        if timeout is None:
            timeout = int(os.getenv("HTTP_DEFAULT_TIMEOUT", str(config.REQUEST_TIMEOUT)))

        try:
            resp = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_body,
                data=data,
                timeout=timeout,
            )
            content_type = resp.headers.get("Content-Type", "")
            body: Any
            try:
                if "application/json" in content_type:
                    body = resp.json()
                else:
                    body = resp.text
            except Exception:
                body = resp.text

            return {
                "success": resp.ok,
                "status": resp.status_code,
                "headers": dict(resp.headers),
                "url": resp.url,
                "content_type": content_type,
                "body": body,
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {e}")
            return {"success": False, "error": str(e)}


def get_http_tools() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "http_request",
                "description": "Perform an HTTP request to an allowed domain.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {"type": "string", "description": "HTTP method (GET, POST, etc.)"},
                        "url": {"type": "string", "description": "Target URL (http/https only)"},
                        "headers": {"type": "object", "description": "Optional headers"},
                        "params": {"type": "object", "description": "Query parameters"},
                        "json_body": {"type": "object", "description": "JSON body for POST/PUT/PATCH"},
                        "data": {"description": "Raw request body (alternative to json_body)"},
                        "timeout": {"type": "integer", "description": "Timeout in seconds"}
                    },
                    "required": ["method", "url"]
                }
            }
        }
    ]


# Global instance
http_client = HttpClient()

