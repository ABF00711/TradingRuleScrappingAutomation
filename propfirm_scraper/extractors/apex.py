"""
Apex Trader Funding extractor
"""
import re
import logging
from typing import List, Dict, Any, Optional
from playwright.async_api import Page

from .base_extractor import BaseExtractor
from ..config.enums import DrawdownType, PayoutFrequency, Platform, Broker
from ..core.utils import extract_number, extract_percentage, classify_drawdown_type
from ..core.currency_converter import converter

logger = logging.getLogger(__name__)

class ApexExtractor(BaseExtractor):
    """Extract trading rules from Apex Trader Funding website"""
    
    def __init__(self, site_config):
        super().__init__(site_config)
        self.account_sizes_data = {}
        self.evaluation_rules = {}
        self.funded_rules = {}
        self.payout_rules = {}
        self.fee_rules = {}
    
    async def get_account_sizes(self, page: Page) -> List[str]:
        """Extract all available account sizes from Apex website"""
        try:
            logger.info("Extracting account sizes from Apex")
            
            # Navigate to evaluation rules page
            eval_rules_url = "https://support.apextraderfunding.com/hc/en-us/articles/31519769997083-Evaluation-Rules"
            await page.goto(eval_rules_url)
            await page.wait_for_load_state('networkidle')
            
            # Look for account size information in tables or text
            account_sizes = []
            
            # Try to find account size table or list
            tables = await page.query_selector_all('table')
            
            for table in tables:
                # Look for account size columns
                headers = await table.query_selector_all('th')
                header_texts = []
                for header in headers:
                    text = await header.text_content()
                    if text:
                        header_texts.append(text.strip())
                
                # Check if this looks like an account size table
                if any('account' in h.lower() or 'size' in h.lower() or '$' in h for h in header_texts):
                    rows = await table.query_selector_all('tr')
                    
                    for row in rows[1:]:  # Skip header row
                        cells = await row.query_selector_all('td')
                        if cells:
                            first_cell_text = await cells[0].text_content()
                            if first_cell_text and '$' in first_cell_text:
                                # Clean and extract account size
                                size = first_cell_text.strip()
                                if size not in account_sizes:
                                    account_sizes.append(size)
            
            # If no table found, look for account sizes in text content
            if not account_sizes:
                content = await page.content()
                
                # Common account size patterns
                size_patterns = [
                    r'\$25,?000',
                    r'\$50,?000', 
                    r'\$75,?000',
                    r'\$100,?000',
                    r'\$150,?000',
                    r'\$250,?000',
                    r'\$300,?000'
                ]
                
                for pattern in size_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        if match not in account_sizes:
                            account_sizes.append(match)
            
            # Default account sizes if none found
            if not account_sizes:
                account_sizes = [
                    "$25,000", "$50,000", "$75,000", "$100,000", 
                    "$150,000", "$250,000", "$300,000"
                ]
                logger.warning("No account sizes found, using default list")
            
            # Store account sizes data for later use
            await self._extract_account_size_details(page, account_sizes)
            
            logger.info(f"Found {len(account_sizes)} account sizes: {account_sizes}")
            return account_sizes
            
        except Exception as e:
            logger.error(f"Error extracting account sizes: {e}")
            # Return default sizes as fallback
            return ["$25,000", "$50,000", "$100,000", "$150,000", "$250,000"]
    
    async def _extract_account_size_details(self, page: Page, account_sizes: List[str]):
        """Extract detailed rules for each account size"""
        try:
            # Parse the current page content for account size details
            soup = await self.parse_html_content(page)
            
            # Look for tables with account size information
            tables = soup.find_all('table')
            
            for table in tables:
                headers = [th.get_text().strip() for th in table.find_all('th')]
                
                # Check if this is an account size details table
                if any('account' in h.lower() or 'size' in h.lower() for h in headers):
                    rows = table.find_all('tr')[1:]  # Skip header
                    
                    for row in rows:
                        cells = [td.get_text().strip() for td in row.find_all('td')]
                        
                        if cells and '$' in cells[0]:
                            account_size = cells[0]
                            
                            # Extract details from table columns
                            details = {}
                            for i, header in enumerate(headers):
                                if i < len(cells):
                                    details[header.lower()] = cells[i]
                            
                            self.account_sizes_data[account_size] = details
            
        except Exception as e:
            logger.error(f"Error extracting account size details: {e}")
    
    async def extract_evaluation_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract evaluation phase rules for a specific account size"""
        try:
            logger.info(f"Extracting evaluation rules for {account_size}")
            
            # Navigate to evaluation rules if not already there
            current_url = page.url
            if 'evaluation-rules' not in current_url.lower():
                eval_rules_url = "https://support.apextraderfunding.com/hc/en-us/articles/31519769997083-Evaluation-Rules"
                await page.goto(eval_rules_url)
                await page.wait_for_load_state('networkidle')
            
            # Parse content
            soup = await self.parse_html_content(page)
            content_text = soup.get_text().lower()
            
            rules = {}
            
            # Extract profit target (typically 6-8% of account size)
            account_value = converter.parse_and_convert(account_size)
            if account_value:
                # Look for profit target percentage in content
                profit_target_patterns = [
                    r'profit target.*?(\d+(?:\.\d+)?)\s*%',
                    r'(\d+(?:\.\d+)?)\s*%.*?profit target',
                    r'target.*?(\d+(?:\.\d+)?)\s*%'
                ]
                
                profit_target_percent = None
                for pattern in profit_target_patterns:
                    matches = re.findall(pattern, content_text)
                    if matches:
                        profit_target_percent = float(matches[0])
                        break
                
                # Default to 8% if not found
                if not profit_target_percent:
                    profit_target_percent = 8.0
                
                rules['target_usd'] = account_value * (profit_target_percent / 100)
            
            # Extract drawdown information
            if account_size in self.account_sizes_data:
                size_data = self.account_sizes_data[account_size]
                
                # Look for max loss/drawdown in the account size data
                for key, value in size_data.items():
                    if 'loss' in key or 'drawdown' in key or 'threshold' in key:
                        drawdown_amount = converter.parse_and_convert(value)
                        if drawdown_amount:
                            rules['max_drawdown_usd'] = drawdown_amount
                            break
            
            # If no specific drawdown found, extract from general content
            if 'max_drawdown_usd' not in rules:
                # Look for drawdown patterns in content
                drawdown_patterns = [
                    rf'{re.escape(account_size)}.*?\$([0-9,]+).*?(?:loss|drawdown)',
                    rf'(?:loss|drawdown).*?\$([0-9,]+).*?{re.escape(account_size)}'
                ]
                
                for pattern in drawdown_patterns:
                    matches = re.findall(pattern, content_text)
                    if matches:
                        drawdown_amount = converter.parse_and_convert(f"${matches[0]}")
                        if drawdown_amount:
                            rules['max_drawdown_usd'] = drawdown_amount
                            break
            
            # Determine drawdown type (trailing vs static)
            if 'static' in content_text:
                rules['drawdown_type'] = DrawdownType.STATIC
            else:
                rules['drawdown_type'] = DrawdownType.TRAILING
            
            # Extract minimum trading days (typically 7 for Apex)
            day_patterns = [
                r'(\d+)\s+(?:trading\s+)?days?.*?minimum',
                r'minimum.*?(\d+)\s+(?:trading\s+)?days?',
                r'at least\s+(\d+)\s+(?:trading\s+)?days?'
            ]
            
            min_days = None
            for pattern in day_patterns:
                matches = re.findall(pattern, content_text)
                if matches:
                    min_days = int(matches[0])
                    break
            
            rules['min_days'] = min_days or 7  # Default to 7 days
            
            # No daily loss limit for evaluation (only for funded accounts)
            rules['daily_loss_usd'] = None
            
            # No consistency rule for evaluation accounts
            rules['consistency'] = False
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting evaluation rules for {account_size}: {e}")
            return {}
    
    async def extract_funded_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract funded phase rules for a specific account size"""
        try:
            logger.info(f"Extracting funded rules for {account_size}")
            
            # Navigate to performance accounts section
            pa_url = "https://support.apextraderfunding.com/hc/en-us/articles/30306093336603-Apex-3-0-Payout-and-Trading-Rules"
            await page.goto(pa_url)
            await page.wait_for_load_state('networkidle')
            
            soup = await self.parse_html_content(page)
            content_text = soup.get_text().lower()
            
            rules = {}
            
            # Same drawdown as evaluation phase
            if account_size in self.account_sizes_data:
                size_data = self.account_sizes_data[account_size]
                for key, value in size_data.items():
                    if 'loss' in key or 'drawdown' in key or 'threshold' in key:
                        drawdown_amount = converter.parse_and_convert(value)
                        if drawdown_amount:
                            rules['max_drawdown_usd'] = drawdown_amount
                            break
            
            # Drawdown type (trailing for funded accounts)
            rules['drawdown_type'] = DrawdownType.TRAILING
            
            # Daily loss limit (30% rule)
            # This is complex - it's 30% of threshold amount or daily starting balance
            # For simplicity, we'll note this as a special rule
            rules['daily_loss_usd'] = None  # Special 30% rule applies
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting funded rules for {account_size}: {e}")
            return {}
    
    async def extract_payout_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract payout rules for a specific account size"""
        try:
            logger.info(f"Extracting payout rules for {account_size}")
            
            # Navigate to payout rules if not already there
            current_url = page.url
            if 'payout' not in current_url.lower():
                payout_url = "https://support.apextraderfunding.com/hc/en-us/articles/30306093336603-Apex-3-0-Payout-and-Trading-Rules"
                await page.goto(payout_url)
                await page.wait_for_load_state('networkidle')
            
            soup = await self.parse_html_content(page)
            content_text = soup.get_text().lower()
            
            rules = {}
            
            # Profit split (100% first $25K, then 90/10)
            # For simplicity, we'll use 90% as the main split
            rules['profit_split_percent'] = 90.0
            
            # Payout frequency (twice per month / on-demand)
            rules['payout_frequency'] = PayoutFrequency.BIWEEKLY
            
            # Minimum payout ($500)
            min_payout_patterns = [
                r'minimum.*?\$([0-9,]+)',
                r'\$([0-9,]+).*?minimum'
            ]
            
            min_payout = None
            for pattern in min_payout_patterns:
                matches = re.findall(pattern, content_text)
                if matches:
                    min_payout = converter.parse_and_convert(f"${matches[0]}")
                    break
            
            rules['min_payout_usd'] = min_payout or 500.0  # Default to $500
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting payout rules for {account_size}: {e}")
            return {}
    
    async def extract_fee_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract fee rules for a specific account size"""
        try:
            logger.info(f"Extracting fee rules for {account_size}")
            
            # Navigate to billing section
            billing_url = "https://support.apextraderfunding.com/hc/en-us/sections/31319717565851-Everything-Billing-Subscriptions-Cancellations-Resets"
            await page.goto(billing_url)
            await page.wait_for_load_state('networkidle')
            
            # Look for fee information
            soup = await self.parse_html_content(page)
            content_text = soup.get_text().lower()
            
            rules = {}
            
            # Account size to fee mapping (approximate based on analysis)
            fee_mapping = {
                "$25,000": 147,
                "$50,000": 247,
                "$75,000": 347,
                "$100,000": 397,
                "$150,000": 497,
                "$250,000": 597,
                "$300,000": 677
            }
            
            # Get evaluation fee for this account size
            rules['evaluation_fee_usd'] = fee_mapping.get(account_size, 397)  # Default to $397
            
            # Reset fees (from analysis: $80 Rithmic, $100 Tradovate)
            # We'll use average
            rules['reset_fee_usd'] = 90.0
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting fee rules for {account_size}: {e}")
            return {}
    
    async def extract_broker_platform(self, page: Page) -> Dict[str, Any]:
        """Extract broker and platform information"""
        try:
            # Apex uses Rithmic and Tradovate
            return {
                'broker': Broker.RITHMIC,  # Primary broker
                'platform': Platform.MULTIPLE  # Supports multiple platforms
            }
            
        except Exception as e:
            logger.error(f"Error extracting broker/platform info: {e}")
            return {'broker': None, 'platform': None}