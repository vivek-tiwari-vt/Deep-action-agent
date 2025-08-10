#!/usr/bin/env python3
"""
FastAPI Server for Deep Action Agent
Provides REST API endpoints for task execution and health monitoring.
"""

import os
import sys
import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
import time

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.manager_agent import ManagerAgent
from tools.progress_tracker import progress_tracker
from tools.rate_limit_manager import rate_limit_manager
from tools.task_monitor import get_task_status as get_task_monitor_status
from tools.event_bus import event_bus
import config

console = Console()

# Global variables for task management
active_tasks: Dict[str, Dict[str, Any]] = {}
task_results: Dict[str, Dict[str, Any]] = {}

class TaskRequest(BaseModel):
    """Request model for task execution."""
    task_description: str = Field(..., description="Description of the task to execute")
    task_type: str = Field(default="research", description="Type of task (research, analysis, coding, mixed)")
    priority: str = Field(default="normal", description="Task priority (low, normal, high)")
    timeout_minutes: int = Field(default=60, description="Task timeout in minutes")
    verbose: bool = Field(default=False, description="Enable verbose logging")

class TaskResponse(BaseModel):
    """Response model for task execution."""
    task_id: str
    status: str
    message: str
    workspace_path: Optional[str] = None
    estimated_duration: Optional[str] = None

class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    timestamp: str
    version: str
    configuration: Dict[str, Any]
    api_health: Dict[str, Any]
    active_tasks: int
    system_resources: Dict[str, Any]

class TaskStatusResponse(BaseModel):
    """Response model for task status."""
    task_id: str
    status: str
    progress: float
    current_step: str
    start_time: str
    estimated_completion: Optional[str] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

