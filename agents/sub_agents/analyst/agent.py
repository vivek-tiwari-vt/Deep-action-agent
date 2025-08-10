"""
Analyst Agent
Specialized in data processing, pattern recognition, synthesis, and categorization.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger

from llm_providers.provider_handler import llm_handler
from tools.file_system_tools import file_system_tools, get_file_system_tools
from tools.code_interpreter import code_interpreter, get_code_interpreter_tools
from tools.venv_manager import venv_manager, get_venv_tools
from tools.spreadsheet_tools import spreadsheet_tools, get_spreadsheet_tools
from tools.doc_ingestion import doc_ingestion, get_doc_ingestion_tools
from tools.structured_extraction import structured_extraction, get_structured_extraction_tools
from tools.vector_memory import vector_memory, get_vector_memory_tools
from tools.html_reporter import html_reporter, get_html_reporter_tools
import config

class AnalystAgent:
    """
    The Analyst Agent specializes in processing information, identifying patterns,
    synthesizing findings, and organizing data into meaningful insights.
    """
    
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        file_system_tools.set_workspace(str(self.workspace_path))
        code_interpreter.set_workspace(str(self.workspace_path))
        
        # Load system prompt
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """Load the analyst agent system prompt."""
        prompt_file = Path(__file__).parent / "system_prompt.md"
        if prompt_file.exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        
        # Fallback system prompt
        return """You are the Analyst Agent, specialized in data analysis and synthesis.

Your capabilities:
- Data processing and pattern recognition
- Information synthesis and organization
- Statistical analysis and insights generation
- Categorization and classification
- Trend identification and interpretation

Your responsibilities:
- Analyze complex datasets and information
- Identify patterns, trends, and relationships
- Synthesize findings from multiple sources
- Create structured summaries and reports
- Provide actionable insights and recommendations

Always focus on accuracy, objectivity, and clear communication of findings."""
    
    def _get_available_tools(self) -> List[Dict]:
        """Get available tools for the analyst agent."""
        tools = []
        tools.extend(get_file_system_tools())
        tools.extend(get_code_interpreter_tools())
        tools.extend(get_venv_tools())
        tools.extend(get_spreadsheet_tools())
        tools.extend(get_doc_ingestion_tools())
        tools.extend(get_structured_extraction_tools())
        tools.extend(get_vector_memory_tools())
        tools.extend(get_html_reporter_tools())
        return tools

    def _ensure_venv_and_get_python(self) -> Optional[str]:
        try:
            creation = venv_manager.create_task_venv(str(self.workspace_path))
            if not creation.get("success"):
                return None
            return creation.get("python")
        except Exception:
            return None
    
    def _call_llm(self, messages: List[Dict], tools: Optional[List[Dict]] = None) -> Dict:
        """Make an LLM call with error handling."""
        try:
            # Determine provider from model name
            provider = config.get_provider_from_model(config.ANALYST_MODEL)
            model = config.clean_model_name(config.ANALYST_MODEL)
            
            return llm_handler.call_llm(
                provider=provider,
                model=model,
                messages=messages,
                tools=tools,
                temperature=0.4  # Balanced temperature for analytical thinking
            )
        except Exception as e:
            logger.error(f"Analyst LLM call failed: {e}")
            raise
    
    def _execute_tool_call(self, tool_call: Dict) -> str:
        """Execute a tool call and return the result."""
        function_name = tool_call['function']['name']
        arguments = json.loads(tool_call['function']['arguments'])
        
        try:
            if function_name == 'execute_python_code':
                if 'python_executable' not in arguments or not arguments.get('python_executable'):
                    py = self._ensure_venv_and_get_python()
                    if py:
                        arguments['python_executable'] = py
                result = code_interpreter.execute_python_code(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'install_package':
                result = code_interpreter.install_package(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'run_shell_command':
                result = code_interpreter.run_shell_command(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'create_and_run_script':
                _ = self._ensure_venv_and_get_python()
                result = code_interpreter.create_and_run_script(**arguments)
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
            
            elif function_name in ['create_task_venv', 'venv_install']:
                if function_name == 'create_task_venv':
                    result = venv_manager.create_task_venv(**arguments)
                else:
                    result = venv_manager.install(**arguments)
                return json.dumps(result, indent=2)

            elif function_name in ['read_table', 'write_table', 'aggregate']:
                if function_name == 'read_table':
                    result = spreadsheet_tools.read_table(**arguments)
                elif function_name == 'write_table':
                    result = spreadsheet_tools.write_table(**arguments)
                else:
                    result = spreadsheet_tools.aggregate(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'ingest':
                result = doc_ingestion.ingest(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'extract_with_patterns':
                result = structured_extraction.extract_with_patterns(**arguments)
                return json.dumps(result, indent=2)

            elif function_name in ['vector_upsert', 'vector_query']:
                if function_name == 'vector_upsert':
                    result = vector_memory.upsert(**arguments)
                else:
                    result = vector_memory.query(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'render_html_report':
                result = html_reporter.render(**arguments)
                return json.dumps(result, indent=2)

            else:
                return f"Unknown function: {function_name}"
                
        except Exception as e:
            logger.error(f"Tool execution failed for {function_name}: {e}")
            return f"Error executing {function_name}: {str(e)}"
    
    def execute_task(self, task_description: str, context: str = "") -> str:
        """
        Execute an analysis task.
        
        Args:
            task_description: Description of the analysis task
            context: Additional context or data sources
            
        Returns:
            Analysis results and insights
        """
        # Prepare messages
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""
Analysis Task: {task_description}

Additional Context: {context}

Please conduct a thorough analysis following this systematic approach:

1. **Data Exploration**: Examine available data sources and understand their structure
2. **Pattern Recognition**: Identify trends, patterns, and relationships in the data
3. **Statistical Analysis**: Perform relevant statistical analysis and calculations
4. **Categorization**: Organize findings into logical categories or themes
5. **Synthesis**: Combine insights from different sources into coherent conclusions
6. **Visualization**: Create charts or graphs to illustrate key findings (when appropriate)
7. **Reporting**: Summarize insights in a clear, structured format

Key principles:
- Maintain objectivity and avoid bias in analysis
- Support conclusions with evidence from the data
- Identify limitations and uncertainties in the analysis
- Provide actionable insights and recommendations
- Use appropriate statistical methods and visualizations
- Save analysis results and supporting data to files

Focus on delivering clear, evidence-based insights that address the analysis objectives.
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
                        result = self._execute_tool_call(tool_call)
                        
                        # Add tool result to conversation
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call['id'],
                            "name": tool_call['function']['name'],
                            "content": result
                        })
                
                # Check if the analysis is complete
                if choice.get('finish_reason') == 'stop' and not message.get('tool_calls'):
                    # Check if we have substantial analysis content
                    if len(message.get('content', '')) > 400:
                        break
                    
                    # Ask for more comprehensive analysis if needed
                    messages.append({
                        "role": "user",
                        "content": "Please provide a more comprehensive analysis summary, including key insights, patterns identified, and actionable recommendations."
                    })
                
            except Exception as e:
                logger.error(f"Error in analysis iteration {iteration}: {e}")
                messages.append({
                    "role": "user",
                    "content": f"An error occurred: {str(e)}. Please continue with alternative analysis approaches."
                })
        
        # Extract final analysis summary
        if messages and messages[-1]['role'] == 'assistant':
            return messages[-1]['content']
        else:
            return "Analysis completed. Please check the workspace files for detailed findings and insights."

