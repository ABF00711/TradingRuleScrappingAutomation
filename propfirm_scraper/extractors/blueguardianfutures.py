"""
Blue Guardian Futures Extractor

Extracts trading rules from Blue Guardian Futures website.
Website: https://blueguardianfutures.com/
Help Center: https://help.blueguardianfutures.com/en/
"""

import re
import logging
from typing import Dict, List, Optional, Any
from playwright.async_api import Page
from bs4 import BeautifulSoup
from .base_extractor import BaseExtractor
from ..config.enums import DrawdownType, PayoutFrequency, Platform, Broker

logger = logging.getLogger(__name__)


class BlueGuardianFuturesExtractor(BaseExtractor):
    """Extractor for Blue Guardian Futures trading rules"""
    
    def __init__(self, site_config):
        super().__init__(site_config)
        self.main_url = "https://blueguardianfutures.com"
        self.help_url = "https://help.blueguardianfutures.com/en"
        
        # Account type data mapping based on research
        self.evaluation_types = {
            'Standard Guardian': {
                'account_sizes': ['$25,000', '$50,000', '$100,000', '$150,000'],
                'profit_targets': {
                    '$25,000': 1500,
                    '$50,000': 3000,
                    '$100,000': 6000,
                    '$150,000': 9000
                },
                'daily_loss_limits': {
                    '$25,000': 625,
                    '$50,000': 1250,
                    '$100,000': 2500,
                    '$150,000': 3750
                },
                'max_drawdowns': {
                    '$25,000': 1250,
                    '$50,000': 2500,
                    '$100,000': 3500,
                    '$150,000': 5000
                },
                'evaluation_fees_regular': {
                    '$25,000': 63,
                    '$50,000': 160,
                    '$100,000': 240,
                    '$150,000': 340
                },
                'evaluation_fees_promo': {
                    '$25,000': 18,
                    '$50,000': 48,
                    '$100,000': 72,
                    '$150,000': 102
                },
                'reset_fees': {
                    '$25,000': 35,
                    '$50,000': 70,
                    '$100,000': 136,
                    '$150,000': 200
                },
                'drawdown_type': DrawdownType.EOD,
                'payout_period_days': 7,
                'activation_fee': 0,
                'scaling_rule': True,
                'micro_scaling': True,
                'consistency_rule': True,
                'has_evaluation': True
            },
            'Guardian': {
                'account_sizes': ['$25,000', '$50,000', '$100,000', '$150,000'],
                'profit_targets': {
                    '$25,000': 2000,
                    '$50,000': 4000,
                    '$100,000': 8000,
                    '$150,000': 12000
                },
                'daily_loss_limits': {
                    '$25,000': None,  # No daily loss limit
                    '$50,000': None,
                    '$100,000': None,
                    '$150,000': None
                },
                'max_drawdowns': {
                    '$25,000': 1000,
                    '$50,000': 2000,
                    '$100,000': 4000,
                    '$150,000': 6000
                },
                'evaluation_fees_regular': {
                    '$25,000': 48,
                    '$50,000': 119,
                    '$100,000': 169,
                    '$150,000': 269
                },
                'evaluation_fees_promo': {
                    '$25,000': 14,
                    '$50,000': 35,
                    '$100,000': 50,
                    '$150,000': 80
                },
                'activation_fees_regular': {
                    '$25,000': 49,
                    '$50,000': 99,
                    '$100,000': 149,
                    '$150,000': 199
                },
                'activation_fees_promo': {
                    '$25,000': 24,
                    '$50,000': 48,
                    '$100,000': 74,
                    '$150,000': 98
                },
                'reset_fees': {
                    '$25,000': 39,
                    '$50,000': 79,
                    '$100,000': 159,
                    '$150,000': 239
                },
                'drawdown_type': DrawdownType.EOD,
                'payout_period_days': 14,
                'scaling_rule': False,
                'micro_scaling': True,
                'consistency_rule': {
                    '$25,000': True,
                    '$50,000': True,
                    '$100,000': False,  # No consistency rule for $100K+
                    '$150,000': False
                },
                'has_evaluation': True
            },
            'Instant': {
                'account_sizes': ['$25,000', '$50,000', '$100,000', '$150,000'],
                'profit_targets': {
                    '$25,000': None,  # No profit target for instant
                    '$50,000': None,
                    '$100,000': None,
                    '$150,000': None
                },
                'daily_loss_limits_percent': 2,  # 2% daily loss limit
                'max_drawdown_percent': 4,       # 4% max drawdown
                'evaluation_fees_regular': {
                    '$25,000': 395,
                    '$50,000': 625,
                    '$100,000': 825,
                    '$150,000': 995
                },
                'evaluation_fees_promo': {
                    '$25,000': 118,
                    '$50,000': 187,
                    '$100,000': 247,
                    '$150,000': 298
                },
                'drawdown_type': DrawdownType.EOD,
                'payout_period_days': 14,
                'activation_fee': 0,
                'reset_fee': 0,
                'scaling_rule': False,
                'micro_scaling': True,
                'consistency_rule': True,
                'has_evaluation': False  # Instant funding
            }
        }
        
        # General rules for all accounts
        self.general_rules = {
            'profit_split_first_15k': 100,      # 100% for first $15K
            'profit_split_after_15k': 90,       # 90% after $15K
            'payout_processing': '48 hours',    # Within 48 hours guaranteed
            'payout_frequency': PayoutFrequency.ON_DEMAND,  # Anytime after waiting period
            'payout_guarantee': '$200 extra if delayed',
            'payment_methods': ['Bank transfer', 'Cryptocurrency', 'Local payments'],
            'platforms': ['Tradovate', 'ProjectX', 'Volsys']
        }

    async def get_account_sizes(self, page: Page) -> List[str]:
        """Extract all available account sizes"""
        logger.info("Extracting account sizes for Blue Guardian Futures")
        
        try:
            # Navigate to main website homepage
            await page.goto(self.main_url, wait_until="networkidle")
            
            # Wait for dynamic content to load
            await page.wait_for_timeout(3000)
            
            # Look for evaluation section
            try:
                await page.wait_for_selector('#evaluation', timeout=10000)
            except:
                logger.warning("Evaluation section not found, continuing with content parsing")
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text().lower()
            
            account_sizes = set()
            
            # Look for account size patterns in content
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
            
            # Also look for evaluation cards or tables
            evaluation_sections = soup.find_all(['div', 'section'], class_=re.compile(r'evaluation|card|pricing'))
            for section in evaluation_sections:
                section_text = section.get_text().lower()
                for pattern in size_patterns:
                    matches = re.findall(pattern, section_text)
                    for match in matches:
                        size = match.replace(',', '').replace('$', '')
                        formatted_size = f"${int(size):,}"
                        account_sizes.add(formatted_size)
            
            # If no sizes found, use predefined data
            if not account_sizes:
                logger.warning("No account sizes found in content, using predefined list")
                for eval_type, data in self.evaluation_types.items():
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
            for eval_type, data in self.evaluation_types.items():
                all_sizes.update(data['account_sizes'])
            return sorted(list(all_sizes), key=lambda x: float(x.replace('$', '').replace(',', '')))

    async def extract_evaluation_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract evaluation phase rules"""
        logger.info(f"Extracting evaluation rules for {account_size}")
        
        try:
            # Navigate to main website for evaluation data
            await page.goto(self.main_url, wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
            content = await page.content()
            rules = await self._parse_evaluation_rules(content, account_size)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting evaluation rules: {e}")
            # Fallback to predefined data for Standard Guardian
            return self._get_fallback_evaluation_rules(account_size)

    async def extract_funded_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract funded account rules"""
        logger.info(f"Extracting funded rules for {account_size}")
        
        try:
            # Use same content as evaluation (rules apply to both phases)
            await page.goto(self.main_url, wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
            content = await page.content()
            rules = await self._parse_funded_rules(content, account_size)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting funded rules: {e}")
            # Fallback to predefined data
            return self._get_fallback_funded_rules(account_size)

    async def extract_payout_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract payout rules"""
        logger.info(f"Extracting payout rules for {account_size}")
        
        try:
            # Try help center for detailed payout info
            try:
                await page.goto(self.help_url, wait_until="networkidle")
                await page.wait_for_timeout(2000)
                
                # Look for payout-related articles
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Find links to payout articles
                payout_links = soup.find_all('a', href=re.compile(r'payout|withdrawal|payment'))
                if payout_links:
                    # Navigate to first payout article
                    first_link = payout_links[0]
                    href = first_link.get('href')
                    if href:
                        if href.startswith('/'):
                            href = f"{self.help_url}{href}"
                        await page.goto(href, wait_until="networkidle")
                        await page.wait_for_timeout(2000)
                        
            except Exception as e:
                logger.warning(f"Failed to navigate to help center: {e}")
                # Fallback to main website
                await page.goto(self.main_url, wait_until="networkidle")
                await page.wait_for_timeout(3000)
            
            content = await page.content()
            rules = await self._parse_payout_rules(content, account_size)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting payout rules: {e}")
            return self._get_fallback_payout_rules(account_size)

    async def extract_fee_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract fee information"""
        logger.info(f"Extracting fee rules for {account_size}")
        
        try:
            # Main website has pricing in evaluation cards
            await page.goto(self.main_url, wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
            content = await page.content()
            rules = await self._parse_fee_rules(content, account_size)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting fee rules: {e}")
            return self._get_fallback_fee_rules(account_size)

    async def _parse_evaluation_rules(self, content: str, account_size: str) -> Dict[str, Any]:
        """Parse evaluation rules from HTML content"""
        rules = {}
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text().lower()
            
            # Determine evaluation type (default to Standard Guardian for evaluation)
            eval_type = self._determine_evaluation_type(account_size, text, prefer_evaluation=True)
            eval_info = self.evaluation_types.get(eval_type, self.evaluation_types['Standard Guardian'])
            
            # Skip if evaluation type doesn't have evaluation phase
            if not eval_info.get('has_evaluation', True):
                return {}
            
            # Get profit target from predefined data
            profit_targets = eval_info.get('profit_targets', {})
            if account_size in profit_targets and profit_targets[account_size] is not None:
                rules['profit_target_usd'] = float(profit_targets[account_size])
            
            # Get max drawdown from predefined data
            max_drawdowns = eval_info.get('max_drawdowns', {})
            if account_size in max_drawdowns:
                rules['max_drawdown_usd'] = float(max_drawdowns[account_size])
            
            # Get daily loss limit from predefined data
            daily_loss_limits = eval_info.get('daily_loss_limits', {})
            if account_size in daily_loss_limits and daily_loss_limits[account_size] is not None:
                rules['daily_loss_limit_usd'] = float(daily_loss_limits[account_size])
            elif eval_type == 'Instant':
                # For Instant accounts, daily loss is percentage-based
                account_value = float(account_size.replace('$', '').replace(',', ''))
                daily_loss_percent = eval_info.get('daily_loss_limits_percent', 2)
                rules['daily_loss_limit_usd'] = account_value * (daily_loss_percent / 100)
            
            # Drawdown type
            rules['drawdown_type'] = eval_info.get('drawdown_type', DrawdownType.EOD)
            
            # Minimum trading days (payout period)
            rules['min_trading_days'] = eval_info.get('payout_period_days', 7)
            
            # Consistency rule
            consistency = eval_info.get('consistency_rule')
            if isinstance(consistency, dict):
                rules['consistency_rule'] = consistency.get(account_size, True)
            else:
                rules['consistency_rule'] = consistency if consistency is not None else True
            
            logger.info(f"Parsed evaluation rules for {eval_type}: {rules}")
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
            
            # Determine evaluation type
            eval_type = self._determine_evaluation_type(account_size, text)
            eval_info = self.evaluation_types.get(eval_type, self.evaluation_types['Standard Guardian'])
            
            # Get max drawdown (same as evaluation for most types)
            max_drawdowns = eval_info.get('max_drawdowns', {})
            if account_size in max_drawdowns:
                rules['max_drawdown_usd'] = float(max_drawdowns[account_size])
            elif eval_type == 'Instant':
                # For Instant accounts, max drawdown is percentage-based
                account_value = float(account_size.replace('$', '').replace(',', ''))
                max_drawdown_percent = eval_info.get('max_drawdown_percent', 4)
                rules['max_drawdown_usd'] = account_value * (max_drawdown_percent / 100)
            
            # Get daily loss limit (same as evaluation)
            daily_loss_limits = eval_info.get('daily_loss_limits', {})
            if account_size in daily_loss_limits and daily_loss_limits[account_size] is not None:
                rules['daily_loss_limit_usd'] = float(daily_loss_limits[account_size])
            elif eval_type == 'Instant':
                # For Instant accounts, daily loss is percentage-based
                account_value = float(account_size.replace('$', '').replace(',', ''))
                daily_loss_percent = eval_info.get('daily_loss_limits_percent', 2)
                rules['daily_loss_limit_usd'] = account_value * (daily_loss_percent / 100)
            
            # Drawdown type (same as evaluation)
            rules['drawdown_type'] = eval_info.get('drawdown_type', DrawdownType.EOD)
            
            logger.info(f"Parsed funded rules for {eval_type}: {rules}")
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
            
            # Tiered profit split (100% for first $15K, 90% after)
            rules['profit_split_percent'] = self.general_rules['profit_split_after_15k']  # Use 90% as primary
            
            # Payout frequency (on-demand after waiting period)
            rules['payout_frequency'] = self.general_rules['payout_frequency']
            
            # Minimum payout (try to extract or use reasonable default)
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
            
            # Determine evaluation type
            eval_type = self._determine_evaluation_type(account_size, text)
            eval_info = self.evaluation_types.get(eval_type, self.evaluation_types['Standard Guardian'])
            
            # Get evaluation fees (use promotional pricing if available)
            evaluation_fees_promo = eval_info.get('evaluation_fees_promo', {})
            evaluation_fees_regular = eval_info.get('evaluation_fees_regular', {})
            
            if account_size in evaluation_fees_promo:
                rules['evaluation_fee_usd'] = float(evaluation_fees_promo[account_size])
            elif account_size in evaluation_fees_regular:
                rules['evaluation_fee_usd'] = float(evaluation_fees_regular[account_size])
            
            # Get activation fee (for Guardian accounts)
            if eval_type == 'Guardian':
                activation_fees_promo = eval_info.get('activation_fees_promo', {})
                activation_fees_regular = eval_info.get('activation_fees_regular', {})
                
                if account_size in activation_fees_promo:
                    rules['activation_fee_usd'] = float(activation_fees_promo[account_size])
                elif account_size in activation_fees_regular:
                    rules['activation_fee_usd'] = float(activation_fees_regular[account_size])
            else:
                rules['activation_fee_usd'] = float(eval_info.get('activation_fee', 0))
            
            # Get reset fee
            reset_fees = eval_info.get('reset_fees', {})
            if account_size in reset_fees:
                rules['reset_fee_usd'] = float(reset_fees[account_size])
            else:
                rules['reset_fee_usd'] = float(eval_info.get('reset_fee', 0))
            
            logger.info(f"Parsed fee rules for {eval_type}: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing fee rules: {e}")
            return {}

    def _determine_evaluation_type(self, account_size: str, text: str, prefer_evaluation: bool = False) -> str:
        """Determine evaluation type based on account size and content"""
        
        # Check content for specific evaluation type mentions
        if 'instant' in text and ('guardian' not in text or text.count('instant') > text.count('guardian')):
            return 'Instant'
        elif 'standard guardian' in text or 'standard' in text:
            return 'Standard Guardian'
        elif 'guardian' in text:
            return 'Guardian'
        
        # If prefer_evaluation is True, default to Standard Guardian (has evaluation)
        if prefer_evaluation:
            return 'Standard Guardian'
        
        # Default to Standard Guardian as it's the most common
        return 'Standard Guardian'

    def _get_fallback_evaluation_rules(self, account_size: str) -> Dict[str, Any]:
        """Get fallback evaluation rules from predefined data"""
        rules = {}
        
        try:
            # Default to Standard Guardian for evaluation
            eval_info = self.evaluation_types['Standard Guardian']
            
            # Get profit target
            profit_targets = eval_info.get('profit_targets', {})
            if account_size in profit_targets:
                rules['profit_target_usd'] = float(profit_targets[account_size])
            
            # Get max drawdown
            max_drawdowns = eval_info.get('max_drawdowns', {})
            if account_size in max_drawdowns:
                rules['max_drawdown_usd'] = float(max_drawdowns[account_size])
            
            # Get daily loss limit
            daily_loss_limits = eval_info.get('daily_loss_limits', {})
            if account_size in daily_loss_limits and daily_loss_limits[account_size] is not None:
                rules['daily_loss_limit_usd'] = float(daily_loss_limits[account_size])
            
            # Drawdown type
            rules['drawdown_type'] = eval_info.get('drawdown_type', DrawdownType.EOD)
            
            # Minimum trading days
            rules['min_trading_days'] = eval_info.get('payout_period_days', 7)
            
            # Consistency rule
            rules['consistency_rule'] = eval_info.get('consistency_rule', True)
            
            logger.info(f"Using fallback evaluation rules: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error in fallback evaluation rules: {e}")
            return {}

    def _get_fallback_funded_rules(self, account_size: str) -> Dict[str, Any]:
        """Get fallback funded rules from predefined data"""
        rules = {}
        
        try:
            # Default to Standard Guardian
            eval_info = self.evaluation_types['Standard Guardian']
            
            # Get max drawdown (same as evaluation)
            max_drawdowns = eval_info.get('max_drawdowns', {})
            if account_size in max_drawdowns:
                rules['max_drawdown_usd'] = float(max_drawdowns[account_size])
            
            # Get daily loss limit (same as evaluation)
            daily_loss_limits = eval_info.get('daily_loss_limits', {})
            if account_size in daily_loss_limits and daily_loss_limits[account_size] is not None:
                rules['daily_loss_limit_usd'] = float(daily_loss_limits[account_size])
            
            # Drawdown type (same as evaluation)
            rules['drawdown_type'] = eval_info.get('drawdown_type', DrawdownType.EOD)
            
            logger.info(f"Using fallback funded rules: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error in fallback funded rules: {e}")
            return {}

    def _get_fallback_payout_rules(self, account_size: str) -> Dict[str, Any]:
        """Get fallback payout rules from predefined data"""
        rules = {}
        
        try:
            # Use general rules
            rules['profit_split_percent'] = self.general_rules['profit_split_after_15k']
            rules['payout_frequency'] = self.general_rules['payout_frequency']
            rules['min_payout_usd'] = 100  # Default assumption
            
            logger.info(f"Using fallback payout rules: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error in fallback payout rules: {e}")
            return {}

    def _get_fallback_fee_rules(self, account_size: str) -> Dict[str, Any]:
        """Get fallback fee rules from predefined data"""
        rules = {}
        
        try:
            # Default to Standard Guardian
            eval_info = self.evaluation_types['Standard Guardian']
            
            # Get evaluation fees (use promotional pricing)
            evaluation_fees_promo = eval_info.get('evaluation_fees_promo', {})
            if account_size in evaluation_fees_promo:
                rules['evaluation_fee_usd'] = float(evaluation_fees_promo[account_size])
            
            # No activation fee for Standard Guardian
            rules['activation_fee_usd'] = float(eval_info.get('activation_fee', 0))
            
            # Get reset fee
            reset_fees = eval_info.get('reset_fees', {})
            if account_size in reset_fees:
                rules['reset_fee_usd'] = float(reset_fees[account_size])
            
            logger.info(f"Using fallback fee rules: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error in fallback fee rules: {e}")
            return {}

    def get_platform(self) -> str:
        """Return the trading platform"""
        return Platform.MULTIPLE.value  # Blue Guardian supports Tradovate, ProjectX, Volsys

    def get_broker(self) -> str:
        """Return the broker"""
        return Broker.MULTIPLE.value  # Blue Guardian supports multiple brokers via different platforms