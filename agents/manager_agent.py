#!/usr/bin/env python3
"""
Manager Agent
The central orchestrator that manages the todo-driven workflow and coordinates sub-agents.
Integrates browser automation, progress tracking, and resilient file creation.
"""

import asyncio
import json
import threading
import time
import uuid
from datetime import datetime
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import inspect

from loguru import logger
from rich.console import Console
from rich.panel import Panel

from tools.file_manager import file_manager, get_file_manager_tools
from tools.web_research import web_research, get_web_research_tools, ContentQuality
from tools.code_interpreter import code_interpreter, get_code_interpreter_tools
from tools.progress_tracker import progress_tracker
from tools.rate_limit_manager import rate_limit_manager
from llm_providers.provider_handler import llm_handler
from tools.debug_logger import (
    log_agent_action, log_error, log_llm_call, log_tool_call, 
    log_research_phase, log_file_operation
)
from tools.task_monitor import get_task_monitor, log_task_activity, get_task_status
import config
from tools.http_client import http_client, get_http_tools
from tools.memory import memory, get_memory_tools
from bs4 import BeautifulSoup
from tools.spreadsheet_tools import spreadsheet_tools, get_spreadsheet_tools
from tools.doc_ingestion import doc_ingestion, get_doc_ingestion_tools
from tools.structured_extraction import structured_extraction, get_structured_extraction_tools
from tools.html_reporter import html_reporter, get_html_reporter_tools
from tools.vector_memory import vector_memory, get_vector_memory_tools
from tools.slack_connector import slack_connector, get_slack_tools
from tools.github_connector import github_connector, get_github_tools
from tools.venv_manager import venv_manager, get_venv_tools
from tools.event_bus import event_bus
from tools.structured_llm_extraction import structured_llm_extraction, get_structured_llm_extraction_tools

console = Console()

