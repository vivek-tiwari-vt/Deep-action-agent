#!/usr/bin/env python3
"""
Task Monitor for Deep Action Agent
Monitors agent activities and ensures they stay on track with assigned tasks
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from loguru import logger
from dataclasses import dataclass, asdict
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    DEVIATED = "deviated"
    REDIRECTED = "redirected"

class ActivityType(Enum):
    SEARCH = "search"
    NAVIGATION = "navigation"
    EXTRACTION = "extraction"
    FILE_OPERATION = "file_operation"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    ERROR = "error"
    DEVIATION = "deviation"

@dataclass
class Activity:
    timestamp: str
    activity_type: str
    description: str
    details: Dict[str, Any]
    duration: Optional[float] = None
    success: bool = True
    deviation_score: float = 0.0

@dataclass
class TaskCheckpoint:
    timestamp: str
    expected_activity: str
    actual_activity: str
    deviation_detected: bool
    feedback_message: str
    correction_applied: bool

class TaskMonitor:
    """Monitors agent activities and ensures task compliance."""
    
    def __init__(self, task_id: str, base_dir: str = "workspace"):
        self.task_id = task_id
        self.base_dir = Path(base_dir)
        
        # Try to get workspace manager for this task
        try:
            from main import get_workspace_manager
            self.workspace_manager = get_workspace_manager(task_id)
            self.task_dir = Path(self.workspace_manager.workspace_path)
            logger.info(f"Task monitor using workspace manager for task {task_id}")
        except Exception as e:
            logger.warning(f"Could not get workspace manager for task {task_id}: {e}")
            self.workspace_manager = None
            
            # Fallback to directory-based approach
            # Look for the task directory in the workspace
            # First try the direct task directory
            self.task_dir = self.base_dir / f"task_{task_id}"
            
            # If not found, look for API task directories
            if not self.task_dir.exists():
                api_task_dirs = list(self.base_dir.glob(f"*api_task*{task_id}*"))
                if api_task_dirs:
                    self.task_dir = api_task_dirs[0]
                else:
                    # Create the task directory if not found
                    self.task_dir.mkdir(parents=True, exist_ok=True)
            else:
                self.task_dir.mkdir(parents=True, exist_ok=True)
        
        # Task tracking
        self.original_task = ""
        self.current_status = TaskStatus.PENDING
        self.activities: List[Activity] = []
        self.checkpoints: List[TaskCheckpoint] = []
        self.deviation_count = 0
        self.last_activity_time = time.time()
        
        # Search-specific monitoring
        self.search_queries_executed = []
        self.pages_visited = []
        self.content_extracted = []
        self.expected_search_terms = []
        
        # Load or create task file
        if self.workspace_manager:
            self.task_file = Path(self.workspace_manager.get_metadata_path("task_monitor.json"))
        else:
            self.task_file = self.task_dir / "task_monitor.json"
        
        self._load_or_create_task_file()
    
    def _load_or_create_task_file(self):
        """Load existing task file or create new one."""
        if self.task_file.exists():
            try:
                with open(self.task_file, 'r') as f:
                    data = json.load(f)
                    self.original_task = data.get('original_task', '')
                    self.current_status = TaskStatus(data.get('current_status', 'pending'))
                    self.activities = [Activity(**act) for act in data.get('activities', [])]
                    self.checkpoints = [TaskCheckpoint(**cp) for cp in data.get('checkpoints', [])]
                    self.deviation_count = data.get('deviation_count', 0)
                    self.search_queries_executed = data.get('search_queries_executed', [])
                    self.pages_visited = data.get('pages_visited', [])
                    self.content_extracted = data.get('content_extracted', [])
                    self.expected_search_terms = data.get('expected_search_terms', [])
            except Exception as e:
                logger.error(f"Error loading task file: {e}")
                self._create_new_task_file()
        else:
            self._create_new_task_file()
    
    def _create_new_task_file(self):
        """Create a new task file with default values."""
        self.original_task = ""
        self.current_status = TaskStatus.PENDING
        self.activities = []
        self.checkpoints = []
        self.deviation_count = 0
        self.search_queries_executed = []
        self.pages_visited = []
        self.content_extracted = []
        self.expected_search_terms = []
        self._save_task_file()
    
    def _save_task_file(self):
        """Save task data to file."""
        try:
            data = {
                'task_id': self.task_id,
                'original_task': self.original_task,
                'current_status': self.current_status.value,
                'activities': [asdict(act) for act in self.activities],
                'checkpoints': [asdict(cp) for cp in self.checkpoints],
                'deviation_count': self.deviation_count,
                'search_queries_executed': self.search_queries_executed,
                'pages_visited': self.pages_visited,
                'content_extracted': self.content_extracted,
                'expected_search_terms': self.expected_search_terms,
                'last_activity_time': self.last_activity_time
            }
            
            # Ensure directory exists
            self.task_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.task_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving task file: {e}")
    
    def _save_activity_to_file(self, activity: Activity):
        """Save individual activity to a separate file."""
        try:
            if self.workspace_manager:
                activity_file = Path(self.workspace_manager.get_activity_path(f"activity_{int(time.time())}.json"))
            else:
                activity_file = self.task_dir / "activities" / f"activity_{int(time.time())}.json"
            
            activity_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(activity_file, 'w') as f:
                json.dump(asdict(activity), f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving activity to file: {e}")
    
    def set_original_task(self, task_description: str):
        """Set the original task description."""
        self.original_task = task_description
        self._extract_expected_search_terms()
        self._save_task_file()
    
    def _extract_expected_search_terms(self):
        """Extract expected search terms from the task description."""
        # Simple keyword extraction - can be enhanced with NLP
        task_lower = self.original_task.lower()
        
        # Common research-related keywords
        research_keywords = ['research', 'find', 'search', 'investigate', 'analyze', 'study']
        if any(keyword in task_lower for keyword in research_keywords):
            # Extract potential search terms (words after research-related keywords)
            words = self.original_task.split()
            for i, word in enumerate(words):
                if word.lower() in research_keywords and i + 1 < len(words):
                    # Take next few words as potential search terms
                    search_terms = words[i+1:i+4]
                    self.expected_search_terms.extend(search_terms)
        
        # If no specific terms found, use the whole task
        if not self.expected_search_terms:
            self.expected_search_terms = self.original_task.split()[:5]
    
    def log_activity(self, activity_type: str, description: str, details: Dict[str, Any], 
                    duration: Optional[float] = None, success: bool = True):
        """Log an agent activity."""
        activity = Activity(
            timestamp=datetime.now().isoformat(),
            activity_type=activity_type,
            description=description,
            details=details,
            duration=duration,
            success=success
        )
        
        self.activities.append(activity)
        self.last_activity_time = time.time()
        
        # Update status
        if self.current_status == TaskStatus.PENDING:
            self.current_status = TaskStatus.IN_PROGRESS
        
        # Check for deviations
        deviation_score = self._check_deviation(activity)
        activity.deviation_score = deviation_score
        
        if deviation_score > 0.7:  # High deviation threshold
            self._handle_deviation(activity)
        
        # Save to file
        self._save_activity_to_file(activity)
        self._save_task_file()
        
        return activity
    
    def _check_deviation(self, activity: Activity) -> float:
        """Check if an activity deviates from the expected task."""
        deviation_score = 0.0
        
        if activity.activity_type == ActivityType.SEARCH.value:
            # Check if search query is relevant to the task
            query = activity.details.get('query', '').lower()
            if not any(term.lower() in query for term in self.expected_search_terms):
                deviation_score += 0.5
            
            # Check if search is being performed at all
            if not query:
                deviation_score += 0.8
        
        elif activity.activity_type == ActivityType.NAVIGATION.value:
            # Check if navigation is to relevant sites
            url = activity.details.get('url', '').lower()
            if not any(term.lower() in url for term in self.expected_search_terms):
                deviation_score += 0.3
        
        elif activity.activity_type == ActivityType.ERROR.value:
            # Errors indicate potential issues
            deviation_score += 0.4
        
        # Check for inactivity
        if time.time() - self.last_activity_time > 300:  # 5 minutes
            deviation_score += 0.6
        
        return min(deviation_score, 1.0)
    
    def _handle_deviation(self, activity: Activity):
        """Handle detected deviation from the task."""
        self.deviation_count += 1
        self.current_status = TaskStatus.DEVIATED
        
        checkpoint = TaskCheckpoint(
            timestamp=datetime.now().isoformat(),
            expected_activity=f"Task-related activity for: {self.original_task}",
            actual_activity=f"{activity.activity_type}: {activity.description}",
            deviation_detected=True,
            feedback_message=self._generate_feedback_message(activity),
            correction_applied=False
        )
        
        self.checkpoints.append(checkpoint)
        logger.warning(f"Task deviation detected: {checkpoint.feedback_message}")
    
    def _generate_feedback_message(self, activity: Activity) -> str:
        """Generate feedback message for deviation."""
        if activity.activity_type == ActivityType.SEARCH.value:
            query = activity.details.get('query', '')
            if not query:
                return "No search query detected. Please perform a search related to the assigned task."
            else:
                return f"Search query '{query}' may not be relevant to the task: '{self.original_task}'. Please focus on the main task."
        
        elif activity.activity_type == ActivityType.ERROR.value:
            return f"Error occurred: {activity.description}. Please retry the task or use a different approach."
        
        else:
            return f"Activity '{activity.description}' may not be progressing the main task. Please focus on: {self.original_task}"
    
    def get_task_status(self) -> Dict[str, Any]:
        """Get current task status and statistics."""
        return {
            'task_id': self.task_id,
            'original_task': self.original_task,
            'current_status': self.current_status.value,
            'deviation_count': self.deviation_count,
            'activities_count': len(self.activities),
            'last_activity_time': self.last_activity_time,
            'search_queries_executed': self.search_queries_executed,
            'pages_visited': self.pages_visited,
            'content_extracted_count': len(self.content_extracted),
            'expected_search_terms': self.expected_search_terms,
            'recent_activities': [asdict(activity) for activity in self.activities[-5:]],  # Last 5 activities
            'recent_checkpoints': [asdict(checkpoint) for checkpoint in self.checkpoints[-3:]]  # Last 3 checkpoints
        }
    
    def log_search_query(self, query: str, results_count: int):
        """Log a search query execution."""
        self.search_queries_executed.append({
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'results_count': results_count
        })
        
        self.log_activity(
            ActivityType.SEARCH.value,
            f"Executed search: {query}",
            {'query': query, 'results_count': results_count},
            success=results_count > 0
        )
    
    def log_page_visit(self, url: str, success: bool):
        """Log a page visit."""
        self.pages_visited.append({
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'success': success
        })
        
        self.log_activity(
            ActivityType.NAVIGATION.value,
            f"Visited page: {url}",
            {'url': url, 'success': success},
            success=success
        )
    
    def log_content_extraction(self, url: str, content_length: int):
        """Log content extraction."""
        self.content_extracted.append({
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'content_length': content_length
        })
        
        self.log_activity(
            ActivityType.EXTRACTION.value,
            f"Extracted content from: {url}",
            {'url': url, 'content_length': content_length},
            success=content_length > 0
        )
    
    def should_redirect_task(self) -> bool:
        """Determine if the task should be redirected."""
        # Redirect if too many deviations or no progress
        if self.deviation_count >= 3:
            return True
        
        # Redirect if no search queries executed
        if not self.search_queries_executed:
            return True
        
        # Redirect if no content extracted
        if not self.content_extracted:
            return True
        
        return False
    
    def get_redirect_instructions(self) -> str:
        """Get instructions for redirecting the task."""
        if not self.search_queries_executed:
            # Extract key search terms from the original task
            search_terms = self._extract_search_terms_from_task()
            return f"Perform web search for: {search_terms}"
        
        if not self.content_extracted:
            return f"Extract content from search results about: {self.original_task}"
        
        return f"Refocus on the main task: {self.original_task}"
    
    def _extract_search_terms_from_task(self) -> str:
        """Extract meaningful search terms from the task description."""
        if not self.original_task:
            return "artificial intelligence machine learning"
        
        # Remove common research words and focus on key terms
        task_lower = self.original_task.lower()
        
        # Remove research-related words
        research_words = ['research', 'find', 'search', 'investigate', 'analyze', 'study', 'latest', 'developments']
        words = self.original_task.split()
        
        # Keep only meaningful content words
        meaningful_words = []
        for word in words:
            word_lower = word.lower()
            if (word_lower not in research_words and 
                len(word) > 2 and 
                word_lower not in ['the', 'and', 'in', 'of', 'to', 'for', 'with', 'about']):
                meaningful_words.append(word)
        
        # If we have meaningful words, use them; otherwise use the original task
        if meaningful_words:
            return ' '.join(meaningful_words[:5])  # Limit to 5 words
        else:
            return self.original_task
    
    def mark_task_completed(self):
        """Mark the task as completed."""
        self.current_status = TaskStatus.COMPLETED
        self._save_task_file()
    
    def mark_task_failed(self, reason: str):
        """Mark the task as failed."""
        self.current_status = TaskStatus.FAILED
        self.log_activity(
            ActivityType.ERROR.value,
            f"Task failed: {reason}",
            {'reason': reason},
            success=False
        )
        self._save_task_file()

# Global task monitor registry
task_monitors = {}

def get_task_monitor(task_id: str) -> TaskMonitor:
    """Get or create a task monitor for the given task ID."""
    if task_id not in task_monitors:
        task_monitors[task_id] = TaskMonitor(task_id)
    return task_monitors[task_id]

def log_task_activity(task_id: str, activity_type: str, description: str, 
                     details: Dict[str, Any], duration: Optional[float] = None, 
                     success: bool = True) -> Activity:
    """Log an activity for a specific task."""
    monitor = get_task_monitor(task_id)
    return monitor.log_activity(activity_type, description, details, duration, success)

def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get status for a specific task."""
    monitor = get_task_monitor(task_id)
    return monitor.get_task_status() 