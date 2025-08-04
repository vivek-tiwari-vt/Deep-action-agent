#!/usr/bin/env python3
"""
Comprehensive Debug Logger for Deep Action Agent
Logs all agent activities, browser operations, and errors by task ID
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger
import traceback
import sys

class DebugLogger:
    """Centralized debug logging system for the Deep Action Agent."""
    
    def __init__(self, base_log_dir: str = "logs"):
        self.base_log_dir = Path(base_log_dir)
        self.base_log_dir.mkdir(exist_ok=True)
        self.task_loggers = {}
        
    def get_task_logger(self, task_id: str) -> 'TaskLogger':
        """Get or create a task-specific logger."""
        if task_id not in self.task_loggers:
            self.task_loggers[task_id] = TaskLogger(task_id, self.base_log_dir)
        return self.task_loggers[task_id]
    
    def log_agent_action(self, task_id: str, action: str, details: Dict[str, Any], level: str = "INFO"):
        """Log an agent action."""
        task_logger = self.get_task_logger(task_id)
        task_logger.log_agent_action(action, details, level)
    
    def log_browser_action(self, task_id: str, action: str, details: Dict[str, Any], level: str = "INFO"):
        """Log a browser action."""
        task_logger = self.get_task_logger(task_id)
        task_logger.log_browser_action(action, details, level)
    
    def log_error(self, task_id: str, error: Exception, context: str = "", level: str = "ERROR"):
        """Log an error with full traceback."""
        task_logger = self.get_task_logger(task_id)
        task_logger.log_error(error, context, level)
    
    def log_llm_call(self, task_id: str, provider: str, model: str, messages: list, response: Dict[str, Any], duration: float):
        """Log LLM calls with details."""
        task_logger = self.get_task_logger(task_id)
        task_logger.log_llm_call(provider, model, messages, response, duration)
    
    def log_tool_call(self, task_id: str, tool_name: str, arguments: Dict[str, Any], result: Any, duration: float):
        """Log tool calls with details."""
        task_logger = self.get_task_logger(task_id)
        task_logger.log_tool_call(tool_name, arguments, result, duration)
    
    def log_research_phase(self, task_id: str, phase_name: str, phase_data: Dict[str, Any]):
        """Log research phase execution."""
        task_logger = self.get_task_logger(task_id)
        task_logger.log_research_phase(phase_name, phase_data)
    
    def log_file_operation(self, task_id: str, operation: str, file_path: str, details: Dict[str, Any]):
        """Log file operations."""
        task_logger = self.get_task_logger(task_id)
        task_logger.log_file_operation(operation, file_path, details)

class TaskLogger:
    """Task-specific logger that writes to a dedicated log file."""
    
    def __init__(self, task_id: str, base_log_dir: Path):
        self.task_id = task_id
        self.log_file = base_log_dir / f"task_{task_id}.log"
        self.json_log_file = base_log_dir / f"task_{task_id}_detailed.json"
        
        # Initialize JSON log file
        if not self.json_log_file.exists():
            with open(self.json_log_file, 'w') as f:
                json.dump({
                    "task_id": task_id,
                    "start_time": datetime.now().isoformat(),
                    "logs": []
                }, f, indent=2)
    
    def _write_log(self, log_entry: Dict[str, Any]):
        """Write a log entry to both text and JSON files."""
        timestamp = datetime.now().isoformat()
        log_entry["timestamp"] = timestamp
        
        # Write to text log
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {log_entry['level']}: {log_entry['message']}\n")
            if log_entry.get('details'):
                f.write(f"  Details: {json.dumps(log_entry['details'], indent=2)}\n")
            if log_entry.get('traceback'):
                f.write(f"  Traceback: {log_entry['traceback']}\n")
            f.write("\n")
        
        # Write to JSON log
        try:
            with open(self.json_log_file, 'r') as f:
                data = json.load(f)
            
            data["logs"].append(log_entry)
            
            with open(self.json_log_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write to JSON log: {e}")
    
    def log_agent_action(self, action: str, details: Dict[str, Any], level: str = "INFO"):
        """Log an agent action."""
        self._write_log({
            "type": "agent_action",
            "level": level,
            "action": action,
            "details": details,
            "message": f"Agent Action: {action}"
        })
    
    def log_browser_action(self, action: str, details: Dict[str, Any], level: str = "INFO"):
        """Log a browser action."""
        self._write_log({
            "type": "browser_action",
            "level": level,
            "action": action,
            "details": details,
            "message": f"Browser Action: {action}"
        })
    
    def log_error(self, error: Exception, context: str = "", level: str = "ERROR"):
        """Log an error with full traceback."""
        self._write_log({
            "type": "error",
            "level": level,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "traceback": traceback.format_exc(),
            "message": f"Error in {context}: {str(error)}"
        })
    
    def log_llm_call(self, provider: str, model: str, messages: list, response: Dict[str, Any], duration: float):
        """Log LLM calls with details."""
        # Truncate messages and response for logging
        truncated_messages = []
        for msg in messages[-3:]:  # Last 3 messages
            truncated_msg = msg.copy()
            if len(truncated_msg.get('content', '')) > 500:
                truncated_msg['content'] = truncated_msg['content'][:500] + "..."
            truncated_messages.append(truncated_msg)
        
        truncated_response = response.copy()
        if 'choices' in truncated_response and truncated_response['choices']:
            choice = truncated_response['choices'][0]
            if 'message' in choice and 'content' in choice['message']:
                if len(choice['message']['content']) > 500:
                    choice['message']['content'] = choice['message']['content'][:500] + "..."
        
        self._write_log({
            "type": "llm_call",
            "level": "INFO",
            "provider": provider,
            "model": model,
            "duration": duration,
            "messages": truncated_messages,
            "response": truncated_response,
            "message": f"LLM Call: {provider}/{model} ({duration:.2f}s)"
        })
    
    def log_tool_call(self, tool_name: str, arguments: Dict[str, Any], result: Any, duration: float):
        """Log tool calls with details."""
        # Truncate result for logging
        truncated_result = result
        if isinstance(result, str) and len(result) > 1000:
            truncated_result = result[:1000] + "..."
        elif isinstance(result, dict):
            truncated_result = {k: str(v)[:200] + "..." if len(str(v)) > 200 else v 
                              for k, v in result.items()}
        
        self._write_log({
            "type": "tool_call",
            "level": "INFO",
            "tool_name": tool_name,
            "arguments": arguments,
            "result": truncated_result,
            "duration": duration,
            "message": f"Tool Call: {tool_name} ({duration:.2f}s)"
        })
    
    def log_research_phase(self, phase_name: str, phase_data: Dict[str, Any]):
        """Log research phase execution."""
        self._write_log({
            "type": "research_phase",
            "level": "INFO",
            "phase_name": phase_name,
            "phase_data": phase_data,
            "message": f"Research Phase: {phase_name}"
        })
    
    def log_file_operation(self, operation: str, file_path: str, details: Dict[str, Any]):
        """Log file operations."""
        self._write_log({
            "type": "file_operation",
            "level": "INFO",
            "operation": operation,
            "file_path": file_path,
            "details": details,
            "message": f"File Operation: {operation} - {file_path}"
        })

# Global debug logger instance
debug_logger = DebugLogger()

def log_agent_action(task_id: str, action: str, details: Dict[str, Any], level: str = "INFO"):
    """Convenience function to log agent actions."""
    debug_logger.log_agent_action(task_id, action, details, level)

def log_browser_action(task_id: str, action: str, details: Dict[str, Any], level: str = "INFO"):
    """Convenience function to log browser actions."""
    debug_logger.log_browser_action(task_id, action, details, level)

def log_error(task_id: str, error: Exception, context: str = "", level: str = "ERROR"):
    """Convenience function to log errors."""
    debug_logger.log_error(task_id, error, context, level)

def log_llm_call(task_id: str, provider: str, model: str, messages: list, response: Dict[str, Any], duration: float):
    """Convenience function to log LLM calls."""
    debug_logger.log_llm_call(task_id, provider, model, messages, response, duration)

def log_tool_call(task_id: str, tool_name: str, arguments: Dict[str, Any], result: Any, duration: float):
    """Convenience function to log tool calls."""
    debug_logger.log_tool_call(task_id, tool_name, arguments, result, duration)

def log_research_phase(task_id: str, phase_name: str, phase_data: Dict[str, Any]):
    """Convenience function to log research phases."""
    debug_logger.log_research_phase(task_id, phase_name, phase_data)

def log_file_operation(task_id: str, operation: str, file_path: str, details: Dict[str, Any]):
    """Convenience function to log file operations."""
    debug_logger.log_file_operation(task_id, operation, file_path, details) 