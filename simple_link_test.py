#!/usr/bin/env python3
"""
Simple test script for the link clicking functionality.
"""

import asyncio
import json
from pathlib import Path
import sys

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

from tools.web_research import web_research
from loguru import logger

async def simple_test():
    """Simple test of link clicking functionality."""
    
    print("🚀 Starting simple link clicking test...")
    
    try:
        # Initialize the web research tool
        await web_research.start_browser()
        print("✅ Browser started successfully")
        
        # Navigate to a simple test page
        print("📖 Navigating to a test page...")
        success = await web_research.navigate_to("https://httpbin.org/links/10/0")
        
        if not success:
            print("❌ Failed to navigate to test page")
            return
        
        print("✅ Successfully navigated to test page")
        
        # Test clicking a link by text (should find "0" link)
        print("\n🔗 Testing link click by text...")
        result = await web_research.click_link_and_extract(
            link_text="0",
            scroll_behavior="instant",  # Use instant for faster testing
            extract_data=True,
            save_data=True
        )
        
        print(f"✅ Link click result: {json.dumps(result, indent=2)}")
        
        print("\n🎉 Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        logger.error(f"Test failed: {e}")
    
    finally:
        # Clean up
        await web_research.stop_browser()
        print("🧹 Browser cleaned up")

if __name__ == "__main__":
    asyncio.run(simple_test()) 