#!/usr/bin/env python3
"""
Progress Tracking System
Provides real-time progress updates and live file creation tracking.
"""

import time
import json
import threading
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.layout import Layout
from rich.text import Text
from rich.columns import Columns
from rich.align import Align
from loguru import logger

console = Console()

class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TaskProgress:
    """Task progress information."""
    task_id: str
    task_name: str
    status: TaskStatus
    progress: float  # 0.0 to 1.0
    current_step: str
    total_steps: int
    current_step_num: int
    start_time: datetime
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

class ProgressTracker:
    """Real-time progress tracking system."""
    
    def __init__(self, workspace_path: str = "workspace"):
        self.workspace_path = Path(workspace_path)
        self.tasks: Dict[str, TaskProgress] = {}
        self.callbacks: List[Callable] = []
        self.lock = threading.Lock()
        self.console = Console()
        self.live_display = None
        self.display_enabled = True
        
        # Create progress directory
        self.progress_dir = self.workspace_path / "progress"
        self.progress_dir.mkdir(parents=True, exist_ok=True)
    
    def add_callback(self, callback: Callable[[TaskProgress], None]):
        """Add a progress callback."""
        self.callbacks.append(callback)
    
    def _notify_callbacks(self, task_progress: TaskProgress):
        """Notify all callbacks of progress update."""
        for callback in self.callbacks:
            try:
                callback(task_progress)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")
    
    def create_task(self, task_id: str, task_name: str, total_steps: int = 1) -> str:
        """Create a new task for tracking."""
        with self.lock:
            task_progress = TaskProgress(
                task_id=task_id,
                task_name=task_name,
                status=TaskStatus.PENDING,
                progress=0.0,
                current_step="Initializing",
                total_steps=total_steps,
                current_step_num=0,
                start_time=datetime.now(),
                metadata={}
            )
            
            self.tasks[task_id] = task_progress
            self._save_task_progress(task_progress)
            self._notify_callbacks(task_progress)
            
            logger.info(f"Created task: {task_name} (ID: {task_id})")
            return task_id
    
    def update_task(self, task_id: str, **kwargs) -> bool:
        """Update task progress."""
        with self.lock:
            if task_id not in self.tasks:
                logger.warning(f"Task {task_id} not found")
                return False
            
            task = self.tasks[task_id]
            
            # Update fields
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            
            # Calculate progress if step numbers are provided
            if 'current_step_num' in kwargs and task.total_steps > 0:
                task.progress = min(kwargs['current_step_num'] / task.total_steps, 1.0)
            
            # Update status based on progress
            if task.progress >= 1.0 and task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.COMPLETED
            
            self._save_task_progress(task)
            self._notify_callbacks(task)
            
            return True
    
    def start_task(self, task_id: str, current_step: str = "Starting"):
        """Start a task."""
        return self.update_task(task_id, status=TaskStatus.RUNNING, current_step=current_step)
    
    def complete_task(self, task_id: str, current_step: str = "Completed"):
        """Mark a task as completed."""
        return self.update_task(
            task_id, 
            status=TaskStatus.COMPLETED, 
            current_step=current_step,
            progress=1.0,
            current_step_num=self.tasks[task_id].total_steps
        )
    
    def fail_task(self, task_id: str, error_message: str):
        """Mark a task as failed."""
        return self.update_task(
            task_id,
            status=TaskStatus.FAILED,
            current_step="Failed",
            error_message=error_message
        )
    
    def _save_task_progress(self, task_progress: TaskProgress):
        """Save task progress to file."""
        try:
            # Try to use workspace manager if available
            try:
                from main import get_workspace_manager
                workspace_manager = get_workspace_manager(task_progress.task_id)
                progress_file = Path(workspace_manager.get_progress_path(f"{task_progress.task_id}.json"))
            except Exception as e:
                logger.warning(f"Could not get workspace manager for task {task_progress.task_id}: {e}")
                # Fallback to local file
                progress_file = self.progress_dir / f"{task_progress.task_id}.json"
            
            # Ensure directory exists
            progress_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to dict for JSON serialization
            progress_data = {
                "task_id": task_progress.task_id,
                "task_name": task_progress.task_name,
                "status": task_progress.status.value,
                "progress": task_progress.progress,
                "current_step": task_progress.current_step,
                "total_steps": task_progress.total_steps,
                "current_step_num": task_progress.current_step_num,
                "start_time": task_progress.start_time.isoformat(),
                "estimated_completion": task_progress.estimated_completion.isoformat() if task_progress.estimated_completion else None,
                "error_message": task_progress.error_message,
                "metadata": task_progress.metadata or {}
            }
            
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save task progress: {e}")
    
    def _load_task_progress(self, task_id: str) -> Optional[TaskProgress]:
        """Load task progress from file."""
        try:
            # Try to use workspace manager if available
            try:
                from main import get_workspace_manager
                workspace_manager = get_workspace_manager(task_id)
                progress_file = Path(workspace_manager.get_progress_path(f"{task_id}.json"))
            except Exception as e:
                logger.warning(f"Could not get workspace manager for task {task_id}: {e}")
                # Fallback to local file
                progress_file = self.progress_dir / f"{task_id}.json"
            
            if not progress_file.exists():
                return None
            
            with open(progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert back to TaskProgress object
            return TaskProgress(
                task_id=data["task_id"],
                task_name=data["task_name"],
                status=TaskStatus(data["status"]),
                progress=data["progress"],
                current_step=data["current_step"],
                total_steps=data["total_steps"],
                current_step_num=data["current_step_num"],
                start_time=datetime.fromisoformat(data["start_time"]),
                estimated_completion=datetime.fromisoformat(data["estimated_completion"]) if data.get("estimated_completion") else None,
                error_message=data.get("error_message"),
                metadata=data.get("metadata", {})
            )
            
        except Exception as e:
            logger.error(f"Failed to load task progress: {e}")
            return None
    
    def get_task_progress(self, task_id: str) -> Optional[TaskProgress]:
        """Get task progress by ID."""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[TaskProgress]:
        """Get all tasks."""
        return list(self.tasks.values())
    
    def get_active_tasks(self) -> List[TaskProgress]:
        """Get all active (running) tasks."""
        return [task for task in self.tasks.values() if task.status == TaskStatus.RUNNING]
    
    def create_progress_display(self) -> Layout:
        """Create a rich progress display layout."""
        layout = Layout()
        
        # Header
        header = Panel(
            Align.center(Text("🤖 Deep Action Agent - Live Progress", style="bold blue")),
            style="blue"
        )
        
        # Task table
        task_table = self._create_task_table()
        
        # Status summary
        status_summary = self._create_status_summary()
        
        # Layout structure
        layout.split_column(
            Layout(header, size=3),
            Layout(task_table, name="tasks"),
            Layout(status_summary, size=8)
        )
        
        return layout
    
    def _create_task_table(self) -> Table:
        """Create a table showing all tasks."""
        table = Table(title="Active Tasks", show_header=True, header_style="bold magenta")
        
        table.add_column("Task ID", style="cyan", width=12)
        table.add_column("Task Name", style="green", width=30)
        table.add_column("Status", style="yellow", width=12)
        table.add_column("Progress", style="blue", width=20)
        table.add_column("Current Step", style="white", width=40)
        table.add_column("Duration", style="magenta", width=12)
        
        for task in self.get_active_tasks():
            duration = datetime.now() - task.start_time
            duration_str = str(duration).split('.')[0]  # Remove microseconds
            
            status_icon = {
                TaskStatus.PENDING: "⏳",
                TaskStatus.RUNNING: "🔄",
                TaskStatus.COMPLETED: "✅",
                TaskStatus.FAILED: "❌",
                TaskStatus.CANCELLED: "🚫"
            }.get(task.status, "❓")
            
            progress_bar = f"{task.progress:.1%}"
            
            table.add_row(
                task.task_id[:12],
                task.task_name[:28] + "..." if len(task.task_name) > 28 else task.task_name,
                f"{status_icon} {task.status.value}",
                progress_bar,
                task.current_step[:38] + "..." if len(task.current_step) > 38 else task.current_step,
                duration_str
            )
        
        return table
    
    def _create_status_summary(self) -> Panel:
        """Create a status summary panel."""
        active_tasks = self.get_active_tasks()
        completed_tasks = [t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]
        failed_tasks = [t for t in self.tasks.values() if t.status == TaskStatus.FAILED]
        
        summary_text = f"""
📊 Task Summary:
• Active: {len(active_tasks)} tasks
• Completed: {len(completed_tasks)} tasks
• Failed: {len(failed_tasks)} tasks
• Total: {len(self.tasks)} tasks

🕒 Last Update: {datetime.now().strftime('%H:%M:%S')}

💡 Tips:
• Tasks run in parallel for efficiency
• Failed tasks can be retried
• Progress is saved automatically
        """
        
        return Panel(summary_text, title="Status Summary", style="green")
    
    def start_live_display(self):
        """Start the live progress display."""
        if not self.display_enabled:
            return
        
        try:
            layout = self.create_progress_display()
            self.live_display = Live(layout, refresh_per_second=2, console=self.console)
            self.live_display.start()
            logger.info("Live progress display started")
        except Exception as e:
            logger.error(f"Failed to start live display: {e}")
    
    def stop_live_display(self):
        """Stop the live progress display."""
        if self.live_display:
            self.live_display.stop()
            self.live_display = None
            logger.info("Live progress display stopped")
    
    def update_display(self):
        """Update the live display."""
        if self.live_display and self.display_enabled:
            try:
                layout = self.create_progress_display()
                self.live_display.update(layout)
            except Exception as e:
                logger.error(f"Failed to update display: {e}")
    
    def create_file_progress_callback(self, task_id: str):
        """Create a callback for file creation progress."""
        def callback(action: str, progress: float, status: str):
            self.update_task(
                task_id,
                current_step=f"File {action}: {status}",
                progress=progress
            )
            self.update_display()
        
        return callback
    
    def create_browser_progress_callback(self, task_id: str):
        """Create a callback for browser action progress."""
        def callback(action: str, progress: float, status: str):
            self.update_task(
                task_id,
                current_step=f"Browser {action}: {status}",
                progress=progress
            )
            self.update_display()
        
        return callback
    
    def create_api_progress_callback(self, task_id: str):
        """Create a callback for API call progress."""
        def callback(provider: str, event: str, delay: float):
            if event == "retry":
                status = f"API retry ({provider}) - waiting {delay:.1f}s"
            elif event == "final_failure":
                status = f"API failed ({provider})"
            else:
                status = f"API {event} ({provider})"
            
            self.update_task(task_id, current_step=status)
            self.update_display()
        
        return callback
    
    def generate_progress_report(self, task_id: str) -> str:
        """Generate a detailed progress report for a task."""
        task = self.get_task_progress(task_id)
        if not task:
            return "Task not found"
        
        report_path = self.progress_dir / f"{task_id}_report.md"
        
        report_content = f"""# Task Progress Report

## Task Information
- **Task ID**: {task.task_id}
- **Task Name**: {task.task_name}
- **Status**: {task.status.value}
- **Progress**: {task.progress:.1%}
- **Start Time**: {task.start_time.strftime('%Y-%m-%d %H:%M:%S')}

## Current Status
- **Current Step**: {task.current_step}
- **Step Progress**: {task.current_step_num}/{task.total_steps}
- **Duration**: {datetime.now() - task.start_time}

## Timeline
- **Started**: {task.start_time.strftime('%H:%M:%S')}
- **Last Update**: {datetime.now().strftime('%H:%M:%S')}
- **Estimated Completion**: {task.estimated_completion.strftime('%H:%M:%S') if task.estimated_completion else 'Unknown'}

## Metadata
```json
{json.dumps(task.metadata, indent=2, default=str)}
```

---
*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        with open(report_path, 'w') as f:
            f.write(report_content)
        
        return str(report_path)
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Clean up old completed/failed tasks."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        with self.lock:
            tasks_to_remove = []
            
            for task_id, task in self.tasks.items():
                if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED] and 
                    task.start_time < cutoff_time):
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
                # Also remove the progress file
                progress_file = self.progress_dir / f"{task_id}.json"
                if progress_file.exists():
                    progress_file.unlink()
            
            if tasks_to_remove:
                logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")

# Global progress tracker instance
progress_tracker = ProgressTracker() 