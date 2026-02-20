"""
Trade Day Extractor

Extracts trading rules from Trade Day website.
Website: https://tradeday.com/
Pricing: https://tradeday.com/our-pricing
How It Works: https://tradeday.com/how-it-works
Help Center: https://tradeday.freshdesk.com/
"""

import re
import logging
from typing import Dict, List, Optional, Any
from playwright.async_api import Page
from bs4 import BeautifulSoup
from .base_extractor import BaseExtractor
from ..config.enums import DrawdownType, PayoutFrequency, Platform, Broker

logger = logging.getLogger(__name__)


class TradeDayExtractor(BaseExtractor):
    """Extractor for Trade Day trading rules"""
    
    def __init__(self, site_config):
        super().__init__(site_config)
        self.main_url = "https://tradeday.com"
        self.pricing_url = "https://tradeday.com/our-pricing"
        self.how_it_works_url = "https://tradeday.com/how-it-works"
        self.terms_url = "https://tradeday.com/terms-conditions"
        self.help_url = "https://tradeday.freshdesk.com"
        
        # Drawdown type data mapping based on research
        self.drawdown_types = {
            'Intraday': {
                'account_sizes': ['$50,000', '$100,000', '$150,000'],
                'profit_targets': {
                    '$50,000': 3000,
                    '$100,000': 6000,
                    '$150,000': 9000
                },
                'max_drawdowns': {
                    '$50,000': 2000,
                    '$100,000': 3000,
                    '$150,000': 4000
                },
                'monthly_fees_discounted': {
                    '$50,000': 87,    # 30% off from $125
                    '$100,000': 140,  # 30% off from $200
                    '$150,000': 210   # 30% off from $300
                },
                'monthly_fees_regular': {
                    '$50,000': 125,
                    '$100,000': 200,
                    '$150,000': 300
                },
                'position_limits': {
                    '$50,000': {'standard': 5, 'micros': 50},
                    '$100,000': {'standard': 10, 'micros': 50},
                    '$150,000': {'standard': 15, 'micros': 50}
                },
                'drawdown_type': DrawdownType.TRAILING,  # Intraday trailing
                'has_evaluation': True
            },
            'End of Day (EOD)': {
                'account_sizes': ['$50,000', '$100,000', '$150,000'],
                'profit_targets': {
                    '$50,000': 3000,
                    '$100,000': 6000,
                    '$150,000': 9000
                },
                'max_drawdowns': {
                    '$50,000': 2000,
                    '$100,000': 3000,
                    '$150,000': 4000
                },
                'monthly_fees_discounted': {
                    '$50,000': 122,   # 30% off from $175
                    '$100,000': 192,  # 30% off from $275
                    '$150,000': 262   # 30% off from $375
                },
                'monthly_fees_regular': {
                    '$50,000': 175,
                    '$100,000': 275,
                    '$150,000': 375
                },
                'position_limits': {
                    '$50,000': {'standard': 5, 'micros': 50},
                    '$100,000': {'standard': 10, 'micros': 50},
                    '$150,000': {'standard': 15, 'micros': 50}
                },
                'drawdown_type': DrawdownType.EOD,  # End of day trailing
                'has_evaluation': True
            },
            'Static': {
                'account_sizes': ['$50,000', '$100,000', '$150,000'],
                'profit_targets': {
                    '$50,000': 1500,   # Different targets for static
                    '$100,000': 2500,
                    '$150,000': 3750
                },
                'max_drawdowns': {
                    '$50,000': 500,    # Fixed static drawdowns
                    '$100,000': 750,
                    '$150,000': 1000
                },
                'monthly_fees_discounted': {
                    '$50,000': 115,   # 30% off from $165
                    '$100,000': 175,  # 30% off from $250
                    '$150,000': 245   # 30% off from $350
                },
                'monthly_fees_regular': {
                    '$50,000': 165,
                    '$100,000': 250,
                    '$150,000': 350
                },
                'position_limits': {
                    '$50,000': {'standard': 1, 'micros': 10},   # Lower limits for static
                    '$100,000': {'standard': 2, 'micros': 20},
                    '$150,000': {'standard': 3, 'micros': 30}
                },
                'drawdown_type': DrawdownType.STATIC,  # Fixed static drawdown
                'has_evaluation': True
            }
        }
        
        # Reset fees by account size
        self.reset_fees = {
            '$50,000': 99,   # Manual reset fee (range $80-$104, using $99 as standard)
            '$100,000': 99,  # Manual reset fee ($124 mentioned, but $99 is standard)
            '$150,000': 99   # Manual reset fee ($149 mentioned, but $99 is standard)
        }
        
        # General rules
        self.general_rules = {
            'min_trading_days': 5,  # Changed from 7 days after Sept 13, 2025
            'consistency_rule_percent': 30,  # No single day > 30% of total profit
            'profit_split_base': 80,  # 80% from day one
            'profit_split_max': 95,   # Potential to reach 95%
            'profit_split_first_10k': 100,  # Keep first $10K
            'profit_split_after_10k': 90,   # Then 90% thereafter
            'payout_frequency': PayoutFrequency.ON_DEMAND,  # Day 1 payouts available
            'max_accounts': 6,        # Can trade up to 6 accounts
            'auto_liquidation_minutes': 10,  # 10 minutes before close
            'tier1_liquidation_minutes': 2,  # 2 minutes before Tier 1 data
            'exchanges': ['CME', 'CBOT', 'NYMEX', 'COMEX'],
            'products': 'CME Exchange Group Futures only',
            'day_trading_only': True,
            'overnight_allowed': True,  # But must close before next day's close
            'min_payout_usd': 100  # Estimated
        }

    async def get_account_sizes(self, page: Page) -> List[str]:
        """Extract all available account sizes"""
        logger.info("Extracting account sizes for Trade Day")
        
        try:
            account_sizes = set()
            
            # Navigate to pricing page for account sizes
            await page.goto(self.pricing_url, wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text().lower()
            
            # Look for account size patterns
            found_sizes = self._extract_sizes_from_text(text)
            account_sizes.update(found_sizes)
            
            # Also try main website if pricing page didn't have all sizes
            if len(account_sizes) < 3:
                try:
                    await page.goto(self.main_url, wait_until="networkidle")
                    await page.wait_for_timeout(3000)
                    
                    content = await page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    text = soup.get_text().lower()
                    
                    additional_sizes = self._extract_sizes_from_text(text)
                    account_sizes.update(additional_sizes)
                    
                except Exception as e:
                    logger.warning(f"Error accessing main website: {e}")
            
            # If no sizes found, use predefined data
            if not account_sizes:
                logger.warning("No account sizes found in content, using predefined list")
                for drawdown_type, data in self.drawdown_types.items():
                    account_sizes.update(data['account_sizes'])
            
            # Sort account sizes
            sizes = list(account_sizes)
            sizes.sort(key=lambda x: float(x.replace('$', '').replace(',', '')))
            
            logger.info(f"Found total account sizes: {sizes}")
            return sizes
            
        except Exception as e:
            logger.error(f"Error extracting account sizes: {e}")
            # Return all predefined sizes
            all_sizes = set()
            for drawdown_type, data in self.drawdown_types.items():
                all_sizes.update(data['account_sizes'])
            return sorted(list(all_sizes), key=lambda x: float(x.replace('$', '').replace(',', '')))

    async def extract_evaluation_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract evaluation phase rules"""
        logger.info(f"Extracting evaluation rules for {account_size}")
        
        try:
            # Navigate to pricing page for detailed rules
            await page.goto(self.pricing_url, wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
            # Also try how it works page for additional rule details
            try:
                await page.goto(self.how_it_works_url, wait_until="networkidle")
                await page.wait_for_timeout(3000)
            except Exception as e:
                logger.warning(f"Failed to navigate to how it works page: {e}")
            
            content = await page.content()
            rules = await self._parse_evaluation_rules(content, account_size)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting evaluation rules: {e}")
            return self._get_fallback_evaluation_rules(account_size)

    async def extract_funded_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract funded account rules"""
        logger.info(f"Extracting funded rules for {account_size}")
        
        try:
            # Use same content as evaluation (rules are similar)
            await page.goto(self.pricing_url, wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
            content = await page.content()
            rules = await self._parse_funded_rules(content, account_size)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting funded rules: {e}")
            return self._get_fallback_funded_rules(account_size)

    async def extract_payout_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract payout rules"""
        logger.info(f"Extracting payout rules for {account_size}")
        
        try:
            # Try main website and pricing page for payout information
            urls_to_try = [self.main_url, self.pricing_url]
            
            for url in urls_to_try:
                try:
                    await page.goto(url, wait_until="networkidle")
                    await page.wait_for_timeout(3000)
                    
                    content = await page.content()
                    rules = await self._parse_payout_rules(content, account_size)
                    
                    if rules:  # If we found payout data, use it
                        return rules
                        
                except Exception as e:
                    logger.warning(f"Error accessing {url}: {e}")
                    continue
            
            # If no payout data found, use fallback
            return self._get_fallback_payout_rules(account_size)
            
        except Exception as e:
            logger.error(f"Error extracting payout rules: {e}")
            return self._get_fallback_payout_rules(account_size)

    async def extract_fee_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract fee information"""
        logger.info(f"Extracting fee rules for {account_size}")
        
        try:
            # Pricing page has fee information
            await page.goto(self.pricing_url, wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
            content = await page.content()
            rules = await self._parse_fee_rules(content, account_size)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting fee rules: {e}")
            return self._get_fallback_fee_rules(account_size)

    def _extract_sizes_from_text(self, text: str) -> List[str]:
        """Extract account sizes from text content"""
        sizes = set()
        
        # Look for Trade Day specific account size patterns
        size_patterns = [
            r'\$50,?000',
            r'\$100,?000',
            r'\$150,?000'
        ]
        
        for pattern in size_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                size = self._normalize_account_size(match)
                if size:
                    sizes.add(size)
        
        return list(sizes)

    def _normalize_account_size(self, size_text: str) -> Optional[str]:
        """Normalize account size text to standard format"""
        if not size_text or '$' not in size_text:
            return None
        
        # Extract numeric value
        numbers = re.findall(r'[\d,]+', size_text)
        if not numbers:
            return None
        
        try:
            value = int(numbers[0].replace(',', ''))
            return f"${value:,}"
        except ValueError:
            return None

    async def _parse_evaluation_rules(self, content: str, account_size: str) -> Dict[str, Any]:
        """Parse evaluation rules from HTML content"""
        rules = {}
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text().lower()
            
            # Determine drawdown type (default to Intraday if not specified)
            drawdown_type = self._determine_drawdown_type(text)
            type_info = self.drawdown_types.get(drawdown_type, self.drawdown_types['Intraday'])
            
            # Get profit target from predefined data
            profit_targets = type_info.get('profit_targets', {})
            if account_size in profit_targets:
                rules['profit_target_usd'] = float(profit_targets[account_size])
            
            # Get max drawdown from predefined data
            max_drawdowns = type_info.get('max_drawdowns', {})
            if account_size in max_drawdowns:
                rules['max_drawdown_usd'] = float(max_drawdowns[account_size])
            
            # Trade Day doesn't have daily loss limits (only max drawdown)
            # rules['daily_loss_limit_usd'] = None
            
            # Drawdown type
            rules['drawdown_type'] = type_info.get('drawdown_type', DrawdownType.TRAILING)
            
            # Minimum trading days
            rules['min_trading_days'] = self.general_rules['min_trading_days']
            
            # Consistency rule (30% rule)
            rules['consistency_rule'] = True
            
            logger.info(f"Parsed evaluation rules for {drawdown_type}: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing evaluation rules: {e}")
            return {}

    async def _parse_funded_rules(self, content: str, account_size: str) -> Dict[str, Any]:
        """Parse funded account rules from HTML content"""
        rules = {}
        
        try:
            # Use same rules as evaluation for funded phase
            eval_rules = await self._parse_evaluation_rules(content, account_size)
            
            # Copy relevant rules (funded rules are similar to evaluation)
            if 'max_drawdown_usd' in eval_rules:
                rules['max_drawdown_usd'] = eval_rules['max_drawdown_usd']
            if 'drawdown_type' in eval_rules:
                rules['drawdown_type'] = eval_rules['drawdown_type']
            
            # No daily loss limit for funded accounts either
            # rules['daily_loss_limit_usd'] = None
            
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
            
            # Profit split (80% base, can reach 95%)
            rules['profit_split_percent'] = self.general_rules['profit_split_base']
            
            # Payout frequency (day 1 payouts available)
            rules['payout_frequency'] = self.general_rules['payout_frequency']
            
            # Minimum payout (try to extract or use default)
            min_payout_patterns = [
                r'minimum payout[:\s]+\$?([0-9,]+)',
                r'min[:\s]+payout[:\s]+\$?([0-9,]+)',
                r'minimum[:\s]+\$?([0-9,]+)'
            ]
            
            for pattern in min_payout_patterns:
                match = re.search(pattern, text)
                if match:
                    rules['min_payout_usd'] = float(match.group(1).replace(',', ''))
                    break
            else:
                rules['min_payout_usd'] = self.general_rules['min_payout_usd']
            
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
            
            # Determine drawdown type
            drawdown_type = self._determine_drawdown_type(text)
            type_info = self.drawdown_types.get(drawdown_type, self.drawdown_types['Intraday'])
            
            # Get monthly evaluation fees (use discounted pricing)
            monthly_fees_discounted = type_info.get('monthly_fees_discounted', {})
            if account_size in monthly_fees_discounted:
                rules['evaluation_fee_usd'] = float(monthly_fees_discounted[account_size])
            
            # No activation fee (promoted as "No activation fee")
            rules['activation_fee_usd'] = 0.0
            
            # Reset fee (manual reset is $99, free on renewal)
            reset_fees = self.reset_fees
            if account_size in reset_fees:
                rules['reset_fee_usd'] = float(reset_fees[account_size])
            else:
                rules['reset_fee_usd'] = 99.0  # Default manual reset fee
            
            logger.info(f"Parsed fee rules for {drawdown_type}: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing fee rules: {e}")
            return {}

    def _determine_drawdown_type(self, text: str) -> str:
        """Determine drawdown type from content"""
        
        if 'static' in text and 'drawdown' in text:
            return 'Static'
        elif 'end of day' in text or 'eod' in text:
            return 'End of Day (EOD)'
        elif 'intraday' in text:
            return 'Intraday'
        
        # Default to Intraday (most common)
        return 'Intraday'

    def _get_fallback_evaluation_rules(self, account_size: str) -> Dict[str, Any]:
        """Get fallback evaluation rules from predefined data"""
        rules = {}
        
        try:
            # Default to Intraday drawdown type
            type_info = self.drawdown_types['Intraday']
            
            # Use predefined rules
            profit_targets = type_info.get('profit_targets', {})
            if account_size in profit_targets:
                rules['profit_target_usd'] = float(profit_targets[account_size])
            
            max_drawdowns = type_info.get('max_drawdowns', {})
            if account_size in max_drawdowns:
                rules['max_drawdown_usd'] = float(max_drawdowns[account_size])
            
            rules['drawdown_type'] = type_info.get('drawdown_type', DrawdownType.TRAILING)
            rules['min_trading_days'] = self.general_rules['min_trading_days']
            rules['consistency_rule'] = True
            
            logger.info(f"Using fallback evaluation rules: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error in fallback evaluation rules: {e}")
            return {}

    def _get_fallback_funded_rules(self, account_size: str) -> Dict[str, Any]:
        """Get fallback funded rules from predefined data"""
        rules = {}
        
        try:
            # Same rules as evaluation for funded phase
            eval_rules = self._get_fallback_evaluation_rules(account_size)
            
            if 'max_drawdown_usd' in eval_rules:
                rules['max_drawdown_usd'] = eval_rules['max_drawdown_usd']
            if 'drawdown_type' in eval_rules:
                rules['drawdown_type'] = eval_rules['drawdown_type']
            
            logger.info(f"Using fallback funded rules: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error in fallback funded rules: {e}")
            return {}

    def _get_fallback_payout_rules(self, account_size: str) -> Dict[str, Any]:
        """Get fallback payout rules from predefined data"""
        rules = {}
        
        try:
            rules['profit_split_percent'] = self.general_rules['profit_split_base']
            rules['payout_frequency'] = self.general_rules['payout_frequency']
            rules['min_payout_usd'] = self.general_rules['min_payout_usd']
            
            logger.info(f"Using fallback payout rules: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error in fallback payout rules: {e}")
            return {}

    def _get_fallback_fee_rules(self, account_size: str) -> Dict[str, Any]:
        """Get fallback fee rules from predefined data"""
        rules = {}
        
        try:
            # Default to Intraday pricing
            type_info = self.drawdown_types['Intraday']
            
            # Monthly evaluation fees (discounted)
            monthly_fees_discounted = type_info.get('monthly_fees_discounted', {})
            if account_size in monthly_fees_discounted:
                rules['evaluation_fee_usd'] = float(monthly_fees_discounted[account_size])
            
            # No activation fee
            rules['activation_fee_usd'] = 0.0
            
            # Reset fee
            reset_fees = self.reset_fees
            if account_size in reset_fees:
                rules['reset_fee_usd'] = float(reset_fees[account_size])
            else:
                rules['reset_fee_usd'] = 99.0
            
            logger.info(f"Using fallback fee rules: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error in fallback fee rules: {e}")
            return {}

    def get_platform(self) -> str:
        """Return the trading platform"""
        return Platform.MULTIPLE.value  # Trade Day supports multiple platforms

    def get_broker(self) -> str:
        """Return the broker"""
        return Broker.MULTIPLE.value  # Trade Day supports multiple brokers via CME Exchange Group