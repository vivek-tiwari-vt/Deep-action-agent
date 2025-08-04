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
        """
        Execute a research task.
        
        Args:
            task_description: Description of the research task
            context: Additional context or previous findings
            
        Returns:
            Research results and findings
        """
        # Prepare messages
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""
Research Task: {task_description}

Additional Context: {context}

Please conduct thorough research on this topic. Your approach should include:

1. **Initial Search Strategy**: Start with broad searches to understand the topic landscape
2. **Source Diversification**: Find multiple types of sources (news, academic, official, expert opinions)
3. **Deep Dive Analysis**: Scrape and analyze the most relevant sources in detail
4. **Source Evaluation**: Assess credibility, bias, and reliability of sources
5. **Information Organization**: Structure findings in a clear, logical format
6. **Data Preservation**: Save important findings to files for future reference

Focus on:
- Finding authoritative and credible sources
- Gathering diverse perspectives on the topic
- Extracting key facts, figures, and insights
- Identifying any controversies or debates
- Noting publication dates and source reliability

Save your research findings to appropriately named files in the workspace.
"""}
        ]
        
        max_iterations = 15
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            try:
                # Get available tools
                tools = self._get_available_tools()
                
                # Make LLM call
                response = self._call_llm(messages, tools)
                
                if not response.get('choices'):
                    break
                
                choice = response['choices'][0]
                message = choice['message']
                
                # Add assistant message to conversation
                messages.append(message)
                
                # Check if there are tool calls
                if message.get('tool_calls'):
                    # Execute tool calls
                    for tool_call in message['tool_calls']:
                        result = await self._execute_tool_call(tool_call)
                        
                        # Add tool result to conversation
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call['id'],
                            "name": tool_call['function']['name'],
                            "content": result
                        })
                
                # Check if the research is complete
                if choice.get('finish_reason') == 'stop' and not message.get('tool_calls'):
                    # Check if we have substantial research content
                    if len(message.get('content', '')) > 500:
                        break
                    
                    # Ask for more comprehensive research if needed
                    messages.append({
                        "role": "user",
                        "content": "Please provide a more comprehensive summary of your research findings, including key sources, main insights, and any important details discovered."
                    })
                
            except Exception as e:
                logger.error(f"Error in research iteration {iteration}: {e}")
                messages.append({
                    "role": "user",
                    "content": f"An error occurred: {str(e)}. Please continue with alternative research approaches."
                })
        
        # Extract final research summary
        if messages and messages[-1]['role'] == 'assistant':
            return messages[-1]['content']
        else:
            return "Research completed. Please check the workspace files for detailed findings."