class ManagerAgent:
    """
    The Manager Agent orchestrates the entire workflow using a todo-driven approach.
    It creates plans, dispatches sub-agents, and manages the overall task execution.
    Integrates browser automation, progress tracking, and resilient file creation.
    """
    
    def __init__(self, workspace_path: str, task_id: str = None, verbose: bool = False):
        self.workspace_path = Path(workspace_path)
        self.verbose = verbose
        self.task_id = task_id
        
        # Set up workspace for tools
        file_manager.set_workspace(str(self.workspace_path))
        code_interpreter.set_workspace(str(self.workspace_path))
        
        # Initialize paths
        self.todo_file = self.workspace_path / "todo.json"
        self.journal_file = self.workspace_path / "journal.log"
        
        # Load system prompt
        self.system_prompt = self._load_system_prompt()
        
        # Initialize sub-agents
        self.sub_agents = {}
        self._initialize_sub_agents()
        
        # Enhanced features
        self.file_manager = file_manager
        self.web_research_tool = None
        self.research_data = {
            'sections': [],
            'data': {},
            'sources': [],
            'summary': ''
        }
        
        # Initialize progress tracking
        self._setup_progress_tracking()
        
        # Initialize workspace manager
        self._setup_workspace_manager()
        # Scratchpad path
        (self.workspace_path / "metadata").mkdir(parents=True, exist_ok=True)
        self.scratchpad_file = self.workspace_path / "metadata" / "scratchpad.jsonl"
        self.cancel_flag_file = self.workspace_path / "metadata" / "cancel.flag"
    
    def _setup_progress_tracking(self):
        """Setup progress tracking for this agent."""
        # Use provided task_id or generate a new one
        if not self.task_id:
            self.task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        progress_tracker.create_task(
            self.task_id,
            "Research Task",
            total_steps=10
        )
        
        # Add progress callbacks
        self.file_manager.add_progress_callback(
            progress_tracker.create_file_progress_callback(self.task_id)
        )
        
        # Setup rate limit callbacks
        rate_limit_manager.add_callback(
            progress_tracker.create_api_progress_callback(self.task_id)
        )
    
    def _setup_workspace_manager(self):
        """Setup workspace manager for this agent."""
        from main import get_workspace_manager
        
        try:
            # Get or create workspace manager for this task
            self.workspace_manager = get_workspace_manager(self.task_id)
            print(f"✅ Workspace manager initialized for task: {self.task_id}")
        except Exception as e:
            print(f"⚠️  Warning: Could not initialize workspace manager: {e}")
            self.workspace_manager = None
    
    def _load_system_prompt(self) -> str:
        """Load the manager agent system prompt."""
        prompt_file = Path(__file__).parent / "system_prompt.md"
        if prompt_file.exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        
        # Fallback system prompt
        return """You are the Manager Agent, the central orchestrator of a deep research and action system.

Your role is to:
1. Break down complex tasks into manageable sub-tasks
2. Create and maintain a todo.json file with task dependencies
3. Dispatch appropriate sub-agents for specialized work
4. Coordinate parallel execution when possible
5. Synthesize results from sub-agents into final outputs

Key principles:
- Always think step-by-step and plan thoroughly
- Use the todo-driven workflow to track progress
- Leverage sub-agents for specialized tasks (research, coding, analysis, criticism)
- Maintain detailed logs of all actions and decisions
- Ensure quality through the critic sub-agent
- Adapt plans based on intermediate results

Available tools:
- Web search and scraping for information gathering
- File system operations for data management
- Code execution for analysis and automation
- Sub-agent dispatch for specialized tasks

When planning:
- Identify dependencies between tasks
- Consider which tasks can run in parallel
- Always include a final synthesis/reporting step
- Add quality control steps using the critic agent

Be thorough, methodical, and adaptive in your approach."""
    
    def _initialize_sub_agents(self):
        """Initialize sub-agent classes."""
        from agents.sub_agents.researcher.agent import ResearcherAgent
        from agents.sub_agents.coder.agent import CoderAgent
        from agents.sub_agents.analyst.agent import AnalystAgent
        from agents.sub_agents.critic.agent import CriticAgent
        
        self.sub_agents = {
            'researcher': ResearcherAgent(self.workspace_path),
            'coder': CoderAgent(self.workspace_path),
            'analyst': AnalystAgent(self.workspace_path),
            'critic': CriticAgent(self.workspace_path)
        }
    
    def _log_action(self, action: str, details: Dict[str, Any]):
        """Log an action to the journal."""
        timestamp = datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'action': action,
            'details': details
        }
        
        with open(self.journal_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def _get_available_tools(self) -> List[Dict]:
        """Get all available tools for the manager agent."""
        tools = []
        tools.extend(get_web_research_tools())
        tools.extend(get_file_manager_tools())
        tools.extend(get_code_interpreter_tools())
        tools.extend(get_http_tools())
        tools.extend(get_memory_tools())
        tools.extend(get_spreadsheet_tools())
        tools.extend(get_doc_ingestion_tools())
        tools.extend(get_structured_extraction_tools())
        tools.extend(get_html_reporter_tools())
        tools.extend(get_vector_memory_tools())
        tools.extend(get_slack_tools())
        tools.extend(get_github_tools())
        tools.extend(get_venv_tools())
        tools.extend(get_structured_llm_extraction_tools())
        
        # Add sub-agent dispatch tools
        tools.append({
            "type": "function",
            "function": {
                "name": "dispatch_sub_agent",
                "description": "Dispatch a task to a specialized sub-agent",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "agent_type": {
                            "type": "string",
                            "enum": ["researcher", "coder", "analyst", "critic"],
                            "description": "Type of sub-agent to dispatch"
                        },
                        "task_description": {
                            "type": "string",
                            "description": "Description of the task to execute"
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context for the task"
                        }
                    },
                    "required": ["agent_type", "task_description"]
                }
            }
        })
        
        # Add todo management tools
        tools.append({
            "type": "function",
            "function": {
                "name": "update_todo",
                "description": "Update the todo.json file with new tasks or status",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "todo_data": {
                            "type": "string",
                            "description": "JSON string containing todo data"
                        }
                    },
                    "required": ["todo_data"]
                }
            }
        })
        
        tools.append({
            "type": "function",
            "function": {
                "name": "create_comprehensive_research_report",
                "description": "Create a comprehensive research report with professional formatting including executive summary, detailed analysis, key findings, and sources",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Research topic"
                        },
                        "extracted_content": {
                            "type": "array",
                            "description": "List of extracted content from web pages"
                        },
                        "sources": {
                            "type": "array",
                            "description": "List of source information"
                        },
                        "task_id": {
                            "type": "string",
                            "description": "Task ID for tracking"
                        }
                    },
                    "required": ["topic", "extracted_content", "sources"]
                }
            }
        })
        
        return tools
    
    async def _execute_tool_call(self, tool_call: Dict) -> str:
        """Execute a tool call and return the result."""
        try:
            function_name = tool_call['function']['name']
            arguments = json.loads(tool_call['function']['arguments'])
            
            # Execute the appropriate tool
            if function_name == 'web_search':
                result = await web_research.web_search(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'search_and_extract':
                result = await web_research.search_and_extract(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'navigate_to':
                result = await web_research.navigate_to(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'extract_content':
                result = await web_research.extract_content(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'read_file':
                result = file_manager.read_file(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'write_file':
                result = file_manager.write_file(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'append_file':
                result = file_manager.append_file(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'list_files':
                result = file_manager.list_files(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'create_directory':
                result = file_manager.create_directory(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'execute_python_code':
                result = code_interpreter.execute_python_code(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'install_package':
                result = code_interpreter.install_package(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'run_shell_command':
                result = code_interpreter.run_shell_command(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'dispatch_sub_agent':
                result = await self._dispatch_sub_agent(**arguments)
                return result
            
            elif function_name == 'update_todo':
                result = self._update_todo(**arguments)
                return result
            
            elif function_name == 'create_comprehensive_research_report':
                result = file_manager.create_comprehensive_research_report(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'http_request':
                result = http_client.http_request(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'memory_remember':
                result = memory.remember(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'memory_search':
                result = memory.search(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'read_table':
                result = spreadsheet_tools.read_table(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'write_table':
                result = spreadsheet_tools.write_table(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'aggregate':
                result = spreadsheet_tools.aggregate(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'ingest':
                result = doc_ingestion.ingest(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'extract_with_patterns':
                result = structured_extraction.extract_with_patterns(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'render_html_report':
                result = html_reporter.render(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'vector_upsert':
                result = vector_memory.upsert(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'vector_query':
                result = vector_memory.query(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'slack_post_message':
                result = slack_connector.post_message(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'github_create_issue':
                result = github_connector.create_issue(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'github_comment_issue':
                result = github_connector.comment_issue(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'create_task_venv':
                result = venv_manager.create_task_venv(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'venv_install':
                result = venv_manager.install(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'extract_with_schema':
                result = structured_llm_extraction.extract_with_schema(**arguments)
                return json.dumps(result, indent=2)

            elif function_name == 'extract_json_mode':
                result = structured_llm_extraction.extract_json_mode(**arguments)
                return json.dumps(result, indent=2)
            
            else:
                return f"Unknown function: {function_name}"
                
        except Exception as e:
            logger.error(f"Tool execution failed for {function_name}: {e}")
            return f"Error executing {function_name}: {str(e)}"
    
    async def _dispatch_sub_agent(self, agent_type: str, task_description: str, context: str = "") -> str:
        """Dispatch a task to a sub-agent."""
        if agent_type not in self.sub_agents:
            return f"Unknown agent type: {agent_type}"
        
        try:
            self._log_action(f"dispatch_{agent_type}", {
                'task': task_description,
                'context': context
            })
            
            agent = self.sub_agents[agent_type]
            # Support both async and sync execute_task implementations
            exec_fn = getattr(agent, "execute_task", None)
            if exec_fn is None:
                return f"Agent {agent_type} has no execute_task method"
            if inspect.iscoroutinefunction(exec_fn):
                result = await exec_fn(task_description, context)
            else:
                result = exec_fn(task_description, context)
                # If a sync function returned an awaitable, await it
                if inspect.isawaitable(result):
                    result = await result
            
            self._log_action(f"completed_{agent_type}", {
                'task': task_description,
                'result_summary': result[:200] + "..." if len(result) > 200 else result
            })
            
            return result
            
        except Exception as e:
            error_msg = f"Sub-agent {agent_type} failed: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def _update_todo(self, todo_data: str) -> str:
        """Update the todo.json file."""
        try:
            todo_dict = json.loads(todo_data)
            with open(self.todo_file, 'w', encoding='utf-8') as f:
                json.dump(todo_dict, f, indent=2)
            
            self._log_action("update_todo", {
                'tasks_count': len(todo_dict.get('tasks', [])),
                'status': todo_dict.get('status', 'unknown')
            })
            
            return "Todo file updated successfully"
            
        except Exception as e:
            error_msg = f"Failed to update todo: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def _load_todo(self) -> Optional[Dict]:
        """Load the current todo.json file."""
        if self.todo_file.exists():
            try:
                with open(self.todo_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load todo: {e}")
        return None
    
    async def execute_task(self, task_description: str) -> str:
        """Execute a task using the todo-driven workflow."""
        try:
            # Load existing todo or create new one
            todo = self._load_todo() or {
                'status': 'planning',
                'tasks': [],
                'current_task': None,
                'completed_tasks': []
            }
            
            # Add the new task
            todo['tasks'].append({
                'id': f"task_{len(todo['tasks']) + 1}",
                'description': task_description,
                'status': 'pending',
                'dependencies': [],
                'assigned_agent': None,
                'result': None
            })
            
            # Update todo file
            self._update_todo(json.dumps(todo))
            
            # Start execution
            return await self._execute_todo_workflow(todo)
            
        except Exception as e:
            error_msg = f"Task execution failed: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    async def _execute_todo_workflow(self, todo: Dict) -> str:
        """Execute the todo-driven workflow."""
        try:
            # Get available tools
            tools = self._get_available_tools()
            
            # Create initial planning message
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Plan and execute this task: {todo['tasks'][-1]['description']}\n\nCurrent todo state: {json.dumps(todo, indent=2)}"}
            ]
            
            # Call LLM for planning
            response = self._call_llm(messages, tools)
            
            if 'error' in response:
                return f"Planning failed: {response['error']}"
            
            # Execute tool calls if any
            if 'tool_calls' in response:
                for tool_call in response['tool_calls']:
                    result = await self._execute_tool_call(tool_call)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call['id'],
                        "content": result
                    })
                
                # Get final response
                final_response = self._call_llm(messages)
                return final_response.get('content', 'Task completed')
            
            return response.get('content', 'Task completed')
            
        except Exception as e:
            error_msg = f"Workflow execution failed: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    async def _initialize_web_research(self):
        """Initialize web research tool if needed."""
        if self.web_research_tool is None:
            try:
                # Use visible browser with slow motion for user to see actions
                self.web_research_tool = web_research
                
                # Set task_id for proper file organization
                if self.task_id and hasattr(self.web_research_tool, 'set_task_id'):
                    self.web_research_tool.set_task_id(self.task_id)
                
                self.web_research_tool.add_progress_callback(
                    progress_tracker.create_browser_progress_callback(self.task_id)
                )
                
                # Start the browser
                await self.web_research_tool.start_browser()
                
                logger.info("Web research tool initialized and browser started successfully")
                console.print("[green]🌐 Web research tool ready for use![/green]")
            except Exception as e:
                logger.error(f"Failed to initialize web research tool: {e}")
                self.web_research_tool = None
    
    async def execute_research_task(self, task_description: str) -> Dict[str, Any]:
        """
        Execute a comprehensive research task with browser automation and progress tracking.
        
        Args:
            task_description: Description of the research task
            
        Returns:
            Dictionary containing research results and file paths
        """
        # Initialize task monitor
        task_monitor = get_task_monitor(self.task_id)
        task_monitor.set_original_task(task_description)
        
        # Log task initialization
        log_task_activity(self.task_id, "task_initialization", f"Task monitor initialized for: {task_description}", {
            "task_description": task_description,
            "task_id": self.task_id,
            "monitor_initialized": True
        })
        
        log_agent_action(self.task_id, "start_research_task", {
            "task_description": task_description,
            "task_id": self.task_id
        })
        
        # Log task start
        log_task_activity(self.task_id, "task_start", f"Starting research task: {task_description}", {
            "task_description": task_description,
            "task_id": self.task_id
        })
        
        try:
            # Start progress tracking
            progress_tracker.start_task(self.task_id, "Initializing research task")
            progress_tracker.start_live_display()
            
            # Update progress
            progress_tracker.update_task(
                self.task_id,
                current_step="Analyzing task requirements",
                current_step_num=1
            )
            
            # Create research plan
            log_agent_action(self.task_id, "create_research_plan", {"task_description": task_description})
            plan = await self._create_research_plan(task_description)
            
            # Execute research phases with task monitoring
            log_agent_action(self.task_id, "execute_research_phases", {"plan_phases": len(plan.get('phases', []))})
            research_results = await self._execute_research_phases(plan)
            
            # Check if task should be redirected
            if task_monitor.should_redirect_task():
                redirect_instructions = task_monitor.get_redirect_instructions()
                logger.warning(f"Task needs redirection: {redirect_instructions}")
                
                # Log redirection attempt
                log_task_activity(self.task_id, "task_redirection", f"Redirecting task: {redirect_instructions}", {
                    "redirect_instructions": redirect_instructions,
                    "deviation_count": task_monitor.deviation_count
                })
                
                # Retry with redirected instructions
                research_results = await self._execute_research_phases_with_redirection(plan, redirect_instructions)
            
            # Create comprehensive report only if we actually extracted content; otherwise fail fast
            if research_results.get('total_sources', 0) <= 0:
                raise RuntimeError("No content extracted; aborting report generation. Check search and extraction logs.")
            report_path = await self._create_comprehensive_report(research_results)
            
            # Mark task as completed
            task_monitor.mark_task_completed()
            
            # Complete progress tracking
            progress_tracker.complete_task(self.task_id, "Research task completed")
            progress_tracker.stop_live_display()
            
            # Clean up browser
            if self.web_research_tool:
                try:
                    await self.web_research_tool.stop_browser()
                    logger.info("Browser stopped successfully")
                except Exception as e:
                    logger.error(f"Error stopping browser: {e}")
            
            # Log task completion
            log_task_activity(self.task_id, "task_completed", f"Research task completed successfully", {
                "total_sources": len(research_results.get('all_results', [])),
                "report_path": report_path
            })
            
            return {
                'success': True,
                'report_path': report_path,
                'research_data': research_results,
                'task_id': self.task_id,
                'task_status': task_monitor.get_task_status()
            }
            
        except Exception as e:
            error_msg = f"Research task failed: {str(e)}"
            logger.error(error_msg)
            
            # Mark task as failed
            task_monitor.mark_task_failed(error_msg)
            
            # Log task failure
            log_task_activity(self.task_id, "task_failed", f"Research task failed: {error_msg}", {
                "error": error_msg
            }, success=False)
            
            progress_tracker.fail_task(self.task_id, str(e))
            progress_tracker.stop_live_display()
            
            # Clean up browser on error
            if self.web_research_tool:
                try:
                    await self.web_research_tool.stop_browser()
                except Exception as cleanup_error:
                    logger.error(f"Error stopping browser during cleanup: {cleanup_error}")
            
            return {
                'success': False,
                'error': str(e),
                'task_id': self.task_id,
                'task_status': task_monitor.get_task_status()
            }

    async def execute_task_iterative(self, task_description: str, max_steps: int = 12) -> str:
        """Iterative planner–executor loop with tool use and reflection."""
        try:
            # Heuristic: route obviously web research tasks to the dedicated flow
            if self._should_route_to_research(task_description):
                research = await self.execute_research_task(task_description)
                if isinstance(research, dict) and research.get('success'):
                    return json.dumps({
                        "message": "Research completed",
                        "report_path": research.get('report_path'),
                        "task_id": research.get('task_id')
                    }, indent=2)
                # If research failed, fall back to iterative loop
            progress_tracker.start_task(self.task_id, "Planning task")
            tools = self._get_available_tools()
            messages: List[Dict[str, Any]] = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Plan and execute the task end-to-end: {task_description}"}
            ]
            step = 0
            while step < max_steps:
                step += 1
                if self._is_cancelled():
                    return "Task cancelled"
                progress_tracker.update_task(self.task_id, current_step=f"Step {step}: Reasoning", current_step_num=min(step, 10))
                def on_delta(evt: Dict[str, Any]):
                    try:
                        asyncio.create_task(event_bus.publish(self.task_id, {"type": "llm_delta", "data": evt}))
                    except Exception:
                        pass
                response = llm_handler.call_llm(
                    provider=config.get_provider_from_model(config.MANAGER_MODEL),
                    model=config.clean_model_name(config.MANAGER_MODEL),
                    messages=messages,
                    tools=tools,
                    stream_tokens=True,
                    on_delta=on_delta,
                    temperature=0.3,
                )
                # Basic OpenAI-format compatibility
                message = None
                if response.get('choices'):
                    message = response['choices'][0].get('message', {})
                    finish = response['choices'][0].get('finish_reason')
                else:
                    message = {"role": "assistant", "content": response.get('content', '')}
                    finish = response.get('finish_reason')

                if not message:
                    break
                messages.append(message)
                self._append_scratchpad({"step": step, "assistant": message})

                tool_calls = message.get('tool_calls') or []
                if tool_calls:
                    # Execute tool calls sequentially (could be parallelized later)
                    for tool_call in tool_calls:
                        tool_name = tool_call.get('function', {}).get('name')
                        await event_bus.publish(self.task_id, {"type": "tool_start", "name": tool_name, "args": tool_call.get('function', {}).get('arguments')})
                        tool_result = await self._execute_tool_call(tool_call)
                        await event_bus.publish(self.task_id, {"type": "tool_end", "name": tool_name, "result": tool_result})
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.get('id'),
                            "content": tool_result
                        })
                        self._append_scratchpad({"step": step, "tool_call": tool_call, "tool_result": tool_result})
                    # Persist memory of tool outcomes
                    try:
                        self._memory_upsert(f"Step {step} tool outcomes: {str([tc.get('function', {}).get('name') for tc in tool_calls])}")
                    except Exception:
                        pass
                    # Continue the loop to let the model observe results
                    continue

                # If model stopped without tool calls and produced content, finish.
                if finish == 'stop' or (not tool_calls and message.get('content')):
                    # Reflection pass with critic before finalization
                    reflection_prompt = {
                        "role": "user",
                        "content": "Critically review the current solution for correctness, completeness, potential risks, and missing steps. Return only actionable fixes or CONFIRM if acceptable."
                    }
                    critic_tools = [{
                        "type": "function",
                        "function": {"name": "dispatch_sub_agent", "parameters": {"type": "object", "properties": {"agent_type": {"type": "string"}, "task_description": {"type": "string"}, "context": {"type": "string"}}, "required": ["agent_type", "task_description"]}}
                    }]
                    messages.append(reflection_prompt)
                    critic_review = await self._dispatch_sub_agent("critic", "Review and improve the solution", context=message.get('content', ''))
                    self._append_scratchpad({"step": step, "critic_review": critic_review})
                    self._memory_upsert(f"Critic review at step {step}: {critic_review[:800]}")
                    if critic_review and critic_review.strip().upper().startswith("CONFIRM"):
                        return message.get('content', 'Task completed')
                    else:
                        # Feed critic feedback back into the loop
                        messages.append({"role": "user", "content": f"Incorporate this critique and finalize: {critic_review[:4000]}"})
                        continue

            return messages[-1].get('content', 'Task completed') if messages and isinstance(messages[-1], dict) else 'Task completed'
        except Exception as e:
            logger.error(f"Iterative execution failed: {e}")
            return f"Task failed: {e}"

    def _should_route_to_research(self, task_description: str) -> bool:
        """Simple heuristic to decide if this task should use the research workflow."""
        if not task_description:
            return False
        text = task_description.lower()
        research_terms = [
            "research", "find sources", "recent", "latest", "news", "articles", "citations", "summarize from web",
            "list", "compare", "gather information"
        ]
        topic_terms = ["ai", "ml", "machine learning", "llm", "technology", "market", "trend", "paper", "study"]
        return any(t in text for t in research_terms) and any(t in text for t in topic_terms)

    def _append_scratchpad(self, entry: Dict[str, Any]) -> None:
        try:
            with open(self.scratchpad_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as _:
            pass

    def _memory_upsert(self, text: str, namespace: str = None) -> None:
        try:
            ns = namespace or (self.task_id or "default")
            vector_memory.upsert(ns, [text], metadatas=[{"task_id": self.task_id}])
        except Exception:
            pass

    def _is_cancelled(self) -> bool:
        return self.cancel_flag_file.exists()
    
    async def _create_research_plan(self, task_description: str) -> Dict[str, Any]:
        """Create a comprehensive research plan."""
        progress_tracker.update_task(
            self.task_id,
            current_step="Creating research plan",
            current_step_num=2
        )
        
        # Initialize web research tool
        await self._initialize_web_research()
        
        # Deterministic, short, normalized queries to avoid LLM drift and gibberish
        topic = self._normalize_query(task_description.strip())
        base = topic if topic else task_description.strip()
        core_terms = ["overview", "trends", "2024", "2025", "recent", "latest", "insights"]
        qs1 = [self._normalize_query(f"{base} {term}") for term in core_terms[:3]]
        qs2 = [self._normalize_query(f"{base} {term}") for term in core_terms[3:6]]
        qs3 = [
            self._normalize_query(f"{base} statistics"),
            self._normalize_query(f"{base} market size"),
            self._normalize_query(f"{base} case studies")
        ]

        plan = {
            'task_description': task_description,
            'phases': [
                {
                    'name': 'Initial Research',
                    'objectives': ['Find authoritative sources', 'Identify key topics'],
                    'search_queries': qs1,
                    'status': 'pending'
                },
                {
                    'name': 'Deep Analysis',
                    'objectives': ['Analyze specific aspects', 'Evaluate source quality'],
                    'search_queries': qs2,
                    'status': 'pending'
                },
                {
                    'name': 'Data Collection',
                    'objectives': ['Gather statistics', 'Collect supporting evidence'],
                    'search_queries': qs3,
                    'status': 'pending'
                }
            ],
            'plan_content': 'deterministic-plan'
        }
        # Augment with LLM-driven breakdown
        try:
            messages = [
                {"role": "system", "content": "You plan web research. Return JSON only."},
                {"role": "user", "content": (
                    "Break the following task into up to 8 succinct, concrete Google queries. "
                    "Queries must be short (<=6 words), contain no quotes or punctuation beyond spaces and hyphens, and be directly useful. "
                    "Respond as a JSON array of strings only.\n\nTask: " + task_description
                )},
            ]
            llm_resp = self._call_llm(messages)
            proposed = []
            if isinstance(llm_resp, dict):
                content = (llm_resp.get('choices') or [{}])[0].get('message', {}).get('content')
                if content:
                    try:
                        import json as _json
                        raw_list = _json.loads(content)
                        if isinstance(raw_list, list):
                            for q in raw_list:
                                if isinstance(q, str):
                                    nq = self._normalize_query(q)
                                    if nq and nq not in proposed:
                                        proposed.append(nq)
                    except Exception:
                        pass
            if proposed:
                plan['phases'].insert(0, {
                    'name': 'LLM Plan',
                    'objectives': ['Use LLM plan to guide initial searches'],
                    'search_queries': proposed[:8],
                    'status': 'pending'
                })
        except Exception:
            pass
        return plan
    
    async def _execute_research_phases(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all research phases."""
        progress_tracker.update_task(
            self.task_id,
            current_step="Executing research phases",
            current_step_num=3
        )
        
        all_results = []
        
        for i, phase in enumerate(plan['phases']):
            progress_tracker.update_task(
                self.task_id,
                current_step=f"Phase {i+1}: {phase['name']}",
                current_step_num=4 + i
            )
            
            phase_results = await self._execute_research_phase(phase)
            all_results.extend(phase_results)
            
            # Update phase status
            plan['phases'][i]['status'] = 'completed'
            plan['phases'][i]['results'] = phase_results
        
        # Iterative follow-ups with LLM based on collected content
        try:
            followups_rounds = 2
            for r in range(followups_rounds):
                if self._is_cancelled():
                    break
                suggested = await self._llm_propose_followups(plan.get('task_description', ''), all_results)
                suggested = [s for s in suggested if s]
                if not suggested:
                    break
                follow_phase = {
                    'name': f'LLM Follow-ups Round {r+1}',
                    'objectives': ['Fill gaps and deepen coverage'],
                    'search_queries': suggested[:6],
                    'status': 'pending'
                }
                phase_results = await self._execute_research_phase(follow_phase)
                follow_phase['status'] = 'completed'
                follow_phase['results'] = phase_results
                plan['phases'].append(follow_phase)
                all_results.extend(phase_results)
                # Stop early if we already have enough material
                if len(all_results) >= 8:
                    break
        except Exception:
            pass

        return {
            'plan': plan,
            'all_results': all_results,
            'total_sources': len(all_results)
        }
    
    async def _execute_research_phase(self, phase: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a single research phase."""
        phase_results = []
        
        log_research_phase(self.task_id, phase['name'], {
            "phase": phase,
            "search_queries": phase['search_queries']
        })
        
        # Parallelize queries with limited concurrency
        sem = asyncio.Semaphore(3)

        async def run_query(query: str) -> List[Dict[str, Any]]:
            async with sem:
                try:
                    if self._is_cancelled():
                        return []
                    norm_query = self._normalize_query(query)
                    log_agent_action(self.task_id, "execute_search_query", {"phase": phase['name'], "query": norm_query})
                    # Always navigate and extract across at least 2 pages for reliability
                    extracted_content = await web_research.search_and_extract(norm_query, max_pages=3, task_id=self.task_id)
                    results: List[Dict[str, Any]] = []
                    if extracted_content:
                        for content in extracted_content:
                            if content.get('url') and content.get('content'):
                                quality_score = ContentQuality.assess_content_relevance(content.get('content', ''), norm_query)
                                credibility_score = ContentQuality.assess_source_credibility(content.get('url', ''))
                                results.append({
                                    'query': norm_query,
                                    'url': content.get('url', ''),
                                    'title': content.get('title', ''),
                                    'content': content.get('content', ''),
                                    'quality_score': quality_score,
                                    'credibility_score': credibility_score,
                                    'phase': phase['name']
                                })
                    # Fallback: direct HTTP fetch of top search results if browser extraction failed
                    if not results:
                        try:
                            search = await web_research.web_search(norm_query, num_results=5, task_id=self.task_id)
                            hits = []
                            if isinstance(search, dict):
                                hits = search.get('results') or search.get('data') or []
                            for hit in (hits or [])[:5]:
                                url = hit.get('url') or hit.get('link') or hit.get('href')
                                title = hit.get('title') or ''
                                if not url:
                                    continue
                                # Temporarily relax HTTP allowlist for controlled fallback fetch
                                import os
                                old_allow = os.getenv('ALLOW_ALL_HTTP')
                                os.environ['ALLOW_ALL_HTTP'] = 'true'
                                try:
                                    resp = http_client.http_request(method='GET', url=url)
                                finally:
                                    if old_allow is None:
                                        os.environ.pop('ALLOW_ALL_HTTP', None)
                                    else:
                                        os.environ['ALLOW_ALL_HTTP'] = old_allow
                                body = (resp.get('text') or '') if isinstance(resp, dict) else ''
                                if not body:
                                    continue
                                try:
                                    soup = BeautifulSoup(body, 'html.parser')
                                    # Basic cleanup: remove script/style
                                    for tag in soup(['script','style','noscript']):
                                        tag.decompose()
                                    text = ' '.join(soup.get_text(separator=' ').split())
                                    if len(text) < 200:
                                        continue
                                    quality_score = ContentQuality.assess_content_relevance(text, norm_query)
                                    credibility_score = ContentQuality.assess_source_credibility(url)
                                    results.append({
                                        'query': norm_query,
                                        'url': url,
                                        'title': title,
                                        'content': text,
                                        'quality_score': quality_score,
                                        'credibility_score': credibility_score,
                                        'phase': phase['name']
                                    })
                                except Exception:
                                    continue
                        except Exception:
                            pass
                    # Persist extracted snippets immediately to files
                    if results:
                        fname = f"data/extract_{self._safe_name(norm_query)}.json"
                        try:
                            file_manager.write_file(fname, json.dumps(results, indent=2))
                        except Exception:
                            pass
                    return results
                except Exception as e:
                    logger.error(f"Failed to execute search query '{query}': {e}")
                    log_error(self.task_id, e, f"search_query_{query}")
                    return []

        tasks = [run_query(q) for q in phase['search_queries']]
        batches = await asyncio.gather(*tasks, return_exceptions=False)
        for batch in batches:
            phase_results.extend(batch)
        
        return phase_results

    def _safe_name(self, text: str) -> str:
        return "".join(c if c.isalnum() else "_" for c in text)[:80]

    def _normalize_query(self, text: str) -> str:
        if not text:
            return ""
        # Remove meta-instructions
        lowered = text.lower()
        lowered = re.sub(r"^\s*extract\s+content\s+from\s+search\s+results\s+about:\s*", "", lowered)
        lowered = re.sub(r"^\s*search\s+for:\s*", "", lowered)
        # Collapse repeated characters (e.g., LLiisstt -> list)
        collapsed = re.sub(r"(.)\1{1,}", r"\1", lowered)
        # Keep words, digits, spaces, hyphens
        cleaned = re.sub(r"[^a-z0-9\-\s]", " ", collapsed)
        # Squash spaces and limit to 6 words
        words = [w for w in cleaned.strip().split() if w]
        words = words[:6]
        return " ".join(words)

    async def _llm_propose_followups(self, task_description: str, results: List[Dict[str, Any]]) -> List[str]:
        """Ask the LLM for follow-up search queries given what we have already extracted."""
        try:
            # Build a compact context of titles and domains to keep token usage low
            def _domain(u: str) -> str:
                try:
                    from urllib.parse import urlparse
                    return (urlparse(u).netloc or '')
                except Exception:
                    return ''
            top = []
            for r in results[-8:]:
                title = (r.get('title') or '')[:80]
                url = r.get('url') or ''
                dom = _domain(url)
                top.append(f"- {title} ({dom})")
            context = "\n".join(top)
            messages = [
                {"role": "system", "content": "You suggest the next best Google queries. Return JSON only."},
                {"role": "user", "content": (
                    "Task: " + task_description + "\n\nAlready covered sources (titles/domains):\n" + context +
                    "\n\nPropose up to 6 short, concrete queries that close coverage gaps. Output JSON array of strings only."
                )}
            ]
            resp = self._call_llm(messages)
            suggestions: List[str] = []
            if isinstance(resp, dict):
                content = (resp.get('choices') or [{}])[0].get('message', {}).get('content')
                if content:
                    try:
                        import json as _json
                        arr = _json.loads(content)
                        if isinstance(arr, list):
                            for q in arr:
                                if isinstance(q, str):
                                    nq = self._normalize_query(q)
                                    if nq and nq not in suggestions:
                                        suggestions.append(nq)
                    except Exception:
                        return []
            return suggestions[:6]
        except Exception:
            return []
    
    async def _execute_research_phases_with_redirection(self, plan: Dict[str, Any], redirect_instructions: str) -> Dict[str, Any]:
        """Execute research phases with redirection instructions."""
        logger.info(f"Executing research phases with redirection: {redirect_instructions}")
        
        # Log redirection activity
        log_task_activity(self.task_id, "redirection_execution", f"Executing redirected research: {redirect_instructions}", {
            "redirect_instructions": redirect_instructions,
            "plan_phases": len(plan.get('phases', []))
        })
        
        # Create a simplified plan focused on the redirect instructions
        simplified_plan = {
            'phases': [{
                'name': 'Redirected Research',
                'search_queries': [redirect_instructions],
                'objectives': ['Focus on the main task'],
                'expected_outcomes': ['Relevant content extraction']
            }]
        }
        
        return await self._execute_research_phases(simplified_plan)
    
    async def _create_comprehensive_report(self, research_results: Dict[str, Any]) -> str:
        """Create a comprehensive research report with enhanced formatting."""
        progress_tracker.update_task(
            self.task_id,
            current_step="Creating comprehensive report",
            current_step_num=8
        )
        
        try:
            # Extract content and sources for the enhanced report
            extracted_content = []
            sources = []
            
            # Process research results to extract content and sources
            for phase in research_results.get('plan', {}).get('phases', []):
                for result in phase.get('results', []):
                    if result.get('content'):
                        extracted_content.append({
                            'title': result.get('title', 'Untitled'),
                            'url': result.get('url', ''),
                            'text': result.get('content', ''),
                            'quality_score': result.get('quality_score', 0),
                            'credibility_score': result.get('credibility_score', 0)
                        })
                    
                    if result.get('url'):
                        sources.append({
                            'url': result.get('url', ''),
                            'title': result.get('title', 'Untitled'),
                            'credibility': result.get('credibility_score', 0),
                            'type': 'web_page',
                            'date': datetime.now().strftime('%Y-%m-%d')
                        })
            
            # Create comprehensive research report using enhanced file manager
            report_result = file_manager.create_comprehensive_research_report(
                topic=research_results.get('plan', {}).get('task_description', 'Research Task'),
                extracted_content=extracted_content,
                sources=sources,
                task_id=self.task_id
            )
            
            if report_result.get('success'):
                logger.info(f"Enhanced research report created: {report_result.get('main_report_path')}")
                progress_tracker.update_task(
                    self.task_id,
                    current_step="Enhanced report completed",
                    current_step_num=9
                )
                return report_result.get('main_report_path', '')
            else:
                logger.error(f"Failed to create enhanced report: {report_result.get('error')}")
                # Fallback to basic report
                return await self._create_basic_report(research_results)
                
        except Exception as e:
            logger.error(f"Error creating enhanced report: {e}")
            # Fallback to basic report
            return await self._create_basic_report(research_results)
    
    async def _create_basic_report(self, research_results: Dict[str, Any]) -> str:
        """Create a basic research report as fallback."""
        progress_tracker.update_task(
            self.task_id,
            current_step="Creating basic report",
            current_step_num=8
        )
        
        # Prepare report sections
        sections = [
            {
                'title': 'Executive Summary',
                'content': f"Comprehensive research on: {research_results.get('plan', {}).get('task_description', 'Research Task')}\n\nTotal sources analyzed: {research_results.get('total_sources', 0)}\nResearch completed on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            },
            {
                'title': 'Research Methodology',
                'content': f"Research conducted across {len(research_results.get('plan', {}).get('phases', []))} phases:\n" + 
                          "\n".join([f"- {phase['name']}: {len(phase.get('results', []))} sources" for phase in research_results.get('plan', {}).get('phases', [])])
            }
        ]
        
        # Add findings from each phase
        for phase in research_results.get('plan', {}).get('phases', []):
            if phase.get('results'):
                phase_content = f"## {phase['name']}\n\n"
                for result in phase['results']:
                    phase_content += f"### {result.get('title', 'Untitled')}\n"
                    phase_content += f"**Source:** {result.get('url', 'N/A')}\n"
                    phase_content += f"**Quality Score:** {result.get('quality_score', 0):.2f}\n"
                    phase_content += f"**Credibility Score:** {result.get('credibility_score', 0):.2f}\n\n"
                    phase_content += f"{result.get('content', '')[:500]}...\n\n"
                
                sections.append({
                    'title': phase['name'],
                    'content': phase_content
                })
        
        # Create the report file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"research_report_{timestamp}.md"
        
        report_path = file_manager.create_markdown_report(
            title=f"Research Report: {research_results.get('plan', {}).get('task_description', 'Research Task')}",
            sections=sections,
            output_path=report_filename
        )
        
        progress_tracker.update_task(
            self.task_id,
            current_step="Basic report completed",
            current_step_num=9
        )
        
        return report_path
    
    def _call_llm(self, messages: List[Dict], tools: Optional[List[Dict]] = None) -> Dict:
        """Call the LLM with messages and optional tools; log request/response and stream deltas."""
        try:
            provider = config.get_provider_from_model(config.MANAGER_MODEL)
            model = config.clean_model_name(config.MANAGER_MODEL)
            start = time.time()

            def on_delta(evt: Dict[str, Any]):
                try:
                    asyncio.create_task(event_bus.publish(self.task_id, {"type": "llm_delta", "data": evt}))
                except Exception:
                    pass

            # Publish a sanitized request snapshot
            try:
                preview_msgs = []
                for m in messages[-6:]:
                    content = m.get("content", "")
                    if isinstance(content, str) and len(content) > 400:
                        content = content[:400] + "…"
                    preview_msgs.append({"role": m.get("role"), "content": content})
                asyncio.create_task(event_bus.publish(self.task_id, {"type": "llm_request", "provider": provider, "model": model, "messages": preview_msgs, "has_tools": bool(tools)}))
            except Exception:
                pass

            response = llm_handler.call_llm(
                provider=provider,
                model=model,
                messages=messages,
                tools=tools,
                temperature=0.3,
                stream_tokens=True,
                on_delta=on_delta,
            )

            duration = time.time() - start
            try:
                # Log and publish a compact response snapshot
                msg = {}
                if isinstance(response, dict) and response.get("choices"):
                    msg = response["choices"][0].get("message", {})
                preview = {"finish_reason": (response.get("choices") or [{}])[0].get("finish_reason") if isinstance(response, dict) else None}
                if msg.get("content"):
                    preview["content"] = (msg.get("content")[:400] + "…") if len(msg.get("content", "")) > 400 else msg.get("content")
                if msg.get("tool_calls"):
                    preview["tool_calls"] = [tc.get("function", {}).get("name") for tc in msg.get("tool_calls", [])]
                log_llm_call(self.task_id, provider, model, messages, response, duration)
                asyncio.create_task(event_bus.publish(self.task_id, {"type": "llm_response", "duration_s": round(duration, 3), "preview": preview}))
            except Exception:
                pass

            return response
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {"error": str(e)}