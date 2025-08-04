#!/usr/bin/env python3
"""
Web Research Tool
Consolidated web research capabilities with browser automation and content quality assessment.
Combines the best features from browser_tool.py and web_tools.py
"""

import time
import json
import re
import random
import requests
import os
import asyncio
import time
import hashlib
from typing import Dict, List, Optional, Callable, Any
from urllib.parse import urlparse, urljoin
from pathlib import Path
import threading
from datetime import datetime
from bs4 import BeautifulSoup

try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.text import Text
from loguru import logger

# Import configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    BROWSER_HEADLESS, BROWSER_SLOW_MO, BROWSER_TIMEOUT, 
    BROWSER_VIEWPORT_WIDTH, BROWSER_VIEWPORT_HEIGHT, BROWSER_USER_AGENT,
    WEB_RESEARCH_MAX_PAGES, WEB_RESEARCH_MAX_RETRIES,
    WEB_RESEARCH_DELAY_MIN, WEB_RESEARCH_DELAY_MAX, WEB_RESEARCH_SHOW_PROGRESS,
    MAX_OUTPUT_TOKENS
)
from tools.debug_logger import log_browser_action, log_error
from tools.task_monitor import log_task_activity, get_task_monitor

console = Console()

class ContentQuality:
    """Content quality assessment."""
    
    @staticmethod
    def assess_source_credibility(url: str) -> float:
        """Assess source credibility based on domain and URL patterns using comprehensive criteria."""
        domain = urlparse(url).netloc.lower()
        
        # High credibility domains with scores
        high_credibility = {
            # Academic and Research
            'arxiv.org': 0.95, 'researchgate.net': 0.9, 'scholar.google.com': 0.95,
            'ieee.org': 0.9, 'acm.org': 0.9, 'springer.com': 0.85, 'sciencedirect.com': 0.85,
            'nature.com': 0.95, 'science.org': 0.95, 'cell.com': 0.9, 'wiley.com': 0.85,
            'tandfonline.com': 0.85, 'jstor.org': 0.9, 'pubmed.ncbi.nlm.nih.gov': 0.95,
            'ncbi.nlm.nih.gov': 0.95,
            
            # Major News and Media
            'reuters.com': 0.9, 'bloomberg.com': 0.85, 'wsj.com': 0.85, 'ft.com': 0.85,
            'techcrunch.com': 0.8, 'wired.com': 0.8, 'theverge.com': 0.75, 'arstechnica.com': 0.8,
            'cnn.com': 0.75, 'bbc.com': 0.8, 'nytimes.com': 0.8, 'washingtonpost.com': 0.8,
            'theguardian.com': 0.8, 'economist.com': 0.85, 'ap.org': 0.9,
            
            # Educational Institutions
            'mit.edu': 0.95, 'stanford.edu': 0.95, 'harvard.edu': 0.95, 'berkeley.edu': 0.95,
            'cmu.edu': 0.95, 'yale.edu': 0.95, 'princeton.edu': 0.95, 'columbia.edu': 0.95,
            
            # Government and Research Organizations
            'mitre.org': 0.9, 'nist.gov': 0.95, 'nasa.gov': 0.95, 'nih.gov': 0.95,
            'nsf.gov': 0.95, 'dod.gov': 0.9, 'energy.gov': 0.9, 'whitehouse.gov': 0.9,
            'worldbank.org': 0.9, 'imf.org': 0.9, 'oecd.org': 0.9, 'un.org': 0.9,
            'who.int': 0.95, 'cdc.gov': 0.95,
            
            # Tech Companies and Platforms
            'github.com': 0.8, 'stackoverflow.com': 0.8, 'medium.com': 0.7, 'substack.com': 0.7,
            'reddit.com': 0.6, 'hackernews.com': 0.75, 'slashdot.org': 0.7,
            
            # Industry and Business
            'forbes.com': 0.75, 'businessinsider.com': 0.7, 'linkedin.com': 0.7,
            'crunchbase.com': 0.75, 'pitchbook.com': 0.8
        }
        
        # Check for high credibility domains
        for credible_domain, score in high_credibility.items():
            if credible_domain in domain:
                return score
                
        # Check for suspicious patterns
        suspicious_patterns = [
            'clickbait', 'fake', 'scam', 'spam', 'virus', 'malware', 'phishing',
            'get-rich-quick', 'miracle', 'secret', 'exposed', 'shocking'
        ]
        
        for pattern in suspicious_patterns:
            if pattern in domain:
                return 0.1
                
        # Domain-based scoring
        if '.edu' in domain:
            return 0.9  # Educational institutions
        elif '.gov' in domain:
            return 0.9  # Government sites
        elif '.org' in domain:
            return 0.7  # Organizations
        elif '.com' in domain:
            return 0.6  # Commercial sites
        elif '.net' in domain:
            return 0.5  # Network sites
        else:
            return 0.4  # Unknown domains
    
    @staticmethod
    def assess_content_relevance(content: str, query: str) -> float:
        """Assess content relevance to the query."""
        if not content or not query:
            return 0.0
            
        # Convert to lowercase for comparison
        content_lower = content.lower()
        query_lower = query.lower()
        
        # Extract keywords from query
        query_words = set(re.findall(r'\b\w+\b', query_lower))
        
        # Count keyword matches
        matches = 0
        for word in query_words:
            if len(word) > 3:  # Only consider words longer than 3 characters
                matches += content_lower.count(word)
                
        # Calculate relevance score
        if len(query_words) == 0:
            return 0.0
            
        relevance = min(matches / len(query_words), 1.0)
        return relevance
    
    @staticmethod
    def assess_content_freshness(publish_date: Optional[str] = None) -> float:
        """Assess content freshness based on publish date."""
        if not publish_date:
            return 0.5  # Unknown date gets medium score
            
        try:
            # Try to parse the date
            if isinstance(publish_date, str):
                # Handle various date formats
                for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                    try:
                        date_obj = datetime.strptime(publish_date, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    return 0.5  # Could not parse date
            else:
                date_obj = publish_date
                
            # Calculate days since publication
            days_old = (datetime.now() - date_obj).days
            
            # Score based on age (newer = higher score)
            if days_old <= 7:
                return 1.0
            elif days_old <= 30:
                return 0.9
            elif days_old <= 90:
                return 0.8
            elif days_old <= 365:
                return 0.6
            else:
                return 0.3
                
        except Exception:
            return 0.5
    
    @staticmethod
    def assess_link_quality(link_data: Dict) -> Dict[str, float]:
        """Comprehensive assessment of link quality and credibility."""
        url = link_data.get('url', '')
        title = link_data.get('title', '')
        text = link_data.get('text', '')
        
        credibility_score = ContentQuality.assess_source_credibility(url)
        
        # Content quality indicators
        title_length = len(title) if title else 0
        text_length = len(text) if text else 0
        
        # Quality scoring based on content characteristics
        content_quality = 0.0
        if title_length > 10 and title_length < 200:
            content_quality += 0.3
        if text_length > 50:
            content_quality += 0.2
        if text_length > 200:
            content_quality += 0.2
        
        # Relevance indicators
        relevance_score = 0.0
        relevant_keywords = ['research', 'study', 'analysis', 'report', 'paper', 'article', 'news', 'update', 'trend', 'development', 'breakthrough', 'innovation']
        for keyword in relevant_keywords:
            if keyword.lower() in title.lower() or keyword.lower() in text.lower():
                relevance_score += 0.1
        
        relevance_score = min(relevance_score, 0.5)
        
        # Overall quality score
        overall_quality = (credibility_score * 0.6) + (content_quality * 0.3) + (relevance_score * 0.1)
        
        return {
            'credibility_score': credibility_score,
            'content_quality': content_quality,
            'relevance_score': relevance_score,
            'overall_quality': overall_quality
        }

class WebResearch:
    """Consolidated web research tool with browser automation and content quality assessment."""
    
    def __init__(self, headless: bool = None, show_progress: bool = None, slow_mo: int = None):
        # Use environment variables if not explicitly provided
        self.headless = headless if headless is not None else BROWSER_HEADLESS
        self.show_progress = show_progress if show_progress is not None else WEB_RESEARCH_SHOW_PROGRESS
        self.slow_mo = slow_mo if slow_mo is not None else BROWSER_SLOW_MO
        
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.progress_callbacks = []
        self.current_url = None
        self.page_sources = []
        self.session_data = {}
        self.browser_initialized = False
        self.task_id = None  # Store task_id for file organization
        
        # HTTP session for simple requests
        self.http_session = requests.Session()
        self.http_session.headers.update({
            'User-Agent': BROWSER_USER_AGENT
        })
        
        # Anti-detection settings with environment variable support
        self.user_agents = [
            BROWSER_USER_AGENT,
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]
        self.current_user_agent = None
        
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available. Browser automation will be disabled.")
        
        # Log browser configuration
        logger.info(f"Browser configuration: headless={self.headless}, slow_mo={self.slow_mo}, show_progress={self.show_progress}")
    
    def set_task_id(self, task_id: str):
        """Set the task_id for proper file organization."""
        self.task_id = task_id
        logger.info(f"Task ID set for web research tool: {task_id}")
    
    def add_progress_callback(self, callback: Callable):
        """Add a progress callback function."""
        self.progress_callbacks.append(callback)
    
    def _notify_progress(self, action: str, progress: float, status: str):
        """Notify all progress callbacks."""
        for callback in self.progress_callbacks:
            try:
                callback(action, progress, status)
            except Exception as e:
                console.print(f"[red]Progress callback error: {e}[/red]")
    
    async def _human_delay(self, min_seconds: float = None, max_seconds: float = None):
        """Add a random human-like delay."""
        min_delay = min_seconds if min_seconds is not None else WEB_RESEARCH_DELAY_MIN
        max_delay = max_seconds if max_seconds is not None else WEB_RESEARCH_DELAY_MAX
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)
    
    def _human_type(self, element, text: str):
        """Type text with human-like speed and variations."""
        for char in text:
            element.type(char)
            # Random delay between characters (50-150ms)
            time.sleep(random.uniform(0.05, 0.15))
            
            # Occasionally pause longer (like a human thinking)
            if random.random() < 0.1:  # 10% chance
                time.sleep(random.uniform(0.2, 0.5))
    
    def _human_scroll(self, direction: str = "down", steps: int = 3):
        """Scroll with human-like behavior."""
        for i in range(steps):
            # Random scroll amount
            scroll_amount = random.randint(300, 800)
            
            if direction == "down":
                self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            else:
                self.page.evaluate(f"window.scrollBy(0, -{scroll_amount})")
            
            # Random delay between scrolls
            time.sleep(random.uniform(0.5, 1.5))
            
            # Occasionally pause longer
            if random.random() < 0.3:  # 30% chance
                time.sleep(random.uniform(1.0, 2.0))
    
    async def _check_for_captcha(self) -> bool:
        """Check if page contains reCAPTCHA or other bot detection."""
        try:
            # Check for common captcha indicators
            captcha_indicators = [
                'iframe[src*="recaptcha"]',
                'div[class*="recaptcha"]',
                'div[id*="recaptcha"]',
                'iframe[src*="captcha"]',
                'div[class*="captcha"]',
                'div[id*="captcha"]',
                'div[class*="challenge"]',
                'div[id*="challenge"]',
                'div[class*="verify"]',
                'div[id*="verify"]'
            ]
            
            for selector in captcha_indicators:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    return True
            
            # Check page content for captcha indicators
            page_content = await self.page.content()
            page_content = page_content.lower()
            captcha_keywords = ['captcha', 'recaptcha', 'verify you are human', 'robot check']
            
            for keyword in captcha_keywords:
                if keyword in page_content:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for captcha: {e}")
            return False
    
    async def _handle_captcha(self) -> bool:
        """Handle reCAPTCHA if detected."""
        if await self._check_for_captcha():
            logger.warning("reCAPTCHA detected! Implementing avoidance strategies...")
            
            # Wait longer and try different approach
            await self._human_delay(10, 20)
            
            # Try refreshing the page
            await self.page.reload()
            await self._human_delay(3, 6)
            
            # Check if still present
            if await self._check_for_captcha():
                logger.error("reCAPTCHA still present after refresh")
                return False
            
            return True
        return True
    
    async def _setup_browser(self):
        """Setup browser with anti-detection measures and proper error handling."""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright is not available. Please install it with: pip install playwright && playwright install")
        
        try:
            logger.info("Starting Playwright...")
            log_browser_action("setup", "start_playwright", {"headless": self.headless, "slow_mo": self.slow_mo})
            self.playwright = await async_playwright().start()
            
            # Choose random user agent
            self.current_user_agent = random.choice(self.user_agents)
            logger.info(f"Using user agent: {self.current_user_agent[:50]}...")
            
            # Launch browser with anti-detection settings
            logger.info(f"Launching browser (headless={self.headless})...")
            log_browser_action("setup", "launch_browser", {
                "headless": self.headless, 
                "slow_mo": self.slow_mo, 
                "timeout": BROWSER_TIMEOUT,
                "args": [
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-images' if self.headless else '--disable-images=false'
                ]
            })
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo,
                timeout=BROWSER_TIMEOUT,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-images' if self.headless else '--disable-images=false'
                ]
            )
            
            # Create context with anti-detection measures
            logger.info("Creating browser context...")
            self.context = await self.browser.new_context(
                user_agent=self.current_user_agent,
                viewport={'width': BROWSER_VIEWPORT_WIDTH, 'height': BROWSER_VIEWPORT_HEIGHT},
                locale='en-US',
                timezone_id='America/New_York',
                extra_http_headers={
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
            )
            
            # Create page
            logger.info("Creating browser page...")
            self.page = await self.context.new_page()
            
            # Set page timeout
            self.page.set_default_timeout(BROWSER_TIMEOUT)
            
            # Execute script to remove webdriver property
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)
            
            # Set extra headers
            await self.page.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
            
            self.browser_initialized = True
            logger.info("Browser setup completed successfully")
            log_browser_action("setup", "browser_setup_complete", {"status": "success"})
            
        except Exception as e:
            logger.error(f"Failed to setup browser: {e}")
            log_error("setup", e, "browser_setup")
            self.browser_initialized = False
            # Clean up any partially initialized components
            await self._cleanup_browser()
            raise
    
    async def _cleanup_browser(self):
        """Clean up browser resources safely."""
        try:
            if hasattr(self, 'page') and self.page:
                await self.page.close()
                self.page = None
            if hasattr(self, 'context') and self.context:
                await self.context.close()
                self.context = None
            if hasattr(self, 'browser') and self.browser:
                await self.browser.close()
                self.browser = None
            if hasattr(self, 'playwright') and self.playwright:
                await self.playwright.stop()
                self.playwright = None
            self.browser_initialized = False
        except Exception as e:
            logger.error(f"Error during browser cleanup: {e}")
    
    async def start_browser(self):
        """Start the browser with proper error handling."""
        try:
            if not self.browser_initialized:
                await self._setup_browser()
            logger.info("Browser started successfully")
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise
    
    async def stop_browser(self):
        """Stop the browser with proper cleanup."""
        try:
            await self._cleanup_browser()
            logger.info("Browser stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping browser: {e}")
    
    async def navigate_to(self, url: str) -> bool:
        """Navigate to a URL with human-like behavior and proper error handling."""
        try:
            # Validate and fix URL
            if not url or not isinstance(url, str):
                logger.error(f"Invalid URL: {url}")
                log_error("navigation", Exception(f"Invalid URL: {url}"), "navigate_to")
                return False
            
            # Fix relative URLs
            if url.startswith('//'):
                url = 'https:' + url
            elif url.startswith('/'):
                url = 'https://duckduckgo.com' + url
            elif not url.startswith('http'):
                url = 'https://' + url
            
            # Validate URL format
            if not url.startswith('http'):
                logger.error(f"Invalid URL format: {url}")
                log_error("navigation", Exception(f"Invalid URL format: {url}"), "navigate_to")
                return False
            
            # Ensure browser is initialized
            if not self.browser_initialized or not self.page:
                logger.error("Browser not initialized. Cannot navigate.")
                log_error("navigation", Exception("Browser not initialized"), "navigate_to")
                self._notify_progress("navigation", 0.0, "Browser not initialized")
                return False
            
            self._notify_progress("navigation", 0.0, f"Navigating to: {url}")
            logger.info(f"Navigating to: {url}")
            log_browser_action("navigation", "start_navigation", {"url": url})
            
            # Navigate to URL with timeout
            log_browser_action("navigation", "page_goto", {"url": url, "timeout": BROWSER_TIMEOUT})
            await self.page.goto(url, wait_until='networkidle', timeout=BROWSER_TIMEOUT)
            self.current_url = url
            
            self._notify_progress("navigation", 0.5, "Page loaded, checking for captcha")
            log_browser_action("navigation", "page_loaded", {"url": url})
            
            # Check for captcha
            if await self._check_for_captcha():
                logger.warning("Captcha detected, attempting to handle...")
                if not await self._handle_captcha():
                    logger.error("Failed to handle captcha")
                    return False
            
            # Human-like delay
            await self._human_delay(WEB_RESEARCH_DELAY_MIN, WEB_RESEARCH_DELAY_MAX)
            
            self._notify_progress("navigation", 1.0, f"Successfully navigated to: {url}")
            logger.info(f"Successfully navigated to: {url}")
            log_browser_action("navigation", "navigation_success", {"url": url})
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {e}")
            log_error("navigation", e, f"navigate_to_{url}")
            self._notify_progress("navigation", 0.0, f"Failed to navigate: {str(e)}")
            return False
    
    def scroll_page(self, direction: str = "down", amount: str = "full") -> bool:
        """Scroll the page with human-like behavior."""
        try:
            self._notify_progress("scrolling", 0.0, f"Scrolling {direction}")
            
            if amount == "full":
                # Scroll to bottom
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            else:
                # Human-like scrolling
                self._human_scroll(direction, 3)
            
            self._notify_progress("scrolling", 1.0, "Scrolling completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to scroll page: {e}")
            return False
    
    async def extract_content(self, selectors: Dict[str, str] = None) -> Dict[str, Any]:
        """Extract content from the current page with improved error handling."""
        try:
            # Ensure browser is initialized
            if not self.browser_initialized or not self.page:
                logger.error("Browser not initialized. Cannot extract content.")
                return {'error': 'Browser not initialized'}
            
            if selectors is None:
                selectors = {
                    'title': 'h1, h2, h3, title',
                    'content': 'p, div[class*="content"], div[class*="text"], article, main',
                    'links': 'a[href]'
                }
            
            extracted_data = {}
            
            # Extract title
            if 'title' in selectors:
                try:
                    title_elements = await self.page.query_selector_all(selectors['title'])
                    titles = [await elem.inner_text() for elem in title_elements if await elem.inner_text()]
                    titles = [title.strip() for title in titles if title.strip()]
                    extracted_data['title'] = titles[0] if titles else ""
                    logger.debug(f"Extracted title: {extracted_data['title'][:50]}...")
                except Exception as e:
                    logger.warning(f"Failed to extract title: {e}")
                    extracted_data['title'] = ""
            
            # Extract content
            if 'content' in selectors:
                try:
                    content_elements = await self.page.query_selector_all(selectors['content'])
                    content = []
                    for elem in content_elements:
                        text = await elem.inner_text()
                        text = text.strip()
                        if text and len(text) > 20:  # Lower threshold for more content
                            content.append(text)
                    extracted_data['content'] = '\n\n'.join(content)
                    logger.debug(f"Extracted {len(content)} content blocks")
                except Exception as e:
                    logger.warning(f"Failed to extract content: {e}")
                    extracted_data['content'] = ""
            
            # Extract links
            if 'links' in selectors:
                try:
                    link_elements = await self.page.query_selector_all(selectors['links'])
                    links = []
                    for elem in link_elements:
                        href = await elem.get_attribute('href')
                        text = await elem.inner_text()
                        text = text.strip()
                        if href and text and len(text) < 100:  # Avoid very long link text
                            links.append({
                                'url': href,
                                'text': text
                            })
                    extracted_data['links'] = links[:20]  # Limit to 20 links
                    logger.debug(f"Extracted {len(links)} links")
                except Exception as e:
                    logger.warning(f"Failed to extract links: {e}")
                    extracted_data['links'] = []
            
            # Add metadata
            extracted_data['url'] = self.current_url
            extracted_data['extracted_at'] = datetime.now().isoformat()
            
            # Validate that we got some content
            if not extracted_data.get('title') and not extracted_data.get('content'):
                logger.warning("No content extracted, trying fallback selectors")
                # Try to get page title from document title
                try:
                    page_title = await self.page.title()
                    if page_title:
                        extracted_data['title'] = page_title
                except:
                    pass
            
            logger.info(f"Content extraction completed: title={bool(extracted_data.get('title'))}, content_length={len(extracted_data.get('content', ''))}")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Failed to extract content: {e}")
            return {'error': str(e), 'url': self.current_url}
    
    async def _navigate_with_interactivity(self, url: str, task_id: str = None) -> bool:
        """Navigate to a URL with enhanced interactivity (scrolling, clicking, etc.)."""
        try:
            await self._write_progress_to_file(task_id, "navigation_start", {"url": url})
            
            # Navigate to the page
            success = await self.navigate_to(url)
            if not success:
                await self._write_progress_to_file(task_id, "navigation_failed", {"url": url, "reason": "initial_navigation"})
                return False
            
            await self._write_progress_to_file(task_id, "navigation_success", {"url": url})
            
            # Wait for page to load
            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(2)
            
            # Take a screenshot
            screenshot_path = await self.page.screenshot(path=f"page_{int(time.time())}.png")
            await self._write_progress_to_file(task_id, "screenshot_taken", {"path": screenshot_path})
            
            # Scroll down to load more content
            await self._scroll_page_interactively()
            await self._write_progress_to_file(task_id, "scrolling_completed", {"url": url})
            
            # Use smart LLM-driven navigation to decide what to do
            await self._smart_navigation_with_llm(task_id, query)
            
            # Wait a bit more for any dynamic content
            await asyncio.sleep(1)
            
            return True
            
        except Exception as e:
            logger.error(f"Interactive navigation failed for {url}: {e}")
            await self._write_progress_to_file(task_id, "navigation_error", {"url": url, "error": str(e)})
            return False
    
    async def _navigate_with_different_user_agent(self, url: str, task_id: str = None) -> bool:
        """Navigate with a different user agent to avoid detection."""
        try:
            # Change user agent
            new_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            await self.page.set_extra_http_headers({"User-Agent": new_user_agent})
            
            # Navigate to the URL
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            
            return True
            
        except Exception as e:
            logger.error(f"Navigation with different user agent failed: {e}")
            return False
    
    async def _navigate_with_stealth(self, url: str, task_id: str = None) -> bool:
        """Navigate with enhanced stealth measures."""
        try:
            # Apply stealth measures
            await self._apply_stealth_measures()
            
            # Set stealth user agent
            stealth_user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            await self.page.set_extra_http_headers({"User-Agent": stealth_user_agent})
            
            # Navigate with longer timeout
            await self.page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(4)
            
            return True
            
        except Exception as e:
            logger.error(f"Stealth navigation failed: {e}")
            return False
    
    async def _extract_content_with_multiple_strategies(self, task_id: str = None) -> Dict[str, Any]:
        """Extract content using multiple strategies for maximum coverage."""
        try:
            content = {}
            
            # Strategy 1: Enhanced content extraction
            enhanced_content = await self._extract_enhanced_content()
            if enhanced_content and enhanced_content.get('text'):
                content.update(enhanced_content)
                log_browser_action("web_search", "extraction_strategy_success", {"strategy": "enhanced", "length": len(enhanced_content.get('text', ''))})
            
            # Strategy 2: Interactive content extraction
            if not content.get('text'):
                interactive_content = await self._extract_content_interactively(task_id)
                if interactive_content and interactive_content.get('text'):
                    content.update(interactive_content)
                    log_browser_action("web_search", "extraction_strategy_success", {"strategy": "interactive", "length": len(interactive_content.get('text', ''))})
            
            # Strategy 3: Basic content extraction as fallback
            if not content.get('text'):
                basic_content = await self._extract_basic_content()
                if basic_content and basic_content.get('text'):
                    content.update(basic_content)
                    log_browser_action("web_search", "extraction_strategy_success", {"strategy": "basic", "length": len(basic_content.get('text', ''))})
            
            return content
            
        except Exception as e:
            logger.error(f"Multi-strategy content extraction failed: {e}")
            return {}
    
    async def _extract_basic_content(self) -> Dict[str, Any]:
        """Extract basic content from the page."""
        try:
            # Get page title
            title = await self.page.title()
            
            # Get main content using common selectors
            content_selectors = [
                'main', 'article', '.content', '.post-content', '.entry-content',
                '.article-content', '.story-content', '.text-content', 'p'
            ]
            
            text_content = ""
            for selector in content_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for element in elements[:5]:  # Limit to first 5 elements
                        text = await element.inner_text()
                        if text and len(text) > 100:
                            text_content += text + "\n\n"
                except Exception:
                    continue
            
            # If no structured content found, get all text
            if not text_content:
                text_content = await self.page.inner_text('body')
            
            return {
                'title': title,
                'text': text_content,
                'url': self.page.url,
                'extraction_method': 'basic'
            }
            
        except Exception as e:
            logger.error(f"Basic content extraction failed: {e}")
            return {}
    
    async def _scroll_page_interactively(self):
        """Scroll the page in a human-like manner to load dynamic content."""
        try:
            # Get page height
            page_height = await self.page.evaluate("document.body.scrollHeight")
            viewport_height = await self.page.evaluate("window.innerHeight")
            
            # Scroll in chunks
            current_position = 0
            scroll_chunk = viewport_height * 0.8  # Scroll 80% of viewport height
            
            while current_position < page_height:
                # Scroll down
                await self.page.evaluate(f"window.scrollTo(0, {current_position + scroll_chunk})")
                current_position += scroll_chunk
                
                # Wait a bit
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Occasionally pause longer (like a human reading)
                if random.random() < 0.3:
                    await asyncio.sleep(random.uniform(1.0, 2.0))
                
                # Check if page height changed (dynamic content loaded)
                new_height = await self.page.evaluate("document.body.scrollHeight")
                if new_height > page_height:
                    page_height = new_height
            
            # Scroll back to top
            await self.page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.warning(f"Interactive scrolling failed: {e}")
    
    async def _smart_navigation_with_llm(self, task_id: str = None, query: str = None):
        """Use LLM to intelligently decide which links to click and what actions to take."""
        try:
            await self._write_progress_to_file(task_id, "smart_navigation_start", {"query": query})
            
            # Get all links on the current page
            all_links = await self.page.query_selector_all('a[href]')
            link_data = []
            
            # Extract information about each link
            for i, link in enumerate(all_links[:20]):  # Limit to first 20 links
                try:
                    href = await link.get_attribute('href')
                    text = await link.inner_text()
                    if href and text and len(text.strip()) > 5:
                        link_data.append({
                            'index': i,
                            'url': href,
                            'text': text.strip(),
                            'full_url': self.page.url + href if href.startswith('/') else href
                        })
                except:
                    continue
            
            if not link_data:
                await self._write_progress_to_file(task_id, "smart_navigation_no_links", {"message": "No links found"})
                return
            
            # Use LLM to decide which links to click
            llm_decision = await self._ask_llm_for_navigation_decision(link_data, query, task_id)
            
            if llm_decision.get('action') == 'click_link':
                link_index = llm_decision.get('link_index')
                if link_index is not None and link_index < len(link_data):
                    selected_link = link_data[link_index]
                    
                    await self._write_progress_to_file(task_id, "llm_link_selection", {
                        "selected_link": selected_link,
                        "reasoning": llm_decision.get('reasoning', '')
                    })
                    
                    # Click the selected link
                    await all_links[link_index].click()
                    await self.page.wait_for_load_state("networkidle")
                    await asyncio.sleep(2)
                    
                    # Scroll and extract content from the new page
                    await self._scroll_page_interactively()
                    
                    await self._write_progress_to_file(task_id, "llm_navigation_completed", {
                        "new_url": self.page.url,
                        "action": "link_clicked"
                    })
                    
            elif llm_decision.get('action') == 'next_page':
                # Try to go to next page of search results
                await self._go_to_next_search_page()
                await self._write_progress_to_file(task_id, "llm_navigation_completed", {
                    "action": "next_page",
                    "new_url": self.page.url
                })
                
            elif llm_decision.get('action') == 'extract_current':
                # LLM decided to extract content from current page
                await self._write_progress_to_file(task_id, "llm_navigation_completed", {
                    "action": "extract_current",
                    "reasoning": llm_decision.get('reasoning', '')
                })
                
        except Exception as e:
            logger.error(f"Smart navigation with LLM failed: {e}")
            await self._write_progress_to_file(task_id, "smart_navigation_error", {"error": str(e)})
    
    async def _ask_llm_for_navigation_decision(self, link_data: List[Dict], query: str, task_id: str = None) -> Dict:
        """Ask LLM to decide which action to take based on available links and search query."""
        try:
            # Prepare context for LLM
            context = {
                "search_query": query,
                "current_url": self.page.url,
                "available_links": link_data[:10],  # Limit to first 10 links
                "task_id": task_id
            }
            
            # Create prompt for LLM
            prompt = f"""
You are an intelligent web research assistant. Based on the search query and available links, decide what action to take:

SEARCH QUERY: {query}
CURRENT URL: {self.page.url}

AVAILABLE LINKS:
{chr(10).join([f"{i+1}. {link['text']} ({link['url']})" for i, link in enumerate(link_data[:10])])}

POSSIBLE ACTIONS:
1. click_link - Click on a specific link that seems most relevant
2. next_page - Go to the next page of search results if current page doesn't have enough relevant content
3. extract_current - Extract content from the current page if it has relevant information

DECISION CRITERIA:
- If you see a link that directly relates to the search query, choose 'click_link' with that link's index
- If the current page has search results but none seem directly relevant, choose 'next_page'
- If the current page has relevant content, choose 'extract_current'
- Consider the link text and URL to determine relevance

Respond in JSON format:
{{
    "action": "click_link|next_page|extract_current",
    "link_index": <index if action is click_link, otherwise null>,
    "reasoning": "Brief explanation of your decision"
}}
"""
            
            # Call LLM
            from llm_providers.provider_handler import LLMProviderHandler
            
            llm_provider = LLMProviderHandler()
            messages = [{"role": "user", "content": prompt}]
            response = llm_provider.call_llm(
                provider="gemini",  # Use Gemini for navigation decisions
                model="gemini-1.5-flash",
                messages=messages,
                max_tokens=MAX_OUTPUT_TOKENS
            )
            
            # Extract the response content
            response_content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
            if not response_content:
                response_content = response.get('content', '')  # Fallback for different response formats
            
            # Parse LLM response
            try:
                import json
                decision = json.loads(response_content)
                return decision
            except json.JSONDecodeError:
                # Fallback decision if LLM response is not valid JSON
                return {
                    "action": "extract_current",
                    "reasoning": "LLM response parsing failed, defaulting to extract current page"
                }
                
        except Exception as e:
            logger.error(f"LLM navigation decision failed: {e}")
            return {
                "action": "extract_current",
                "reasoning": f"Error in LLM decision: {str(e)}"
            }
    
    async def _go_to_next_search_page(self):
        """Navigate to the next page of search results."""
        try:
            # Look for next page links
            next_page_selectors = [
                'a[aria-label*="Next"]',
                'a[aria-label*="next"]',
                'a:contains("Next")',
                'a:contains("next")',
                'a[href*="search"]:contains("2")',
                'a[href*="search"]:contains("3")',
                'a[href*="search"]:contains("4")',
                'a[href*="search"]:contains("5")',
                'a[href*="&start="]',
                'a[href*="&page="]'
            ]
            
            for selector in next_page_selectors:
                try:
                    next_link = await self.page.query_selector(selector)
                    if next_link:
                        await next_link.click()
                        await self.page.wait_for_load_state("networkidle")
                        await asyncio.sleep(2)
                        return True
                except:
                    continue
            
            # Try to find next page by URL manipulation
            current_url = self.page.url
            if '&start=' in current_url:
                # Google search with start parameter
                import re
                match = re.search(r'&start=(\d+)', current_url)
                if match:
                    current_start = int(match.group(1))
                    next_start = current_start + 10
                    next_url = re.sub(r'&start=\d+', f'&start={next_start}', current_url)
                    await self.page.goto(next_url)
                    await self.page.wait_for_load_state("networkidle")
                    await asyncio.sleep(2)
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Failed to go to next page: {e}")
            return False

    async def _click_interesting_links(self, task_id: str = None):
        """Find and click on interesting links that might contain relevant content."""
        try:
            # Look for links that might be interesting
            interesting_selectors = [
                'a[href*="article"]',
                'a[href*="post"]',
                'a[href*="news"]',
                'a[href*="blog"]',
                'a[href*="read"]',
                'a[href*="more"]',
                'a[href*="continue"]',
                '.read-more',
                '.continue-reading',
                '.more-link'
            ]
            
            for selector in interesting_selectors:
                try:
                    links = await self.page.query_selector_all(selector)
                    if links:
                        # Click on the first interesting link
                        await links[0].click()
                        await self.page.wait_for_load_state("networkidle")
                        await asyncio.sleep(2)
                        
                        await self._write_progress_to_file(task_id, "interesting_link_clicked", {
                            "selector": selector,
                            "new_url": self.page.url
                        })
                        
                        # Scroll the new page
                        await self._scroll_page_interactively()
                        break
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            logger.warning(f"Clicking interesting links failed: {e}")

    async def _extract_content_interactively(self, task_id: str = None) -> Dict[str, Any]:
        """Extract content with enhanced methods and continuous progress updates."""
        try:
            await self._write_progress_to_file(task_id, "content_extraction_start", {"url": self.page.url})
            
            # Wait for page to fully load
            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(1)
            
            # Take a screenshot before extraction
            screenshot_path = await self.page.screenshot(path=f"extraction_{int(time.time())}.png")
            
            # Extract basic content first
            content = await self.extract_content()
            
            await self._write_progress_to_file(task_id, "basic_extraction_completed", {
                "title_length": len(content.get('title', '')),
                "text_length": len(content.get('content', '')),
                "screenshot": screenshot_path
            })
            
            # Try to extract additional content with different methods
            enhanced_content = await self._extract_enhanced_content()
            
            # Merge the content
            content.update(enhanced_content)
            
            # Write extraction results
            await self._write_progress_to_file(task_id, "content_extraction_completed", {
                "final_title_length": len(content.get('title', '')),
                "final_text_length": len(content.get('content', '')),
                "enhanced_methods_used": list(enhanced_content.keys())
            })
            
            return content
            
        except Exception as e:
            logger.error(f"Interactive content extraction failed: {e}")
            await self._write_progress_to_file(task_id, "content_extraction_error", {"error": str(e)})
            return {}
    
    async def _extract_enhanced_content(self) -> Dict[str, Any]:
        """Extract content using enhanced methods."""
        enhanced_content = {}
        
        try:
            # Try to find article content with more specific selectors
            article_selectors = [
                'article',
                '.article-content',
                '.post-content',
                '.entry-content',
                '.content-area',
                '.main-content',
                '[role="main"]',
                '.story-body',
                '.article-body'
            ]
            
            for selector in article_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        # Get the largest article element
                        largest_element = max(elements, key=lambda e: len(e.inner_text()) if e.inner_text() else 0)
                        text = await largest_element.inner_text()
                        if text and len(text) > 100:
                            enhanced_content['article_content'] = text.strip()
                            break
                except:
                    continue
            
            # Try to extract structured data
            try:
                structured_data = await self.page.evaluate("""
                    () => {
                        const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                        const data = [];
                        scripts.forEach(script => {
                            try {
                                data.push(JSON.parse(script.textContent));
                            } catch (e) {}
                        });
                        return data;
                    }
                """)
                if structured_data:
                    enhanced_content['structured_data'] = structured_data
            except:
                pass
            
            # Try to extract meta tags
            try:
                meta_tags = await self.page.evaluate("""
                    () => {
                        const metas = document.querySelectorAll('meta');
                        const metaData = {};
                        metas.forEach(meta => {
                            const name = meta.getAttribute('name') || meta.getAttribute('property');
                            const content = meta.getAttribute('content');
                            if (name && content) {
                                metaData[name] = content;
                            }
                        });
                        return metaData;
                    }
                """)
                if meta_tags:
                    enhanced_content['meta_tags'] = meta_tags
            except:
                pass
            
        except Exception as e:
            logger.warning(f"Enhanced content extraction failed: {e}")
        
        return enhanced_content
    
    async def _multi_page_extraction_with_intelligence(self, search_results: List[Dict], query: str, max_pages: int, task_id: str = None) -> List[Dict[str, Any]]:
        """Extract content from multiple pages using intelligent link selection and credibility assessment."""
        try:
            extracted_content = []
            pages_visited = 0
            all_prioritized_links = []
            
            await self._write_progress_to_file(task_id, "multi_page_extraction_start", {
                "total_results": len(search_results),
                "max_pages": max_pages,
                "query": query
            })
            
            # Step 1: Analyze and prioritize all search results
            if search_results:
                await self._write_progress_to_file(task_id, "analyzing_all_search_results", {
                    "total_results": len(search_results)
                })
                
                # Use intelligent link prioritization
                prioritized_links = await self._ask_llm_to_prioritize_links(search_results, max_pages * 2, task_id)
                
                await self._write_progress_to_file(task_id, "intelligent_prioritization_completed", {
                    "prioritized_links": len(prioritized_links),
                    "total_results": len(search_results)
                })
                
                all_prioritized_links = prioritized_links
            
            # Step 2: Extract from multiple pages with intelligent selection
            for i, link_data in enumerate(all_prioritized_links):
                if pages_visited >= max_pages:
                    break
                
                await self._write_progress_to_file(task_id, "processing_intelligent_link", {
                    "link_index": i,
                    "title": link_data.get('title', '')[:50],
                    "url": link_data.get('url', ''),
                    "priority_score": link_data.get('priority_score', 0),
                    "credibility_score": link_data.get('quality_scores', {}).get('credibility_score', 0)
                })
                
                # Visit and extract from this link
                success = await self._visit_and_extract_result(link_data, query, task_id)
                if success:
                    pages_visited += 1
                    extracted_content.append(success)
                    
                    log_browser_action("web_search", "intelligent_extraction_success", {
                        "url": link_data.get('url', ''),
                        "pages_visited": pages_visited,
                        "content_length": len(success.get('text', '')),
                        "quality_score": success.get('quality_score', 0),
                        "credibility_score": success.get('credibility_score', 0)
                    })
                    
                    await self._write_progress_to_file(task_id, "intelligent_link_extraction_success", {
                        "pages_visited": pages_visited,
                        "max_pages": max_pages,
                        "content_length": len(success.get('text', '')),
                        "quality_score": success.get('quality_score', 0),
                        "credibility_score": success.get('credibility_score', 0)
                    })
                else:
                    log_browser_action("web_search", "intelligent_extraction_failed", {
                        "url": link_data.get('url', ''),
                        "reason": "extraction_failed"
                    })
                    
                    await self._write_progress_to_file(task_id, "intelligent_link_extraction_failed", {
                        "url": link_data.get('url', ''),
                        "reason": "extraction_failed"
                    })
                
                # Check if we have sufficient quality content
                if self._has_sufficient_quality_content(extracted_content, query):
                    await self._write_progress_to_file(task_id, "sufficient_quality_content_reached", {
                        "total_extracted": len(extracted_content),
                        "quality_check": "passed"
                    })
                    break
                
                # Human-like delay between extractions
                await self._human_delay(2, 4)
            
            # Step 3: Assess overall extraction quality
            total_content_length = sum(len(content.get('text', '')) for content in extracted_content)
            avg_quality = sum(content.get('quality_score', 0) for content in extracted_content) / len(extracted_content) if extracted_content else 0
            avg_credibility = sum(content.get('credibility_score', 0) for content in extracted_content) / len(extracted_content) if extracted_content else 0
            
            log_browser_action("web_search", "multi_page_extraction_completed", {
                "total_extracted": len(extracted_content),
                "pages_visited": pages_visited,
                "total_content_length": total_content_length,
                "avg_quality": avg_quality,
                "avg_credibility": avg_credibility
            })
            
            await self._write_progress_to_file(task_id, "multi_page_extraction_completed", {
                "total_extracted": len(extracted_content),
                "pages_visited": pages_visited,
                "max_pages": max_pages,
                "total_content_length": total_content_length,
                "avg_quality": avg_quality,
                "avg_credibility": avg_credibility
            })
            
            return extracted_content
            
        except Exception as e:
            logger.error(f"Multi-page extraction with intelligence failed: {e}")
            await self._write_progress_to_file(task_id, "multi_page_extraction_error", {"error": str(e)})
            return extracted_content
    
    async def _ask_llm_to_prioritize_links(self, search_results: List[Dict], max_results: int) -> List[Dict]:
        """Intelligent link prioritization using multiple criteria and LLM guidance."""
        try:
            # Prepare context for LLM
            available_results = [r for r in search_results if r.get('href') and r.get('text')]
            
            if not available_results:
                return []
            
            # First, assess quality of all links using our credibility system
            assessed_links = []
            for i, result in enumerate(available_results):
                quality_assessment = ContentQuality.assess_link_quality({
                    'url': result.get('href', ''),
                    'title': result.get('text', ''),
                    'text': result.get('snippet', '')
                })
                
                assessed_links.append({
                    'index': i,
                    'title': result.get('text', ''),
                    'url': result.get('href', ''),
                    'snippet': result.get('snippet', ''),
                    'quality_scores': quality_assessment,
                    'overall_quality': quality_assessment['overall_quality']
                })
            
            # Sort by quality score first
            assessed_links.sort(key=lambda x: x['overall_quality'], reverse=True)
            
            # Take top candidates for LLM analysis
            top_candidates = assessed_links[:min(15, len(assessed_links))]
            
            prompt = f"""
You are an expert web research assistant. Analyze these pre-filtered search results and select the most relevant links for deep research.

SEARCH CONTEXT: Research task requiring high-quality, credible sources

PRE-FILTERED CANDIDATES (sorted by quality):
{chr(10).join([f"{i+1}. {r['title']} ({r['url']}) - Quality: {r['overall_quality']:.2f} - Credibility: {r['quality_scores']['credibility_score']:.2f}" for i, r in enumerate(top_candidates)])}

SELECTION CRITERIA:
1. **Credibility**: Prefer academic (.edu), government (.gov), research institutions, major news outlets
2. **Relevance**: Direct match to research topic, recent developments, authoritative analysis
3. **Content Quality**: Substantial content, well-structured information, professional presentation
4. **Diversity**: Avoid duplicate sources, prefer different perspectives and angles

TASK: Select the top {max_results} most promising links for deep research. Consider:
- Source authority and credibility
- Content relevance and depth
- Recency and timeliness
- Information diversity

Respond with a JSON array of selected results:
[
    {{
        "index": <original_index>,
        "title": "<title>",
        "url": "<url>",
        "priority_score": <1-10>,
        "reasoning": "Why this source is valuable for research"
    }},
    ...
]

Order by priority_score (highest first). Focus on the most credible and relevant sources.
"""
            
            # Call LLM for final selection
            from llm_providers.provider_handler import LLMProviderHandler
            
            llm_provider = LLMProviderHandler()
            messages = [{"role": "user", "content": prompt}]
            response = llm_provider.call_llm(
                provider="gemini",
                model="gemini-1.5-flash",
                messages=messages,
                max_tokens=MAX_OUTPUT_TOKENS
            )
            
            # Extract the response content
            response_content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
            if not response_content:
                response_content = response.get('content', '')
            
            # Parse LLM response
            try:
                import json
                prioritized = json.loads(response_content)
                
                # Validate and return prioritized links
                valid_links = []
                for item in prioritized:
                    if isinstance(item, dict) and 'index' in item and 'url' in item:
                        original_index = item['index']
                        if 0 <= original_index < len(top_candidates):
                            original_result = top_candidates[original_index]
                            valid_links.append({
                                'index': original_result['index'],  # Original index in search results
                                'title': original_result['title'],
                                'url': original_result['url'],
                                'snippet': original_result['snippet'],
                                'priority_score': item.get('priority_score', 5),
                                'reasoning': item.get('reasoning', ''),
                                'quality_scores': original_result['quality_scores']
                            })
                
                log_browser_action("web_search", "intelligent_link_selection", {
                    "total_candidates": len(assessed_links),
                    "top_candidates": len(top_candidates),
                    "selected_links": len(valid_links),
                    "avg_quality": sum(l['overall_quality'] for l in assessed_links) / len(assessed_links) if assessed_links else 0
                })
                
                return valid_links[:max_results]
                
            except json.JSONDecodeError:
                # Fallback: return top quality results
                return [{
                    'index': r['index'],
                    'title': r['title'],
                    'url': r['url'],
                    'snippet': r['snippet'],
                    'priority_score': int(r['overall_quality'] * 10),
                    'reasoning': f"High quality source (score: {r['overall_quality']:.2f})",
                    'quality_scores': r['quality_scores']
                } for r in top_candidates[:max_results]]
                
        except Exception as e:
            logger.error(f"Intelligent link prioritization failed: {e}")
            # Fallback: return first few results with basic quality assessment
            return [{
                'index': i,
                'title': r.get('text', ''),
                'url': r.get('href', ''),
                'priority_score': 5,
                'reasoning': 'Fallback prioritization',
                'quality_scores': ContentQuality.assess_link_quality({
                    'url': r.get('href', ''),
                    'title': r.get('text', ''),
                    'text': r.get('snippet', '')
                })
            } for i, r in enumerate(available_results[:max_results])]
    
    async def _ask_llm_continue_or_more_results(self, extracted_content: List[Dict], query: str, pages_visited: int, max_pages: int, task_id: str = None) -> Dict:
        """Ask LLM to decide whether to continue with current results or get more search results."""
        try:
            prompt = f"""
You are an intelligent web research assistant. Decide whether to continue with current results or get more search results.

SEARCH QUERY: {query}
PAGES VISITED: {pages_visited}/{max_pages}

CURRENT EXTRACTED CONTENT SUMMARY:
- {len(extracted_content)} pages extracted
- Content quality: {self._assess_extracted_content_quality(extracted_content, query)}
- Total content length: {sum(len(content.get('text', '')) for content in extracted_content)} characters

DECISION CRITERIA:
- If we have sufficient, high-quality content that covers the query well, choose 'stop'
- If we need more diverse or comprehensive information, choose 'get_more_results'
- Consider the depth and breadth of current content

Respond in JSON format:
{{
    "action": "get_more_results|stop",
    "reasoning": "Brief explanation of your decision"
}}
"""
            
            # Call LLM
            from llm_providers.provider_handler import LLMProviderHandler
            
            llm_provider = LLMProviderHandler()
            messages = [{"role": "user", "content": prompt}]
            response = llm_provider.call_llm(
                provider="gemini",
                model="gemini-1.5-flash",
                messages=messages,
                max_tokens=MAX_OUTPUT_TOKENS
            )
            
            # Extract the response content
            response_content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
            if not response_content:
                response_content = response.get('content', '')
            
            # Parse LLM response
            try:
                import json
                decision = json.loads(response_content)
                return decision
            except json.JSONDecodeError:
                return {
                    "action": "stop",
                    "reasoning": "LLM response parsing failed, defaulting to stop"
                }
                
        except Exception as e:
            logger.error(f"LLM continue decision failed: {e}")
            return {
                "action": "stop",
                "reasoning": f"Error in LLM decision: {str(e)}"
            }
    
    async def _visit_and_extract_result(self, result: Dict, query: str, task_id: str = None) -> Dict[str, Any]:
        """Visit a search result and extract its content using multiple strategies."""
        try:
            url = result.get('url', '')
            if not url or not url.startswith('http'):
                return None
            
            log_browser_action("web_search", "visiting_page", {
                "url": url,
                "title": result.get('title', ''),
                "quality_scores": result.get('quality_scores', {})
            })
            
            await self._write_progress_to_file(task_id, "visiting_result", {
                "url": url,
                "title": result.get('title', ''),
                "priority_score": result.get('priority_score', 0)
            })
            
            # Strategy 1: Direct navigation
            navigation_success = await self._navigate_with_interactivity(url, task_id)
            if not navigation_success:
                # Strategy 2: Try with different user agent
                log_browser_action("web_search", "navigation_retry", {"url": url, "strategy": "user_agent_change"})
                navigation_success = await self._navigate_with_different_user_agent(url, task_id)
            
            if not navigation_success:
                # Strategy 3: Try with stealth measures
                log_browser_action("web_search", "navigation_retry", {"url": url, "strategy": "stealth_mode"})
                navigation_success = await self._navigate_with_stealth(url, task_id)
            
            if not navigation_success:
                log_browser_action("web_search", "navigation_failed", {"url": url, "all_strategies_failed": True})
                return None
            
            # Scroll the page to load more content
            await self._scroll_page_to_load_content()
            
            # Extract content using multiple methods
            content = await self._extract_content_with_multiple_strategies(task_id)
            if not content or not content.get('text'):
                log_browser_action("web_search", "extraction_failed", {"url": url, "reason": "no_content"})
                return None
            
            # Save content to temporary file
            temp_file_path = await self._save_content_to_temp_file(content.get('text', ''), url, task_id)
            
            # Add comprehensive metadata
            content['search_result'] = result
            content['query'] = query
            content['temp_file_path'] = temp_file_path
            content['quality_score'] = ContentQuality.assess_content_relevance(
                content.get('text', ''), query
            )
            content['credibility_score'] = result.get('quality_scores', {}).get('credibility_score', 0.5)
            content['content_length'] = len(content.get('text', ''))
            content['extraction_method'] = 'enhanced_multi_strategy'
            
            # Log to task monitor
            if task_id:
                monitor = get_task_monitor(task_id)
                monitor.log_page_visit(url, True)
                monitor.log_content_extraction(url, len(content.get('text', '')))
            
            await self._write_progress_to_file(task_id, "result_extraction_success", {
                "url": url,
                "content_length": len(content.get('text', '')),
                "quality_score": content.get('quality_score', 0),
                "credibility_score": content.get('credibility_score', 0)
            })
            
            log_browser_action("web_search", "page_extraction_success", {
                "url": url,
                "content_length": len(content.get('text', '')),
                "quality_score": content.get('quality_score', 0),
                "credibility_score": content.get('credibility_score', 0)
            })
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to visit and extract result: {e}")
            log_browser_action("web_search", "page_extraction_error", {
                "url": result.get('url', 'unknown'),
                "error": str(e)
            })
            await self._write_progress_to_file(task_id, "result_extraction_error", {
                "url": result.get('url', 'unknown'),
                "error": str(e)
            })
            return None
    
    def _has_sufficient_quality_content(self, extracted_content: List[Dict], query: str) -> bool:
        """Check if we have sufficient quality content."""
        if not extracted_content:
            return False
        
        # Check total content length
        total_length = sum(len(content.get('text', '')) for content in extracted_content)
        if total_length < 1000:  # Need at least 1000 characters
            return False
        
        # Check quality scores
        quality_scores = [content.get('quality_score', 0) for content in extracted_content]
        avg_quality = sum(quality_scores) / len(quality_scores)
        if avg_quality < 0.3:  # Need reasonable quality
            return False
        
        return True
    
    def _assess_extracted_content_quality(self, extracted_content: List[Dict], query: str) -> str:
        """Assess the quality of extracted content."""
        if not extracted_content:
            return "No content"
        
        total_length = sum(len(content.get('text', '')) for content in extracted_content)
        quality_scores = [content.get('quality_score', 0) for content in extracted_content]
        avg_quality = sum(quality_scores) / len(quality_scores)
        
        if total_length > 5000 and avg_quality > 0.7:
            return "Excellent"
        elif total_length > 2000 and avg_quality > 0.5:
            return "Good"
        elif total_length > 1000 and avg_quality > 0.3:
            return "Fair"
        else:
            return "Poor"
    
    async def web_search(self, query: str, num_results: int = 10, task_id: str = None) -> Dict[str, Any]:
        """
        Perform a web search using Google with Playwright automation.
        
        Args:
            query: Search query
            num_results: Number of results to return
            task_id: Task ID for monitoring
            
        Returns:
            Dictionary with search results
        """
        start_time = time.time()
        
        try:
            log_browser_action("web_search", "start_web_search", {
                "query": query, 
                "num_results": num_results,
                "search_engine": "google_playwright"
            })
            
            # Log task activity if task_id provided
            if task_id:
                log_task_activity(task_id, "search", f"Starting Google search for: {query}", {
                    "query": query,
                    "num_results": num_results,
                    "search_engine": "google_playwright"
                })
            
            # Ensure browser is initialized
            if not self.page:
                log_browser_action("web_search", "starting_browser", {"reason": "page_not_available"})
                await self.start_browser()
            
            # Navigate to Google
            log_browser_action("web_search", "navigate_to_google", {"url": "https://www.google.com"})
            await self.page.goto("https://www.google.com", wait_until="domcontentloaded")
            
            # Handle cookie consent if present
            try:
                cookie_button = await self.page.wait_for_selector('button:has-text("I agree"), button:has-text("Accept all"), button:has-text("Accept")', timeout=5000)
                if cookie_button:
                    await cookie_button.click()
                    log_browser_action("web_search", "cookie_consent_handled", {"action": "accepted"})
            except:
                log_browser_action("web_search", "cookie_consent_handled", {"action": "not_found"})
                pass
            
            # Wait for search box and fill it
            log_browser_action("web_search", "filling_search_box", {"query": query})
            
            # Try different selectors for the search box
            search_selectors = [
                'textarea[name="q"]',
                'input[name="q"]',
                '[role="combobox"]',
                '[aria-label*="Search"]'
            ]
            
            search_box = None
            for selector in search_selectors:
                try:
                    search_box = await self.page.wait_for_selector(selector, timeout=3000)
                    if search_box:
                        log_browser_action("web_search", "search_box_found", {"selector": selector})
                        break
                except:
                    continue
            
            if not search_box:
                raise Exception("Could not find Google search box")
            
            # Clear and fill the search box
            await search_box.click()
            await search_box.fill("")
            await search_box.type(query, delay=100)  # Type with delay to be more human-like
            
            # Press Enter to search
            await search_box.press("Enter")
            
            # Wait for search results
            log_browser_action("web_search", "waiting_for_results", {"query": query})
            await self.page.wait_for_selector('h3, .g, [data-hveid]', timeout=10000)
            
            # Extract search results
            results = await self._extract_google_results_playwright(num_results)
            
            duration = time.time() - start_time
            
            log_browser_action("web_search", "search_completed", {
                "query": query,
                "total_results": len(results),
                "results_returned": min(len(results), num_results),
                "duration": duration
            })
            
            # Log task activity with results
            if task_id:
                monitor = get_task_monitor(task_id)
                monitor.log_search_query(query, len(results))
                
                log_task_activity(task_id, "search", f"Completed Google search for: {query}", {
                    "query": query,
                    "results_count": len(results),
                    "duration": duration,
                    "success": len(results) > 0
                }, duration, success=len(results) > 0)
            
            return {
                'query': query,
                'results': results[:num_results],
                'total_results': len(results)
            }
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Web search failed: {e}")
            log_error("web_search", e, f"web_search_{query}")
            
            # Log task activity for error
            if task_id:
                log_task_activity(task_id, "error", f"Google search failed for: {query}", {
                    "query": query,
                    "error": str(e),
                    "duration": duration
                }, duration, success=False)
            
            return {
                'query': query,
                'results': [],
                'total_results': 0,
                'error': str(e)
            }
    
    def _parse_google_results(self, html_content: str, num_results: int) -> List[Dict]:
        """Parse Google search results from HTML."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            results = []
            
            # Find search result containers
            # Google uses different selectors, try multiple approaches
            selectors = [
                'div.g',  # Main result containers
                'div[data-hveid]',  # Results with data attributes
                'div.rc',  # Result containers
                'div.yuRUbf',  # Another result container
                'div[jscontroller]'  # Results with JS controllers
            ]
            
            result_elements = []
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    result_elements = elements
                    break
            
            log_browser_action("web_search", "parse_google_results", {
                "total_elements_found": len(result_elements),
                "selectors_tried": selectors
            })
            
            for element in result_elements[:num_results]:
                try:
                    # Extract title and URL
                    title_elem = element.select_one('h3') or element.select_one('a h3') or element.select_one('.LC20lb')
                    link_elem = element.select_one('a[href]')
                    snippet_elem = element.select_one('.VwiC3b') or element.select_one('.st') or element.select_one('.aCOpRe')
                    
                    if title_elem and link_elem:
                        title = title_elem.get_text(strip=True)
                        url = link_elem.get('href', '')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                        
                        # Clean and validate URL
                        if url.startswith('/url?q='):
                            # Extract actual URL from Google redirect
                            url = url.split('/url?q=')[1].split('&')[0]
                            url = requests.utils.unquote(url)
                        
                        # Skip Google's own pages and invalid URLs
                        if (url and url.startswith('http') and 
                            not url.startswith('https://www.google.com') and
                            not url.startswith('https://accounts.google.com') and
                            not url.startswith('https://support.google.com')):
                            
                            results.append({
                                'title': title,
                                'url': url,
                                'snippet': snippet,
                                'type': 'search_result',
                                'credibility': ContentQuality.assess_source_credibility(url)
                            })
                            
                            log_browser_action("web_search", "extracted_result", {
                                "title": title[:50] + "..." if len(title) > 50 else title,
                                "url": url,
                                "snippet_length": len(snippet)
                            })
                
                except Exception as e:
                    log_browser_action("web_search", "parse_element_error", {
                        "error": str(e),
                        "element_text": element.get_text()[:100] if element else "None"
                    })
                    continue
            
            log_browser_action("web_search", "parse_completed", {
                "results_extracted": len(results),
                "requested_results": num_results
            })
            
            return results
            
        except Exception as e:
            logger.error(f"Google results parsing failed: {e}")
            log_error("web_search", e, "parse_google_results")
            return []
    
    async def _extract_google_results_playwright(self, num_results: int) -> List[Dict]:
        """Extract Google search results using Playwright with comprehensive debugging and multiple fallback methods."""
        try:
            results = []
            
            # Wait for page to load (faster approach)
            try:
                await self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                await asyncio.sleep(2)
            except Exception as e:
                log_browser_action("web_search", "page_load_timeout", {"error": str(e)})
                # Continue anyway
            
            # Scroll the page to load more content (infinite scroll handling)
            await self._scroll_page_to_load_content()
            
            # Take a screenshot for debugging (with error handling)
            try:
                screenshot_path = f"debug_google_search_{int(time.time())}.png"
                await self.page.screenshot(path=screenshot_path)
                log_browser_action("web_search", "debug_screenshot", {"path": screenshot_path})
            except Exception as e:
                log_browser_action("web_search", "screenshot_error", {"error": str(e)})
            
            # Get page HTML for debugging (with error handling)
            try:
                page_html = await self.page.content()
                log_browser_action("web_search", "debug_html", {
                    "html_length": len(page_html),
                    "html_preview": page_html[:1000] + "..." if len(page_html) > 1000 else page_html
                })
            except Exception as e:
                log_browser_action("web_search", "html_extraction_error", {"error": str(e)})
            
            # Method 1: Enhanced link extraction with LLM-driven selection
            log_browser_action("web_search", "method_start", {"method": "enhanced_link_extraction"})
            
            # Get all links on the page
            all_links = await self.page.query_selector_all('a[href]')
            log_browser_action("web_search", "total_links_found", {"count": len(all_links)})
            
            # Extract and analyze all links
            link_analysis = []
            for i, link in enumerate(all_links[:100]):  # Analyze first 100 links
                try:
                    href = await link.get_attribute('href')
                    text = await link.inner_text()
                    
                    if href and text:
                        link_analysis.append({
                            'index': i,
                            'href': href,
                            'text': text[:150],
                            'text_length': len(text)
                        })
                except Exception as e:
                    continue
            
            log_browser_action("web_search", "link_analysis", {
                "analyzed_links": len(link_analysis),
                "sample_links": link_analysis[:5]
            })
            
            # Filter for search result links
            search_result_links = []
            for link_data in link_analysis:
                href = link_data['href']
                text = link_data['text']
                
                # Check if this looks like a search result
                if (href.startswith('http') and 
                    not href.startswith('https://www.google.com') and
                    not href.startswith('https://google.com') and
                    text and len(text) > 10 and len(text) < 300):
                    
                    # Additional filtering to avoid navigation links
                    skip_domains = ['google.com', 'youtube.com', 'maps.google.com', 'accounts.google.com', 'support.google.com']
                    if not any(skip in href.lower() for skip in skip_domains):
                        search_result_links.append(link_data)
            
            log_browser_action("web_search", "search_result_links_filtered", {
                "count": len(search_result_links),
                "sample_results": search_result_links[:5]
            })
            
            # Use LLM to prioritize which links to extract and visit
            if search_result_links:
                prioritized_links = await self._ask_llm_to_prioritize_links(search_result_links, num_results)
                log_browser_action("web_search", "llm_prioritization", {
                    "prioritized_count": len(prioritized_links),
                    "original_count": len(search_result_links)
                })
                
                # Extract results from prioritized links
                for link_data in prioritized_links:
                    try:
                        href = link_data['href']
                        title = link_data['text']
                        
                        # Handle Google redirect URLs
                        if href.startswith('/url?q='):
                            href = href.split('/url?q=')[1].split('&')[0]
                            import urllib.parse
                            href = urllib.parse.unquote(href)
                        
                        # Get snippet from nearby elements
                        snippet = await self._extract_snippet_near_link(all_links[link_data['index']])
                        
                        if title and href and href.startswith('http'):
                            results.append({
                                'title': title,
                                'url': href,
                                'snippet': snippet[:300] if snippet else '',
                                'type': 'search_result',
                                'credibility': ContentQuality.assess_source_credibility(href),
                                'priority_score': link_data.get('priority_score', 5)
                            })
                            
                            log_browser_action("web_search", "prioritized_link_extracted", {
                                "title": title[:50] + "..." if len(title) > 50 else title,
                                "url": href,
                                "priority_score": link_data.get('priority_score', 5)
                            })
                            
                    except Exception as e:
                        log_browser_action("web_search", "link_extraction_error", {
                            "error": str(e),
                            "link_data": link_data
                        })
                        continue
            
            # Method 2: JavaScript-based extraction as fallback
            if not results:
                log_browser_action("web_search", "fallback_method", {"method": "javascript_extraction"})
                
                search_results = await self.page.evaluate("""
                    () => {
                        const results = [];
                        
                        // Try multiple selectors for Google search results
                        const selectors = [
                            'div[data-hveid]',
                            'div.g',
                            'div[jscontroller]',
                            'div[data-ved]',
                            'div.yuRUbf',
                            'div.rc',
                            'div[jsname]',
                            'div[data-sokoban-container]'
                        ];
                        
                        for (const selector of selectors) {
                            const containers = document.querySelectorAll(selector);
                            console.log(`Selector ${selector} found ${containers.length} elements`);
                            
                            containers.forEach((container, index) => {
                                try {
                                    const linkElement = container.querySelector('a[href]');
                                    if (!linkElement) return;
                                    
                                    const href = linkElement.getAttribute('href');
                                    if (!href || !href.startsWith('http')) return;
                                    
                                    // Skip Google's own pages
                                    if (href.includes('google.com') && !href.includes('/url?q=')) return;
                                    
                                    const titleElement = container.querySelector('h3, .LC20lb, [role="heading"]');
                                    const title = titleElement ? titleElement.textContent.trim() : '';
                                    
                                    const snippetElement = container.querySelector('.VwiC3b, .st, .aCOpRe, .s3v9rd');
                                    const snippet = snippetElement ? snippetElement.textContent.trim() : '';
                                    
                                    if (title && href) {
                                        results.push({
                                            index: index,
                                            title: title,
                                            url: href,
                                            snippet: snippet
                                        });
                                    }
                                } catch (e) {
                                    console.log('Error processing container:', e);
                                }
                            });
                            
                            if (results.length > 0) break;
                        }
                        
                        return results.slice(0, 20);
                    }
                """)
                
                log_browser_action("web_search", "javascript_extraction_results", {
                    "found_results": len(search_results)
                })
                
                # Process JavaScript results
                for result in search_results[:num_results]:
                    try:
                        url = result['url']
                        if url.startswith('/url?q='):
                            url = url.split('/url?q=')[1].split('&')[0]
                            import urllib.parse
                            url = urllib.parse.unquote(url)
                        
                        if url.startswith('http'):
                            results.append({
                                'title': result['title'],
                                'url': url,
                                'snippet': result.get('snippet', ''),
                                'type': 'search_result',
                                'credibility': ContentQuality.assess_source_credibility(url)
                            })
                            
                            log_browser_action("web_search", "js_result_extracted", {
                                "title": result['title'][:50] + "..." if len(result['title']) > 50 else result['title'],
                                "url": url
                            })
                            
                    except Exception as e:
                        log_browser_action("web_search", "js_result_processing_error", {"error": str(e)})
                        continue
            
            # Method 3: Final fallback - extract any external links
            if not results:
                log_browser_action("web_search", "final_fallback", {"method": "external_links_extraction"})
                
                # Look for any external links that might be search results
                external_links = []
                for link_data in link_analysis:
                    href = link_data['href']
                    text = link_data['text']
                    
                    if (href.startswith('http') and 
                        not any(skip in href.lower() for skip in ['google.com', 'youtube.com', 'maps.google.com']) and
                        text and len(text) > 5):
                        
                        external_links.append({
                            'title': text,
                            'url': href,
                            'snippet': '',
                            'type': 'search_result',
                            'credibility': ContentQuality.assess_source_credibility(href)
                        })
                
                results = external_links[:num_results]
                log_browser_action("web_search", "external_links_fallback", {
                    "found_results": len(results)
                })
            
            log_browser_action("web_search", "extraction_completed", {
                "total_extracted": len(results),
                "requested": num_results,
                "methods_used": ["direct_link_extraction", "javascript_extraction", "external_links_fallback"]
            })
            
            return results[:num_results]
            
        except Exception as e:
            logger.error(f"Playwright Google results extraction failed: {e}")
            log_error("web_search", e, "extract_google_results_playwright")
            return []
    
    async def _apply_stealth_measures(self):
        """Apply stealth measures to avoid bot detection."""
        try:
            # Simple stealth measures that are less likely to fail
            await self.page.evaluate("""
                // Remove webdriver property if it exists
                if (navigator.webdriver !== undefined) {
                    delete navigator.webdriver;
                }
                
                // Add user agent override if needed
                if (navigator.userAgent.includes('Headless')) {
                    Object.defineProperty(navigator, 'userAgent', {
                        get: () => 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    });
                }
            """)
            
            log_browser_action("web_search", "stealth_measures_applied", {"status": "success"})
            
        except Exception as e:
            log_browser_action("web_search", "stealth_measures_error", {"error": str(e)})
            # Continue without stealth measures
    
    async def _scroll_page_to_load_content(self):
        """Scroll the page to load more content (infinite scroll handling)."""
        try:
            log_browser_action("web_search", "scroll_start", {"action": "scrolling_page"})
            
            # Scroll down multiple times to load more content
            for i in range(3):
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)
                
                # Check if more content loaded
                new_height = await self.page.evaluate("document.body.scrollHeight")
                log_browser_action("web_search", "scroll_progress", {
                    "scroll_iteration": i + 1,
                    "page_height": new_height
                })
            
            # Scroll back to top
            await self.page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)
            
            log_browser_action("web_search", "scroll_completed", {"action": "scrolling_finished"})
            
        except Exception as e:
            log_browser_action("web_search", "scroll_error", {"error": str(e)})
    
    async def _extract_snippet_near_link(self, link_element) -> str:
        """Extract snippet text near a link element."""
        try:
            # Look for snippet in parent or sibling elements
            parent = await link_element.query_selector('xpath=..')
            if parent:
                # Try multiple selectors for snippets
                snippet_selectors = [
                    '.VwiC3b', '.st', '.aCOpRe', '.s3v9rd', 
                    'span', 'div', 'p', '.snippet', '.description'
                ]
                
                for selector in snippet_selectors:
                    try:
                        snippet_elem = await parent.query_selector(selector)
                        if snippet_elem:
                            snippet_text = await snippet_elem.inner_text()
                            if snippet_text and len(snippet_text) > 10:
                                return snippet_text.strip()
                    except Exception:
                        continue
                
                # If no specific snippet found, get all text from parent
                parent_text = await parent.inner_text()
                if parent_text:
                    # Remove the link text from parent text
                    link_text = await link_element.inner_text()
                    if link_text in parent_text:
                        snippet = parent_text.replace(link_text, '').strip()
                        if len(snippet) > 10:
                            return snippet
            
            return ""
            
        except Exception as e:
            log_browser_action("web_search", "snippet_extraction_error", {"error": str(e)})
            return ""
    
    async def _save_content_to_temp_file(self, content: str, url: str, task_id: str = None) -> str:
        """Save content to a temporary file in the workspace."""
        try:
            # Create filename based on URL
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"content_{url_hash}_{timestamp}.txt"
            
            # Use workspace manager if available
            try:
                from main import get_workspace_manager
                workspace_manager = get_workspace_manager(task_id) if task_id else None
                if workspace_manager:
                    file_path = workspace_manager.save_file(content, filename, "data")
                else:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(content)
                    file_path = filename
            except:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                file_path = filename
            
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving content to temp file: {e}")
            return ""
    
    async def _save_summary_to_file(self, summary: str, query: str, task_id: str = None) -> str:
        """Save summary to a file in the workspace."""
        try:
            # Create filename based on query
            query_safe = re.sub(r'[^\w\s-]', '', query)[:30].replace(' ', '_')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"summary_{query_safe}_{timestamp}.md"
            
            # Use workspace manager if available
            try:
                from main import get_workspace_manager
                workspace_manager = get_workspace_manager(task_id) if task_id else None
                if workspace_manager:
                    file_path = workspace_manager.save_file(summary, filename, "outputs")
                else:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(summary)
                    file_path = filename
            except:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(summary)
                file_path = filename
            
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving summary to file: {e}")
            return ""
    
    async def _write_progress_to_file(self, task_id: str, action: str, data: dict):
        """Write progress information to file."""
        try:
            if not task_id:
                return
            
            timestamp = datetime.now().isoformat()
            progress_entry = {
                "timestamp": timestamp,
                "action": action,
                "data": data
            }
            
            # Use workspace manager if available
            try:
                from main import get_workspace_manager
                workspace_manager = get_workspace_manager(task_id)
                progress_file = workspace_manager.get_progress_path("progress_log.json")
                
                # Load existing progress or create new
                try:
                    with open(progress_file, 'r', encoding='utf-8') as f:
                        progress_data = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    progress_data = {"entries": []}
                
                progress_data["entries"].append(progress_entry)
                
                with open(progress_file, 'w', encoding='utf-8') as f:
                    json.dump(progress_data, f, indent=2)
                    
            except Exception as e:
                logger.warning(f"Could not write to workspace progress file: {e}")
                # Fallback to local file
                with open(f"progress_log_{task_id}.json", 'a', encoding='utf-8') as f:
                    f.write(json.dumps(progress_entry) + '\n')
                    
        except Exception as e:
            logger.error(f"Error writing progress to file: {e}")
    
    async def _summarize_extracted_content(self, extracted_content: List[Dict], query: str, task_id: str = None) -> str:
        """Use LLM to summarize all extracted content."""
        try:
            if not extracted_content:
                return "No content extracted to summarize."
            
            # Prepare content for summarization
            content_summary = []
            for i, content in enumerate(extracted_content[:10]):  # Limit to first 10 for summarization
                title = content.get('title', 'Unknown Title')
                url = content.get('url', 'Unknown URL')
                text = content.get('text', '')[:1000]  # Limit text length
                quality = content.get('quality_score', 0)
                
                content_summary.append(f"Source {i+1}: {title} ({url})\nQuality: {quality:.2f}\nContent: {text}\n")
            
            # Create LLM prompt for summarization
            prompt = f"""
