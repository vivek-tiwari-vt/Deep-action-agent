"""
LLM Provider Handler
Manages API calls to multiple LLM providers with round-robin key rotation.
"""

import itertools
import time
import json
from typing import Dict, List, Optional, Any, Union, Callable
import requests
from loguru import logger
import config

class LLMProviderHandler:
    """Handles LLM API calls with round-robin key management and fallback logic."""
    
    def __init__(self):
        # Initialize round-robin iterators for API keys
        self.openrouter_keys = itertools.cycle(config.OPENROUTER_API_KEYS)
        self.gemini_keys = itertools.cycle(config.GEMINI_API_KEYS)
        
        # Track failed keys to avoid immediate retry
        self.failed_keys = {
            'openrouter': set(),
            'gemini': set()
        }
        
        # Rate limiting - more conservative for Gemini
        self.last_call_time = {}
        self.min_call_interval = {
            'openrouter': 0.1,  # 100ms between calls
            'gemini': 1.0       # 1 second between calls to avoid rate limits
        }
        
        # Track rate limit hits per key
        self.rate_limit_hits = {
            'openrouter': {},
            'gemini': {}
        }
    
    def _wait_for_rate_limit(self, provider: str):
        """Implement basic rate limiting."""
        now = time.time()
        last_call = self.last_call_time.get(provider, 0)
        time_since_last = now - last_call
        
        wait_time = self.min_call_interval[provider] - time_since_last
        if wait_time > 0:
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s for {provider}")
            time.sleep(wait_time)
        
        self.last_call_time[provider] = time.time()
    
    def _handle_rate_limit(self, provider: str, api_key: str):
        """Handle rate limit by tracking hits and implementing backoff."""
        if provider not in self.rate_limit_hits:
            self.rate_limit_hits[provider] = {}
        
        if api_key not in self.rate_limit_hits[provider]:
            self.rate_limit_hits[provider][api_key] = 0
        
        self.rate_limit_hits[provider][api_key] += 1
        
        # Add exponential backoff: 2^hits seconds, but cap at 30 seconds
        backoff_time = min(2 ** self.rate_limit_hits[provider][api_key], 30)
        logger.warning(f"Rate limit hit for {provider} key. Backing off for {backoff_time} seconds.")
        time.sleep(backoff_time)
    
    def _get_next_key(self, provider: str) -> str:
        """Get the next API key for the specified provider, avoiding rate-limited keys."""
        if provider == 'openrouter':
            # Try to find a key that hasn't hit rate limits recently
            for _ in range(len(config.OPENROUTER_API_KEYS)):
                key = next(self.openrouter_keys)
                if key not in self.rate_limit_hits.get('openrouter', {}) or \
                   self.rate_limit_hits['openrouter'].get(key, 0) < 3:  # Allow up to 3 rate limit hits
                    return key
            # If all keys are rate limited, return the next one anyway
            return next(self.openrouter_keys)
        elif provider == 'gemini':
            # Try to find a key that hasn't hit rate limits recently
            for _ in range(len(config.GEMINI_API_KEYS)):
                key = next(self.gemini_keys)
                if key not in self.rate_limit_hits.get('gemini', {}) or \
                   self.rate_limit_hits['gemini'].get(key, 0) < 2:  # Allow up to 2 rate limit hits
                    return key
            # If all keys are rate limited, return the next one anyway
            return next(self.gemini_keys)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def _call_openrouter(self, 
                        model: str, 
                        messages: List[Dict], 
                        tools: Optional[List[Dict]] = None,
                        **kwargs) -> Dict:
        """Make API call to OpenRouter."""
        self._wait_for_rate_limit('openrouter')
        
        api_key = self._get_next_key('openrouter')
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/deep-agent-project",
            "X-Title": "Deep Research Agent"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            **kwargs
        }
        
        # Only add tools if they exist and the model supports them
        if tools and len(tools) > 0:
            # Check if this is a simple request that doesn't need tools
            simple_request = all(msg.get('role') == 'user' and 'tool' not in msg.get('content', '').lower() 
                               for msg in messages if msg.get('role') == 'user')
            
            if not simple_request:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"
        
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenRouter API call failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response content: {e.response.text}")
                
                # Handle rate limiting specifically
                if e.response.status_code == 429:
                    self._handle_rate_limit('openrouter', api_key)
                
            self.failed_keys['openrouter'].add(api_key)
            raise
    
    def _call_gemini(self, 
                    model: str, 
                    messages: List[Dict], 
                    tools: Optional[List[Dict]] = None,
                    **kwargs) -> Dict:
        """Make API call to Gemini."""
        self._wait_for_rate_limit('gemini')
        
        api_key = self._get_next_key('gemini')
        
        # Convert messages to Gemini format
        gemini_messages = self._convert_to_gemini_format(messages)
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        payload = {
            "contents": gemini_messages,
            "generationConfig": {
                "temperature": kwargs.get("temperature", 0.7),
                "maxOutputTokens": kwargs.get("max_tokens", config.MAX_OUTPUT_TOKENS),
            }
        }
        
        # Skip tools for now to avoid format issues
        # if tools:
        #     payload["tools"] = {"functionDeclarations": [t["function"] for t in tools if t["type"] == "function"]}
        #     payload["tool_config"] = {"functionCallingConfig": {"mode": "AUTO"}}
        
        try:
            logger.debug(f"Making Gemini API call to {url}")
            logger.debug(f"Payload: {payload}")
            
            response = requests.post(url, json=payload, timeout=30)  # Reduced timeout
            response.raise_for_status()
            gemini_response = response.json()
            
            logger.debug(f"Gemini response: {gemini_response}")
            
            # Convert back to OpenAI format for consistency
            return self._convert_gemini_response_to_openai_format(gemini_response)
            
        except requests.exceptions.Timeout:
            logger.error(f"Gemini API call timed out after 30 seconds")
            self.failed_keys['gemini'].add(api_key)
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Gemini API call failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response content: {e.response.text}")
                
                # Handle rate limiting specifically
                if e.response.status_code == 429:
                    self._handle_rate_limit('gemini', api_key)
                
            self.failed_keys['gemini'].add(api_key)
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Gemini API call: {e}")
            self.failed_keys['gemini'].add(api_key)
            raise
    
    def _convert_to_gemini_format(self, messages: List[Dict]) -> List[Dict]:
        """Convert OpenAI format messages to Gemini format."""
        gemini_messages = []
        system_message_content = ""

        # Extract system message first
        for msg in messages:
            if msg["role"] == "system":
                system_message_content = msg["content"]
                break

        # Process other messages
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                continue # Already handled
            elif role == "user":
                # Prepend system message to the first user message if it exists
                if system_message_content and not gemini_messages:
                    gemini_messages.append({
                        "role": "user",
                        "parts": [{"text": f"{system_message_content}\n\n{content}"}]
                    })
                    system_message_content = "" # Clear system message after prepending
                else:
                    gemini_messages.append({
                        "role": "user",
                        "parts": [{"text": content}]
                    })
            elif role == "assistant":
                # For now, only handle text content, skip tool calls to avoid format issues
                if content:
                    gemini_messages.append({
                        "role": "model",
                        "parts": [{"text": content}]
                    })
            elif role == "tool":
                # Skip tool messages for now to avoid format issues
                continue
        
        return gemini_messages
    
    def _convert_gemini_response_to_openai_format(self, gemini_response: Dict) -> Dict:
        """Convert Gemini response to OpenAI format."""
        try:
            if "candidates" not in gemini_response or not gemini_response["candidates"]:
                # Handle cases where Gemini might return no candidates (e.g., safety reasons)
                if "promptFeedback" in gemini_response and "blockReason" in gemini_response["promptFeedback"]:
                    logger.warning(f"Gemini blocked prompt: {gemini_response['promptFeedback']['blockReason']}")
                    return {
                        "choices": [{
                            "message": {"role": "assistant", "content": ""},
                            "finish_reason": "content_filter"
                        }],
                        "usage": {}
                    }
                logger.error(f"Unexpected Gemini response format: {gemini_response}")
                raise ValueError("No candidates in Gemini response")
            
            candidate = gemini_response["candidates"][0]
            
            # Handle text response
            content = ""
            if "content" in candidate and "parts" in candidate["content"]:
                text_parts = []
                for part in candidate["content"]["parts"]:
                    if "text" in part:
                        text_parts.append(part["text"])
                content = " ".join(text_parts)
            
            # Handle tool calls
            tool_calls = []
            if "content" in candidate and "parts" in candidate["content"]:
                for part in candidate["content"]["parts"]:
                    if "functionCall" in part:
                        func_call = part["functionCall"]
                        tool_calls.append({
                            "id": f"call_{func_call['name']}", # Dummy ID
                            "type": "function",
                            "function": {
                                "name": func_call["name"],
                                "arguments": json.dumps(func_call["args"])
                            }
                        })
            
            message = {"role": "assistant"}
            if content:
                message["content"] = content
            if tool_calls:
                message["tool_calls"] = tool_calls

            finish_reason = "stop"
            if "finishReason" in candidate:
                if candidate["finishReason"] == "STOP":
                    finish_reason = "stop"
                elif candidate["finishReason"] == "MAX_TOKENS":
                    finish_reason = "length"
                elif candidate["finishReason"] == "SAFETY":
                    finish_reason = "content_filter"
                elif candidate["finishReason"] == "TOOL_CALLS":
                    finish_reason = "tool_calls"

            return {
                "choices": [{
                    "message": message,
                    "finish_reason": finish_reason
                }],
                "usage": gemini_response.get("usageMetadata", {})
            }
        except Exception as e:
            logger.error(f"Error converting Gemini response: {e}")
            logger.error(f"Gemini response: {gemini_response}")
            raise
    
    def call_llm(self, 
                provider: str,
                model: str,
                messages: List[Dict],
                tools: Optional[List[Dict]] = None,
                max_retries: int = 3,
                stream_tokens: bool = False,
                on_delta: Optional[Callable[[Dict[str, Any]], None]] = None,
                **kwargs) -> Dict:
        """
        Main method to call LLM with automatic provider selection and retry logic.
        
        Args:
            provider: 'openrouter' or 'gemini'
            model: Model name
            messages: List of message dictionaries
            tools: Optional list of tool definitions
            max_retries: Maximum number of retries
            **kwargs: Additional parameters for the API call
        
        Returns:
            API response in OpenAI format
        """
        # Clean model name consistently
        model = config.clean_model_name(model)
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                if provider == 'openrouter':
                    return self._call_openrouter(model, messages, tools, stream_tokens=stream_tokens, on_delta=on_delta, **kwargs)
                elif provider == 'gemini':
                    return self._call_gemini(model, messages, tools, stream_tokens=stream_tokens, on_delta=on_delta, **kwargs)
                else:
                    raise ValueError(f"Unknown provider: {provider}")
                    
            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt + 1} failed for {provider}: {e}")
                
                # Don't retry immediately on rate limits - let the rate limit handler deal with it
                if hasattr(e, 'response') and e.response and e.response.status_code == 429:
                    logger.info(f"Rate limit hit for {provider}, skipping retry")
                    break
                
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        # If all retries failed for the primary provider, try the other provider as fallback
        fallback_provider = 'gemini' if provider == 'openrouter' else 'openrouter'
        fallback_model = config.clean_model_name(config.DEFAULT_GEMINI_MODEL if fallback_provider == 'gemini' else config.DEFAULT_OPENROUTER_MODEL)
        
        logger.info(f"Primary provider ({provider}) failed after {max_retries} attempts. Falling back to {fallback_provider}.")
        try:
            # Only one attempt for fallback to avoid infinite loops
            return self.call_llm(fallback_provider, fallback_model, messages, tools, max_retries=1, **kwargs)
        except Exception as fallback_exception:
            logger.error(f"Fallback provider ({fallback_provider}) also failed: {fallback_exception}")
            # Re-raise the original exception from the primary provider if fallback also fails
            raise last_exception

# Global instance
llm_handler = LLMProviderHandler()