def create_task_workspace(task_description: str, task_id: str = None) -> str:
    """Create a new workspace directory for the task."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Use provided task_id or generate a new one
    if task_id is None:
        task_id = f"task_{uuid.uuid4().hex[:8]}"
    
    workspace_name = f"api_task_{timestamp}_{task_id}"
    workspace_path = Path(config.WORKSPACE_BASE) / workspace_name

    # Create workspace structure
    workspace_path.mkdir(parents=True, exist_ok=True)
    (workspace_path / "data").mkdir(exist_ok=True)
    (workspace_path / "outputs").mkdir(exist_ok=True)
    (workspace_path / "temp_code").mkdir(exist_ok=True)
    (workspace_path / "logs").mkdir(exist_ok=True)
    (workspace_path / "screenshots").mkdir(exist_ok=True)
    (workspace_path / "progress").mkdir(exist_ok=True)
    (workspace_path / "metadata").mkdir(exist_ok=True)
    (workspace_path / "activities").mkdir(exist_ok=True)

    # Create task metadata
    task_metadata = {
        "task_description": task_description,
        "task_id": task_id,
        "created_at": datetime.now().isoformat(),
        "workspace_path": str(workspace_path),
        "agent_type": "api_manager",
        "features": [
            "browser_automation",
            "progress_tracking",
            "resilient_file_creation",
            "rate_limit_management",
            "content_quality_assessment"
        ]
    }

    with open(workspace_path / "task_metadata.json", "w") as f:
        json.dump(task_metadata, f, indent=2)

    return str(workspace_path), task_id

class WorkspaceManager:
    """Manages file operations within a single task workspace."""
    
    def __init__(self, workspace_path: str, task_id: str):
        self.workspace_path = Path(workspace_path)
        self.task_id = task_id
        self.console = Console()
        
        # Ensure workspace structure exists
        self._ensure_workspace_structure()
    
    def _ensure_workspace_structure(self):
        """Ensure all required directories exist."""
        directories = [
            "data", "outputs", "temp_code", "logs", 
            "screenshots", "progress", "metadata", "activities"
        ]
        
        for directory in directories:
            (self.workspace_path / directory).mkdir(exist_ok=True)
    
    def get_screenshot_path(self, filename: str = None) -> str:
        """Get path for screenshot files."""
        if filename is None:
            timestamp = int(time.time())
            filename = f"screenshot_{timestamp}.png"
        
        return str(self.workspace_path / "screenshots" / filename)
    
    def get_log_path(self, filename: str = None) -> str:
        """Get path for log files."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"task_log_{timestamp}.log"
        
        return str(self.workspace_path / "logs" / filename)
    
    def get_progress_path(self, filename: str = None) -> str:
        """Get path for progress files."""
        if filename is None:
            filename = f"progress_log.json"
        
        return str(self.workspace_path / "progress" / filename)
    
    def get_output_path(self, filename: str = None) -> str:
        """Get path for output files."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"output_{timestamp}.json"
        
        return str(self.workspace_path / "outputs" / filename)
    
    def get_metadata_path(self, filename: str = None) -> str:
        """Get path for metadata files."""
        if filename is None:
            filename = f"metadata.json"
        
        return str(self.workspace_path / "metadata" / filename)
    
    def get_activity_path(self, filename: str = None) -> str:
        """Get path for activity files."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"activities_{timestamp}.log"
        
        return str(self.workspace_path / "activities" / filename)
    
    def save_file(self, content: str, filename: str, subdirectory: str = "outputs") -> str:
        """Save a file to the workspace."""
        file_path = self.workspace_path / subdirectory / filename
        file_path.parent.mkdir(exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(file_path)
    
    def save_json(self, data: dict, filename: str, subdirectory: str = "outputs") -> str:
        """Save JSON data to the workspace."""
        file_path = self.workspace_path / subdirectory / filename
        file_path.parent.mkdir(exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return str(file_path)
    
    def get_workspace_info(self) -> dict:
        """Get information about the workspace."""
        return {
            "workspace_path": str(self.workspace_path),
            "task_id": self.task_id,
            "directories": {
                "data": str(self.workspace_path / "data"),
                "outputs": str(self.workspace_path / "outputs"),
                "logs": str(self.workspace_path / "logs"),
                "screenshots": str(self.workspace_path / "screenshots"),
                "progress": str(self.workspace_path / "progress"),
                "metadata": str(self.workspace_path / "metadata"),
                "activities": str(self.workspace_path / "activities")
            }
        }

# Global workspace managers
workspace_managers = {}

def get_workspace_manager(task_id: str) -> WorkspaceManager:
    """Get or create a workspace manager for a task."""
    if task_id not in workspace_managers:
        # Find the workspace path for this task
        workspace_path = None
        
        # First check active_tasks
        for task_info in active_tasks.values():
            if task_info.get("task_id") == task_id:
                workspace_path = task_info.get("workspace_path")
                break
        
        # If not found in active_tasks, look for existing workspace directories
        if workspace_path is None:
            workspace_base = Path(config.WORKSPACE_BASE)
            api_task_dirs = list(workspace_base.glob(f"*api_task*{task_id}*"))
            if api_task_dirs:
                workspace_path = str(api_task_dirs[0])
                logger.info(f"Found existing workspace for task {task_id}: {workspace_path}")
            else:
                # Create a new workspace for this task
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                workspace_name = f"api_task_{timestamp}_{task_id}"
                workspace_path = str(workspace_base / workspace_name)
                
                # Create the workspace structure
                workspace_path_obj = Path(workspace_path)
                workspace_path_obj.mkdir(parents=True, exist_ok=True)
                
                # Create subdirectories
                directories = [
                    "data", "outputs", "temp_code", "logs", 
                    "screenshots", "progress", "metadata", "activities"
                ]
                for directory in directories:
                    (workspace_path_obj / directory).mkdir(exist_ok=True)
                
                logger.info(f"Created new workspace for task {task_id}: {workspace_path}")
        
        workspace_managers[task_id] = WorkspaceManager(workspace_path, task_id)
    
    return workspace_managers[task_id]

async def execute_task_background(task_id: str, task_request: TaskRequest):
    """Background task execution function."""
    try:
        # Update task status
        active_tasks[task_id]["status"] = "running"
        active_tasks[task_id]["start_time"] = datetime.now().isoformat()
        
        # Create workspace with the API task ID
        workspace_path, _ = create_task_workspace(task_request.task_description, task_id=task_id)
        active_tasks[task_id]["workspace_path"] = workspace_path
        
        # Initialize manager agent with the API task ID
        manager = ManagerAgent(workspace_path, task_id=task_id)
        
        # Smart routing: always use the iterative planner–executor loop which
        # internally decides whether to run the dedicated research flow
        result = await manager.execute_task_iterative(task_request.task_description)
        
        # Store result
        task_results[task_id] = {
            "success": True,
            "result": result,
            "workspace_path": workspace_path,
            "completed_at": datetime.now().isoformat()
        }
        
        # Update task status
        active_tasks[task_id]["status"] = "completed"
        active_tasks[task_id]["completed_at"] = datetime.now().isoformat()
        
        logger.info(f"Task {task_id} completed successfully")
        
    except Exception as e:
        error_msg = f"Task execution failed: {str(e)}"
        logger.error(f"Task {task_id} failed: {e}")
        
        # Store error result
        task_results[task_id] = {
            "success": False,
            "error": error_msg,
            "workspace_path": active_tasks.get(task_id, {}).get("workspace_path"),
            "completed_at": datetime.now().isoformat()
        }
        
        # Update task status
        active_tasks[task_id]["status"] = "failed"
        active_tasks[task_id]["error_message"] = error_msg
        active_tasks[task_id]["completed_at"] = datetime.now().isoformat()

def get_system_resources() -> Dict[str, Any]:
    """Get system resource information."""
    try:
        import psutil
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # Disk usage
        disk = psutil.disk_usage(config.WORKSPACE_BASE)
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024**3),
            "disk_percent": disk.percent,
            "disk_free_gb": disk.free / (1024**3)
        }
    except ImportError:
        return {
            "cpu_percent": "N/A",
            "memory_percent": "N/A",
            "memory_available_gb": "N/A",
            "disk_percent": "N/A",
            "disk_free_gb": "N/A"
        }

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    console.print(Panel(
        Text("🚀 Deep Action Agent API Server", style="bold blue"),
        subtitle="Starting up...",
        border_style="blue"
    ))
    
    # Validate configuration
    if not config.validate_config():
        console.print("[red]❌ Configuration validation failed![/red]")
        raise RuntimeError("Configuration validation failed")
    
    console.print("[green]✅ Configuration validation passed![/green]")
    console.print("[green]✅ API Server ready![/green]")
    
    yield
    
    # Shutdown
    console.print("[yellow]🔄 Shutting down API Server...[/yellow]")

