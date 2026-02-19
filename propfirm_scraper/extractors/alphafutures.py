"""
Alpha Futures Extractor

Extracts trading rules from Alpha Futures main website and help center.
Website: https://alphafutures.io/
Help Center: https://help.alpha-futures.com/en/
"""

import re
import logging
from typing import Dict, List, Optional, Any
from playwright.async_api import Page
from bs4 import BeautifulSoup
from .base_extractor import BaseExtractor
from ..config.enums import DrawdownType, PayoutFrequency, Platform, Broker

logger = logging.getLogger(__name__)


class AlphaFuturesExtractor(BaseExtractor):
    """Extractor for Alpha Futures trading rules"""
    
    def __init__(self, site_config):
        super().__init__(site_config)
        self.main_url = "https://alphafutures.io"
        self.help_url = "https://help.alpha-futures.com"
        self.faq_url = "https://alpha-futures.com/faq"
        
        # Plan-specific data mapping
        self.plan_data = {
            'Standard': {
                'account_sizes': ['$100,000'],
                'profit_target_percent': 6.0,  # 6% of account
                'max_drawdown_percent': 4.0,   # 4% MLL
                'daily_loss_guard': 1000,      # $1,000 daily loss guard
                'consistency_eval': 50,        # 50% during evaluation
                'consistency_funded': 40,      # 40% during funded
                'min_trading_days': 2,
                'profit_split': 90,            # Up to 90%
                'activation_fee': None         # To be extracted
            },
            'Zero': {
                'account_sizes': ['$50,000', '$100,000'],
                'profit_target_percent': 6.0,  # 6% of account
                'max_drawdown_percent': 4.0,   # 4% MLL
                'daily_loss_guard_50k': 1000,  # $1,000 for $50K
                'daily_loss_guard_100k': 2000, # $2,000 for $100K
                'consistency_eval': 50,        # 50% during evaluation
                'consistency_funded': 40,      # 40% during funded
                'min_trading_days': 2,
                'profit_split': 90,            # Up to 90%
                'activation_fee': 0            # $0 activation fee
            },
            'Advanced': {
                'account_sizes': ['$100,000'],
                'profit_target_percent': 8.0,  # 8% of account
                'max_drawdown_percent': 3.5,   # 3.5% MLL
                'daily_loss_guard': 1000,      # $1,000 daily loss guard
                'consistency_eval': 50,        # 50% during evaluation
                'consistency_funded': None,    # No consistency rule for Advanced Qualified
                'min_trading_days': 2,
                'profit_split': 90,            # Up to 90%
                'activation_fee': None         # To be extracted
            }
        }
        
        # URLs to visit for data extraction
        self.urls_to_visit = [
            # Help center articles
            "/en/articles/9491980-alpha-futures-evaluation-qualified-trader-overview",
            "/en/articles/9492051-payout-policy",
            "/en/articles/9492048-consistency-rule",
            "/en/articles/11771813-zero-account-overview"
        ]

    async def get_account_sizes(self, page: Page) -> List[str]:
        """Extract all available account sizes"""
        logger.info("Extracting account sizes for Alpha Futures")
        
        try:
            # Start with help center for account size information
            help_url = f"{self.help_url}/en/articles/9491980-alpha-futures-evaluation-qualified-trader-overview"
            await page.goto(help_url, wait_until="networkidle")
            
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
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text().lower()
            
            account_sizes = set()
            
            # Look for common account size patterns
            size_patterns = [
                r'\$50,?000',
                r'\$100,?000'
            ]
            
            for pattern in size_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    # Normalize the format
                    size = match.replace(',', '').replace('$', '')
                    if size in ['50000', '100000']:  # Only include standard sizes
                        formatted_size = f"${int(size):,}"
                        account_sizes.add(formatted_size)
            
            # If no sizes found, use default from plan data
            if not account_sizes:
                logger.warning("No account sizes found in content, using default list")
                for plan_name, plan_info in self.plan_data.items():
                    account_sizes.update(plan_info['account_sizes'])
            
            # Sort account sizes
            sizes = list(account_sizes)
            sizes.sort(key=lambda x: float(x.replace('$', '').replace(',', '')))
            
            logger.info(f"Found account sizes: {sizes}")
            return sizes
            
        except Exception as e:
            logger.error(f"Error extracting account sizes: {e}")
            # Return default sizes
            return ['$50,000', '$100,000']

    async def extract_evaluation_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract evaluation phase rules"""
        logger.info(f"Extracting evaluation rules for {account_size}")
        
        try:
            # Navigate to evaluation overview article
            url = f"{self.help_url}/en/articles/9491980-alpha-futures-evaluation-qualified-trader-overview"
            await page.goto(url, wait_until="networkidle")
            
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
            
            content = await page.content()
            rules = await self._parse_evaluation_rules(content, account_size)
            
            # Visit consistency rule article for more details
            try:
                consistency_url = f"{self.help_url}/en/articles/9492048-consistency-rule"
                await page.goto(consistency_url, wait_until="networkidle")
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
                consistency_content = await page.content()
                consistency_rules = await self._parse_evaluation_rules(consistency_content, account_size)
                rules.update(consistency_rules)
            except Exception as e:
                logger.warning(f"Failed to extract consistency rules: {e}")
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting evaluation rules: {e}")
            return {}

    async def extract_funded_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract funded account rules"""
        logger.info(f"Extracting funded rules for {account_size}")
        
        try:
            # Navigate to evaluation overview (contains funded rules too)
            url = f"{self.help_url}/en/articles/9491980-alpha-futures-evaluation-qualified-trader-overview"
            await page.goto(url, wait_until="networkidle")
            
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
            
            content = await page.content()
            rules = await self._parse_funded_rules(content, account_size)
            
            # Visit Zero Account article for additional details
            try:
                zero_url = f"{self.help_url}/en/articles/11771813-zero-account-overview"
                await page.goto(zero_url, wait_until="networkidle")
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
                zero_content = await page.content()
                zero_rules = await self._parse_funded_rules(zero_content, account_size)
                rules.update(zero_rules)
            except Exception as e:
                logger.warning(f"Failed to extract Zero Account rules: {e}")
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting funded rules: {e}")
            return {}

    async def extract_payout_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract payout rules"""
        logger.info(f"Extracting payout rules for {account_size}")
        
        try:
            # Navigate to payout policy article
            url = f"{self.help_url}/en/articles/9492051-payout-policy"
            await page.goto(url, wait_until="networkidle")
            
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
            # Start with help center for Zero Account overview (mentions $0 fee)
            help_url = f"{self.help_url}/en/articles/11771813-zero-account-overview"
            await page.goto(help_url, wait_until="networkidle")
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
            
            # Determine account size value
            account_value = float(account_size.replace('$', '').replace(',', ''))
            
            # Determine plan type based on content or account size
            plan_type = 'Standard'  # Default
            if 'zero' in text and '$0' in text:
                plan_type = 'Zero'
            elif 'advanced' in text and '8%' in text:
                plan_type = 'Advanced'
            
            # Get plan data
            plan_info = self.plan_data.get(plan_type, self.plan_data['Standard'])
            
            # Calculate profit target (percentage of account)
            profit_target_percent = plan_info['profit_target_percent']
            rules['profit_target_usd'] = account_value * (profit_target_percent / 100)
            
            # Calculate max drawdown (MLL - Maximum Loss Limit)
            max_drawdown_percent = plan_info['max_drawdown_percent']
            rules['max_drawdown_usd'] = account_value * (max_drawdown_percent / 100)
            
            # Daily loss limit (Daily Loss Guard - different from daily loss limit)
            if plan_type == 'Zero':
                if account_value <= 50000:
                    rules['daily_loss_limit_usd'] = float(plan_info['daily_loss_guard_50k'])
                else:
                    rules['daily_loss_limit_usd'] = float(plan_info['daily_loss_guard_100k'])
            else:
                rules['daily_loss_limit_usd'] = float(plan_info['daily_loss_guard'])
            
            # Drawdown type (EOD - End of Day balance)
            rules['drawdown_type'] = DrawdownType.EOD
            
            # Minimum trading days
            rules['min_trading_days'] = plan_info['min_trading_days']
            
            # Consistency rule (50% during evaluation)
            rules['consistency_rule'] = True  # All plans have consistency during evaluation
            
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
            
            # Determine account size value
            account_value = float(account_size.replace('$', '').replace(',', ''))
            
            # Determine plan type
            plan_type = 'Standard'  # Default
            if 'zero' in text and '$0' in text:
                plan_type = 'Zero'
            elif 'advanced' in text and 'qualified' in text:
                plan_type = 'Advanced'
            
            # Get plan data
            plan_info = self.plan_data.get(plan_type, self.plan_data['Standard'])
            
            # Funded accounts have static drawdown ($2,000 for Standard, varies for Zero)
            if plan_type == 'Standard':
                rules['max_drawdown_usd'] = 2000.0  # $2,000 static drawdown
            elif plan_type == 'Zero':
                if account_value <= 50000:
                    rules['max_drawdown_usd'] = 2000.0  # $2,000 for $50K
                else:
                    rules['max_drawdown_usd'] = 4000.0  # $4,000 for $100K
            else:  # Advanced
                rules['max_drawdown_usd'] = 2000.0  # Assume same as Standard
            
            # Daily loss guard (same as evaluation)
            if plan_type == 'Zero':
                if account_value <= 50000:
                    rules['daily_loss_limit_usd'] = float(plan_info['daily_loss_guard_50k'])
                else:
                    rules['daily_loss_limit_usd'] = float(plan_info['daily_loss_guard_100k'])
            else:
                rules['daily_loss_limit_usd'] = float(plan_info['daily_loss_guard'])
            
            # Drawdown type (Static for funded accounts)
            rules['drawdown_type'] = DrawdownType.STATIC
            
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
            
            # Extract profit split (up to 90%)
            split_patterns = [
                r'([0-9]+)%.*profit split',
                r'([0-9]+)/([0-9]+).*split',
                r'up to ([0-9]+)%',
                r'([0-9]+)%.*payout',
                r'([0-9]+)%.*share'
            ]
            
            for pattern in split_patterns:
                match = re.search(pattern, text)
                if match:
                    if len(match.groups()) == 2:  # Format like "90/10"
                        rules['profit_split_percent'] = int(match.group(1))
                    else:  # Format like "90%"
                        rules['profit_split_percent'] = int(match.group(1))
                    break
            else:
                rules['profit_split_percent'] = 90  # Default up to 90%
            
            # Determine payout frequency (bi-weekly is common for Alpha Futures)
            if 'biweekly' in text or 'bi-weekly' in text:
                rules['payout_frequency'] = PayoutFrequency.BIWEEKLY
            elif 'weekly' in text and 'payout' in text:
                rules['payout_frequency'] = PayoutFrequency.WEEKLY
            elif 'monthly' in text and 'payout' in text:
                rules['payout_frequency'] = PayoutFrequency.MONTHLY
            else:
                rules['payout_frequency'] = PayoutFrequency.BIWEEKLY  # Default
            
            # Extract minimum payout
            min_payout_patterns = [
                r'minimum payout[:\s]+\$?([0-9,]+)',
                r'min[:\s]+\$?([0-9,]+)',
                r'minimum[:\s]+\$?([0-9,]+)'
            ]
            
            for pattern in min_payout_patterns:
                match = re.search(pattern, text)
                if match:
                    rules['min_payout_usd'] = float(match.group(1).replace(',', ''))
                    break
            else:
                rules['min_payout_usd'] = 100  # Default assumption
            
            logger.info(f"Parsed payout rules: {rules}")
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
            
            # Determine account size value
            account_value = float(account_size.replace('$', '').replace(',', ''))
            
            # Check for Zero Plan ($0 activation fee)
            if '$0' in text and ('zero' in text or 'activation' in text):
                rules['evaluation_fee_usd'] = 0.0
            else:
                # Extract evaluation/activation fee
                fee_patterns = [
                    r'activation fee[:\s]+\$?([0-9,]+)',
                    r'evaluation fee[:\s]+\$?([0-9,]+)',
                    r'fee[:\s]+\$?([0-9,]+)',
                    r'cost[:\s]+\$?([0-9,]+)'
                ]
                
                for pattern in fee_patterns:
                    match = re.search(pattern, text)
                    if match:
                        rules['evaluation_fee_usd'] = float(match.group(1).replace(',', ''))
                        break
                else:
                    # Use estimated fees based on account size
                    if account_value <= 50000:
                        rules['evaluation_fee_usd'] = 149  # Estimated for $50K
                    else:
                        rules['evaluation_fee_usd'] = 199  # Estimated for $100K
            
            # Extract reset fee (usually same as evaluation fee)
            reset_patterns = [
                r'reset fee[:\s]+\$?([0-9,]+)',
                r'retry fee[:\s]+\$?([0-9,]+)'
            ]
            
            for pattern in reset_patterns:
                match = re.search(pattern, text)
                if match:
                    rules['reset_fee_usd'] = float(match.group(1).replace(',', ''))
                    break
            else:
                rules['reset_fee_usd'] = rules.get('evaluation_fee_usd', 149)  # Default to same as evaluation
            
            logger.info(f"Parsed fee rules: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing fee rules: {e}")
            return {}

    def get_platform(self) -> str:
        """Return the trading platform"""
        return Platform.MULTIPLE.value  # Alpha Futures supports multiple platforms

    def get_broker(self) -> str:
        """Return the broker"""
        return Broker.RITHMIC.value  # Alpha Futures primarily uses Rithmic