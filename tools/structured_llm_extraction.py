#!/usr/bin/env python3
"""
LLM-Structured Extraction Tools
Supports schema-driven extraction using function/tool-calling when available,
with JSON-mode fallback prompting otherwise.
"""

from typing import Dict, Any, Optional, List
import json
from loguru import logger

from llm_providers.provider_handler import llm_handler
import config


class StructuredLLMExtraction:
    def __init__(self) -> None:
        pass

    def extract_with_schema(self, text: str, schema: Dict[str, Any], instructions: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        """Attempt function-calling structured extraction with the provided JSON Schema.

        Args:
            text: Input text to extract from
            schema: JSON schema dict specifying desired structure
            instructions: Optional extraction instructions to include in system prompt
            model: Optional model override
        """
        try:
            model_name = model or config.MANAGER_MODEL
            provider = config.get_provider_from_model(model_name)
            cleaned_model = config.clean_model_name(model_name)

            system = instructions or "Extract the requested structured data. Use the provided function strictly with keys matching the schema."
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ]

            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "extract",
                        "description": "Return structured data that matches the provided JSON schema",
                        "parameters": schema,
                    },
                }
            ]

            resp = llm_handler.call_llm(provider=provider, model=cleaned_model, messages=messages, tools=tools, temperature=0.0)

            # Try OpenAI-style tool_calls first
            if resp.get("choices"):
                msg = resp["choices"][0].get("message", {})
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    try:
                        args = tool_calls[0]["function"]["arguments"]
                        if isinstance(args, str):
                            return {"success": True, "data": json.loads(args)}
                        return {"success": True, "data": args}
                    except Exception as e:
                        logger.warning(f"Failed to parse tool_call arguments: {e}")

                # If no tool call returned but we have content, try JSON parse
                content = msg.get("content")
                if content:
                    try:
                        return {"success": True, "data": json.loads(content)}
                    except Exception:
                        return {"success": True, "raw": content}

            return {"success": False, "error": "No structured data returned"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def extract_json_mode(self, text: str, schema: Dict[str, Any], instructions: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        """Prompt the model to output JSON that matches the provided schema.

        Fallback approach for providers/models without function-calling.
        """
        try:
            model_name = model or config.MANAGER_MODEL
            provider = config.get_provider_from_model(model_name)
            cleaned_model = config.clean_model_name(model_name)

            schema_str = json.dumps(schema, indent=2)
            system = instructions or "You output ONLY valid JSON that conforms to the provided JSON Schema. No prose."
            prompt = f"JSON Schema:\n{schema_str}\n\nInput:\n{text}\n\nReturn valid JSON only."
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
            resp = llm_handler.call_llm(provider=provider, model=cleaned_model, messages=messages, tools=None, temperature=0.0)
            if resp.get("choices"):
                content = resp["choices"][0].get("message", {}).get("content", "")
                try:
                    return {"success": True, "data": json.loads(content)}
                except Exception:
                    return {"success": False, "raw": content, "error": "Invalid JSON returned"}
            return {"success": False, "error": "No content"}
        except Exception as e:
            return {"success": False, "error": str(e)}


structured_llm_extraction = StructuredLLMExtraction()


def get_structured_llm_extraction_tools() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "extract_with_schema",
                "description": "Structured extraction using function/tool-calling with a JSON Schema",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "schema": {"type": "object"},
                        "instructions": {"type": "string"},
                        "model": {"type": "string"},
                    },
                    "required": ["text", "schema"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "extract_json_mode",
                "description": "Structured extraction by prompting the model to return JSON that matches a JSON Schema",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "schema": {"type": "object"},
                        "instructions": {"type": "string"},
                        "model": {"type": "string"},
                    },
                    "required": ["text", "schema"]
                }
            }
        }
    ]

