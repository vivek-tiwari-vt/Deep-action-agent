#!/usr/bin/env python3
"""
Slack Connector (minimal)
Post messages to a Slack channel via Webhook or Bot token.
"""

from typing import Dict, Any
import os
import requests
from loguru import logger


class SlackConnector:
    def post_message(self, text: str, channel: str = None) -> Dict[str, Any]:
        webhook = os.getenv("SLACK_WEBHOOK_URL")
        bot_token = os.getenv("SLACK_BOT_TOKEN")
        try:
            if webhook:
                resp = requests.post(webhook, json={"text": text})
                return {"success": resp.ok, "status": resp.status_code}
            if bot_token and channel:
                resp = requests.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={"Authorization": f"Bearer {bot_token}"},
                    json={"channel": channel, "text": text},
                    timeout=30,
                )
                return {"success": resp.ok, "status": resp.status_code, "body": resp.json()}
            return {"success": False, "error": "No Slack webhook or bot token configured"}
        except Exception as e:
            logger.error(f"Slack post failed: {e}")
            return {"success": False, "error": str(e)}


def get_slack_tools():
    return [
        {
            "type": "function",
            "function": {
                "name": "slack_post_message",
                "description": "Post a message to Slack via webhook or bot token.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "channel": {"type": "string"}
                    },
                    "required": ["text"]
                }
            }
        }
    ]


slack_connector = SlackConnector()

