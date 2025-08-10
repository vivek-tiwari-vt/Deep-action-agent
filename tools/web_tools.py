#!/usr/bin/env python3
"""
Web Tools Facade
Wrapper around WebResearch to present a stable async tool API for sub-agents.
"""

from typing import Dict, Any, List

from .web_research import web_research, get_web_research_tools


class WebTools:
    async def web_search(self, **kwargs) -> Dict[str, Any]:
        return await web_research.web_search(**kwargs)

    async def search_and_extract(self, **kwargs) -> List[Dict[str, Any]]:
        return await web_research.search_and_extract(**kwargs)

    async def navigate_to(self, **kwargs) -> bool:
        return await web_research.navigate_to(**kwargs)

    async def extract_content(self, **kwargs) -> Dict[str, Any]:
        return await web_research.extract_content(**kwargs)

    async def click_link_and_extract(self, **kwargs) -> Dict[str, Any]:
        return await web_research.click_link_and_extract(**kwargs)


def get_web_tools() -> List[Dict]:
    return get_web_research_tools()


# Global instance
web_tools = WebTools()

#!/usr/bin/env python3
"""
Web Tools - Compatibility layer for web_research.py
This file provides backward compatibility for sub-agents that import from tools.web_tools
"""

from .web_research import web_research, get_web_research_tools

# Create aliases for backward compatibility
web_tools = web_research
get_web_tools = get_web_research_tools 