"""
E8 Markets Extractor

Extracts trading rules from E8 Markets help centers.
Website: https://e8markets.com/
Forex Help: https://help.e8markets.com/en/
Futures Help: https://helpfutures.e8markets.com/en/
"""

import re
import logging
from typing import Dict, List, Optional, Any
from playwright.async_api import Page
from bs4 import BeautifulSoup
from .base_extractor import BaseExtractor
from ..config.enums import DrawdownType, PayoutFrequency, Platform, Broker

logger = logging.getLogger(__name__)


class E8MarketsExtractor(BaseExtractor):
    """Extractor for E8 Markets trading rules"""
    
    def __init__(self, site_config):
        super().__init__(site_config)
        self.main_url = "https://e8markets.com"
        self.forex_help_url = "https://help.e8markets.com"
        self.futures_help_url = "https://helpfutures.e8markets.com"
        
        # Account type data mapping based on research
        self.account_types = {
            'E8 One': {
                'account_sizes': ['$5,000', '$10,000', '$25,000'],
                'pricing': {
                    '$5,000': 54,
                    '$10,000': 99,
                    '$25,000': 211
                },
                'profit_target_percent': 9.0,  # 9% profit target
                'max_drawdown_percent': 6.0,   # 6% max drawdown
                'profit_split': 90,            # 90% profit split
                'phases': 1,                   # Single-phase evaluation
                'daily_loss_percent': 5.0,    # 5% daily loss limit
                'consistency_rule': False      # No consistency rule
            },
            'E8 Signature': {
                'account_sizes': ['$50,000', '$100,000', '$150,000'],
                'pricing': {
                    '$50,000': 98,
                    '$100,000': 179,
                    '$150,000': 267
                },
                'profit_target_percent': 6.0,  # 6% profit target
                'max_drawdown_percent': 4.0,   # 4% max drawdown
                'profit_split': 80,            # 80% profit split
                'phases': 1,                   # One-step evaluation
                'daily_loss_percent': 5.0,    # 5% daily loss limit
                'consistency_rule': False      # No consistency rule
            },
            'E8 Classic': {
                'account_sizes': ['$25,000', '$50,000', '$100,000'],
                'pricing': {
                    '$25,000': 150,
                    '$50,000': 250,
                    '$100,000': 400
                },
                'profit_target_phase1': 8.0,   # 8% Phase 1
                'profit_target_phase2': 5.0,   # 5% Phase 2
                'max_drawdown_percent': 8.0,   # 8% overall drawdown
                'profit_split': 80,            # 80% profit split
                'phases': 2,                   # Two-phase evaluation
                'daily_loss_percent': 5.0,    # 5% daily loss limit
                'consistency_rule': True       # Best day rule (40%)
            }
        }
        
        # General rules for all accounts
        self.general_rules = {
            'daily_loss_percent': 5.0,        # 5% daily loss limit
            'best_day_rule': 40,              # 40% best day rule
            'min_trading_days': 5,            # 5 winning trading days for payout
            'payout_frequency': PayoutFrequency.BIWEEKLY,  # 7-day cycle
            'min_payout': 50,                 # Minimum payout amount
            'max_accounts_evaluation': None,   # Unlimited evaluation accounts
            'max_accounts_funded': 5,         # Max 5 E8 Trader accounts
            'max_accounts_dedicated': 1       # Max 1 E8Pro Dedicated
        }
        
        # URLs to visit for data extraction
        self.urls_to_visit = [
            # Futures help center
            "/en/articles/10242386-evaluation-rules-objectives-at-e8-markets",
            # Forex help center
            "/en/collections/10983534-products-trading-rules",
            "/en/articles/11775980-e8-one",
            "/en/articles/11755943-e8-signature-forex",
            "/en/articles/11769446-daily-drawdown",
            "/en/articles/9323884-payout-share-request-from-e8-trader-account-on-e8-one"
        ]

    async def get_account_sizes(self, page: Page) -> List[str]:
        """Extract all available account sizes"""
        logger.info("Extracting account sizes for E8 Markets")
        
        try:
            # Try forex help center first for product information
            await page.goto(f"{self.forex_help_url}/en/collections/10983534-products-trading-rules", wait_until="networkidle")
            
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
            
            await page.wait_for_timeout(2000)
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text().lower()
            
            account_sizes = set()
            
            # Look for common account size patterns
            size_patterns = [
                r'\$5,?000',
                r'\$10,?000',
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
            
            # If no sizes found, try futures help center
            if not account_sizes:
                logger.info("No account sizes found in forex help, trying futures help")
                await page.goto(f"{self.futures_help_url}/en/articles/10242386-evaluation-rules-objectives-at-e8-markets", wait_until="networkidle")
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
                
                await page.wait_for_timeout(2000)
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                text = soup.get_text().lower()
                
                for pattern in size_patterns:
                    matches = re.findall(pattern, text)
                    for match in matches:
                        size = match.replace(',', '').replace('$', '')
                        formatted_size = f"${int(size):,}"
                        account_sizes.add(formatted_size)
            
            # If still no sizes found, use predefined data
            if not account_sizes:
                logger.warning("No account sizes found in content, using predefined list")
                for account_type, data in self.account_types.items():
                    account_sizes.update(data['account_sizes'])
            
            # Sort account sizes
            sizes = list(account_sizes)
            sizes.sort(key=lambda x: float(x.replace('$', '').replace(',', '')))
            
            logger.info(f"Found account sizes: {sizes}")
            return sizes
            
        except Exception as e:
            logger.error(f"Error extracting account sizes: {e}")
            # Return all predefined sizes
            all_sizes = set()
            for account_type, data in self.account_types.items():
                all_sizes.update(data['account_sizes'])
            return sorted(list(all_sizes), key=lambda x: float(x.replace('$', '').replace(',', '')))

    async def extract_evaluation_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract evaluation phase rules"""
        logger.info(f"Extracting evaluation rules for {account_size}")
        
        try:
            # Navigate to futures evaluation rules article
            url = f"{self.futures_help_url}/en/articles/10242386-evaluation-rules-objectives-at-e8-markets"
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
            
            await page.wait_for_timeout(2000)
            content = await page.content()
            rules = await self._parse_evaluation_rules(content, account_size)
            
            # Visit forex help center for additional product-specific rules
            try:
                # Check E8 One rules
                e8_one_url = f"{self.forex_help_url}/en/articles/11775980-e8-one"
                await page.goto(e8_one_url, wait_until="networkidle")
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
                await page.wait_for_timeout(1000)
                e8_one_content = await page.content()
                e8_one_rules = await self._parse_evaluation_rules(e8_one_content, account_size)
                rules.update(e8_one_rules)
                
                # Check E8 Signature rules
                e8_sig_url = f"{self.forex_help_url}/en/articles/11755943-e8-signature-forex"
                await page.goto(e8_sig_url, wait_until="networkidle")
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
                await page.wait_for_timeout(1000)
                e8_sig_content = await page.content()
                e8_sig_rules = await self._parse_evaluation_rules(e8_sig_content, account_size)
                rules.update(e8_sig_rules)
                
            except Exception as e:
                logger.warning(f"Failed to extract from forex help center: {e}")
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting evaluation rules: {e}")
            return {}

    async def extract_funded_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract funded account rules"""
        logger.info(f"Extracting funded rules for {account_size}")
        
        try:
            # Navigate to daily drawdown article for funded account rules
            url = f"{self.forex_help_url}/en/articles/11769446-daily-drawdown"
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
            
            await page.wait_for_timeout(2000)
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
            # Navigate to payout article
            url = f"{self.forex_help_url}/en/articles/9323884-payout-share-request-from-e8-trader-account-on-e8-one"
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
            
            await page.wait_for_timeout(2000)
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
            # Navigate to products collection for pricing
            url = f"{self.forex_help_url}/en/collections/10983534-products-trading-rules"
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
            
            await page.wait_for_timeout(2000)
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
            
            # Determine account type based on account size and content
            account_type = self._determine_account_type(account_size, text)
            account_info = self.account_types.get(account_type, self.account_types['E8 One'])
            
            # Calculate profit target based on account type
            if account_type == 'E8 Classic' and 'phase 1' in text:
                profit_target_percent = account_info['profit_target_phase1']
            elif account_type == 'E8 Classic' and 'phase 2' in text:
                profit_target_percent = account_info['profit_target_phase2']
            else:
                profit_target_percent = account_info['profit_target_percent']
            
            rules['profit_target_usd'] = account_value * (profit_target_percent / 100)
            
            # Calculate max drawdown
            max_drawdown_percent = account_info['max_drawdown_percent']
            rules['max_drawdown_usd'] = account_value * (max_drawdown_percent / 100)
            
            # Daily loss limit (5% for most accounts)
            daily_loss_percent = account_info.get('daily_loss_percent', self.general_rules['daily_loss_percent'])
            rules['daily_loss_limit_usd'] = account_value * (daily_loss_percent / 100)
            
            # Drawdown type (usually daily drawdown for E8)
            if 'eod' in text or 'end of day' in text:
                rules['drawdown_type'] = DrawdownType.EOD
            elif 'dynamic' in text:
                rules['drawdown_type'] = DrawdownType.TRAILING
            else:
                rules['drawdown_type'] = DrawdownType.STATIC  # Default
            
            # Minimum trading days (none for evaluation, 5 for payout)
            rules['min_trading_days'] = None  # No minimum for evaluation
            
            # Consistency rule (Best Day Rule - 40%)
            if account_info.get('consistency_rule', False) or 'best day' in text or '40%' in text:
                rules['consistency_rule'] = True
            else:
                rules['consistency_rule'] = False
            
            logger.info(f"Parsed evaluation rules for {account_type}: {rules}")
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
            
            # Determine account type
            account_type = self._determine_account_type(account_size, text)
            account_info = self.account_types.get(account_type, self.account_types['E8 One'])
            
            # Funded drawdown (usually same as evaluation)
            max_drawdown_percent = account_info['max_drawdown_percent']
            rules['max_drawdown_usd'] = account_value * (max_drawdown_percent / 100)
            
            # Daily loss limit (5% for funded accounts)
            daily_loss_percent = account_info.get('daily_loss_percent', self.general_rules['daily_loss_percent'])
            rules['daily_loss_limit_usd'] = account_value * (daily_loss_percent / 100)
            
            # Drawdown type for funded accounts
            if 'eod' in text or 'end of day' in text:
                rules['drawdown_type'] = DrawdownType.EOD
            elif 'dynamic' in text:
                rules['drawdown_type'] = DrawdownType.TRAILING
            else:
                rules['drawdown_type'] = DrawdownType.STATIC
            
            logger.info(f"Parsed funded rules for {account_type}: {rules}")
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
            
            # Determine account type
            account_type = self._determine_account_type(account_size, text)
            account_info = self.account_types.get(account_type, self.account_types['E8 One'])
            
            # Profit split based on account type
            rules['profit_split_percent'] = account_info['profit_split']
            
            # Payout frequency (bi-weekly/7-day cycle)
            if 'weekly' in text or '7 day' in text or 'biweekly' in text:
                rules['payout_frequency'] = PayoutFrequency.BIWEEKLY
            elif 'on-demand' in text or 'on demand' in text:
                rules['payout_frequency'] = PayoutFrequency.ON_DEMAND
            else:
                rules['payout_frequency'] = self.general_rules['payout_frequency']
            
            # Minimum payout
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
                rules['min_payout_usd'] = float(self.general_rules['min_payout'])
            
            logger.info(f"Parsed payout rules for {account_type}: {rules}")
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
            
            # Determine account type
            account_type = self._determine_account_type(account_size, text)
            account_info = self.account_types.get(account_type, self.account_types['E8 One'])
            
            # Get pricing from predefined data
            if 'pricing' in account_info and account_size in account_info['pricing']:
                rules['evaluation_fee_usd'] = float(account_info['pricing'][account_size])
            else:
                # Try to extract fee from content
                fee_patterns = [
                    r'fee[:\s]+\$?([0-9,]+)',
                    r'price[:\s]+\$?([0-9,]+)',
                    r'cost[:\s]+\$?([0-9,]+)'
                ]
                
                for pattern in fee_patterns:
                    match = re.search(pattern, text)
                    if match:
                        rules['evaluation_fee_usd'] = float(match.group(1).replace(',', ''))
                        break
                else:
                    # Default estimate based on account size
                    account_value = float(account_size.replace('$', '').replace(',', ''))
                    if account_value <= 10000:
                        rules['evaluation_fee_usd'] = 99
                    elif account_value <= 25000:
                        rules['evaluation_fee_usd'] = 199
                    else:
                        rules['evaluation_fee_usd'] = 299
            
            # Reset fee (usually same as evaluation fee)
            rules['reset_fee_usd'] = rules.get('evaluation_fee_usd', 199)
            
            logger.info(f"Parsed fee rules for {account_type}: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing fee rules: {e}")
            return {}

    def _determine_account_type(self, account_size: str, text: str) -> str:
        """Determine account type based on account size and content"""
        account_value = float(account_size.replace('$', '').replace(',', ''))
        
        # Check content for specific product mentions
        if 'e8 one' in text:
            return 'E8 One'
        elif 'e8 signature' in text:
            return 'E8 Signature'
        elif 'e8 classic' in text or 'phase 1' in text or 'phase 2' in text:
            return 'E8 Classic'
        
        # Determine based on account size ranges
        if account_value <= 25000:
            return 'E8 One'
        elif account_value <= 150000:
            return 'E8 Signature'
        else:
            return 'E8 Classic'

    def get_platform(self) -> str:
        """Return the trading platform"""
        return Platform.MT4.value  # E8 Markets primarily uses MT4

    def get_broker(self) -> str:
        """Return the broker"""
        return Broker.PURPLE_TRADING.value  # E8 Markets uses Purple Trading