You are an expert research analyst. Summarize the following extracted content related to the search query.

SEARCH QUERY: {query}

EXTRACTED CONTENT:
{chr(10).join(content_summary)}

TASK: Create a comprehensive summary that includes:
1. Key findings and insights
2. Main trends or patterns identified
3. Important sources and their credibility
4. Gaps in information or areas needing more research
5. Overall assessment of content quality and relevance

Provide a well-structured summary with clear sections and actionable insights.
"""
            
            # Call LLM for summarization
            from llm_providers.provider_handler import LLMProviderHandler
            
            llm_provider = LLMProviderHandler()
            messages = [{"role": "user", "content": prompt}]
            response = llm_provider.call_llm(
                provider="gemini",
                model="gemini-1.5-flash",
                messages=messages,
                max_tokens=MAX_OUTPUT_TOKENS
            )
            
            # Extract the response content
            response_content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
            if not response_content:
                response_content = response.get('content', '')
            
            # Save summary to file
            summary_file_path = await self._save_summary_to_file(response_content, query, task_id)
            
            log_browser_action("web_search", "content_summarized", {
                "sources_count": len(extracted_content),
                "summary_length": len(response_content),
                "summary_file": summary_file_path
            })
            
            return response_content
            
        except Exception as e:
            logger.error(f"Failed to summarize content: {e}")
            log_browser_action("web_search", "summarization_error", {"error": str(e)})
            return f"Error summarizing content: {str(e)}"
    
    async def search_and_extract(self, query: str, max_pages: int = None, task_id: str = None) -> List[Dict[str, Any]]:
        """
        Search for content and extract it from multiple pages with enhanced interactivity.
        
        Args:
            query: Search query
            max_pages: Maximum number of pages to extract from (defaults to WEB_RESEARCH_MAX_PAGES)
            task_id: Task ID for monitoring
            
        Returns:
            List of extracted content dictionaries
        """
        start_time = time.time()
        
        # Use environment variable if not specified
        if max_pages is None:
            max_pages = WEB_RESEARCH_MAX_PAGES
        
        log_browser_action("search", "start_search_and_extract", {
            "query": query, 
            "max_pages": max_pages,
            "browser_initialized": self.browser_initialized,
            "task_id": task_id
        })
        
        # Write initial progress
        await self._write_progress_to_file(task_id, "search_start", {
            "query": query,
            "max_pages": max_pages,
            "timestamp": start_time
        })
        
        # Log task activity
        if task_id:
            log_task_activity(task_id, "search", f"Starting search and extract for: {query}", {
                "query": query,
                "max_pages": max_pages
            })
        
        try:
            # Start browser if not already started
            if not self.page:
                log_browser_action("search", "starting_browser", {"reason": "page_not_available"})
                await self.start_browser()
                await self._write_progress_to_file(task_id, "browser_started", {"status": "success"})
            
            # Perform search with task monitoring
            log_browser_action("search", "performing_web_search", {"query": query, "num_results": max_pages * 3})
            await self._write_progress_to_file(task_id, "web_search_start", {"query": query})
            
            search_results = await self.web_search(query, num_results=max_pages * 3, task_id=task_id)
            
            await self._write_progress_to_file(task_id, "web_search_completed", {
                "results_count": len(search_results.get('results', [])),
                "first_results": search_results.get('results', [])[:3]
            })
            
            log_browser_action("search", "web_search_completed", {
                "query": query,
                "results_count": len(search_results.get('results', [])),
                "results": search_results.get('results', [])[:3]  # Log first 3 results
            })
            
            extracted_content = []
            
            # Multi-page extraction with intelligent link selection
            extracted_content = await self._multi_page_extraction_with_intelligence(
                search_results['results'], query, max_pages, task_id
            )
            
            duration = time.time() - start_time
            
            self._notify_progress("extraction", 1.0, f"Extracted from {len(extracted_content)} pages")
            
            # Write final progress
            await self._write_progress_to_file(task_id, "search_completed", {
                "total_extracted": len(extracted_content),
                "total_pages_attempted": len(search_results.get('results', [])),
                "duration": duration,
                "success": len(extracted_content) > 0
            })
            
            log_browser_action("search", "search_and_extract_completed", {
                "query": query,
                "total_pages_attempted": len(search_results.get('results', [])),
                "successful_extractions": len(extracted_content),
                "extracted_content": extracted_content,
                "duration": duration
            })
            
            # Generate summary of extracted content using LLM
            if extracted_content:
                log_browser_action("search", "starting_summarization", {
                    "content_count": len(extracted_content),
                    "query": query
                })
                
                summary = await self._summarize_extracted_content(extracted_content, query, task_id)
                
                log_browser_action("search", "summarization_completed", {
                    "summary_length": len(summary),
                    "query": query
                })
                
                # Add summary to the returned content
                extracted_content.append({
                    'title': f"Research Summary: {query}",
                    'url': 'summary_generated',
                    'text': summary,
                    'type': 'summary',
                    'quality_score': 1.0,
                    'credibility_score': 1.0
                })
            
            # Log final task activity
            if task_id:
                log_task_activity(task_id, "search", f"Completed search and extract for: {query}", {
                    "query": query,
                    "successful_extractions": len(extracted_content),
                    "total_pages_attempted": len(search_results.get('results', [])),
                    "duration": duration,
                    "summary_generated": len(extracted_content) > 0
                }, duration, success=len(extracted_content) > 0)
            
            return extracted_content
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Search and extract failed: {e}")
            log_error("search", e, f"search_and_extract_{query}")
            
            await self._write_progress_to_file(task_id, "search_error", {
                "error": str(e),
                "duration": duration
            })
            
            # Log error in task activity
            if task_id:
                log_task_activity(task_id, "error", f"Search and extract failed for: {query}", {
                    "query": query,
                    "error": str(e),
                    "duration": duration
                }, duration, success=False)
            
            return []
    
    def get_page_screenshot(self, filename: str = None) -> str:
        """Take a screenshot of the current page."""
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
            
            screenshot_path = Path("screenshots") / filename
            screenshot_path.parent.mkdir(exist_ok=True)
            
            self.page.screenshot(path=str(screenshot_path))
            return str(screenshot_path)
            
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return ""
    
    def __enter__(self):
        """Context manager entry."""
        if PLAYWRIGHT_AVAILABLE:
            self.start_browser()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if PLAYWRIGHT_AVAILABLE:
            self.stop_browser()

    async def click_link_and_extract(self, link_selector: str = None, link_text: str = None, link_url: str = None, 
                                   scroll_behavior: str = "human", extract_data: bool = True, 
                                   save_data: bool = True, task_id: str = None) -> Dict[str, Any]:
        """
        Click a link and extract data with human-like behavior.
        
        Args:
            link_selector: CSS selector for the link
            link_text: Text content of the link to find
            link_url: URL pattern to match
            scroll_behavior: "human", "smooth", "instant", or "none"
            extract_data: Whether to extract content after clicking
            save_data: Whether to save extracted data to file
            task_id: Task ID for monitoring
            
        Returns:
            Dictionary with click results and extracted data
        """
        try:
            log_browser_action("link_click", "start_link_click", {
                "link_selector": link_selector,
                "link_text": link_text,
                "link_url": link_url,
                "scroll_behavior": scroll_behavior
            })
            
            await self._write_progress_to_file(task_id, "link_click_start", {
                "link_selector": link_selector,
                "link_text": link_text,
                "link_url": link_url
            })
            
            # Find the link to click
            link_element = await self._find_link_to_click(link_selector, link_text, link_url)
            
            if not link_element:
                error_msg = f"Could not find link with selector={link_selector}, text={link_text}, url={link_url}"
                log_browser_action("link_click", "link_not_found", {"error": error_msg})
                await self._write_progress_to_file(task_id, "link_click_error", {"error": error_msg})
                return {"success": False, "error": error_msg}
            
            # Get link information before clicking
            link_info = await self._get_link_information(link_element)
            
            log_browser_action("link_click", "link_found", {
                "href": link_info.get('href', ''),
                "text": link_info.get('text', ''),
                "is_external": link_info.get('is_external', False)
            })
            
            await self._write_progress_to_file(task_id, "link_found", link_info)
            
            # Scroll to the link with human-like behavior
            if scroll_behavior != "none":
                await self._scroll_to_element_human_like(link_element, scroll_behavior)
            
            # Click the link with human-like behavior
            await self._click_link_human_like(link_element)
            
            # Wait for navigation
            await self._wait_for_navigation()
            
            # Extract data if requested
            extracted_data = {}
            if extract_data:
                extracted_data = await self._extract_data_after_click(task_id)
            
            # Save data if requested
            saved_file_path = None
            if save_data and extracted_data:
                saved_file_path = await self._save_extracted_data(extracted_data, link_info, task_id)
            
            result = {
                "success": True,
                "link_info": link_info,
                "new_url": self.page.url,
                "extracted_data": extracted_data,
                "saved_file_path": saved_file_path
            }
            
            log_browser_action("link_click", "link_click_success", {
                "href": link_info.get('href', ''),
                "new_url": self.page.url,
                "data_extracted": bool(extracted_data),
                "data_saved": bool(saved_file_path)
            })
            
            await self._write_progress_to_file(task_id, "link_click_success", {
                "new_url": self.page.url,
                "data_extracted": bool(extracted_data),
                "data_saved": bool(saved_file_path)
            })
            
            return result
            
        except Exception as e:
            error_msg = f"Link click failed: {str(e)}"
            logger.error(error_msg)
            log_browser_action("link_click", "link_click_error", {"error": str(e)})
            await self._write_progress_to_file(task_id, "link_click_error", {"error": str(e)})
            return {"success": False, "error": error_msg}
    
    async def _find_link_to_click(self, link_selector: str = None, link_text: str = None, link_url: str = None):
        """Find a link to click based on various criteria."""
        try:
            # Method 1: Use CSS selector
            if link_selector:
                try:
                    element = await self.page.wait_for_selector(link_selector, timeout=5000)
                    if element:
                        return element
                except:
                    pass
            
            # Method 2: Find by text content
            if link_text:
                try:
                    # Try exact text match
                    element = await self.page.wait_for_selector(f'a:has-text("{link_text}")', timeout=3000)
                    if element:
                        return element
                except:
                    pass
                
                try:
                    # Try partial text match
                    element = await self.page.wait_for_selector(f'a:has-text("{link_text}")', timeout=3000)
                    if element:
                        return element
                except:
                    pass
            
            # Method 3: Find by URL pattern
            if link_url:
                try:
                    all_links = await self.page.query_selector_all('a[href]')
                    for link in all_links:
                        href = await link.get_attribute('href')
                        if href and link_url in href:
                            return link
                except:
                    pass
            
            # Method 4: Find any clickable link
            try:
                all_links = await self.page.query_selector_all('a[href]')
                for link in all_links[:10]:  # Check first 10 links
                    href = await link.get_attribute('href')
                    text = await link.inner_text()
                    if href and text and len(text.strip()) > 3:
                        return link
            except:
                pass
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding link to click: {e}")
            return None
    
    async def _get_link_information(self, link_element) -> Dict[str, Any]:
        """Get comprehensive information about a link."""
        try:
            href = await link_element.get_attribute('href')
            text = await link_element.inner_text()
            title = await link_element.get_attribute('title')
            
            # Determine if it's an external link
            current_domain = urlparse(self.page.url).netloc
            link_domain = urlparse(href).netloc if href else None
            is_external = link_domain and link_domain != current_domain
            
            # Get link position and size
            bounding_box = await link_element.bounding_box()
            
            return {
                'href': href,
                'text': text.strip() if text else '',
                'title': title,
                'is_external': is_external,
                'domain': link_domain,
                'position': {
                    'x': bounding_box['x'] if bounding_box else 0,
                    'y': bounding_box['y'] if bounding_box else 0,
                    'width': bounding_box['width'] if bounding_box else 0,
                    'height': bounding_box['height'] if bounding_box else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting link information: {e}")
            return {}
    
    async def _scroll_to_element_human_like(self, element, behavior: str = "human"):
        """Scroll to an element with human-like behavior."""
        try:
            if behavior == "none":
                return
            
            # Get element position
            bounding_box = await element.bounding_box()
            if not bounding_box:
                return
            
            # Get current scroll position
            current_scroll = await self.page.evaluate("window.pageYOffset")
            element_y = bounding_box['y']
            viewport_height = await self.page.evaluate("window.innerHeight")
            
            # Calculate target scroll position
            target_scroll = element_y - (viewport_height / 2)  # Center the element
            
            if behavior == "human":
                # Human-like scrolling with pauses and variable speed
                await self._human_scroll_to_position(target_scroll)
            elif behavior == "smooth":
                # Smooth scrolling
                await self.page.evaluate(f"window.scrollTo({{top: {target_scroll}, behavior: 'smooth'}})")
                await asyncio.sleep(1)
            elif behavior == "instant":
                # Instant scroll
                await self.page.evaluate(f"window.scrollTo(0, {target_scroll})")
            
            # Small delay after scrolling
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            logger.warning(f"Error scrolling to element: {e}")
    
    async def _human_scroll_to_position(self, target_position: float):
        """Scroll to a position with human-like behavior."""
        try:
            current_position = await self.page.evaluate("window.pageYOffset")
            distance = target_position - current_position
            
            if abs(distance) < 100:
                return  # Already close enough
            
            # Scroll in chunks with human-like behavior
            chunk_size = random.randint(200, 400)
            direction = 1 if distance > 0 else -1
            
            while abs(distance) > 50:
                # Calculate next scroll position
                scroll_amount = min(chunk_size, abs(distance))
                next_position = current_position + (scroll_amount * direction)
                
                # Scroll with variable speed
                scroll_duration = random.uniform(0.3, 0.8)
                await self.page.evaluate(f"""
                    window.scrollTo({{
                        top: {next_position},
                        behavior: 'smooth'
                    }});
                """)
                
                # Wait with human-like pauses
                await asyncio.sleep(scroll_duration)
                
                # Occasionally pause longer (like reading)
                if random.random() < 0.2:
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Update positions
                current_position = await self.page.evaluate("window.pageYOffset")
                distance = target_position - current_position
                
                # Adjust chunk size for final approach
                if abs(distance) < 200:
                    chunk_size = random.randint(50, 150)
            
        except Exception as e:
            logger.warning(f"Error in human scroll: {e}")
    
    async def _click_link_human_like(self, link_element):
        """Click a link with human-like behavior."""
        try:
            # Move mouse to link with human-like movement
            await self._move_mouse_human_like(link_element)
            
            # Hover over the link briefly
            await asyncio.sleep(random.uniform(0.2, 0.5))
            
            # Click with human-like timing
            await link_element.click(delay=random.randint(50, 150))
            
            log_browser_action("link_click", "link_clicked", {
                "click_delay": "human_like",
                "mouse_movement": "human_like"
            })
            
        except Exception as e:
            logger.error(f"Error clicking link: {e}")
            # Fallback to simple click
            await link_element.click()
    
    async def _move_mouse_human_like(self, element):
        """Move mouse to an element with human-like movement."""
        try:
            # Get element position
            bounding_box = await element.bounding_box()
            if not bounding_box:
                return
            
            # Get current mouse position
            current_mouse = await self.page.evaluate("""
                () => ({ x: window.mouseX || 0, y: window.mouseY || 0 })
            """)
            
            # Calculate target position (center of element)
            target_x = bounding_box['x'] + bounding_box['width'] / 2
            target_y = bounding_box['y'] + bounding_box['height'] / 2
            
            # Move mouse with human-like curve
            await self._move_mouse_along_curve(
                current_mouse.get('x', 0), current_mouse.get('y', 0),
                target_x, target_y
            )
            
        except Exception as e:
            logger.warning(f"Error in human mouse movement: {e}")
            # Fallback to direct movement
            await element.hover()
    
    async def _move_mouse_along_curve(self, start_x: float, start_y: float, end_x: float, end_y: float):
        """Move mouse along a curved path for human-like movement."""
        try:
            # Create a curved path with control points
            distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
            
            if distance < 50:
                # For short distances, move directly
                await self.page.mouse.move(end_x, end_y)
                return
            
            # Create control points for curve
            control_x = start_x + (end_x - start_x) * random.uniform(0.3, 0.7)
            control_y = start_y + (end_y - start_y) * random.uniform(0.3, 0.7)
            
            # Add some randomness to the curve
            control_x += random.uniform(-20, 20)
            control_y += random.uniform(-20, 20)
            
            # Move along the curve in steps
            steps = max(5, int(distance / 20))
            for i in range(steps + 1):
                t = i / steps
                
                # Quadratic Bezier curve
                x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * control_x + t ** 2 * end_x
                y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * control_y + t ** 2 * end_y
                
                await self.page.mouse.move(x, y)
                
                # Variable speed
                delay = random.uniform(0.01, 0.03)
                await asyncio.sleep(delay)
            
        except Exception as e:
            logger.warning(f"Error in curved mouse movement: {e}")
            # Fallback to direct movement
            await self.page.mouse.move(end_x, end_y)
    
    async def _wait_for_navigation(self):
        """Wait for navigation to complete with proper error handling."""
        try:
            # Wait for network to be idle
            await self.page.wait_for_load_state("networkidle", timeout=10000)
            
            # Additional wait for dynamic content
            await asyncio.sleep(random.uniform(1, 3))
            
            # Check if navigation was successful
            if self.page.url == "about:blank":
                raise Exception("Navigation resulted in blank page")
            
            log_browser_action("link_click", "navigation_completed", {
                "new_url": self.page.url
            })
            
        except Exception as e:
            logger.warning(f"Navigation wait failed: {e}")
            # Continue anyway
    
    async def _extract_data_after_click(self, task_id: str = None) -> Dict[str, Any]:
        """Extract data from the page after clicking a link."""
        try:
            await self._write_progress_to_file(task_id, "data_extraction_start", {"url": self.page.url})
            
            # Scroll the page to load all content
            await self._scroll_page_naturally()
            
            # Extract content using multiple methods
            content = await self.extract_content()
            
            # Try to extract additional structured data
            structured_data = await self._extract_structured_data()
            
            # Extract meta information
            meta_data = await self._extract_meta_data()
            
            # Combine all extracted data
            extracted_data = {
                'url': self.page.url,
                'title': content.get('title', ''),
                'content': content.get('content', ''),
                'links': content.get('links', []),
                'structured_data': structured_data,
                'meta_data': meta_data,
                'extracted_at': datetime.now().isoformat(),
                'page_screenshot': await self._take_page_screenshot()
            }
            
            await self._write_progress_to_file(task_id, "data_extraction_completed", {
                "content_length": len(extracted_data.get('content', '')),
                "links_count": len(extracted_data.get('links', [])),
                "has_structured_data": bool(structured_data),
                "has_meta_data": bool(meta_data)
            })
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error extracting data after click: {e}")
            await self._write_progress_to_file(task_id, "data_extraction_error", {"error": str(e)})
            return {}
    
    async def _scroll_page_naturally(self):
        """Scroll the page naturally like a human reading."""
        try:
            # Get page dimensions
            page_height = await self.page.evaluate("document.body.scrollHeight")
            viewport_height = await self.page.evaluate("window.innerHeight")
            
            if page_height <= viewport_height:
                return  # No scrolling needed
            
            # Scroll in natural reading pattern
            current_position = 0
            scroll_speed = random.uniform(0.8, 1.2)  # Variable speed
            
            while current_position < page_height:
                # Calculate next scroll position
                scroll_amount = viewport_height * 0.7 * scroll_speed  # Scroll 70% of viewport
                next_position = min(current_position + scroll_amount, page_height)
                
                # Scroll with smooth behavior
                await self.page.evaluate(f"""
                    window.scrollTo({{
                        top: {next_position},
                        behavior: 'smooth'
                    }});
                """)
                
                # Wait for scroll to complete
                await asyncio.sleep(random.uniform(0.8, 1.5))
                
                # Occasionally pause longer (like reading content)
                if random.random() < 0.3:
                    await asyncio.sleep(random.uniform(1.0, 3.0))
                
                current_position = next_position
                
                # Check if page height changed (dynamic content)
                new_height = await self.page.evaluate("document.body.scrollHeight")
                if new_height > page_height:
                    page_height = new_height
                
                # Adjust scroll speed occasionally
                if random.random() < 0.2:
                    scroll_speed = random.uniform(0.8, 1.2)
            
            # Scroll back to top
            await self.page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.warning(f"Error in natural scrolling: {e}")
    
    async def _extract_structured_data(self) -> Dict[str, Any]:
        """Extract structured data from the page."""
        try:
            # Extract JSON-LD structured data
            structured_data = await self.page.evaluate("""
                () => {
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    const data = [];
                    scripts.forEach(script => {
                        try {
                            data.push(JSON.parse(script.textContent));
                        } catch (e) {}
                    });
                    return data;
                }
            """)
            
            # Extract microdata
            microdata = await self.page.evaluate("""
                () => {
                    const items = document.querySelectorAll('[itemtype]');
                    const data = [];
                    items.forEach(item => {
                        const itemData = {
                            type: item.getAttribute('itemtype'),
                            properties: {}
                        };
                        
                        const props = item.querySelectorAll('[itemprop]');
                        props.forEach(prop => {
                            const name = prop.getAttribute('itemprop');
                            const value = prop.textContent || prop.getAttribute('content');
                            if (name && value) {
                                itemData.properties[name] = value;
                            }
                        });
                        
                        if (Object.keys(itemData.properties).length > 0) {
                            data.push(itemData);
                        }
                    });
                    return data;
                }
            """)
            
            return {
                'json_ld': structured_data,
                'microdata': microdata
            }
            
        except Exception as e:
            logger.warning(f"Error extracting structured data: {e}")
            return {}
    
    async def _extract_meta_data(self) -> Dict[str, Any]:
        """Extract meta data from the page."""
        try:
            meta_data = await self.page.evaluate("""
                () => {
                    const metas = document.querySelectorAll('meta');
                    const metaData = {};
                    metas.forEach(meta => {
                        const name = meta.getAttribute('name') || meta.getAttribute('property');
                        const content = meta.getAttribute('content');
                        if (name && content) {
                            metaData[name] = content;
                        }
                    });
                    return metaData;
                }
            """)
            
            return meta_data
            
        except Exception as e:
            logger.warning(f"Error extracting meta data: {e}")
            return {}
    
    async def _take_page_screenshot(self) -> str:
        """Take a screenshot of the current page."""
        try:
            timestamp = int(time.time())
            filename = f"screenshot_{timestamp}.png"
            
            # Use workspace manager if available
            try:
                from main import get_workspace_manager
                workspace_manager = get_workspace_manager(self.task_id) if hasattr(self, 'task_id') else None
                if workspace_manager:
                    screenshot_path = workspace_manager.get_screenshot_path(filename)
                else:
                    screenshot_path = filename
            except:
                screenshot_path = filename
            
            await self.page.screenshot(path=screenshot_path)
            return screenshot_path
        except Exception as e:
            logger.warning(f"Error taking screenshot: {e}")
            return ""
    
    async def _save_extracted_data(self, extracted_data: Dict[str, Any], link_info: Dict[str, Any], task_id: str = None) -> str:
        """Save extracted data to a file."""
        try:
            # Create filename based on link info
            link_text = link_info.get('text', 'unknown').replace(' ', '_')[:30]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"extracted_data_{link_text}_{timestamp}.json"
            
            # Prepare data for saving
            save_data = {
                'link_info': link_info,
                'extracted_data': extracted_data,
                'task_id': task_id,
                'saved_at': datetime.now().isoformat()
            }
            
            # Use workspace manager if available
            try:
                from main import get_workspace_manager
                workspace_manager = get_workspace_manager(task_id) if task_id else None
                if workspace_manager:
                    file_path = workspace_manager.save_json(save_data, filename, "outputs")
                else:
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(save_data, f, indent=2, ensure_ascii=False)
                    file_path = filename
            except:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, indent=2, ensure_ascii=False)
                file_path = filename
            
            await self._write_progress_to_file(task_id, "data_saved", {
                "filename": file_path,
                "data_size": len(json.dumps(save_data))
            })
            
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving extracted data: {e}")
            await self._write_progress_to_file(task_id, "data_save_error", {"error": str(e)})
            return ""

# Global instance with environment variable configuration
web_research = WebResearch(
    headless=BROWSER_HEADLESS,
    show_progress=WEB_RESEARCH_SHOW_PROGRESS,
    slow_mo=BROWSER_SLOW_MO
)

def get_web_research_tools() -> List[Dict]:
    """Get web research tools for the agent."""
    return [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Perform a web search using DuckDuckGo",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of results to return (default: 10)"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_and_extract",
                "description": "Search for content and extract it from multiple pages",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "max_pages": {
                            "type": "integer",
                            "description": "Maximum number of pages to extract from (default: 3)"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "navigate_to",
                "description": "Navigate to a URL with human-like behavior",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to navigate to"
                        }
                    },
                    "required": ["url"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "extract_content",
                "description": "Extract content from the current page",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selectors": {
                            "type": "object",
                            "description": "CSS selectors for different content types"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "click_link_and_extract",
                "description": "Click a link and extract data with human-like behavior including natural scrolling, mouse movement, and data extraction",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "link_selector": {
                            "type": "string",
                            "description": "CSS selector for the link to click"
                        },
                        "link_text": {
                            "type": "string",
                            "description": "Text content of the link to find and click"
                        },
                        "link_url": {
                            "type": "string",
                            "description": "URL pattern to match for the link"
                        },
                        "scroll_behavior": {
                            "type": "string",
                            "description": "Scroll behavior: 'human' (natural human-like), 'smooth', 'instant', or 'none'",
                            "enum": ["human", "smooth", "instant", "none"],
                            "default": "human"
                        },
                        "extract_data": {
                            "type": "boolean",
                            "description": "Whether to extract content after clicking the link",
                            "default": True
                        },
                        "save_data": {
                            "type": "boolean",
                            "description": "Whether to save extracted data to a file",
                            "default": True
                        }
                    },
                    "required": []
                }
            }
        }
    ] 