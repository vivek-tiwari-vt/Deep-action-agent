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
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

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
    
    def _call_llm(self, messages: List[Dict], tools: Optional[List[Dict]] = None) -> Dict:
        """Call the LLM with messages and optional tools."""
        try:
            response = llm_handler.call_llm(
                messages=messages,
                tools=tools,
                model=config.DEFAULT_MODEL
            )
            return response
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {"error": str(e)}
    
    async def _execute_tool_call(self, tool_call: Dict) -> str:
        """Execute a tool call and return the result."""
        try:
            function_name = tool_call['function']['name']
            arguments = json.loads(tool_call['function']['arguments'])
            
            # Execute the appropriate tool
            if function_name == 'web_search':
                result = web_research.web_search(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'search_and_extract':
                result = web_research.search_and_extract(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'navigate_to':
                result = web_research.navigate_to(**arguments)
                return json.dumps(result, indent=2)
            
            elif function_name == 'extract_content':
                result = web_research.extract_content(**arguments)
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
            result = await agent.execute_task(task_description, context)
            
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
            
            # Create comprehensive report
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
    
    async def _create_research_plan(self, task_description: str) -> Dict[str, Any]:
        """Create a comprehensive research plan."""
        progress_tracker.update_task(
            self.task_id,
            current_step="Creating research plan",
            current_step_num=2
        )
        
        # Initialize web research tool
        await self._initialize_web_research()
        
        # Create research plan using LLM
        messages = [
            {"role": "system", "content": """You are a research planning expert. Create a comprehensive research plan with the following phases:
1. Initial Research: Broad overview and key sources
2. Deep Analysis: Detailed examination of specific aspects
3. Data Collection: Gather statistics, facts, and supporting evidence
4. Synthesis: Combine findings into coherent insights
5. Report Creation: Generate comprehensive final report

For each phase, specify:
- Objectives
- Search queries (keep them short and focused, 3-5 words maximum)
- Expected outcomes
- Quality criteria

IMPORTANT: Search queries should be concise and focused, not full sentences. Use key terms only."""},
            {"role": "user", "content": f"Create a research plan for: {task_description}"}
        ]
        
        response = self._call_llm(messages)
        plan_content = response.get('content', '')
        
        # Parse the plan (simplified - in practice, you'd want more robust parsing)
        plan = {
            'task_description': task_description,
            'phases': [
                {
                    'name': 'Initial Research',
                    'objectives': ['Find authoritative sources', 'Identify key topics'],
                    'search_queries': [
                        f"latest developments {task_description} 2024",
                        f"recent advances {task_description}",
                        f"current state {task_description}"
                    ],
                    'status': 'pending'
                },
                {
                    'name': 'Deep Analysis',
                    'objectives': ['Analyze specific aspects', 'Evaluate source quality'],
                    'search_queries': [
                        f"detailed analysis {task_description}",
                        f"comprehensive review {task_description}",
                        f"expert opinion {task_description}"
                    ],
                    'status': 'pending'
                },
                {
                    'name': 'Data Collection',
                    'objectives': ['Gather statistics', 'Collect supporting evidence'],
                    'search_queries': [
                        f"statistics data {task_description}",
                        f"research findings {task_description}",
                        f"case studies {task_description}"
                    ],
                    'status': 'pending'
                }
            ],
            'plan_content': plan_content
        }
        
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
        
        for query in phase['search_queries']:
            try:
                log_agent_action(self.task_id, "execute_search_query", {
                    "phase": phase['name'],
                    "query": query
                })
                
                # Use search_and_extract for better results with task monitoring
                extracted_content = await web_research.search_and_extract(query, max_pages=3, task_id=self.task_id)
                
                if extracted_content:
                    for content in extracted_content:
                        if content.get('url') and content.get('content'):
                            # Assess content quality
                            quality_score = ContentQuality.assess_content_relevance(
                                content.get('content', ''), query
                            )
                            credibility_score = ContentQuality.assess_source_credibility(content.get('url', ''))
                            
                            phase_results.append({
                                'query': query,
                                'url': content.get('url', ''),
                                'title': content.get('title', ''),
                                'content': content.get('content', ''),
                                'quality_score': quality_score,
                                'credibility_score': credibility_score,
                                'phase': phase['name']
                            })
                
                # Human-like delay between searches
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"Failed to execute search query '{query}': {e}")
                log_error(self.task_id, e, f"search_query_{query}")
                continue
        
        return phase_results
    
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
        """Call the LLM with messages and optional tools."""
        try:
            # Determine provider from model name
            provider = config.get_provider_from_model(config.MANAGER_MODEL)
            model = config.clean_model_name(config.MANAGER_MODEL)
            
            response = llm_handler.call_llm(
                provider=provider,
                model=model,
                messages=messages,
                tools=tools,
                temperature=0.3
            )
            return response
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {"error": str(e)} 