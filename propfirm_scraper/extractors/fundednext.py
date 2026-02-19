"""
Funded Next Extractor

Extracts trading rules from Funded Next Futures help center.
Website: https://helpfutures.fundednext.com/en/
"""

import re
import logging
from typing import Dict, List, Optional, Any
from playwright.async_api import Page
from bs4 import BeautifulSoup
from .base_extractor import BaseExtractor
from ..config.enums import DrawdownType, PayoutFrequency, Platform, Broker

logger = logging.getLogger(__name__)


class FundedNextExtractor(BaseExtractor):
    """Extractor for Funded Next Futures trading rules"""
    
    def __init__(self, site_config):
        super().__init__(site_config)
        self.help_url = "https://helpfutures.fundednext.com"
        
        # Challenge type data mapping
        self.challenge_data = {
            'Rapid': {
                'account_sizes': ['$25,000', '$50,000', '$100,000'],
                'profit_targets': {
                    '$25,000': 1500,
                    '$50,000': 3000,
                    '$100,000': 5000
                },
                'consistency_rule': False,
                'daily_loss_limit': None,
                'time_limit': None
            },
            'Legacy': {
                'account_sizes': ['$25,000', '$50,000', '$100,000'],
                'profit_targets': {
                    '$25,000': 1250,
                    '$50,000': 2500,
                    '$100,000': 6000
                },
                'consistency_rule': True,  # 40% daily profit limit
                'consistency_percentage': 40,
                'daily_loss_limit': None,
                'time_limit': None
            }
        }
        
        # Contract limits per account size
        self.contract_limits = {
            '$25,000': {'mini': 2, 'micro': 20},
            '$50,000': {'mini': 3, 'micro': 30},
            '$100,000': {'mini': 5, 'micro': 50}
        }
        
        # Live account structure
        self.live_account_tiers = {
            'below_15k': {'mini': 2, 'micro': 6},
            '15k_to_30k': {'mini': 3, 'micro': 9},
            'above_30k': {'mini': 5, 'micro': 15}
        }
        
        # URLs to visit for data extraction
        self.urls_to_visit = [
            "/collections/12136956-trading-rules-guidelines",
            "/articles/10740629-what-is-the-profit-target-in-the-futures-challenge",
            "/articles/10740610-how-do-i-pass-a-fundednext-futures-challenge",
            "/articles/10740843-is-there-any-consistency-rule-to-be-followed-in-the-fundednext-futures-challenge",
            "/articles/10749392-what-are-the-performance-reward-eligibility-criteria-for-fundednext-accounts",
            "/articles/10835786-what-will-be-my-reward-from-the-challenge",
            "/articles/10740530-is-there-any-contract-limit-at-fundednext-futures",
            "/articles/12646388-live-account-structure"
        ]

    async def get_account_sizes(self, page: Page) -> List[str]:
        """Extract all available account sizes"""
        logger.info("Extracting account sizes for Funded Next")
        
        try:
            # Navigate to trading rules collection
            url = f"{self.help_url}/en/collections/12136956-trading-rules-guidelines"
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
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text().lower()
            
            # Extract account sizes from content
            account_sizes = set()
            
            # Look for common account size patterns
            size_patterns = [
                r'\$25,?000',
                r'\$50,?000', 
                r'\$100,?000'
            ]
            
            for pattern in size_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    # Normalize the format
                    size = match.replace(',', '').replace('$', '')
                    formatted_size = f"${int(size):,}"
                    account_sizes.add(formatted_size)
            
            # If no sizes found, use default from challenge data
            if not account_sizes:
                logger.warning("No account sizes found in content, using default list")
                for challenge_type, data in self.challenge_data.items():
                    account_sizes.update(data['account_sizes'])
            
            # Sort account sizes
            sizes = list(account_sizes)
            sizes.sort(key=lambda x: float(x.replace('$', '').replace(',', '')))
            
            logger.info(f"Found account sizes: {sizes}")
            return sizes
            
        except Exception as e:
            logger.error(f"Error extracting account sizes: {e}")
            # Return default sizes
            return ['$25,000', '$50,000', '$100,000']

    async def extract_evaluation_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract evaluation phase rules"""
        logger.info(f"Extracting evaluation rules for {account_size}")
        
        try:
            # Navigate to profit target article
            url = f"{self.help_url}/en/articles/10740629-what-is-the-profit-target-in-the-futures-challenge"
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
                consistency_url = f"{self.help_url}/en/articles/10740843-is-there-any-consistency-rule-to-be-followed-in-the-fundednext-futures-challenge"
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
            # Navigate to live account structure article
            url = f"{self.help_url}/en/articles/12646388-live-account-structure"
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
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting funded rules: {e}")
            return {}

    async def extract_payout_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract payout rules"""
        logger.info(f"Extracting payout rules for {account_size}")
        
        try:
            # Navigate to reward article
            url = f"{self.help_url}/en/articles/10835786-what-will-be-my-reward-from-the-challenge"
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
            
            # Visit performance rewards article for more details
            try:
                performance_url = f"{self.help_url}/en/articles/10749392-what-are-the-performance-reward-eligibility-criteria-for-fundednext-accounts"
                await page.goto(performance_url, wait_until="networkidle")
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
                performance_content = await page.content()
                performance_rules = await self._parse_payout_rules(performance_content, account_size)
                rules.update(performance_rules)
            except Exception as e:
                logger.warning(f"Failed to extract performance rules: {e}")
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting payout rules: {e}")
            return {}

    async def extract_fee_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract fee information"""
        logger.info(f"Extracting fee rules for {account_size}")
        
        try:
            # Navigate to trading rules collection for fee information
            url = f"{self.help_url}/en/collections/12136956-trading-rules-guidelines"
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
            
            # Determine account size value for calculations
            account_value = float(account_size.replace('$', '').replace(',', ''))
            
            # Extract profit target based on challenge type and account size
            # Try to detect challenge type first
            challenge_type = 'Rapid'  # Default
            if 'legacy' in text or '40%' in text or 'consistency' in text:
                challenge_type = 'Legacy'
            
            # Get profit target from predefined data
            if account_size in self.challenge_data[challenge_type]['profit_targets']:
                rules['profit_target_usd'] = float(self.challenge_data[challenge_type]['profit_targets'][account_size])
            else:
                # Extract from text if not in predefined data
                profit_patterns = [
                    r'profit target[:\s]+\$?([0-9,]+)',
                    r'target[:\s]+\$?([0-9,]+)',
                    r'reach[:\s]+\$?([0-9,]+)'
                ]
                
                for pattern in profit_patterns:
                    match = re.search(pattern, text)
                    if match:
                        rules['profit_target_usd'] = float(match.group(1).replace(',', ''))
                        break
            
            # Extract maximum loss limit (drawdown)
            drawdown_patterns = [
                r'maximum loss[:\s]+\$?([0-9,]+)',
                r'max loss[:\s]+\$?([0-9,]+)',
                r'loss limit[:\s]+\$?([0-9,]+)',
                r'drawdown[:\s]+\$?([0-9,]+)'
            ]
            
            for pattern in drawdown_patterns:
                match = re.search(pattern, text)
                if match:
                    rules['max_drawdown_usd'] = float(match.group(1).replace(',', ''))
                    break
            else:
                # Use account value as default max loss (100% of account)
                rules['max_drawdown_usd'] = account_value
            
            # Daily loss limit (usually none during challenge)
            daily_loss_patterns = [
                r'daily loss[:\s]+\$?([0-9,]+)',
                r'daily limit[:\s]+\$?([0-9,]+)'
            ]
            
            for pattern in daily_loss_patterns:
                match = re.search(pattern, text)
                if match:
                    rules['daily_loss_limit_usd'] = float(match.group(1).replace(',', ''))
                    break
            else:
                rules['daily_loss_limit_usd'] = None  # No daily loss limit during challenge
            
            # Determine drawdown type (usually static for max loss limit)
            if 'trailing' in text:
                rules['drawdown_type'] = DrawdownType.TRAILING
            elif 'eod' in text or 'end of day' in text:
                rules['drawdown_type'] = DrawdownType.EOD
            else:
                rules['drawdown_type'] = DrawdownType.STATIC  # Default for max loss limit
            
            # Extract minimum trading days (usually none)
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
                rules['min_trading_days'] = None  # No minimum trading days
            
            # Check for consistency rule
            if challenge_type == 'Legacy' or ('40%' in text and 'consistency' in text):
                rules['consistency_rule'] = True
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
            
            # Determine account size value
            account_value = float(account_size.replace('$', '').replace(',', ''))
            
            # Extract funded drawdown (Maximum Loss Limit - MLL)
            drawdown_patterns = [
                r'maximum loss limit[:\s]+\$?([0-9,]+)',
                r'mll[:\s]+\$?([0-9,]+)',
                r'funded.*drawdown[:\s]+\$?([0-9,]+)',
                r'live.*loss[:\s]+\$?([0-9,]+)'
            ]
            
            for pattern in drawdown_patterns:
                match = re.search(pattern, text)
                if match:
                    rules['max_drawdown_usd'] = float(match.group(1).replace(',', ''))
                    break
            else:
                # Use same as evaluation if not specified
                rules['max_drawdown_usd'] = account_value
            
            # Extract funded daily loss (usually none)
            daily_loss_patterns = [
                r'funded.*daily loss[:\s]+\$?([0-9,]+)',
                r'live.*daily loss[:\s]+\$?([0-9,]+)'
            ]
            
            for pattern in daily_loss_patterns:
                match = re.search(pattern, text)
                if match:
                    rules['daily_loss_limit_usd'] = float(match.group(1).replace(',', ''))
                    break
            else:
                rules['daily_loss_limit_usd'] = None  # No daily loss limit on funded accounts
            
            # Determine drawdown type for funded
            if 'trailing' in text:
                rules['drawdown_type'] = DrawdownType.TRAILING
            elif 'eod' in text or 'end of day' in text:
                rules['drawdown_type'] = DrawdownType.EOD
            else:
                rules['drawdown_type'] = DrawdownType.STATIC  # Default for MLL
            
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
                r'keep[:\s]+([0-9]+)%',
                r'([0-9]+)%.*reward',
                r'([0-9]+)%.*share'
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
                rules['profit_split_percent'] = 80  # Default assumption
            
            # Determine payout frequency
            if 'weekly' in text and 'payout' in text:
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
            
            # Determine account size value for fee calculations
            account_value = float(account_size.replace('$', '').replace(',', ''))
            
            # Extract evaluation fee based on account size
            # Common fee patterns for different account sizes
            fee_patterns = [
                r'evaluation fee[:\s]+\$?([0-9,]+)',
                r'challenge fee[:\s]+\$?([0-9,]+)',
                r'entry fee[:\s]+\$?([0-9,]+)',
                r'fee[:\s]+\$?([0-9,]+)'
            ]
            
            for pattern in fee_patterns:
                match = re.search(pattern, text)
                if match:
                    rules['evaluation_fee_usd'] = float(match.group(1).replace(',', ''))
                    break
            else:
                # Use estimated fees based on account size
                if account_value <= 25000:
                    rules['evaluation_fee_usd'] = 99  # Estimated for $25K
                elif account_value <= 50000:
                    rules['evaluation_fee_usd'] = 149  # Estimated for $50K
                else:
                    rules['evaluation_fee_usd'] = 249  # Estimated for $100K
            
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
        return Platform.MULTIPLE.value  # Funded Next supports multiple platforms

    def get_broker(self) -> str:
        """Return the broker"""
        return Broker.RITHMIC.value  # Funded Next primarily uses Rithmic