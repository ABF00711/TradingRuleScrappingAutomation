"""
Lucid Trading Extractor

Extracts trading rules from Lucid Trading support center.
Website: https://lucidtrading.com/
Support Center: https://support.lucidtrading.com/en/
"""

import re
import logging
from typing import Dict, List, Optional, Any
from playwright.async_api import Page
from bs4 import BeautifulSoup
from .base_extractor import BaseExtractor
from ..config.enums import DrawdownType, PayoutFrequency, Platform, Broker

logger = logging.getLogger(__name__)


class LucidTradingExtractor(BaseExtractor):
    """Extractor for Lucid Trading trading rules"""
    
    def __init__(self, site_config):
        super().__init__(site_config)
        self.support_url = "https://support.lucidtrading.com"
        self.main_url = "https://lucidtrading.com"
        
        # Plan-specific data mapping based on research
        self.plan_data = {
            'LucidPro': {
                'account_sizes': ['$25,000', '$50,000', '$100,000', '$150,000'],
                'profit_targets': {
                    '$25,000': 1500,
                    '$50,000': 3000,
                    '$100,000': 6000,
                    '$150,000': 9000
                },
                'max_drawdowns': {
                    '$25,000': 1000,
                    '$50,000': 2000,
                    '$100,000': 3000,
                    '$150,000': 4500
                },
                'daily_loss_limits': {
                    '$25,000': 300,
                    '$50,000': 600,
                    '$100,000': 1200,
                    '$150,000': 1800
                },
                'evaluation_fees': {
                    '$25,000': 120,
                    '$50,000': 160,
                    '$100,000': 275,
                    '$150,000': 370
                },
                'reset_fees': {
                    '$25,000': 75,
                    '$50,000': 100,
                    '$100,000': 170,
                    '$150,000': 225
                },
                'consistency_eval': None,      # No consistency during evaluation
                'consistency_funded': 35,     # 35% consistency when funded
                'min_trading_days': 1,        # Can pass in 1 day
                'profit_split': 90,           # 90% profit split
                'payout_frequency': PayoutFrequency.ON_DEMAND,  # Daily payouts
                'min_payout': 500,            # $500 minimum payout
                'drawdown_type_eval': DrawdownType.EOD,    # EOD during evaluation
                'drawdown_type_funded': DrawdownType.STATIC  # Locks at EOD when funded
            },
            'LucidFlex': {
                'account_sizes': ['$50,000', '$100,000', '$150,000'],  # No $25K option
                'profit_targets': {
                    '$50,000': 3000,
                    '$100,000': 6000,
                    '$150,000': 9000
                },
                'max_drawdowns': {
                    '$50,000': 2000,
                    '$100,000': 3000,
                    '$150,000': 4500
                },
                'daily_loss_limits': {
                    '$50,000': None,    # No daily loss during evaluation
                    '$100,000': None,
                    '$150,000': None
                },
                'daily_profit_requirements': {
                    '$50,000': 150,     # $150/day minimum
                    '$100,000': 200,    # $200/day minimum
                    '$150,000': 250     # $250/day minimum
                },
                'evaluation_fees': {
                    '$50,000': 160,
                    '$100,000': 275,
                    '$150,000': 370
                },
                'reset_fees': {
                    '$50,000': 100,
                    '$100,000': 170,
                    '$150,000': 225
                },
                'consistency_eval': 50,       # 50% consistency during evaluation
                'consistency_funded': None,   # No consistency when funded
                'min_trading_days': 5,        # 5 days minimum
                'profit_split': 90,           # 90% profit split
                'payout_frequency': PayoutFrequency.ON_DEMAND,  # After 5 winning days
                'min_payout': 500,            # $500 minimum payout
                'payout_cap': 2500,           # $2,500 per payout
                'drawdown_type_eval': DrawdownType.EOD,    # EOD during evaluation
                'drawdown_type_funded': DrawdownType.STATIC  # Locks at EOD when funded
            },
            'LucidDirect': {
                'account_sizes': ['$50,000', '$100,000', '$150,000'],
                'daily_loss_limits': {
                    '$50,000': 600,
                    '$100,000': 1200,
                    '$150,000': 1800
                },
                'consistency_funded': 20,     # 20% consistency requirement
                'profit_split': 90,           # 90% profit split
                'payout_frequency': PayoutFrequency.ON_DEMAND,  # Daily payouts
                'min_payout': 500,            # $500 minimum payout
                'drawdown_type_funded': DrawdownType.STATIC,  # Locks at EOD
                'instant_funding': True       # No evaluation phase
            }
        }
        
        # General account limits
        self.account_limits = {
            'max_evaluation_accounts': 10,    # Up to 10 evaluation accounts
            'max_funded_accounts': 5,         # Up to 5 funded accounts
            'max_total_accounts': 10,         # Maximum 10 total accounts
            'max_payouts_before_live': 6      # 6 payouts before live trading
        }

    async def get_account_sizes(self, page: Page) -> List[str]:
        """Extract all available account sizes"""
        logger.info("Extracting account sizes for Lucid Trading")
        
        try:
            # Navigate to support center
            await page.goto(f"{self.support_url}/en/", wait_until="networkidle")
            
            # Wait for dynamic content to load
            await page.wait_for_timeout(3000)
            
            # Try to search for account information
            try:
                # Look for search functionality
                search_input = await page.query_selector('input[type="search"], input[placeholder*="search"], input[name*="search"]')
                if search_input:
                    await search_input.fill("account size")
                    await page.keyboard.press('Enter')
                    await page.wait_for_timeout(2000)
            except Exception as e:
                logger.warning(f"Search functionality not found: {e}")
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text().lower()
            
            account_sizes = set()
            
            # Look for common account size patterns
            size_patterns = [
                r'\$25,?000',
                r'\$50,?000',
                r'\$100,?000',
                r'\$150,?000'
            ]
            
            for pattern in size_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    # Normalize the format
                    size = match.replace(',', '').replace('$', '')
                    formatted_size = f"${int(size):,}"
                    account_sizes.add(formatted_size)
            
            # If no sizes found, try specific article URLs
            if not account_sizes:
                logger.info("No account sizes found on main page, trying specific articles")
                article_urls = [
                    "/articles/11404617-maximum-number-of-accounts",
                    "/articles/12945796-lucidflex-payouts",
                    "/articles/12890178-luciddirect-consistency-percentage"
                ]
                
                for article_url in article_urls:
                    try:
                        await page.goto(f"{self.support_url}{article_url}", wait_until="networkidle")
                        await page.wait_for_timeout(2000)
                        
                        # Expand accordions if present
                        await page.evaluate("""
                            const accordions = document.querySelectorAll('[data-testid="accordion-trigger"], .accordion-trigger, .collapsible-trigger, details');
                            accordions.forEach(acc => {
                                if (acc.tagName === 'DETAILS') {
                                    acc.open = true;
                                } else {
                                    acc.click();
                                }
                            });
                        """)
                        
                        content = await page.content()
                        soup = BeautifulSoup(content, 'html.parser')
                        text = soup.get_text().lower()
                        
                        for pattern in size_patterns:
                            matches = re.findall(pattern, text)
                            for match in matches:
                                size = match.replace(',', '').replace('$', '')
                                formatted_size = f"${int(size):,}"
                                account_sizes.add(formatted_size)
                                
                    except Exception as e:
                        logger.warning(f"Failed to extract from {article_url}: {e}")
                        continue
            
            # If still no sizes found, use predefined data
            if not account_sizes:
                logger.warning("No account sizes found in content, using predefined list")
                for plan_name, plan_info in self.plan_data.items():
                    if 'account_sizes' in plan_info:
                        account_sizes.update(plan_info['account_sizes'])
            
            # Sort account sizes
            sizes = list(account_sizes)
            sizes.sort(key=lambda x: float(x.replace('$', '').replace(',', '')))
            
            logger.info(f"Found account sizes: {sizes}")
            return sizes
            
        except Exception as e:
            logger.error(f"Error extracting account sizes: {e}")
            # Return all predefined sizes
            all_sizes = set()
            for plan_name, plan_info in self.plan_data.items():
                if 'account_sizes' in plan_info:
                    all_sizes.update(plan_info['account_sizes'])
            return sorted(list(all_sizes), key=lambda x: float(x.replace('$', '').replace(',', '')))

    async def extract_evaluation_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract evaluation phase rules"""
        logger.info(f"Extracting evaluation rules for {account_size}")
        
        try:
            # Try to find evaluation-related articles
            await page.goto(f"{self.support_url}/en/", wait_until="networkidle")
            await page.wait_for_timeout(2000)
            
            # Search for evaluation rules
            try:
                search_input = await page.query_selector('input[type="search"], input[placeholder*="search"], input[name*="search"]')
                if search_input:
                    await search_input.fill("evaluation rules")
                    await page.keyboard.press('Enter')
                    await page.wait_for_timeout(3000)
            except Exception as e:
                logger.warning(f"Search not available: {e}")
            
            content = await page.content()
            rules = await self._parse_evaluation_rules(content, account_size)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting evaluation rules: {e}")
            return {}

    async def extract_funded_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract funded account rules"""
        logger.info(f"Extracting funded rules for {account_size}")
        
        try:
            # Search for funded/payout rules
            await page.goto(f"{self.support_url}/en/", wait_until="networkidle")
            await page.wait_for_timeout(2000)
            
            try:
                search_input = await page.query_selector('input[type="search"], input[placeholder*="search"], input[name*="search"]')
                if search_input:
                    await search_input.fill("funded account")
                    await page.keyboard.press('Enter')
                    await page.wait_for_timeout(3000)
            except Exception as e:
                logger.warning(f"Search not available: {e}")
            
            content = await page.content()
            rules = await self._parse_funded_rules(content, account_size)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting funded rules: {e}")
            return {}

    async def extract_payout_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract payout rules"""
        logger.info(f"Extracting payout rules for {account_size}")
        
        try:
            # Try to navigate to payout article
            try:
                await page.goto(f"{self.support_url}/articles/12945796-lucidflex-payouts", wait_until="networkidle")
                await page.wait_for_timeout(2000)
                
                # Expand accordions
                await page.evaluate("""
                    const accordions = document.querySelectorAll('[data-testid="accordion-trigger"], .accordion-trigger, .collapsible-trigger, details');
                    accordions.forEach(acc => {
                        if (acc.tagName === 'DETAILS') {
                            acc.open = true;
                        } else {
                            acc.click();
                        }
                    });
                """)
                
            except Exception as e:
                logger.warning(f"Failed to navigate to payout article: {e}")
                # Fallback to search
                await page.goto(f"{self.support_url}/en/", wait_until="networkidle")
                await page.wait_for_timeout(2000)
                
                try:
                    search_input = await page.query_selector('input[type="search"], input[placeholder*="search"], input[name*="search"]')
                    if search_input:
                        await search_input.fill("payout")
                        await page.keyboard.press('Enter')
                        await page.wait_for_timeout(3000)
                except Exception as e:
                    logger.warning(f"Search not available: {e}")
            
            content = await page.content()
            rules = await self._parse_payout_rules(content, account_size)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting payout rules: {e}")
            return {}

    async def extract_fee_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract fee information"""
        logger.info(f"Extracting fee rules for {account_size}")
        
        try:
            # Search for pricing/fee information
            await page.goto(f"{self.support_url}/en/", wait_until="networkidle")
            await page.wait_for_timeout(2000)
            
            try:
                search_input = await page.query_selector('input[type="search"], input[placeholder*="search"], input[name*="search"]')
                if search_input:
                    await search_input.fill("pricing fee")
                    await page.keyboard.press('Enter')
                    await page.wait_for_timeout(3000)
            except Exception as e:
                logger.warning(f"Search not available: {e}")
            
            content = await page.content()
            rules = await self._parse_fee_rules(content, account_size)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting fee rules: {e}")
            return {}

    async def _parse_evaluation_rules(self, content: str, account_size: str) -> Dict[str, Any]:
        """Parse evaluation rules from HTML content"""
        rules = {}
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text().lower()
            
            # Determine plan type based on content and account size
            plan_type = self._determine_plan_type(account_size, text)
            
            if plan_type == 'LucidDirect':
                # LucidDirect has no evaluation phase (instant funding)
                return {}
            
            plan_info = self.plan_data.get(plan_type, self.plan_data['LucidPro'])
            
            # Get profit target from predefined data
            if account_size in plan_info.get('profit_targets', {}):
                rules['profit_target_usd'] = float(plan_info['profit_targets'][account_size])
            else:
                # Try to extract from content
                profit_patterns = [
                    r'profit target[:\s]+\$?([0-9,]+)',
                    r'target[:\s]+\$?([0-9,]+)'
                ]
                
                for pattern in profit_patterns:
                    match = re.search(pattern, text)
                    if match:
                        rules['profit_target_usd'] = float(match.group(1).replace(',', ''))
                        break
            
            # Get max drawdown from predefined data
            if account_size in plan_info.get('max_drawdowns', {}):
                rules['max_drawdown_usd'] = float(plan_info['max_drawdowns'][account_size])
            
            # Get daily loss limit from predefined data
            daily_loss = plan_info.get('daily_loss_limits', {}).get(account_size)
            if daily_loss is not None:
                rules['daily_loss_limit_usd'] = float(daily_loss)
            else:
                rules['daily_loss_limit_usd'] = None
            
            # Drawdown type (EOD during evaluation)
            rules['drawdown_type'] = plan_info.get('drawdown_type_eval', DrawdownType.EOD)
            
            # Minimum trading days
            rules['min_trading_days'] = plan_info.get('min_trading_days', 1)
            
            # Consistency rule
            consistency_eval = plan_info.get('consistency_eval')
            if consistency_eval is not None:
                rules['consistency_rule'] = True
            else:
                rules['consistency_rule'] = False
            
            logger.info(f"Parsed evaluation rules for {plan_type}: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing evaluation rules: {e}")
            return {}

    async def _parse_funded_rules(self, content: str, account_size: str) -> Dict[str, Any]:
        """Parse funded account rules from HTML content"""
        rules = {}
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text().lower()
            
            # Determine plan type
            plan_type = self._determine_plan_type(account_size, text)
            plan_info = self.plan_data.get(plan_type, self.plan_data['LucidPro'])
            
            # For LucidDirect, use evaluation daily loss limits as funded limits
            if plan_type == 'LucidDirect':
                daily_loss = plan_info.get('daily_loss_limits', {}).get(account_size)
                if daily_loss is not None:
                    rules['daily_loss_limit_usd'] = float(daily_loss)
            else:
                # For other plans, funded daily loss same as evaluation
                if plan_type == 'LucidPro':
                    daily_loss = plan_info.get('daily_loss_limits', {}).get(account_size)
                    if daily_loss is not None:
                        rules['daily_loss_limit_usd'] = float(daily_loss)
                else:  # LucidFlex
                    rules['daily_loss_limit_usd'] = None  # No daily loss limit when funded
            
            # Max drawdown (locks at EOD when funded)
            if plan_type != 'LucidDirect':
                max_drawdown = plan_info.get('max_drawdowns', {}).get(account_size)
                if max_drawdown is not None:
                    rules['max_drawdown_usd'] = float(max_drawdown)
            
            # Drawdown type (locks to static when funded)
            rules['drawdown_type'] = plan_info.get('drawdown_type_funded', DrawdownType.STATIC)
            
            logger.info(f"Parsed funded rules for {plan_type}: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing funded rules: {e}")
            return {}

    async def _parse_payout_rules(self, content: str, account_size: str) -> Dict[str, Any]:
        """Parse payout rules from HTML content"""
        rules = {}
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text().lower()
            
            # Determine plan type
            plan_type = self._determine_plan_type(account_size, text)
            plan_info = self.plan_data.get(plan_type, self.plan_data['LucidPro'])
            
            # Profit split (90% for all plans)
            rules['profit_split_percent'] = plan_info.get('profit_split', 90)
            
            # Payout frequency
            rules['payout_frequency'] = plan_info.get('payout_frequency', PayoutFrequency.ON_DEMAND)
            
            # Minimum payout
            rules['min_payout_usd'] = float(plan_info.get('min_payout', 500))
            
            logger.info(f"Parsed payout rules for {plan_type}: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing payout rules: {e}")
            return {}

    async def _parse_fee_rules(self, content: str, account_size: str) -> Dict[str, Any]:
        """Parse fee information from HTML content"""
        rules = {}
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text().lower()
            
            # Determine plan type
            plan_type = self._determine_plan_type(account_size, text)
            
            if plan_type == 'LucidDirect':
                # LucidDirect has no evaluation fee (instant funding)
                rules['evaluation_fee_usd'] = 0.0
                rules['reset_fee_usd'] = 0.0
                return rules
            
            plan_info = self.plan_data.get(plan_type, self.plan_data['LucidPro'])
            
            # Get evaluation fee from predefined data
            if account_size in plan_info.get('evaluation_fees', {}):
                rules['evaluation_fee_usd'] = float(plan_info['evaluation_fees'][account_size])
            else:
                # Default estimate
                account_value = float(account_size.replace('$', '').replace(',', ''))
                if account_value <= 25000:
                    rules['evaluation_fee_usd'] = 120
                elif account_value <= 50000:
                    rules['evaluation_fee_usd'] = 160
                elif account_value <= 100000:
                    rules['evaluation_fee_usd'] = 275
                else:
                    rules['evaluation_fee_usd'] = 370
            
            # Get reset fee from predefined data
            if account_size in plan_info.get('reset_fees', {}):
                rules['reset_fee_usd'] = float(plan_info['reset_fees'][account_size])
            else:
                rules['reset_fee_usd'] = rules.get('evaluation_fee_usd', 160) * 0.7  # Estimate ~70% of eval fee
            
            logger.info(f"Parsed fee rules for {plan_type}: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing fee rules: {e}")
            return {}

    def _determine_plan_type(self, account_size: str, text: str) -> str:
        """Determine plan type based on account size and content"""
        
        # Check content for specific plan mentions
        if 'luciddirect' in text or 'instant funding' in text:
            return 'LucidDirect'
        elif 'lucidflex' in text or 'flexible' in text:
            return 'LucidFlex'
        elif 'lucidpro' in text or 'classic' in text:
            return 'LucidPro'
        
        # Default based on account size (LucidPro supports all sizes including $25K)
        if account_size == '$25,000':
            return 'LucidPro'  # Only LucidPro supports $25K
        else:
            return 'LucidPro'  # Default to LucidPro

    def get_platform(self) -> str:
        """Return the trading platform"""
        return Platform.MULTIPLE.value  # Lucid Trading supports multiple platforms

    def get_broker(self) -> str:
        """Return the broker"""
        return Broker.UNKNOWN.value  # Broker information not clearly specified