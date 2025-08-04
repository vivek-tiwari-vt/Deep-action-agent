"""
Coder Agent
Specialized in programming, data analysis, automation, and script creation.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger

from llm_providers.provider_handler import llm_handler
from tools.code_interpreter import code_interpreter, get_code_interpreter_tools
from tools.file_system_tools import file_system_tools, get_file_system_tools
import config

class CoderAgent:
    """
    The Coder Agent specializes in programming tasks, data analysis,
    automation, and creating scripts or tools.
    """
    
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        file_system_tools.set_workspace(str(self.workspace_path))
        code_interpreter.set_workspace(str(self.workspace_path))
        
        # Load system prompt
        self.system_prompt = self._load_system_prompt()
    
    def _load_system_prompt(self) -> str:
        """Load the coder agent system prompt."""
        prompt_file = Path(__file__).parent / "system_prompt.md"
        if prompt_file.exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        
        # Fallback system prompt
        return """You are the Coder Agent, specialized in programming and data analysis.

Your capabilities:
- Python programming and script creation
- Data analysis and visualization
- File processing and automation
- Code debugging and optimization

Your responsibilities:
- Write clean, efficient, and well-documented code
- Perform data analysis and create visualizations
- Automate repetitive tasks
- Debug and fix code issues
- Create reusable tools and utilities

Always follow best practices for code quality, security, and maintainability."""
    
    def _get_available_tools(self) -> List[Dict]:
        """Get available tools for the coder agent."""
        tools = []
        tools.extend(get_code_interpreter_tools())
        tools.extend(get_file_system_tools())
        return tools
    
    def _call_llm(self, messages: List[Dict], tools: Optional[List[Dict]] = None) -> Dict:
        """Make an LLM call with error handling."""
        try:
            # Determine provider from model name
            provider = config.get_provider_from_model(config.CODER_MODEL)
            model = config.clean_model_name(config.CODER_MODEL)
            
            return llm_handler.call_llm(
                provider=provider,
                model=model,
                messages=messages,
                tools=tools,
                temperature=0.2  # Lower temperature for more precise coding
            )
        except Exception as e:
            logger.error(f"Coder LLM call failed: {e}")
            raise
    
    def _execute_tool_call(self, tool_call: Dict) -> str:
        """Execute a tool call and return the result."""
        function_name = tool_call['function']['name']
        arguments = json.loads(tool_call['function']['arguments'])
        
        try:
            if function_name == 'execute_python_code':
                result = code_interpreter.execute_python_code(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'install_package':
                result = code_interpreter.install_package(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'run_shell_command':
                result = code_interpreter.run_shell_command(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'create_and_run_script':
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
            
            else:
                return f"Unknown function: {function_name}"
                
        except Exception as e:
            logger.error(f"Tool execution failed for {function_name}: {e}")
            return f"Error executing {function_name}: {str(e)}"
    
    def execute_task(self, task_description: str, context: str = "") -> str:
        """
        Execute a coding task.
        
        Args:
            task_description: Description of the coding task
            context: Additional context or requirements
            
        Returns:
            Coding results and outputs
        """
        # Prepare messages
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""
Coding Task: {task_description}

Additional Context: {context}

Please approach this coding task systematically:

1. **Analysis**: Understand the requirements and break down the problem
2. **Planning**: Design the solution approach and identify needed tools/libraries
3. **Implementation**: Write clean, well-documented code
4. **Testing**: Test the code with appropriate test cases
5. **Documentation**: Create clear documentation and usage examples
6. **Optimization**: Optimize for performance and maintainability if needed

Guidelines:
- Write clean, readable, and well-commented code
- Follow Python best practices and conventions
- Handle errors gracefully with appropriate exception handling
- Create modular, reusable code when possible
- Test your code thoroughly before finalizing
- Save important scripts and outputs to files
- Provide clear explanations of your approach and solutions

Focus on creating robust, maintainable solutions that solve the problem effectively.
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
                
                # Check if the coding task is complete
                if choice.get('finish_reason') == 'stop' and not message.get('tool_calls'):
                    # Check if we have substantial coding content
                    if len(message.get('content', '')) > 300:
                        break
                    
                    # Ask for more comprehensive results if needed
                    messages.append({
                        "role": "user",
                        "content": "Please provide a comprehensive summary of your coding work, including the final solution, any files created, and usage instructions."
                    })
                
            except Exception as e:
                logger.error(f"Error in coding iteration {iteration}: {e}")
                messages.append({
                    "role": "user",
                    "content": f"An error occurred: {str(e)}. Please continue with alternative approaches or debug the issue."
                })
        
        # Extract final coding summary
        if messages and messages[-1]['role'] == 'assistant':
            return messages[-1]['content']
        else:
            return "Coding task completed. Please check the workspace files for scripts and outputs."

