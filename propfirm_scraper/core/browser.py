"""
Browser management using Playwright
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)

class BrowserManager:
    """Manage Playwright browser instances"""
    
    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        
    async def start(self):
        """Start the browser"""
        try:
            self.playwright = await async_playwright().start()
            
            # Launch browser with options
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-extensions',
                ]
            )
            
            # Create context with realistic settings
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # Set default timeout
            self.context.set_default_timeout(self.timeout)
            
            logger.info("Browser started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise
    
    async def new_page(self) -> Page:
        """Create a new page"""
        if not self.context:
            await self.start()
        
        page = await self.context.new_page()
        
        # Set up page with anti-detection measures
        await page.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Mock chrome property
            window.chrome = {
                runtime: {},
            };
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        return page
    
    async def load_page(self, url: str, page: Optional[Page] = None) -> Page:
        """Load a page with the given URL"""
        if page is None:
            page = await self.new_page()
        
        try:
            logger.info(f"Loading page: {url}")
            
            # Navigate to the page
            response = await page.goto(url, wait_until='domcontentloaded')
            
            if response and response.status >= 400:
                logger.warning(f"Page loaded with status {response.status}: {url}")
            
            # Wait for page to be ready
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            logger.info(f"Page loaded successfully: {url}")
            return page
            
        except Exception as e:
            logger.error(f"Failed to load page {url}: {e}")
            raise
    
    async def detect_login_page(self, page: Page) -> bool:
        """Detect if the current page requires login"""
        try:
            # Get page content first
            content = await page.content()
            title = await page.title()
            url = page.url
            
            # Skip login detection for known support/help sites
            help_domains = [
                'support.apextraderfunding.com',
                'support.lucidtrading.com', 
                'help.tradeify.co',
                'help.myfundedfutures.com',
                'helpfutures.fundednext.com',
                'help.alpha-futures.com',
                'intercom.help',
                'help.blueguardianfutures.com',
                'support.thetradingpit.com',
                'knowledge.thelegendstrading.com',
                'helpfutures.e8markets.com',
                'zendesk.com'
            ]
            
            # Check if this is a known help/support domain
            for domain in help_domains:
                if domain in url:
                    logger.info(f"Skipping login detection for help/support domain: {domain}")
                    return False
            
            # More specific login indicators (avoid false positives)
            strict_login_indicators = [
                'form[action*="login"]',
                'form[action*="signin"]',
                '.login-form',
                '.signin-form',
                'input[name="username"]',
                'input[name="email"][type="email"] + input[type="password"]'  # Email + password combo
            ]
            
            # Check for strict login indicators
            for selector in strict_login_indicators:
                try:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        logger.warning(f"Login required - found: {selector}")
                        return True
                except:
                    continue
            
            # Check for login-specific page titles (more restrictive)
            login_title_keywords = ['login', 'sign in', 'authenticate']
            
            # Only flag as login if title is PRIMARILY about login
            title_lower = title.lower()
            if any(keyword == title_lower.strip() or title_lower.startswith(keyword + ' ') for keyword in login_title_keywords):
                logger.warning(f"Login required - login-specific title: {title}")
                return True
            
            # Check for login-specific URLs (more restrictive)
            login_url_patterns = ['/login', '/signin', '/auth/login', '/authentication']
            
            if any(pattern in url.lower() for pattern in login_url_patterns):
                logger.warning(f"Login required - login URL pattern: {url}")
                return True
            
            # Check for "access denied" or "unauthorized" messages
            content_lower = content.lower()
            access_denied_keywords = [
                'access denied',
                'unauthorized',
                'please log in',
                'you must be logged in',
                'authentication required'
            ]
            
            if any(keyword in content_lower for keyword in access_denied_keywords):
                logger.warning(f"Login required - access denied message found")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting login page: {e}")
            return False
    
    async def expand_accordions(self, page: Page):
        """Expand all accordion/collapsible elements on the page"""
        try:
            # Common accordion selectors
            accordion_selectors = [
                '[data-toggle="collapse"]',
                '.accordion-button',
                '.collapsible-header',
                '.expand-button',
                '.toggle-button',
                '[aria-expanded="false"]',
                'details summary',
            ]
            
            expanded_count = 0
            
            for selector in accordion_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        try:
                            # Check if element is visible and clickable
                            if await element.is_visible():
                                await element.click()
                                expanded_count += 1
                                await page.wait_for_timeout(500)  # Small delay
                        except:
                            continue
                except:
                    continue
            
            if expanded_count > 0:
                logger.info(f"Expanded {expanded_count} accordion elements")
                await page.wait_for_timeout(2000)  # Wait for content to load
            
        except Exception as e:
            logger.error(f"Error expanding accordions: {e}")
    
    async def find_search_field(self, page: Page) -> Optional[str]:
        """Find search input field on the page"""
        try:
            search_selectors = [
                'input[type="search"]',
                'input[name*="search"]',
                'input[id*="search"]',
                'input[placeholder*="search"]',
                'input[placeholder*="Search"]',
                '.search-input',
                '.search-field',
                '#search',
                '[data-testid*="search"]',
            ]
            
            for selector in search_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        logger.info(f"Found search field: {selector}")
                        return selector
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding search field: {e}")
            return None
    
    async def search_content(self, page: Page, search_terms: list) -> bool:
        """Search for content using search field if available"""
        try:
            search_selector = await self.find_search_field(page)
            
            if not search_selector:
                logger.info("No search field found")
                return False
            
            for term in search_terms:
                try:
                    logger.info(f"Searching for: {term}")
                    
                    # Clear and type search term
                    await page.fill(search_selector, term)
                    await page.press(search_selector, 'Enter')
                    
                    # Wait for results
                    await page.wait_for_timeout(3000)
                    
                    # Check if we got useful results
                    content = await page.content()
                    if any(keyword in content.lower() for keyword in ['drawdown', 'profit', 'target', 'rules']):
                        logger.info(f"Found relevant content for search term: {term}")
                        return True
                    
                except Exception as e:
                    logger.warning(f"Search failed for term '{term}': {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error searching content: {e}")
            return False
    
    async def close(self):
        """Close the browser"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            logger.info("Browser closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()