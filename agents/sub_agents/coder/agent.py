"""
Coder Agent
Specialized in programming, data analysis, automation, and script creation.
"""

import json
import subprocess
import tempfile
import time
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
        
        # Create output directory for generated code files
        self.code_output_dir = self.workspace_path / "generated_code"
        self.code_output_dir.mkdir(exist_ok=True)
    
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

IMPORTANT: You must create COMPLETE, RUNNABLE Python files that can be executed directly.
Your code should include:
1. Complete function implementations
2. Comprehensive test cases
3. Main execution block (if __name__ == "__main__")
4. Proper error handling
5. Clear documentation

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
    
    def _create_code_file(self, code_content: str, filename: str = None) -> str:
        """Create a runnable Python code file."""
        if not filename:
            # Generate filename from task description
            filename = f"solution_{int(time.time())}.py"
        
        # Ensure .py extension
        if not filename.endswith('.py'):
            filename += '.py'
        
        file_path = self.code_output_dir / filename
        
        # Write the code to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(code_content)
        
        logger.info(f"Created code file: {file_path}")
        return str(file_path)
    
    def _test_code_file(self, file_path: str) -> Dict[str, Any]:
        """Test a Python code file and return results."""
        try:
            # Run the Python file
            result = subprocess.run(
                ['python', file_path],
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'file_path': file_path
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Execution timed out after 30 seconds',
                'returncode': -1,
                'file_path': file_path
            }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': f'Error running file: {str(e)}',
                'returncode': -1,
                'file_path': file_path
            }
    
    def _extract_code_from_response(self, response_text: str) -> str:
        """Extract Python code from LLM response."""
        # Look for code blocks
        if '```python' in response_text:
            start = response_text.find('```python') + 9
            end = response_text.find('```', start)
            if end != -1:
                return response_text[start:end].strip()
        
        # If no code blocks, look for def or class patterns
        lines = response_text.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            if line.strip().startswith('def ') or line.strip().startswith('class ') or line.strip().startswith('import ') or line.strip().startswith('from '):
                in_code = True
            
            if in_code:
                code_lines.append(line)
            
            # Stop at markdown headers or other non-code content
            if in_code and line.strip().startswith('**') and line.strip().endswith('**'):
                break
        
        if code_lines:
            return '\n'.join(code_lines).strip()
        
        # If still no code found, return the whole response
        return response_text
    
    def _generate_test_feedback(self, test_result: Dict[str, Any]) -> str:
        """Generate feedback based on test results."""
        if test_result['success']:
            return f"✅ Code executed successfully!\nOutput:\n{test_result['stdout']}"
        else:
            feedback = f"❌ Code execution failed!\n"
            if test_result['stderr']:
                feedback += f"Error:\n{test_result['stderr']}\n"
            if test_result['stdout']:
                feedback += f"Output:\n{test_result['stdout']}\n"
            return feedback
    
    def execute_task(self, task_description: str, context: str = "") -> str:
        """
        Execute a coding task with automatic testing and iteration.
        
        Args:
            task_description: Description of the coding task
            context: Additional context or requirements
            
        Returns:
            Path to the final working code file
        """
        logger.info(f"Starting coding task: {task_description}")
        
        # Prepare initial messages
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""
Coding Task: {task_description}

Additional Context: {context}

CRITICAL REQUIREMENTS:
1. Create a COMPLETE, RUNNABLE Python file that can be executed directly
2. Include comprehensive test cases within the same file
3. Add a main execution block (if __name__ == "__main__") that runs the tests
4. Handle all edge cases and error conditions
5. Provide clear documentation and comments

The code should be self-contained and executable. Include all necessary imports, function definitions, test cases, and a main execution block.

Please create the complete Python code file now.
"""}
        ]
        
        max_attempts = 5
        attempt = 0
        last_test_result = None
        
        while attempt < max_attempts:
            attempt += 1
            logger.info(f"Attempt {attempt}/{max_attempts}")
            
            try:
                # Get available tools
                tools = self._get_available_tools()
                
                # Make LLM call
                response = self._call_llm(messages, tools)
                
                if not response.get('choices'):
                    logger.error("No response from LLM")
                    break
                
                choice = response['choices'][0]
                message = choice['message']
                
                # Add assistant message to conversation
                messages.append(message)
                
                # Extract code from response
                code_content = self._extract_code_from_response(message.get('content', ''))
                
                if not code_content or len(code_content.strip()) < 50:
                    logger.warning("No substantial code found in response")
                    messages.append({
                        "role": "user",
                        "content": "Please provide the complete Python code implementation. The response should contain the full, runnable code."
                    })
                    continue
                
                # Create code file
                filename = f"solution_attempt_{attempt}.py"
                file_path = self._create_code_file(code_content, filename)
                
                # Test the code
                test_result = self._test_code_file(file_path)
                last_test_result = test_result
                
                logger.info(f"Test result: {'SUCCESS' if test_result['success'] else 'FAILED'}")
                
                if test_result['success']:
                    logger.info("✅ Code executed successfully!")
                    return f"✅ SUCCESS! Working code file created: {file_path}\n\nOutput:\n{test_result['stdout']}"
                
                # If failed, generate feedback and try again
                feedback = self._generate_test_feedback(test_result)
                logger.info(f"Code failed, generating feedback for next attempt")
                
                messages.append({
                    "role": "user",
                    "content": f"""
The code failed to execute properly. Here are the issues:

{feedback}

Please fix the code and provide a corrected version that:
1. Addresses the specific errors shown above
2. Includes proper error handling
3. Has complete, runnable code
4. Passes all test cases

Provide the complete corrected Python code.
"""
                })
                
            except Exception as e:
                logger.error(f"Error in attempt {attempt}: {e}")
                messages.append({
                    "role": "user",
                    "content": f"An error occurred: {str(e)}. Please provide a simpler, working solution."
                })
        
        # If all attempts failed, return the last result
        if last_test_result:
            return f"❌ FAILED after {max_attempts} attempts. Last file: {last_test_result['file_path']}\n\nError:\n{last_test_result['stderr']}"
        else:
            return "❌ FAILED: Could not generate any code"

