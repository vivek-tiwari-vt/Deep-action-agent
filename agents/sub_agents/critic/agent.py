"""
Critic Agent
Specialized in quality control, fact-checking, bias detection, and validation.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger

from llm_providers.provider_handler import llm_handler
from tools.file_system_tools import file_system_tools, get_file_system_tools
from tools.web_tools import web_tools, get_web_tools
import config

class CriticAgent:
    """
    The Critic Agent specializes in quality control, validation, and critical evaluation
    of research findings, analysis results, and other outputs from the agent system.
    """
    
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        file_system_tools.set_workspace(str(self.workspace_path))
        
        # Load system prompt
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """Load the critic agent system prompt."""
        prompt_file = Path(__file__).parent / "system_prompt.md"
        if prompt_file.exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        
        # Fallback system prompt
        return """You are the Critic Agent, specialized in quality control and validation.

Your capabilities:
- Fact-checking and source verification
- Bias detection and neutrality assessment
- Logical fallacy identification
- Quality assurance and validation
- Critical evaluation of arguments and evidence

Your responsibilities:
- Critically evaluate research findings and analysis
- Identify potential biases, errors, or weaknesses
- Verify facts and claims against reliable sources
- Assess the quality and credibility of sources
- Provide constructive feedback for improvement

Always maintain objectivity and focus on improving the quality and reliability of outputs."""
    
    def _get_available_tools(self) -> List[Dict]:
        """Get available tools for the critic agent."""
        tools = []
        tools.extend(get_file_system_tools())
        tools.extend(get_web_tools())  # For fact-checking and verification
        return tools
    
    def _call_llm(self, messages: List[Dict], tools: Optional[List[Dict]] = None) -> Dict:
        """Make an LLM call with error handling."""
        try:
            # Determine provider from model name
            provider = config.get_provider_from_model(config.CRITIC_MODEL)
            model = config.clean_model_name(config.CRITIC_MODEL)
            
            return llm_handler.call_llm(
                provider=provider,
                model=model,
                messages=messages,
                tools=tools,
                temperature=0.3  # Lower temperature for more focused criticism
            )
        except Exception as e:
            logger.error(f"Critic LLM call failed: {e}")
            raise
    
    def _execute_tool_call(self, tool_call: Dict) -> str:
        """Execute a tool call and return the result."""
        function_name = tool_call['function']['name']
        arguments = json.loads(tool_call['function']['arguments'])
        
        try:
            if function_name == 'web_search':
                result = web_tools.web_search(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'scrape_url':
                result = web_tools.scrape_url(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'read_url_content':
                result = web_tools.read_url_content(**arguments)
                return result
            
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
    
    def execute_task(self, task_description: str, context: str = "") -> str:
        """
        Execute a critical evaluation task.
        
        Args:
            task_description: Description of what to evaluate
            context: Additional context or files to review
            
        Returns:
            Critical evaluation and recommendations
        """
        # Prepare messages
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""
Critical Evaluation Task: {task_description}

Additional Context: {context}

Please conduct a thorough critical evaluation following this systematic approach:

1. **Content Review**: Examine the material to be evaluated in detail
2. **Fact Verification**: Check key claims and facts against reliable sources
3. **Source Assessment**: Evaluate the credibility and reliability of sources used
4. **Bias Detection**: Identify potential biases, assumptions, or one-sided perspectives
5. **Logic Analysis**: Check for logical fallacies, inconsistencies, or weak arguments
6. **Completeness Check**: Assess whether important aspects or perspectives are missing
7. **Quality Assessment**: Evaluate overall quality, accuracy, and reliability
8. **Improvement Recommendations**: Provide specific suggestions for enhancement

Critical evaluation criteria:
- Accuracy and factual correctness
- Source credibility and authority
- Logical consistency and reasoning
- Completeness and comprehensiveness
- Objectivity and balance
- Clarity and organization
- Evidence quality and support

Focus on providing constructive, specific feedback that helps improve the quality and reliability of the work.
"""}
        ]
        
        max_iterations = 12
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
                
                # Check if the evaluation is complete
                if choice.get('finish_reason') == 'stop' and not message.get('tool_calls'):
                    # Check if we have substantial evaluation content
                    if len(message.get('content', '')) > 400:
                        break
                    
                    # Ask for more comprehensive evaluation if needed
                    messages.append({
                        "role": "user",
                        "content": "Please provide a more comprehensive critical evaluation, including specific issues identified and detailed recommendations for improvement."
                    })
                
            except Exception as e:
                logger.error(f"Error in criticism iteration {iteration}: {e}")
                messages.append({
                    "role": "user",
                    "content": f"An error occurred: {str(e)}. Please continue with the critical evaluation using alternative approaches."
                })
        
        # Extract final evaluation summary
        if messages and messages[-1]['role'] == 'assistant':
            return messages[-1]['content']
        else:
            return "Critical evaluation completed. Please check the workspace files for detailed feedback and recommendations."

