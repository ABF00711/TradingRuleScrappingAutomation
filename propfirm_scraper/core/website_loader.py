"""
Website Loader - Implements HTTP → Browser → Chatbot fallback chain
"""
import asyncio
import logging
import requests
from typing import Dict, Any, Optional, List
from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

class WebsiteLoader:
    """Loads website content using multiple methods with fallback chain"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        # Common chatbot selectors
        self.chatbot_selectors = [
            '[class*="chat"]',
            '[id*="chat"]',
            '[class*="intercom"]',
            '[id*="intercom"]',
            '[class*="zendesk"]',
            '[class*="helpdesk"]',
            '[class*="support"]',
            'iframe[src*="chat"]',
            'iframe[src*="intercom"]',
            'iframe[src*="zendesk"]'
        ]
        
        # Common search field selectors
        self.search_selectors = [
            'input[type="search"]',
            'input[placeholder*="search"]',
            'input[placeholder*="Search"]',
            '[class*="search"] input',
            '[id*="search"] input',
            '.search-input',
            '#search-input'
        ]
    
    async def load_with_http(self, url: str) -> Optional[str]:
        """Try to load website content with HTTP request"""
        try:
            logger.info(f"Attempting HTTP request to {url}")
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Check if content looks useful (not just a redirect or error page)
            if len(response.text) < 1000:
                logger.warning(f"HTTP response too short ({len(response.text)} chars)")
                return None
            
            # Check for common indicators that we need JavaScript
            if any(indicator in response.text.lower() for indicator in [
                'javascript is required',
                'please enable javascript',
                'noscript',
                'loading...',
                'redirecting...'
            ]):
                logger.info("HTTP content indicates JavaScript required")
                return None
            
            logger.info(f"HTTP request successful ({len(response.text)} chars)")
            return response.text
            
        except Exception as e:
            logger.warning(f"HTTP request failed: {e}")
            return None
    
    async def load_with_browser(self, url: str) -> Optional[Dict[str, Any]]:
        """Load website content using browser automation"""
        try:
            logger.info(f"Attempting browser automation for {url}")
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                try:
                    # Navigate to page
                    await page.goto(url, timeout=30000)
                    await page.wait_for_load_state('networkidle', timeout=10000)
                    
                    # Check for login requirements
                    if await self.detect_login_required(page):
                        logger.warning("Login required, skipping browser extraction")
                        return None
                    
                    # Expand common accordions/dropdowns
                    await self.expand_content(page)
                    
                    # Get content from main page
                    html_content = await page.content()
                    page_text = await page.evaluate('document.body.innerText')
                    
                    # Look for additional pages with trading rules
                    additional_urls = await self.find_trading_rule_pages(page)
                    
                    # Visit and extract from additional pages
                    additional_content = []
                    if additional_urls:
                        logger.info(f"Visiting {len(additional_urls)} additional pages for better data")
                        
                        for additional_url in additional_urls[:3]:  # Limit to top 3 to avoid too much time
                            try:
                                await page.goto(additional_url, timeout=15000)
                                await page.wait_for_load_state('networkidle', timeout=5000)
                                
                                # Expand content on this page too
                                await self.expand_content(page)
                                
                                add_html = await page.content()
                                add_text = await page.evaluate('document.body.innerText')
                                
                                additional_content.append({
                                    'url': additional_url,
                                    'html': add_html,
                                    'text': add_text
                                })
                                
                                logger.debug(f"Extracted content from: {additional_url}")
                                
                            except Exception as e:
                                logger.debug(f"Failed to load additional page {additional_url}: {e}")
                                continue
                    
                    browser_data = {
                        'html': html_content,
                        'text': page_text,
                        'additional_urls': additional_urls,
                        'additional_content': additional_content,
                        'url': url
                    }
                    
                    logger.info(f"Browser automation successful ({len(html_content)} chars)")
                    return browser_data
                    
                finally:
                    await browser.close()
                    
        except Exception as e:
            logger.warning(f"Browser automation failed: {e}")
            return None
    
    async def try_chatbot_extraction(self, url: str) -> Optional[Dict[str, Any]]:
        """Try to extract data using chatbot if available"""
        try:
            logger.info(f"Attempting chatbot extraction for {url}")
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                try:
                    await page.goto(url, timeout=30000)
                    await page.wait_for_load_state('networkidle', timeout=10000)
                    
                    # Look for chatbot
                    chatbot_found = await self.find_chatbot(page)
                    
                    if not chatbot_found:
                        # Try search functionality instead
                        search_results = await self.try_search_functionality(page)
                        if search_results:
                            return {'responses': search_results, 'method': 'search'}
                        return None
                    
                    # Try to interact with chatbot
                    responses = await self.interact_with_chatbot(page)
                    
                    if responses:
                        return {'responses': responses, 'method': 'chatbot'}
                    
                    return None
                    
                finally:
                    await browser.close()
                    
        except Exception as e:
            logger.warning(f"Chatbot extraction failed: {e}")
            return None
    
    async def detect_login_required(self, page: Page) -> bool:
        """Detect if login is required"""
        try:
            # Check for common login indicators
            login_indicators = [
                'input[type="password"]',
                'form[action*="login"]',
                'form[action*="signin"]',
                '.login-form',
                '.signin-form'
            ]
            
            for selector in login_indicators:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
                    return True
            
            # Check page title and content
            title = await page.title()
            content = await page.evaluate('document.body.innerText')
            
            login_keywords = ['login', 'sign in', 'authentication required']
            
            if any(keyword in title.lower() for keyword in login_keywords):
                return True
            
            if any(keyword in content.lower() for keyword in login_keywords):
                return True
            
            return False
            
        except Exception:
            return False
    
    async def expand_content(self, page: Page):
        """Expand accordions, dropdowns, and other collapsible content"""
        try:
            # Common selectors for expandable content
            expandable_selectors = [
                '[class*="accordion"]',
                '[class*="collapse"]',
                '[class*="dropdown"]',
                '[class*="expand"]',
                'details',
                '[aria-expanded="false"]'
            ]
            
            for selector in expandable_selectors:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    try:
                        if await element.is_visible():
                            await element.click()
                            await asyncio.sleep(0.5)  # Wait for animation
                    except:
                        continue
                        
        except Exception as e:
            logger.debug(f"Error expanding content: {e}")
    
    async def find_trading_rule_pages(self, page: Page) -> List[str]:
        """Smart discovery of pages that contain trading rules"""
        try:
            base_url = page.url
            parsed_base = urlparse(base_url)
            
            # High-priority keywords that strongly indicate trading rule pages
            high_priority_keywords = [
                'pricing', 'price', 'cost', 'fee', 'plan', 'package',
                'challenge', 'evaluation', 'account', 'size', 'rule',
                'funded', 'profit', 'target', 'drawdown', 'risk'
            ]
            
            # Medium-priority keywords
            medium_priority_keywords = [
                'faq', 'help', 'support', 'guide', 'how', 'what',
                'trading', 'trader', 'fund', 'capital', 'balance'
            ]
            
            # URL path patterns that often contain trading rules
            url_patterns = [
                r'/pricing', r'/price', r'/cost', r'/fee', r'/plan',
                r'/challenge', r'/evaluation', r'/account', r'/rule',
                r'/funded', r'/profit', r'/target', r'/drawdown',
                r'/faq', r'/help', r'/guide', r'/support'
            ]
            
            links = await page.query_selector_all('a[href]')
            rule_urls = []
            
            for link in links:
                href = await link.get_attribute('href')
                text = await link.text_content()
                
                if not href or not text:
                    continue
                
                # Convert relative URLs to absolute
                full_url = urljoin(base_url, href)
                parsed_url = urlparse(full_url)
                
                # Skip external domains
                if parsed_url.netloc and parsed_url.netloc != parsed_base.netloc:
                    continue
                
                # Calculate relevance score
                score = 0
                text_lower = text.lower()
                url_lower = full_url.lower()
                
                # High priority text matches
                for keyword in high_priority_keywords:
                    if keyword in text_lower:
                        score += 10
                    if keyword in url_lower:
                        score += 8
                
                # Medium priority text matches
                for keyword in medium_priority_keywords:
                    if keyword in text_lower:
                        score += 3
                    if keyword in url_lower:
                        score += 2
                
                # URL pattern matches
                for pattern in url_patterns:
                    if re.search(pattern, url_lower):
                        score += 15
                
                # Boost score for specific page types
                if any(term in url_lower for term in ['pricing', 'challenge', 'evaluation', 'account']):
                    score += 20
                
                # Add to list if score is high enough
                if score >= 5:
                    rule_urls.append((full_url, score, text.strip()))
            
            # Sort by score (highest first) and return top URLs
            rule_urls.sort(key=lambda x: x[1], reverse=True)
            
            # Return top 8 URLs (increased from 5)
            top_urls = [url[0] for url in rule_urls[:8]]
            
            # Log discovered URLs for debugging
            if top_urls:
                logger.info(f"Discovered {len(top_urls)} potential trading rule pages")
                for i, (url, score, text) in enumerate(rule_urls[:8]):
                    logger.debug(f"  {i+1}. Score {score}: {text[:50]}... -> {url}")
            
            return top_urls
            
        except Exception as e:
            logger.debug(f"Error finding trading rule pages: {e}")
            return []
    
    async def find_chatbot(self, page: Page) -> bool:
        """Find chatbot on the page"""
        try:
            for selector in self.chatbot_selectors:
                element = await page.query_selector(selector)
                if element:
                    # Check if it's visible or can be made visible
                    if await element.is_visible():
                        return True
                    
                    # Try to click to open chatbot
                    try:
                        await element.click()
                        await asyncio.sleep(2)
                        return True
                    except:
                        continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error finding chatbot: {e}")
            return False
    
    async def interact_with_chatbot(self, page: Page) -> List[str]:
        """Interact with chatbot to get trading rule information"""
        try:
            responses = []
            
            # Comprehensive and specific questions about trading rules
            questions = [
                # Account sizes and pricing
                "What account sizes do you offer?",
                "What are your challenge account options?", 
                "How much do your evaluation accounts cost?",
                "What are your pricing plans?",
                
                # Profit targets
                "What is the profit target for evaluation?",
                "How much profit do I need to make in phase 1?",
                "What percentage profit target is required?",
                
                # Drawdown rules
                "What is the maximum drawdown allowed?",
                "What are your drawdown rules?",
                "Is the drawdown trailing or static?",
                "What is the daily loss limit?",
                
                # Profit splits and payouts
                "What is the profit split percentage?",
                "How much of the profits do I keep?",
                "What are your payout terms?",
                "How often can I request withdrawals?",
                
                # Fees and costs
                "What are your fees?",
                "Is there a monthly fee?",
                "What does the evaluation cost?",
                "Are there any reset fees?"
            ]
            
            # Look for chat input field
            chat_input = None
            input_selectors = [
                'input[placeholder*="message"]',
                'input[placeholder*="Message"]',
                'textarea[placeholder*="message"]',
                '.chat-input input',
                '.message-input',
                '[class*="chat"] input[type="text"]'
            ]
            
            for selector in input_selectors:
                chat_input = await page.query_selector(selector)
                if chat_input and await chat_input.is_visible():
                    break
            
            if not chat_input:
                return responses
            
            # Ask questions with smart timing and response collection
            for i, question in enumerate(questions):
                try:
                    logger.debug(f"Asking chatbot question {i+1}/{len(questions)}: {question}")
                    
                    await chat_input.fill(question)
                    await chat_input.press('Enter')
                    
                    # Wait for response with adaptive timing
                    await asyncio.sleep(2)  # Initial wait
                    
                    # Try to detect when response is complete
                    for attempt in range(3):
                        # Look for response text
                        response_selectors = [
                            '.chat-message',
                            '.message',
                            '[class*="chat"] [class*="response"]',
                            '[class*="bot"] [class*="message"]',
                            '[class*="assistant"] [class*="message"]',
                            '.bot-response',
                            '.ai-response'
                        ]
                        
                        current_responses = []
                        for selector in response_selectors:
                            elements = await page.query_selector_all(selector)
                            for element in elements[-5:]:  # Get last 5 messages
                                text = await element.text_content()
                                if text and len(text) > 15:  # Longer responses are more likely to be useful
                                    current_responses.append(text.strip())
                        
                        if current_responses:
                            # Add new responses
                            for response in current_responses:
                                if response not in responses:  # Avoid duplicates
                                    responses.append(response)
                            break
                        
                        await asyncio.sleep(1)  # Wait a bit more
                    
                    # Limit questions to avoid being blocked
                    if i >= 8:  # Stop after 8 questions to avoid overwhelming
                        break
                        
                except Exception as e:
                    logger.debug(f"Error asking question '{question}': {e}")
                    continue
            
            return responses
            
        except Exception as e:
            logger.debug(f"Error interacting with chatbot: {e}")
            return []
    
    async def try_search_functionality(self, page: Page) -> List[str]:
        """Try to use search functionality to find trading rule information"""
        try:
            responses = []
            
            # Find search input
            search_input = None
            for selector in self.search_selectors:
                search_input = await page.query_selector(selector)
                if search_input and await search_input.is_visible():
                    break
            
            if not search_input:
                return responses
            
            # Comprehensive search terms for trading rules
            search_terms = [
                # Account and pricing terms
                "account sizes",
                "challenge accounts", 
                "evaluation accounts",
                "pricing plans",
                "account options",
                
                # Rule-specific terms
                "profit target",
                "profit goal",
                "drawdown rules",
                "maximum drawdown",
                "daily loss limit",
                "evaluation rules",
                "trading rules",
                
                # Financial terms
                "profit split",
                "payout percentage", 
                "fees and costs",
                "evaluation fee",
                "monthly fee"
            ]
            
            for term in search_terms:
                try:
                    await search_input.fill(term)
                    await search_input.press('Enter')
                    
                    # Wait for results
                    await asyncio.sleep(2)
                    
                    # Get search results text
                    results = await page.evaluate('document.body.innerText')
                    if results and len(results) > 100:
                        responses.append(results[:1000])  # Limit response length
                    
                except Exception as e:
                    logger.debug(f"Error searching for '{term}': {e}")
                    continue
            
            return responses
            
        except Exception as e:
            logger.debug(f"Error using search functionality: {e}")
            return []