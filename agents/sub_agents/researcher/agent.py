"""
Researcher Agent
Specialized in web research, information gathering, and source analysis.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger

from llm_providers.provider_handler import llm_handler
from tools.web_tools import web_tools, get_web_tools
from tools.file_system_tools import file_system_tools, get_file_system_tools
from tools.doc_ingestion import doc_ingestion, get_doc_ingestion_tools
from tools.structured_extraction import structured_extraction, get_structured_extraction_tools
from tools.spreadsheet_tools import spreadsheet_tools, get_spreadsheet_tools
from tools.http_client import http_client, get_http_tools
from tools.vector_memory import vector_memory, get_vector_memory_tools
from tools.html_reporter import html_reporter, get_html_reporter_tools
import config

class ResearcherAgent:
    """
    The Researcher Agent specializes in gathering information from the web,
    analyzing sources, and providing comprehensive research findings.
    """
    
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        file_system_tools.set_workspace(str(self.workspace_path))
        
        # Load system prompt
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """Load the researcher agent system prompt."""
        prompt_file = Path(__file__).parent / "system_prompt.md"
        if prompt_file.exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        
        # Fallback system prompt
        return """You are the Researcher Agent, specialized in web research and information gathering.

Your capabilities:
- Web search using multiple strategies
- URL scraping and content analysis
- Source evaluation and credibility assessment
- Information synthesis and organization

Your responsibilities:
- Find authoritative and diverse sources
- Extract relevant information efficiently
- Evaluate source credibility and bias
- Organize findings in structured formats
- Save research data for further analysis

