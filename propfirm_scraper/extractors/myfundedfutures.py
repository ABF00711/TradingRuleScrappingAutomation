"""
My Funded Futures Extractor

Extracts trading rules from My Funded Futures help center and blog articles.
Website: https://help.myfundedfutures.com/en/
"""

import re
import logging
from typing import Dict, List, Optional, Any
from playwright.async_api import Page
from bs4 import BeautifulSoup
from .base_extractor import BaseExtractor
from ..config.enums import DrawdownType, PayoutFrequency, Platform, Broker

logger = logging.getLogger(__name__)


class MyFundedFuturesExtractor(BaseExtractor):
    """Extractor for My Funded Futures trading rules"""
    
    def __init__(self, site_config):
        super().__init__(site_config)
        self.help_url = "https://help.myfundedfutures.com"
        
        # Plan-specific data mapping
        self.plan_data = {
            'Core': {
                'account_sizes': ['$50,000'],
                'evaluation_fee': 77,
                'profit_target': 3000,
                'eod_drawdown': 2000,
                'daily_loss': None,
                'consistency': True,
                'profit_split': 80,
                'payout_frequency': PayoutFrequency.ON_DEMAND,  # Every 5 winning days
                'min_payout': 250,
                'payout_cap': 1000
            },
            'Scale': {
                'account_sizes': ['$50,000', '$100,000', '$150,000'],
                'evaluation_fee': 127,  # Base fee for $50K
                'profit_target': 3000,  # Base for $50K
                'eod_drawdown': 2000,   # Base for $50K
                'daily_loss': None,
                'consistency': True,
                'profit_split': 80,
                'payout_frequency': PayoutFrequency.WEEKLY,
                'min_payout': 250,
                'payout_cap': 1500  # Base cap for $50K
            },
            'Pro': {
                'account_sizes': ['$50,000', '$100,000', '$150,000'],
                'evaluation_fee': 227,  # Base fee for $50K
                'profit_target': 3000,  # Base for $50K
                'eod_drawdown': 2000,   # Base for $50K
                'daily_loss': None,
                'consistency': True,
                'profit_split': 80,
                'payout_frequency': PayoutFrequency.WEEKLY,
                'min_payout': 250,
                'payout_cap': 3500  # Higher cap
            },
            'Rapid': {
                'account_sizes': ['$50,000', '$100,000', '$150,000'],
                'evaluation_fee': None,  # Will extract from page
                'profit_target': 3000,  # Base for $50K
                'eod_drawdown': 2000,   # Base for $50K
                'daily_loss': None,
                'consistency': False,  # No consistency on funded
                'profit_split': 90,
                'payout_frequency': PayoutFrequency.ON_DEMAND,  # Daily payouts
                'min_payout': 500,
                'payout_cap': None  # No cap mentioned
            },
            'Starter': {
                'account_sizes': ['$50,000'],  # Only $50K available now
                'evaluation_fee': 97,
                'profit_target': 3000,
                'eod_drawdown': 2500,  # Maximum loss limit
                'daily_loss': 1200,
                'consistency': True,
                'profit_split': 80,
                'payout_frequency': PayoutFrequency.ON_DEMAND,
                'min_payout': 250,
                'payout_cap': 1000
            },
            'Milestone': {
                'account_sizes': ['$50,000', '$100,000', '$150,000'],
                'evaluation_fee': 445,  # Base fee for $50K
                'profit_target': 2000,  # Phase-based
                'eod_drawdown': 2000,   # Base for $50K
                'daily_loss': None,
                'consistency': True,  # 20% consistency rule
                'profit_split': 80,
                'payout_frequency': PayoutFrequency.ON_DEMAND,  # Phase payouts
                'min_payout': 250,
                'payout_cap': 3000  # Per phase
            }
        }
        
        # Account size multipliers for scaling
        self.size_multipliers = {
            '$50,000': 1.0,
            '$100,000': 2.0,
            '$150,000': 3.0
        }
        
        # URLs to visit for data extraction
        self.urls_to_visit = [
            "/collections/5808821-traders-evaluation",
            "/articles/11802636-traders-evaluation-simplified",
            "/articles/8528339-understanding-evaluation-parameters-at-mffu",
            "/collections/17350372-rapid-plan",
            "/articles/11802674-pro-plan-sim-funded-and-live-account-highlights",
            "/articles/11994562-consistency-rule-at-my-funded-futures-pro-rapid-plans",
            "/articles/12802721-intraday-drawdown-explained"
        ]

    async def get_account_sizes(self, page: Page) -> List[str]:
        """Extract all available account sizes across all plans"""
        logger.info("Extracting account sizes for My Funded Futures")
        
        all_sizes = set()
        for plan_name, plan_info in self.plan_data.items():
            all_sizes.update(plan_info['account_sizes'])
        
        # Sort account sizes
        sizes = list(all_sizes)
        sizes.sort(key=lambda x: float(x.replace('$', '').replace(',', '')))
        
        logger.info(f"Found account sizes: {sizes}")
        return sizes

    async def extract_evaluation_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract evaluation phase rules"""
        logger.info(f"Extracting evaluation rules for {account_size}")
        
        try:
            # Navigate to main evaluation collection
            url = f"{self.help_url}/collections/5808821-traders-evaluation"
            await page.goto(url, wait_until="networkidle")
            
            # Expand accordions to reveal content
            await page.evaluate("""
                const accordions = document.querySelectorAll('[data-testid="accordion-trigger"], .accordion-trigger, .collapsible-trigger');
                accordions.forEach(acc => acc.click());
            """)
            
            content = await page.content()
            
            # Parse evaluation rules from content
            rules = await self._parse_evaluation_rules(content, account_size)
            
            # Visit specific articles for more details
            for article_url in ["/articles/11802636-traders-evaluation-simplified",
                               "/articles/8528339-understanding-evaluation-parameters-at-mffu"]:
                try:
                    await page.goto(f"{self.help_url}{article_url}", wait_until="networkidle")
                    await page.evaluate("""
                        const accordions = document.querySelectorAll('[data-testid="accordion-trigger"], .accordion-trigger, .collapsible-trigger');
                        accordions.forEach(acc => acc.click());
                    """)
                    article_content = await page.content()
                    additional_rules = await self._parse_evaluation_rules(article_content, account_size)
                    rules.update(additional_rules)
                except Exception as e:
                    logger.warning(f"Failed to extract from {article_url}: {e}")
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting evaluation rules: {e}")
            return {}

    async def extract_funded_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract funded account rules"""
        logger.info(f"Extracting funded rules for {account_size}")
        
        try:
            # Navigate to Pro Plan article for funded account details
            url = f"{self.help_url}/articles/11802674-pro-plan-sim-funded-and-live-account-highlights"
            await page.goto(url, wait_until="networkidle")
            
            # Expand accordions
            await page.evaluate("""
                const accordions = document.querySelectorAll('[data-testid="accordion-trigger"], .accordion-trigger, .collapsible-trigger');
                accordions.forEach(acc => acc.click());
            """)
            
            content = await page.content()
            rules = await self._parse_funded_rules(content, account_size)
            
            # Visit drawdown explanation article
            try:
                drawdown_url = f"{self.help_url}/articles/12802721-intraday-drawdown-explained"
                await page.goto(drawdown_url, wait_until="networkidle")
                await page.evaluate("""
                    const accordions = document.querySelectorAll('[data-testid="accordion-trigger"], .accordion-trigger, .collapsible-trigger');
                    accordions.forEach(acc => acc.click());
                """)
                drawdown_content = await page.content()
                drawdown_rules = await self._parse_funded_rules(drawdown_content, account_size)
                rules.update(drawdown_rules)
            except Exception as e:
                logger.warning(f"Failed to extract drawdown rules: {e}")
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting funded rules: {e}")
            return {}

    async def extract_payout_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract payout rules"""
        logger.info(f"Extracting payout rules for {account_size}")
        
        try:
            # Navigate to Rapid Plan collection for payout details
            url = f"{self.help_url}/collections/17350372-rapid-plan"
            await page.goto(url, wait_until="networkidle")
            
            # Expand accordions
            await page.evaluate("""
                const accordions = document.querySelectorAll('[data-testid="accordion-trigger"], .accordion-trigger, .collapsible-trigger');
                accordions.forEach(acc => acc.click());
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
            # Navigate to evaluation collection for fee information
            url = f"{self.help_url}/collections/5808821-traders-evaluation"
            await page.goto(url, wait_until="networkidle")
            
            # Expand accordions
            await page.evaluate("""
                const accordions = document.querySelectorAll('[data-testid="accordion-trigger"], .accordion-trigger, .collapsible-trigger');
                accordions.forEach(acc => acc.click());
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
            
            # Determine account size multiplier
            multiplier = self.size_multipliers.get(account_size, 1.0)
            
            # Extract profit target
            profit_patterns = [
                r'profit target[:\s]+\$?([0-9,]+)',
                r'target[:\s]+\$?([0-9,]+)',
                r'reach[:\s]+\$?([0-9,]+)'
            ]
            
            for pattern in profit_patterns:
                match = re.search(pattern, text)
                if match:
                    base_target = float(match.group(1).replace(',', ''))
                    rules['profit_target_usd'] = base_target * multiplier
                    break
            else:
                # Use default based on account size
                rules['profit_target_usd'] = 3000 * multiplier
            
            # Extract drawdown limit
            drawdown_patterns = [
                r'eod drawdown[:\s]+\$?([0-9,]+)',
                r'drawdown[:\s]+\$?([0-9,]+)',
                r'maximum loss[:\s]+\$?([0-9,]+)'
            ]
            
            for pattern in drawdown_patterns:
                match = re.search(pattern, text)
                if match:
                    base_drawdown = float(match.group(1).replace(',', ''))
                    rules['max_drawdown_usd'] = base_drawdown * multiplier
                    break
            else:
                # Use default based on account size
                rules['max_drawdown_usd'] = 2000 * multiplier
            
            # Extract daily loss limit
            daily_loss_patterns = [
                r'daily loss[:\s]+\$?([0-9,]+)',
                r'daily limit[:\s]+\$?([0-9,]+)'
            ]
            
            for pattern in daily_loss_patterns:
                match = re.search(pattern, text)
                if match:
                    base_daily = float(match.group(1).replace(',', ''))
                    rules['daily_loss_limit_usd'] = base_daily * multiplier
                    break
            else:
                rules['daily_loss_limit_usd'] = None  # Most plans don't have daily loss limits
            
            # Determine drawdown type
            if 'eod' in text or 'end of day' in text:
                rules['drawdown_type'] = DrawdownType.EOD
            elif 'trailing' in text:
                rules['drawdown_type'] = DrawdownType.TRAILING
            else:
                rules['drawdown_type'] = DrawdownType.STATIC  # Default
            
            # Extract minimum trading days
            min_days_patterns = [
                r'minimum[:\s]+([0-9]+)[:\s]+days?',
                r'([0-9]+)[:\s]+days? minimum',
                r'at least[:\s]+([0-9]+)[:\s]+days?'
            ]
            
            for pattern in min_days_patterns:
                match = re.search(pattern, text)
                if match:
                    rules['min_trading_days'] = int(match.group(1))
                    break
            else:
                rules['min_trading_days'] = None  # Can pass in 1 day
            
            # Check for consistency rule
            if 'consistency' in text and '50%' in text:
                rules['consistency_rule'] = True
            elif '20%' in text and 'consistency' in text:
                rules['consistency_rule'] = True  # Milestone plan
            else:
                rules['consistency_rule'] = False
            
            logger.info(f"Parsed evaluation rules: {rules}")
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
            
            # Determine account size multiplier
            multiplier = self.size_multipliers.get(account_size, 1.0)
            
            # Extract funded drawdown (usually same as evaluation)
            drawdown_patterns = [
                r'funded.*drawdown[:\s]+\$?([0-9,]+)',
                r'sim.*drawdown[:\s]+\$?([0-9,]+)',
                r'live.*drawdown[:\s]+\$?([0-9,]+)'
            ]
            
            for pattern in drawdown_patterns:
                match = re.search(pattern, text)
                if match:
                    base_drawdown = float(match.group(1).replace(',', ''))
                    rules['max_drawdown_usd'] = base_drawdown * multiplier
                    break
            else:
                # Use same as evaluation
                rules['max_drawdown_usd'] = 2000 * multiplier
            
            # Extract funded daily loss (usually none)
            daily_loss_patterns = [
                r'funded.*daily loss[:\s]+\$?([0-9,]+)',
                r'sim.*daily loss[:\s]+\$?([0-9,]+)'
            ]
            
            for pattern in daily_loss_patterns:
                match = re.search(pattern, text)
                if match:
                    base_daily = float(match.group(1).replace(',', ''))
                    rules['daily_loss_limit_usd'] = base_daily * multiplier
                    break
            else:
                rules['daily_loss_limit_usd'] = None  # Most funded accounts don't have daily limits
            
            # Determine drawdown type for funded
            if 'eod' in text or 'end of day' in text:
                rules['drawdown_type'] = DrawdownType.EOD
            elif 'trailing' in text:
                rules['drawdown_type'] = DrawdownType.TRAILING
            else:
                rules['drawdown_type'] = DrawdownType.STATIC
            
            logger.info(f"Parsed funded rules: {rules}")
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
            
            # Extract profit split
            split_patterns = [
                r'([0-9]+)%.*profit split',
                r'([0-9]+)/([0-9]+).*split',
                r'keep[:\s]+([0-9]+)%'
            ]
            
            for pattern in split_patterns:
                match = re.search(pattern, text)
                if match:
                    if len(match.groups()) == 2:  # Format like "80/20"
                        rules['profit_split_percent'] = int(match.group(1))
                    else:  # Format like "80%"
                        rules['profit_split_percent'] = int(match.group(1))
                    break
            else:
                rules['profit_split_percent'] = 80  # Default
            
            # Determine payout frequency
            if 'daily' in text and 'payout' in text:
                rules['payout_frequency'] = PayoutFrequency.ON_DEMAND
            elif 'weekly' in text and 'payout' in text:
                rules['payout_frequency'] = PayoutFrequency.WEEKLY
            elif 'biweekly' in text or 'bi-weekly' in text:
                rules['payout_frequency'] = PayoutFrequency.BIWEEKLY
            elif 'monthly' in text and 'payout' in text:
                rules['payout_frequency'] = PayoutFrequency.MONTHLY
            else:
                rules['payout_frequency'] = PayoutFrequency.ON_DEMAND  # Default
            
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
                rules['min_payout_usd'] = 250  # Default
            
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
            
            # Determine account size multiplier for fees
            multiplier = self.size_multipliers.get(account_size, 1.0)
            
            # Extract evaluation fee based on account size and plan
            # Use predefined fees as they're more reliable than parsing
            base_fees = {
                '$50,000': 127,   # Scale plan base
                '$100,000': 200,  # Estimated
                '$150,000': 300   # Estimated
            }
            
            rules['evaluation_fee_usd'] = base_fees.get(account_size, 127)
            
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
                rules['reset_fee_usd'] = rules['evaluation_fee_usd']  # Default to same as evaluation
            
            logger.info(f"Parsed fee rules: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing fee rules: {e}")
            return {}

    def get_platform(self) -> str:
        """Return the trading platform"""
        return Platform.MULTIPLE.value  # MFF supports multiple platforms

    def get_broker(self) -> str:
        """Return the broker"""
        return Broker.RITHMIC.value  # MFF primarily uses Rithmic