#!/usr/bin/env python3
"""
Example API Client for Deep Action Agent
Demonstrates how to use the FastAPI server endpoints.
"""

import requests
import json
import time
from typing import Dict, Any

class DeepActionAgentClient:
    """Client for interacting with the Deep Action Agent API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
    
    def health_check(self) -> Dict[str, Any]:
        """Check the health status of the API."""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def execute_task(self, task_description: str, task_type: str = "research", 
                    priority: str = "normal", timeout_minutes: int = 60, 
                    verbose: bool = False) -> Dict[str, Any]:
        """Execute a new task."""
        payload = {
            "task_description": task_description,
            "task_type": task_type,
            "priority": priority,
            "timeout_minutes": timeout_minutes,
            "verbose": verbose
        }
        
        response = requests.post(f"{self.base_url}/execute", json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a specific task."""
        response = requests.get(f"{self.base_url}/status/{task_id}")
        response.raise_for_status()
        return response.json()
    
    def list_tasks(self) -> Dict[str, Any]:
        """List all tasks."""
        response = requests.get(f"{self.base_url}/tasks")
        response.raise_for_status()
        return response.json()
    
    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel a running task."""
        response = requests.delete(f"{self.base_url}/tasks/{task_id}")
        response.raise_for_status()
        return response.json()
    
    def wait_for_task_completion(self, task_id: str, check_interval: int = 5, 
                                max_wait_time: int = 3600) -> Dict[str, Any]:
        """Wait for a task to complete and return the final result."""
        start_time = time.time()
        
        while True:
            # Check if we've exceeded max wait time
            if time.time() - start_time > max_wait_time:
                raise TimeoutError(f"Task {task_id} did not complete within {max_wait_time} seconds")
            
            # Get task status
            status = self.get_task_status(task_id)
            
            print(f"Task {task_id}: {status['status']} - {status['progress']:.1%} - {status['current_step']}")
            
            # Check if task is completed
            if status['status'] in ['completed', 'failed', 'cancelled']:
                return status
            
            # Wait before next check
            time.sleep(check_interval)

def main():
    """Example usage of the Deep Action Agent API client."""
    
    # Initialize client
    client = DeepActionAgentClient()
    
    try:
        # 1. Check API health
        print("🔍 Checking API health...")
        health = client.health_check()
        print(f"✅ API Status: {health['status']}")
        print(f"📊 Active Tasks: {health['active_tasks']}")
        print(f"💾 Memory Usage: {health['system_resources']['memory_percent']:.1f}%")
        print()
        
        # 2. Execute a research task
        print("🚀 Executing research task...")
        task_response = client.execute_task(
            task_description="Research the latest developments in quantum computing and their potential applications",
            task_type="research",
            priority="normal",
            timeout_minutes=30
        )
        
        task_id = task_response['task_id']
        print(f"✅ Task queued with ID: {task_id}")
        print(f"📝 Message: {task_response['message']}")
        print(f"⏱️ Estimated duration: {task_response['estimated_duration']}")
        print()
        
        # 3. Monitor task progress
        print("📊 Monitoring task progress...")
        try:
            final_result = client.wait_for_task_completion(task_id, check_interval=10)
            
            if final_result['status'] == 'completed':
                print("🎉 Task completed successfully!")
                if final_result['result']:
                    print(f"📄 Result available at: {final_result['result'].get('workspace_path', 'N/A')}")
            else:
                print(f"❌ Task failed: {final_result.get('error_message', 'Unknown error')}")
                
        except TimeoutError as e:
            print(f"⏰ {e}")
        
        print()
        
        # 4. List all tasks
        print("📋 Listing all tasks...")
        tasks = client.list_tasks()
        print(f"Total tasks: {len(tasks)}")
        for task in tasks:
            print(f"  - {task['task_id']}: {task['status']} ({task['progress']:.1f}%)")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API server.")
        print("Make sure the server is running with: python main_fastapi.py")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 