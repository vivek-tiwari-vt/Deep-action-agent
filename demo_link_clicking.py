#!/usr/bin/env python3
"""
Comprehensive demo of the link clicking functionality.
"""

import asyncio
import json
from pathlib import Path
import sys

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

from tools.web_research import web_research
from loguru import logger

async def demo_link_clicking():
    """Demo of the link clicking functionality."""
    
    print("🎯 Link Clicking Tool Demo")
    print("=" * 50)
    
    try:
        # Initialize the web research tool
        await web_research.start_browser()
        print("✅ Browser started successfully")
        
        # Demo 1: Basic navigation and content extraction
        print("\n📖 Demo 1: Basic navigation and content extraction")
        print("-" * 40)
        
        success = await web_research.navigate_to("https://example.com")
        if success:
            print("✅ Successfully navigated to example.com")
            
            # Extract content from the current page
            content = await web_research.extract_content()
            print(f"📄 Extracted content length: {len(content.get('content', ''))} characters")
            print(f"🔗 Found {len(content.get('links', []))} links")
        
        # Demo 2: Link clicking with different methods
        print("\n🔗 Demo 2: Link clicking with different methods")
        print("-" * 40)
        
        # Navigate to a page with multiple links
        await web_research.navigate_to("https://httpbin.org/links/5/0")
        
        # Method 1: Click by text
        print("Testing click by text...")
        result1 = await web_research.click_link_and_extract(
            link_text="1",
            scroll_behavior="instant",
            extract_data=True,
            save_data=False
        )
        print(f"Result: {result1.get('success', False)}")
        
        # Method 2: Click by selector
        print("Testing click by selector...")
        result2 = await web_research.click_link_and_extract(
            link_selector="a[href*='1']",
            scroll_behavior="instant",
            extract_data=True,
            save_data=False
        )
        print(f"Result: {result2.get('success', False)}")
        
        # Method 3: Click by URL pattern
        print("Testing click by URL pattern...")
        result3 = await web_research.click_link_and_extract(
            link_url="2",
            scroll_behavior="instant",
            extract_data=True,
            save_data=False
        )
        print(f"Result: {result3.get('success', False)}")
        
        # Demo 3: Human-like behavior
        print("\n👤 Demo 3: Human-like behavior")
        print("-" * 40)
        
        await web_research.navigate_to("https://httpbin.org/links/3/0")
        
        print("Testing human-like scrolling and clicking...")
        result4 = await web_research.click_link_and_extract(
            link_text="0",
            scroll_behavior="human",
            extract_data=True,
            save_data=True
        )
        
        if result4.get('success'):
            print("✅ Human-like behavior test successful")
            print(f"📄 Extracted data length: {len(result4.get('extracted_data', {}).get('content', ''))}")
            if result4.get('saved_file_path'):
                print(f"💾 Data saved to: {result4['saved_file_path']}")
        else:
            print(f"❌ Human-like behavior test failed: {result4.get('error', 'Unknown error')}")
        
        # Demo 4: Error handling
        print("\n🛡️ Demo 4: Error handling")
        print("-" * 40)
        
        print("Testing error handling with non-existent link...")
        result5 = await web_research.click_link_and_extract(
            link_text="non_existent_link",
            scroll_behavior="instant",
            extract_data=True,
            save_data=False
        )
        
        if not result5.get('success'):
            print("✅ Error handling working correctly")
            print(f"Error message: {result5.get('error', 'No error message')}")
        
        print("\n🎉 All demos completed successfully!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        logger.error(f"Demo failed: {e}")
    
    finally:
        # Clean up
        await web_research.stop_browser()
        print("🧹 Browser cleaned up")

async def demo_researcher_integration():
    """Demo of the researcher agent integration."""
    
    print("\n🤖 Researcher Agent Integration Demo")
    print("=" * 50)
    
    try:
        from agents.sub_agents.researcher.agent import ResearcherAgent
        
        # Create researcher agent
        agent = ResearcherAgent(workspace_path="workspace/demo_research")
        
        # Simple research task
        task = """
        Research basic information about web scraping.
        Navigate to a simple website and extract some basic information.
        Focus on:
        1. What is web scraping?
        2. Basic techniques
        3. Common tools used
        
        Use the available tools to gather this information.
        """
        
        print("🔍 Starting research task...")
        result = await agent.execute_task(task)
        
        print("✅ Research completed!")
        print(f"📄 Research summary: {result[:300]}...")
        
    except Exception as e:
        print(f"❌ Researcher agent demo failed: {e}")
        logger.error(f"Researcher agent demo failed: {e}")

async def main():
    """Main demo function."""
    
    # Demo 1: Direct tool usage
    await demo_link_clicking()
    
    # Demo 2: Agent integration
    await demo_researcher_integration()
    
    print("\n✅ All demos completed!")

if __name__ == "__main__":
    asyncio.run(main()) 