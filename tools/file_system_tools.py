#!/usr/bin/env python3
"""
File System Tools Facade
Lightweight facade over FileManager so sub-agents can depend on a stable API.
"""

from typing import Dict, Any, List

from .file_manager import file_manager, get_file_manager_tools


class FileSystemTools:
    """Facade around FileManager providing a minimal, stable surface."""

    def set_workspace(self, workspace_path: str) -> None:
        file_manager.set_workspace(workspace_path)

    def read_file(self, **kwargs) -> Dict[str, Any]:
        return file_manager.read_file(**kwargs)

    def write_file(self, **kwargs) -> Dict[str, Any]:
        return file_manager.write_file(**kwargs)

    def append_file(self, **kwargs) -> Dict[str, Any]:
        return file_manager.append_file(**kwargs)

    def list_files(self, **kwargs) -> Dict[str, Any]:
        return file_manager.list_files(**kwargs)

    def create_directory(self, **kwargs) -> Dict[str, Any]:
        return file_manager.create_directory(**kwargs)


def get_file_system_tools() -> List[Dict]:
    """Expose the underlying file manager tool definitions to agents."""
    return get_file_manager_tools()


# Global instance
file_system_tools = FileSystemTools()

#!/usr/bin/env python3
"""
File System Tools - Compatibility layer for file_manager.py
This file provides backward compatibility for sub-agents that import from tools.file_system_tools
"""

from .file_manager import file_manager, get_file_manager_tools

# Create aliases for backward compatibility
file_system_tools = file_manager
get_file_system_tools = get_file_manager_tools 