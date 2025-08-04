"""
Code Interpreter
Provides safe Python code execution capabilities.
"""

import subprocess
import tempfile
import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger
import time

class CodeInterpreter:
    """Safe Python code execution environment."""
    
    def __init__(self, workspace_root: str = "workspace"):
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(exist_ok=True)
        
        # Create a temporary directory for code execution
        self.temp_dir = self.workspace_root / "temp_code"
        self.temp_dir.mkdir(exist_ok=True)
    
    def set_workspace(self, workspace_path: str):
        """Set the current workspace directory."""
        self.workspace_root = Path(workspace_path)
        self.workspace_root.mkdir(exist_ok=True)
        self.temp_dir = self.workspace_root / "temp_code"
        self.temp_dir.mkdir(exist_ok=True)
    
    def execute_python_code(self, 
                           code: str, 
                           timeout: int = 30,
                           capture_output: bool = True) -> Dict[str, Any]:
        """
        Execute Python code in a safe environment.
        
        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds
            capture_output: Whether to capture stdout/stderr
            
        Returns:
            Dictionary with execution results
        """
        try:
            # Create a temporary file for the code
            timestamp = int(time.time() * 1000)
            code_file = self.temp_dir / f"code_{timestamp}.py"
            
            # Prepare the code with workspace path
            workspace_path = str(self.workspace_root.absolute())
            prepared_code = f"""
import sys
import os
import json
from pathlib import Path

# Set workspace path
WORKSPACE_PATH = r"{workspace_path}"
os.chdir(WORKSPACE_PATH)
sys.path.insert(0, WORKSPACE_PATH)

# User code starts here
{code}
"""
            
            # Write code to file
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write(prepared_code)
            
            # Execute the code
            result = subprocess.run(
                [sys.executable, str(code_file)],
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                cwd=str(self.workspace_root)
            )
            
            # Clean up the temporary file
            try:
                code_file.unlink()
            except:
                pass
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout if capture_output else '',
                'stderr': result.stderr if capture_output else '',
                'return_code': result.returncode,
                'execution_time': timeout if result.returncode != 0 else None
            }
            
        except subprocess.TimeoutExpired:
            logger.warning(f"Code execution timed out after {timeout} seconds")
            return {
                'success': False,
                'stdout': '',
                'stderr': f'Execution timed out after {timeout} seconds',
                'return_code': -1,
                'execution_time': timeout
            }
            
        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'return_code': -1,
                'execution_time': None
            }
    
    def install_package(self, package: str) -> Dict[str, Any]:
        """
        Install a Python package using pip.
        
        Args:
            package: Package name to install
            
        Returns:
            Dictionary with installation result
        """
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', package],
                capture_output=True,
                text=True,
                timeout=120  # 2 minutes timeout for package installation
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode,
                'package': package
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Package installation timed out',
                'return_code': -1,
                'package': package
            }
            
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'return_code': -1,
                'package': package
            }
    
    def run_shell_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Run a shell command safely with security restrictions.
        
        Args:
            command: Shell command to run
            timeout: Execution timeout in seconds
            
        Returns:
            Dictionary with execution results
        """
        # Security: Define dangerous commands that should be blocked
        dangerous_commands = [
            'rm -rf', 'rm -r', 'rm -f', 'rm -', 'rm /', 'rm ~',
            'sudo', 'su', 'chmod 777', 'chmod +x /', 'chown',
            'dd if=', 'mkfs', 'fdisk', 'mount', 'umount',
            'shutdown', 'reboot', 'halt', 'poweroff',
            'killall', 'pkill -9', 'kill -9',
            'curl -O', 'wget -O', 'scp', 'rsync',
            'nc ', 'netcat', 'telnet', 'ssh',
            'python -c "import os; os.system', 'python -c "import subprocess; subprocess.call',
            'eval ', 'exec ', 'source /', 'cat /etc/passwd', 'cat /etc/shadow',
            'find / -name', 'grep -r /', 'locate /',
            'echo $PATH', 'export PATH', 'unset PATH',
            'history', 'cat ~/.bash_history', 'cat ~/.zsh_history'
        ]
        
        # Check for dangerous commands
        command_lower = command.lower().strip()
        for dangerous in dangerous_commands:
            if dangerous.lower() in command_lower:
                return {
                    'success': False,
                    'stdout': '',
                    'stderr': f'Security: Command blocked - "{dangerous}" is not allowed',
                    'return_code': -1,
                    'command': command,
                    'blocked': True
                }
        
        # Security: Only allow safe commands
        safe_commands = [
            'ls', 'pwd', 'whoami', 'date', 'echo', 'cat', 'head', 'tail',
            'grep', 'find', 'wc', 'sort', 'uniq', 'cut', 'awk', 'sed',
            'mkdir', 'touch', 'cp', 'mv', 'rm ', 'chmod', 'chown',
            'python', 'python3', 'pip', 'pip3', 'conda',
            'git', 'git status', 'git log', 'git diff',
            'node', 'npm', 'npx', 'yarn',
            'java', 'javac', 'mvn', 'gradle',
            'gcc', 'g++', 'make', 'cmake',
            'docker', 'docker-compose',
            'kubectl', 'helm',
            'curl', 'wget', 'http', 'https',
            'ps', 'top', 'htop', 'free', 'df', 'du',
            'tar', 'zip', 'unzip', 'gzip', 'gunzip',
            'ssh-keygen', 'ssh-copy-id',
            'rsync', 'scp',
            'vim', 'nano', 'emacs', 'code',
            'jupyter', 'jupyter-lab', 'jupyter-notebook',
            'conda activate', 'conda deactivate',
            'source venv/bin/activate', 'deactivate'
        ]
        
        # Check if command starts with a safe command
        command_parts = command.strip().split()
        if not command_parts:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Security: Empty command not allowed',
                'return_code': -1,
                'command': command,
                'blocked': True
            }
        
        first_command = command_parts[0].lower()
        is_safe = False
        
        for safe in safe_commands:
            if first_command == safe.lower() or command_lower.startswith(safe.lower() + ' '):
                is_safe = True
                break
        
        if not is_safe:
            return {
                'success': False,
                'stdout': '',
                'stderr': f'Security: Command "{first_command}" is not in the allowed list',
                'return_code': -1,
                'command': command,
                'blocked': True
            }
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.workspace_root)
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode,
                'command': command
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': f'Command timed out after {timeout} seconds',
                'return_code': -1,
                'command': command
            }
            
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'return_code': -1,
                'command': command
            }
    
    def create_and_run_script(self, 
                             script_content: str, 
                             script_name: str = "script.py",
                             timeout: int = 30) -> Dict[str, Any]:
        """
        Create a script file and run it.
        
        Args:
            script_content: Content of the script
            script_name: Name of the script file
            timeout: Execution timeout in seconds
            
        Returns:
            Dictionary with execution results
        """
        try:
            script_path = self.workspace_root / script_name
            
            # Write script to file
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # Make script executable
            os.chmod(script_path, 0o755)
            
            # Run the script
            result = self.execute_python_code(
                f"exec(open('{script_name}').read())",
                timeout=timeout
            )
            
            result['script_path'] = str(script_path)
            result['script_name'] = script_name
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to create and run script {script_name}: {e}")
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'return_code': -1,
                'script_path': str(self.workspace_root / script_name),
                'script_name': script_name
            }

def get_code_interpreter_tools() -> List[Dict]:
    """Return tool definitions for code interpreter tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": "execute_python_code",
                "description": "Execute Python code safely. Use this for data analysis, calculations, file processing, or any Python operations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python code to execute"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Execution timeout in seconds (default: 30)",
                            "default": 30
                        },
                        "capture_output": {
                            "type": "boolean",
                            "description": "Whether to capture stdout/stderr (default: true)",
                            "default": True
                        }
                    },
                    "required": ["code"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "install_package",
                "description": "Install a Python package using pip. Use this when you need additional libraries.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "package": {
                            "type": "string",
                            "description": "Package name to install (e.g., 'requests', 'pandas')"
                        }
                    },
                    "required": ["package"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "run_shell_command",
                "description": "Run a shell command safely. Use this for system operations or running external tools.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Shell command to run"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Execution timeout in seconds (default: 30)",
                            "default": 30
                        }
                    },
                    "required": ["command"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_and_run_script",
                "description": "Create a script file and run it. Use this for complex operations that need to be saved as files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "script_content": {
                            "type": "string",
                            "description": "Content of the script"
                        },
                        "script_name": {
                            "type": "string",
                            "description": "Name of the script file (default: script.py)",
                            "default": "script.py"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Execution timeout in seconds (default: 30)",
                            "default": 30
                        }
                    },
                    "required": ["script_content"]
                }
            }
        }
    ]

# Global instance
code_interpreter = CodeInterpreter()

