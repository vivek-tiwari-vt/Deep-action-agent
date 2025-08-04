#!/usr/bin/env python3
"""
Web Tools - Compatibility layer for web_research.py
This file provides backward compatibility for sub-agents that import from tools.web_tools
"""

from .web_research import web_research, get_web_research_tools

# Create aliases for backward compatibility
web_tools = web_research
get_web_tools = get_web_research_tools 