#!/usr/bin/env python3
"""
Per-task Virtual Environment Manager
Create a Python venv under a task workspace and install packages.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import subprocess
import sys
from loguru import logger


class VenvManager:
    def __init__(self, workspace_root: str = "workspace"):
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def _venv_paths(self, task_workspace: str) -> Dict[str, Path]:
        root = Path(task_workspace)
        venv_dir = root / "venv"
        bin_dir = venv_dir / ("Scripts" if sys.platform.startswith("win") else "bin")
        python_exe = bin_dir / ("python.exe" if sys.platform.startswith("win") else "python")
        pip_exe = bin_dir / ("pip.exe" if sys.platform.startswith("win") else "pip")
        return {"venv_dir": venv_dir, "python": python_exe, "pip": pip_exe}

    def create_task_venv(self, task_workspace: str) -> Dict[str, Any]:
        try:
            paths = self._venv_paths(task_workspace)
            if not paths["venv_dir"].exists():
                result = subprocess.run([sys.executable, "-m", "venv", str(paths["venv_dir"])], capture_output=True, text=True)
                if result.returncode != 0:
                    return {"success": False, "stderr": result.stderr}
            return {"success": True, "python": str(paths["python"]), "pip": str(paths["pip"]) }
        except Exception as e:
            logger.error(f"create_task_venv failed: {e}")
            return {"success": False, "error": str(e)}

    def install(self, task_workspace: str, package: str, timeout: int = 300) -> Dict[str, Any]:
        try:
            paths = self._venv_paths(task_workspace)
            if not paths["pip"].exists():
                make = self.create_task_venv(task_workspace)
                if not make.get("success"):
                    return make
            result = subprocess.run([str(paths["pip"]), "install", package], capture_output=True, text=True, timeout=timeout)
            return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}
        except subprocess.TimeoutExpired:
            return {"success": False, "stderr": "pip install timed out"}
        except Exception as e:
            logger.error(f"install failed: {e}")
            return {"success": False, "error": str(e)}


venv_manager = VenvManager()


def get_venv_tools() -> List[Dict[str, Any]]:
    """Expose venv operations as tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": "create_task_venv",
                "description": "Create a Python virtual environment under the task workspace",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_workspace": {"type": "string", "description": "Absolute path to the task workspace"}
                    },
                    "required": ["task_workspace"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "venv_install",
                "description": "Install a Python package into the task's virtual environment",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_workspace": {"type": "string", "description": "Absolute path to the task workspace"},
                        "package": {"type": "string", "description": "Package spec, e.g., pandas==2.1.4"},
                        "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 300}
                    },
                    "required": ["task_workspace", "package"]
                }
            }
        }
    ]

