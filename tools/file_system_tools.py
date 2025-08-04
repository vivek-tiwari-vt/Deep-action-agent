#!/usr/bin/env python3
"""
File System Tools - Compatibility layer for file_manager.py
This file provides backward compatibility for sub-agents that import from tools.file_system_tools
"""

from .file_manager import file_manager, get_file_manager_tools

# Create aliases for backward compatibility
file_system_tools = file_manager
get_file_system_tools = get_file_manager_tools 