Always prioritize accuracy, comprehensiveness, and source diversity in your research."""
    
    def _get_available_tools(self) -> List[Dict]:
        """Get available tools for the researcher agent."""
        tools = []
        tools.extend(get_web_tools())
        tools.extend(get_file_system_tools())
        tools.extend(get_doc_ingestion_tools())
        tools.extend(get_structured_extraction_tools())
        tools.extend(get_spreadsheet_tools())
        tools.extend(get_http_tools())
        tools.extend(get_vector_memory_tools())
        tools.extend(get_html_reporter_tools())
        return tools
    
    def _call_llm(self, messages: List[Dict], tools: Optional[List[Dict]] = None) -> Dict:
        """Make an LLM call with error handling."""
        try:
            # Determine provider from model name
            provider = config.get_provider_from_model(config.RESEARCHER_MODEL)
            model = config.clean_model_name(config.RESEARCHER_MODEL)
            
            return llm_handler.call_llm(
                provider=provider,
                model=model,
                messages=messages,
                tools=tools,
                temperature=0.3  # Lower temperature for more focused research
            )
        except Exception as e:
            logger.error(f"Researcher LLM call failed: {e}")
            raise
    
    async def _execute_tool_call(self, tool_call: Dict) -> str:
        """Execute a tool call and return the result."""
        function_name = tool_call['function']['name']
        arguments = json.loads(tool_call['function']['arguments'])
        
        try:
            if function_name == 'web_search':
                # Use web_search directly
                result = await web_tools.web_search(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'search_and_extract':
                result = await web_tools.search_and_extract(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'navigate_to':
                result = await web_tools.navigate_to(**arguments)
                return json.dumps({"success": result}, indent=2)
            
            elif function_name == 'extract_content':
                result = await web_tools.extract_content(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'click_link_and_extract':
                result = await web_tools.click_link_and_extract(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'ingest':
                result = doc_ingestion.ingest(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'extract_with_patterns':
                result = structured_extraction.extract_with_patterns(**arguments)
                return json.dumps(result, indent=2)

            elif function_name in ['read_table', 'write_table', 'aggregate']:
                if function_name == 'read_table':
                    result = spreadsheet_tools.read_table(**arguments)
                elif function_name == 'write_table':
                    result = spreadsheet_tools.write_table(**arguments)
                elif function_name == 'aggregate':
                    result = spreadsheet_tools.aggregate(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'http_request':
                result = http_client.http_request(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'vector_upsert':
                result = vector_memory.upsert(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'vector_query':
                result = vector_memory.query(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'render_html_report':
                result = html_reporter.render(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name in ['read_file', 'write_file', 'append_file', 'list_files', 'create_directory']:
                # File system operations
                if function_name == 'read_file':
                    result = file_system_tools.read_file(**arguments)
                elif function_name == 'write_file':
                    result = file_system_tools.write_file(**arguments)
                elif function_name == 'append_file':
                    result = file_system_tools.append_file(**arguments)
                elif function_name == 'list_files':
                    result = file_system_tools.list_files(**arguments)
                elif function_name == 'create_directory':
                    result = file_system_tools.create_directory(**arguments)
                
                return json.dumps(result, indent=2)
            
            else:
                return f"Unknown function: {function_name}"
                
        except Exception as e:
            logger.error(f"Tool execution failed for {function_name}: {e}")
            return f"Error executing {function_name}: {str(e)}"
    
    async def execute_task(self, task_description: str, context: str = "") -> str:
        """Continuous LLM-guided research loop with query planning, link selection, and extraction."""
        from tools.web_tools import web_tools
        from tools.vector_memory import vector_memory
        from tools.file_system_tools import file_system_tools
        import time as _time
        
        def _normalize(q: str) -> str:
            try:
                import re
                lowered = (q or "").lower()
                lowered = re.sub(r"^\s*search\s+for:\s*", "", lowered)
                collapsed = re.sub(r"(.)\1{1,}", r"\1", lowered)
                cleaned = re.sub(r"[^a-z0-9\-\s]", " ", collapsed)
                words = [w for w in cleaned.strip().split() if w]
                return " ".join(words[:6])
            except Exception:
                return q
        
        # 1) Ask LLM to propose initial short queries
        plan_msgs = [
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": (
                "Break the task into up to 8 short Google queries (<=6 words each).\n"
                "Task: " + task_description + ("\nContext: " + context if context else "")
            )}
        ]
        proposed = []
        try:
            resp = self._call_llm(plan_msgs)
            content = (resp.get('choices') or [{}])[0].get('message', {}).get('content') if isinstance(resp, dict) else None
            if content:
                import json as _json
                arr = _json.loads(content)
                if isinstance(arr, list):
                    for q in arr:
                        if isinstance(q, str):
                            nq = _normalize(q)
                            if nq and nq not in proposed:
                                proposed.append(nq)
        except Exception:
            pass
        if not proposed:
            # Deterministic fallback
            base = _normalize(task_description)
            proposed = [f"{base} overview", f"{base} latest", f"{base} trends"]
            proposed = [
                _normalize(p) for p in proposed
            ]
        
        # 2) For each query: search → collect links → ask LLM which to open → open & extract
        extracted_notes: List[Dict[str, Any]] = []
        for q in proposed[:8]:
            try:
                search = await web_tools.web_search(query=q, num_results=12)
                results = search.get('results', []) if isinstance(search, dict) else []
                # Compact list for LLM
                compact = []
                for i, r in enumerate(results):
                    href = r.get('url') or r.get('href')
                    title = r.get('title') or r.get('text')
                    if href and title:
                        compact.append({"i": i, "title": title[:120], "url": href})
                if not compact:
                    continue
                chooser = [
                    {"role": "system", "content": "Return JSON only."},
                    {"role": "user", "content": (
                        "Query: " + q + "\nChoose up to 5 URLs to open now. Respond as JSON array of indices (from list).\nList:\n" +
                        "\n".join([f"{c['i']}: {c['title']} ({c['url']})" for c in compact])
                    )}
                ]
                ch_resp = self._call_llm(chooser)
                chosen_idx = []
                if isinstance(ch_resp, dict):
                    ctext = (ch_resp.get('choices') or [{}])[0].get('message', {}).get('content')
                    if ctext:
                        import json as _json
                        try:
                            chosen_idx = _json.loads(ctext)
                        except Exception:
                            chosen_idx = []
                if not isinstance(chosen_idx, list):
                    chosen_idx = []
                # Visit
                visited = 0
                for i in chosen_idx[:5]:
                    if not isinstance(i, int) or i < 0 or i >= len(results):
                        continue
                    href = results[i].get('url') or results[i].get('href')
                    title = results[i].get('title') or results[i].get('text') or ''
                    if not href:
                        continue
                    ok = await web_tools.navigate_to(url=href)
                    if not ok:
                        continue
                    data = await web_tools.extract_content()
                    text = (data or {}).get('content') or ''
                    if text and len(text) > 200:
                        note = {
                            'query': q, 'url': href, 'title': title, 'text': text[:4000]
                        }
                        extracted_notes.append(note)
                        try:
                            vector_memory.upsert("researcher_notes", [text[:1000]], metadatas=[{"q": q, "url": href}])
                        except Exception:
                            pass
                        filename = f"research_{_time.time_ns()}_{i}.json"
                        file_system_tools.write_file(filename, json.dumps(note, indent=2))
                        visited += 1
                    if visited >= 3:
                        break
            except Exception as e:
                logger.warning(f"Query loop error for '{q}': {e}")
                continue
        
        # 3) Summarize findings via LLM
        summary_msgs = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": (
                "Task: " + task_description + ("\nContext: " + context if context else "") +
                "\n\nSummarize the key insights from these notes (title, url, text snippet):\n" +
                "\n\n".join([f"- {n.get('title','')} | {n.get('url','')}\n{n.get('text','')[:600]}" for n in extracted_notes[:10]])
            )}
        ]
        final = self._call_llm(summary_msgs)
        content = (final.get('choices') or [{}])[0].get('message', {}).get('content', '') if isinstance(final, dict) else ''
        return content or "Research completed. Check workspace for saved notes."