# Create FastAPI app
app = FastAPI(
    title="Deep Action Agent API",
    description="REST API for Deep Action Agent - A sophisticated multi-agent AI system for research, analysis, and action tasks",
    version="1.0.0",
    lifespan=lifespan
)

# Serve minimal frontend if present
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.isdir(FRONTEND_DIR):
    # Serve UI at /app to avoid conflicting with API routes like /execute
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

    # Redirect / to /app
    @app.get("/")
    async def _root_redirect():
        return RedirectResponse(url="/app/")

@app.post("/execute", response_model=TaskResponse)
async def execute_task(task_request: TaskRequest, background_tasks: BackgroundTasks):
    """
    Execute a task using the Deep Action Agent.
    
    This endpoint accepts a task description and executes it using the appropriate
    sub-agents and tools. The task runs in the background and can be monitored
    using the /status/{task_id} endpoint.
    """
    try:
        # Generate task ID
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        # Initialize task in active tasks
        active_tasks[task_id] = {
            "task_description": task_request.task_description,
            "task_type": task_request.task_type,
            "priority": task_request.priority,
            "status": "queued",
            "created_at": datetime.now().isoformat(),
            "workspace_path": None,
            "error_message": None,
            "completed_at": None
        }
        
        # Add task to background execution
        background_tasks.add_task(execute_task_background, task_id, task_request)
        
        # Estimate duration based on task type
        duration_estimates = {
            "research": "10-30 minutes",
            "analysis": "5-15 minutes",
            "coding": "5-20 minutes",
            "mixed": "15-45 minutes"
        }
        estimated_duration = duration_estimates.get(task_request.task_type, "10-30 minutes")
        
        logger.info(f"Task {task_id} queued for execution: {task_request.task_description}")
        
        return TaskResponse(
            task_id=task_id,
            status="queued",
            message=f"Task '{task_request.task_description}' has been queued for execution",
            estimated_duration=estimated_duration
        )
        
    except Exception as e:
        logger.error(f"Failed to queue task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to queue task: {str(e)}")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check the health status of the Deep Action Agent API.
    
    Returns comprehensive health information including:
    - API status and configuration
    - LLM provider health
    - Active task count
    - System resource usage
    """
    try:
        # Get API health report
        api_health = rate_limit_manager.get_health_report()
        
        # Get system resources
        system_resources = get_system_resources()
        
        # Count active tasks
        active_task_count = len([t for t in active_tasks.values() if t["status"] in ["queued", "running"]])
        
        # Configuration summary
        config_summary = {
            "openrouter_configured": bool(config.OPENROUTER_API_KEYS),
            "gemini_configured": bool(config.GEMINI_API_KEYS),
            "manager_model": config.MANAGER_MODEL,
            "researcher_model": config.RESEARCHER_MODEL,
            "coder_model": config.CODER_MODEL,
            "analyst_model": config.ANALYST_MODEL,
            "critic_model": config.CRITIC_MODEL,
            "workspace_base": config.WORKSPACE_BASE
        }
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            version="1.0.0",
            configuration=config_summary,
            api_health=api_health,
            active_tasks=active_task_count,
            system_resources=system_resources
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get the status of a specific task.
    
    Returns detailed information about the task including:
    - Current status and progress
    - Current step being executed
    - Start time and estimated completion
    - Error messages if any
    - Final result if completed
    """
    try:
        # Check if task exists
        if task_id not in active_tasks:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        task_info = active_tasks[task_id]
        
        # Get progress information if task is running
        progress = 0.0
        current_step = "Initializing"
        estimated_completion = None
        
        if task_info["status"] == "running":
            # Try to get progress from progress tracker
            task_progress = progress_tracker.get_task_progress(task_id)
            if task_progress:
                progress = task_progress.progress
                current_step = task_progress.current_step
                if task_progress.estimated_completion:
                    estimated_completion = task_progress.estimated_completion.isoformat()
        
        # Get result if task is completed
        result = None
        if task_id in task_results:
            result = task_results[task_id]
        
        return TaskStatusResponse(
            task_id=task_id,
            status=task_info["status"],
            progress=progress,
            current_step=current_step,
            start_time=task_info["start_time"] if task_info.get("start_time") else task_info["created_at"],
            estimated_completion=estimated_completion,
            error_message=task_info.get("error_message"),
            result=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status for {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")

@app.get("/monitor/{task_id}")
async def get_task_monitor(task_id: str):
    """Get detailed task monitoring information."""
    try:
        # Check if task exists
        if task_id not in active_tasks:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        # Get task monitor status
        monitor_status = get_task_monitor_status(task_id)
        
        # Get progress info
        progress_info = progress_tracker.get_task_progress(task_id)
        
        # Convert progress_info to dict if it's an object
        if progress_info and hasattr(progress_info, '__dict__'):
            progress_info = {
                'progress': getattr(progress_info, 'progress', 0.0),
                'current_step': getattr(progress_info, 'current_step', 'Unknown'),
                'status': str(getattr(progress_info, 'status', 'unknown'))
            }
        elif progress_info and hasattr(progress_info, 'value'):
            # Handle enum objects
            progress_info = {
                'progress': getattr(progress_info, 'progress', 0.0),
                'current_step': getattr(progress_info, 'current_step', 'Unknown'),
                'status': str(getattr(progress_info, 'status', 'unknown'))
            }
        
        # Combine all information
        detailed_status = {
            "task_id": task_id,
            "basic_status": active_tasks[task_id],
            "progress_info": progress_info,
            "monitor_status": monitor_status,
            "timestamp": datetime.now().isoformat()
        }
        
        return JSONResponse(content=detailed_status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task monitor for {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving task monitor: {str(e)}")

@app.get("/events/{task_id}")
async def sse_events(task_id: str, request: Request):
    """Minimal Server-Sent Events endpoint streaming progress lines."""
    from starlette.responses import StreamingResponse

    async def event_generator():
        last_progress = -1
        while True:
            if await request.is_disconnected():
                break
            prog = progress_tracker.get_task_progress(task_id)
            if prog and getattr(prog, 'current_step_num', -1) != last_progress:
                last_progress = getattr(prog, 'current_step_num', -1)
                data = {
                    "task_id": task_id,
                    "status": prog.status.value if hasattr(prog.status, 'value') else str(prog.status),
                    "progress": prog.progress,
                    "current_step": prog.current_step,
                }
                yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.websocket("/ws/{task_id}")
async def websocket_events(websocket: WebSocket, task_id: str):
    await websocket.accept()
    try:
        async for evt in event_bus.subscribe(task_id):
            await websocket.send_json(evt)
    except WebSocketDisconnect:
        return

@app.get("/tasks", response_model=List[TaskStatusResponse])
async def list_tasks():
    """
    List all tasks with their current status.
    
    Returns a list of all tasks (active and completed) with their
    current status and basic information.
    """
    try:
        tasks = []
        
        for task_id, task_info in active_tasks.items():
            # Get progress information
            progress = 0.0
            current_step = "Initializing"
            estimated_completion = None
            
            if task_info["status"] == "running":
                task_progress = progress_tracker.get_task_progress(task_id)
                if task_progress:
                    progress = task_progress.progress
                    current_step = task_progress.current_step
                    if task_progress.estimated_completion:
                        estimated_completion = task_progress.estimated_completion.isoformat()
            
            # Get result if available
            result = task_results.get(task_id)
            
            tasks.append(TaskStatusResponse(
                task_id=task_id,
                status=task_info["status"],
                progress=progress,
                current_step=current_step,
                start_time=task_info["start_time"] if task_info.get("start_time") else task_info["created_at"],
                estimated_completion=estimated_completion,
                error_message=task_info.get("error_message"),
                result=result
            ))
        
        return tasks
        
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")

@app.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """
    Cancel a running task.
    
    Attempts to cancel a task if it's currently running.
    Note: This is a best-effort cancellation and may not immediately stop the task.
    """
    try:
        if task_id not in active_tasks:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        task_info = active_tasks[task_id]
        
        if task_info["status"] not in ["queued", "running"]:
            raise HTTPException(status_code=400, detail=f"Cannot cancel task in status: {task_info['status']}")
        
        # Mark task as cancelled
        active_tasks[task_id]["status"] = "cancelled"
        active_tasks[task_id]["completed_at"] = datetime.now().isoformat()
        
        logger.info(f"Task {task_id} marked as cancelled")
        
        return {"message": f"Task {task_id} has been cancelled"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")

@app.get("/")
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "message": "Deep Action Agent API",
        "version": "1.0.0",
        "description": "A sophisticated multi-agent AI system for research, analysis, and action tasks",
        "endpoints": {
            "POST /execute": "Execute a new task",
            "GET /health": "Check API health status",
            "GET /status/{task_id}": "Get task status",
            "GET /tasks": "List all tasks",
            "DELETE /tasks/{task_id}": "Cancel a task",
            "GET /docs": "API documentation (Swagger UI)"
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    console.print(Panel(
        Text("🚀 Starting Deep Action Agent API Server", style="bold blue"),
        subtitle="FastAPI with Uvicorn",
        border_style="blue"
    ))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    ) 