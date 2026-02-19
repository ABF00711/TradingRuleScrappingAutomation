"""
Top One Futures Extractor

Extracts trading rules from Top One Futures website.
Website: https://toponefutures.com/
Help Center: https://help.toponefutures.com/
"""

import re
import logging
from typing import Dict, List, Optional, Any
from playwright.async_api import Page
from bs4 import BeautifulSoup
from .base_extractor import BaseExtractor
from ..config.enums import DrawdownType, PayoutFrequency, Platform, Broker

logger = logging.getLogger(__name__)


class TopOneFuturesExtractor(BaseExtractor):
    """Extractor for Top One Futures trading rules"""
    
    def __init__(self, site_config):
        super().__init__(site_config)
        self.main_url = "https://toponefutures.com"
        self.help_url = "https://help.toponefutures.com"
        self.checkout_url = "https://checkout.toponefutures.com"
        
        # Account type data mapping based on research
        self.account_types = {
            'ELITE Challenge': {
                'account_sizes': ['$25,000', '$50,000', '$100,000', '$150,000'],
                'profit_target_percent': 6.0,  # 6% of account size
                'daily_loss_limits': {
                    '$25,000': 625,
                    '$50,000': 1250,
                    '$100,000': 2500,
                    '$150,000': 3750
                },
                'max_drawdowns': {
                    '$25,000': 1000,
                    '$50,000': 2000,
                    '$100,000': 3000,
                    '$150,000': 4500
                },
                'monthly_fees': {
                    '$25,000': 45,    # Promotional price (regular $69)
                    '$50,000': 68,    # Promotional price (regular $105)
                    '$100,000': 136,  # Promotional price (regular $209)
                    '$150,000': 201   # Promotional price (regular $309)
                },
                'reset_fees': {
                    '$25,000': 29,
                    '$50,000': 59,
                    '$100,000': 89,
                    '$150,000': 119
                },
                'activation_fee': 149,
                'consistency_eval': None,     # No consistency during challenge
                'consistency_funded': 25,    # 25% consistency when funded
                'min_trading_days': 1,       # Can pass in 1 day
                'drawdown_type': DrawdownType.EOD,  # End of day
                'max_accounts': 3,
                'has_evaluation': True
            },
            'INSTANT Sim Funded': {
                'account_sizes': ['$25,000', '$50,000', '$100,000', '$150,000'],
                'profit_targets_tiered': {
                    'first_payout': 6.0,     # 6% of starting balance
                    'second_payout': 5.0,    # 5% of new balance
                    'subsequent': 4.0        # 4% of new balance
                },
                'daily_loss_limits': {
                    '$25,000': 625,
                    '$50,000': 1250,
                    '$100,000': 2500,
                    '$150,000': 3750
                },
                'max_drawdowns': {
                    '$25,000': 1000,
                    '$50,000': 2000,
                    '$100,000': 3000,
                    '$150,000': 4500
                },
                'one_time_fees': {
                    '$25,000': 272,   # Promotional price (regular $419)
                    '$50,000': 441,   # Promotional price (regular $679)
                    '$100,000': 534,  # Promotional price (regular $821)
                    '$150,000': 610   # Promotional price (regular $939)
                },
                'max_payouts': {
                    '$25,000': 1500,
                    '$50,000': 2500,
                    '$100,000': 3000,
                    '$150,000': 3500
                },
                'consistency_funded': 20,    # 20% consistency
                'drawdown_type': DrawdownType.EOD,  # End of day
                'max_accounts': 3,
                'has_evaluation': False      # Instant funding
            },
            'S2F Sim PRO': {
                'account_sizes': ['$25,000', '$50,000', '$100,000', '$150,000'],
                'profit_targets_tiered': {
                    'first_payout': 6.0,     # 6% of starting balance
                    'second_payout': 5.0,    # 5% of post-payout balance
                    'subsequent': 4.0        # 4% of post-payout balance
                },
                'daily_loss_limits': {
                    '$25,000': 500,
                    '$50,000': 1000,
                    '$100,000': 2000,
                    '$150,000': 3000
                },
                'max_drawdowns': {
                    '$25,000': 1000,
                    '$50,000': 1625,
                    '$100,000': 3250,
                    '$150,000': 5000
                },
                'one_time_fees': {
                    '$25,000': 141,   # Promotional price (regular $257)
                    '$50,000': 232,   # Promotional price (regular $421)
                    '$100,000': 348,  # Promotional price (regular $632)
                    '$150,000': 400   # Promotional price (regular $727)
                },
                'ess_requirement': 20,       # 20% Equity Stability Score
                'min_trading_days': 10,      # 10 days minimum
                'drawdown_type': DrawdownType.TRAILING,  # Intraday trailing
                'max_accounts': {
                    '$25,000': 10,
                    '$50,000': 5,
                    '$100,000': 3,
                    '$150,000': 3
                },
                'has_evaluation': False      # Instant funding
            },
            'IGNITE': {
                'account_sizes': ['$25,000', '$50,000'],  # Limited sizes
                'profit_targets_tiered': {
                    'first_payout': 5.0,     # 5% of initial balance
                    'subsequent': 5.0        # 5% of new balance
                },
                'daily_loss_limits': {
                    '$25,000': 500,
                    '$50,000': 1000
                },
                'max_drawdowns': {
                    '$25,000': 1000,
                    '$50,000': 2000
                },
                'one_time_fees': {
                    '$25,000': 120,   # Promotional price (regular $218)
                    '$50,000': 219    # Promotional price (regular $398)
                },
                'consistency_funded': 15,    # 15% consistency
                'min_trading_days': 10,      # 10 days minimum
                'drawdown_type': DrawdownType.EOD,  # End of day
                'max_accounts': {
                    '$25,000': 10,
                    '$50,000': 6
                },
                'has_evaluation': False      # Instant funding
            }
        }
        
        # General rules for all accounts
        self.general_rules = {
            'profit_split': 90,              # 90% to trader, 10% to firm
            'payout_processing': '< 24 hours',  # Often < 12 hours
            'payout_frequency': PayoutFrequency.ON_DEMAND,  # Anytime after requirements
            'path_to_live': 3,               # After 3 payouts
            'news_trading': True,            # Allowed
            'support_response': '< 60 seconds'  # Average response time
        }

    async def get_account_sizes(self, page: Page) -> List[str]:
        """Extract all available account sizes"""
        logger.info("Extracting account sizes for Top One Futures")
        
        try:
            # Navigate to main website homepage
            await page.goto(self.main_url, wait_until="networkidle")
            
            # Wait for dynamic content to load
            await page.wait_for_timeout(3000)
            
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text().lower()
            
            account_sizes = set()
            
            # Look for account size patterns in tables and content
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
            
            # Also look for tables with account information
            tables = soup.find_all('table')
            for table in tables:
                table_text = table.get_text().lower()
                for pattern in size_patterns:
                    matches = re.findall(pattern, table_text)
                    for match in matches:
                        size = match.replace(',', '').replace('$', '')
                        formatted_size = f"${int(size):,}"
                        account_sizes.add(formatted_size)
            
            # If no sizes found, use predefined data
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
            # Navigate to main website for table data
            await page.goto(self.main_url, wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
            content = await page.content()
            rules = await self._parse_evaluation_rules(content, account_size)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting evaluation rules: {e}")
            # Fallback to predefined data for ELITE Challenge
            return self._get_fallback_evaluation_rules(account_size)

    async def extract_funded_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract funded account rules"""
        logger.info(f"Extracting funded rules for {account_size}")
        
        try:
            # Use same content as evaluation (tables contain both eval and funded info)
            await page.goto(self.main_url, wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
            content = await page.content()
            rules = await self._parse_funded_rules(content, account_size)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting funded rules: {e}")
            # Fallback to predefined data for ELITE Challenge
            return self._get_fallback_funded_rules(account_size)

    async def extract_payout_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract payout rules"""
        logger.info(f"Extracting payout rules for {account_size}")
        
        try:
            # Try help center for payout details
            try:
                await page.goto(f"{self.help_url}/en/", wait_until="networkidle")
                await page.wait_for_timeout(2000)
                
                # Look for payout-related articles
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Find links to payout articles
                payout_links = soup.find_all('a', href=re.compile(r'payout|withdrawal'))
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
            return {}

    async def extract_fee_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract fee information"""
        logger.info(f"Extracting fee rules for {account_size}")
        
        try:
            # Main website has pricing tables
            await page.goto(self.main_url, wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
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
            
            # Determine account type (default to ELITE Challenge for evaluation)
            account_type = self._determine_account_type(account_size, text, prefer_evaluation=True)
            account_info = self.account_types.get(account_type, self.account_types['ELITE Challenge'])
            
            # Skip if account type doesn't have evaluation
            if not account_info.get('has_evaluation', True):
                return {}
            
            # Calculate profit target
            account_value = float(account_size.replace('$', '').replace(',', ''))
            if 'profit_target_percent' in account_info:
                profit_target_percent = account_info['profit_target_percent']
                rules['profit_target_usd'] = account_value * (profit_target_percent / 100)
            elif 'profit_targets_tiered' in account_info:
                # Use first payout target for evaluation
                first_payout_percent = account_info['profit_targets_tiered']['first_payout']
                rules['profit_target_usd'] = account_value * (first_payout_percent / 100)
            
            # Get max drawdown from predefined data
            max_drawdowns = account_info.get('max_drawdowns', {})
            if account_size in max_drawdowns:
                rules['max_drawdown_usd'] = float(max_drawdowns[account_size])
            
            # Get daily loss limit from predefined data
            daily_loss_limits = account_info.get('daily_loss_limits', {})
            if account_size in daily_loss_limits:
                rules['daily_loss_limit_usd'] = float(daily_loss_limits[account_size])
            
            # Drawdown type
            rules['drawdown_type'] = account_info.get('drawdown_type', DrawdownType.EOD)
            
            # Minimum trading days
            rules['min_trading_days'] = account_info.get('min_trading_days', 1)
            
            # Consistency rule
            consistency_eval = account_info.get('consistency_eval')
            if consistency_eval is not None:
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
            
            # Determine account type
            account_type = self._determine_account_type(account_size, text)
            account_info = self.account_types.get(account_type, self.account_types['ELITE Challenge'])
            
            # Get max drawdown (same as evaluation for most types)
            max_drawdowns = account_info.get('max_drawdowns', {})
            if account_size in max_drawdowns:
                rules['max_drawdown_usd'] = float(max_drawdowns[account_size])
            
            # Get daily loss limit (same as evaluation)
            daily_loss_limits = account_info.get('daily_loss_limits', {})
            if account_size in daily_loss_limits:
                rules['daily_loss_limit_usd'] = float(daily_loss_limits[account_size])
            
            # Drawdown type (same as evaluation)
            rules['drawdown_type'] = account_info.get('drawdown_type', DrawdownType.EOD)
            
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
            
            # Profit split (90% for all accounts)
            rules['profit_split_percent'] = self.general_rules['profit_split']
            
            # Payout frequency (on-demand)
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
            
            # Determine account type
            account_type = self._determine_account_type(account_size, text)
            account_info = self.account_types.get(account_type, self.account_types['ELITE Challenge'])
            
            # Get fees based on account type
            if account_type == 'ELITE Challenge':
                # Monthly subscription + activation fee
                monthly_fees = account_info.get('monthly_fees', {})
                if account_size in monthly_fees:
                    rules['evaluation_fee_usd'] = float(monthly_fees[account_size])  # Monthly fee
                
                # Activation fee (one-time after passing)
                rules['activation_fee_usd'] = float(account_info.get('activation_fee', 149))
                
                # Reset fee
                reset_fees = account_info.get('reset_fees', {})
                if account_size in reset_fees:
                    rules['reset_fee_usd'] = float(reset_fees[account_size])
            
            else:
                # One-time fees for instant funding accounts
                one_time_fees = account_info.get('one_time_fees', {})
                if account_size in one_time_fees:
                    rules['evaluation_fee_usd'] = float(one_time_fees[account_size])
                
                # No reset fee for instant funding
                rules['reset_fee_usd'] = 0.0
            
            logger.info(f"Parsed fee rules for {account_type}: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing fee rules: {e}")
            return {}

    def _determine_account_type(self, account_size: str, text: str, prefer_evaluation: bool = False) -> str:
        """Determine account type based on account size and content"""
        
        # Check content for specific account type mentions
        if 'elite' in text and 'challenge' in text:
            return 'ELITE Challenge'
        elif 'instant sim funded' in text:
            return 'INSTANT Sim Funded'
        elif 's2f sim pro' in text or 's2f' in text:
            return 'S2F Sim PRO'
        elif 'ignite' in text:
            return 'IGNITE'
        
        # If prefer_evaluation is True, default to ELITE Challenge
        if prefer_evaluation:
            return 'ELITE Challenge'
        
        # Default based on account size availability
        if account_size in ['$25,000', '$50,000']:
            # All account types support these sizes, default to most popular
            return 'ELITE Challenge'
        else:
            # $100K and $150K - default to ELITE Challenge
            return 'ELITE Challenge'

    def get_platform(self) -> str:
        """Return the trading platform"""
        return Platform.MULTIPLE.value  # Top One Futures supports multiple platforms

    def get_broker(self) -> str:
        """Return the broker"""
        return Broker.RITHMIC.value  # Top One Futures primarily uses Rithmic

    def _get_fallback_evaluation_rules(self, account_size: str) -> Dict[str, Any]:
        """Get fallback evaluation rules from predefined data"""
        rules = {}
        
        try:
            # Default to ELITE Challenge for evaluation
            account_info = self.account_types['ELITE Challenge']
            
            # Calculate profit target
            account_value = float(account_size.replace('$', '').replace(',', ''))
            profit_target_percent = account_info['profit_target_percent']
            rules['profit_target_usd'] = account_value * (profit_target_percent / 100)
            
            # Get max drawdown from predefined data
            max_drawdowns = account_info.get('max_drawdowns', {})
            if account_size in max_drawdowns:
                rules['max_drawdown_usd'] = float(max_drawdowns[account_size])
            
            # Get daily loss limit from predefined data
            daily_loss_limits = account_info.get('daily_loss_limits', {})
            if account_size in daily_loss_limits:
                rules['daily_loss_limit_usd'] = float(daily_loss_limits[account_size])
            
            # Drawdown type
            rules['drawdown_type'] = account_info.get('drawdown_type', DrawdownType.EOD)
            
            # Minimum trading days
            rules['min_trading_days'] = account_info.get('min_trading_days', 1)
            
            # Consistency rule
            rules['consistency_rule'] = False  # No consistency during challenge
            
            logger.info(f"Using fallback evaluation rules: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error in fallback evaluation rules: {e}")
            return {}

    def _get_fallback_funded_rules(self, account_size: str) -> Dict[str, Any]:
        """Get fallback funded rules from predefined data"""
        rules = {}
        
        try:
            # Default to ELITE Challenge
            account_info = self.account_types['ELITE Challenge']
            
            # Get max drawdown (same as evaluation for ELITE Challenge)
            max_drawdowns = account_info.get('max_drawdowns', {})
            if account_size in max_drawdowns:
                rules['max_drawdown_usd'] = float(max_drawdowns[account_size])
            
            # Get daily loss limit (same as evaluation)
            daily_loss_limits = account_info.get('daily_loss_limits', {})
            if account_size in daily_loss_limits:
                rules['daily_loss_limit_usd'] = float(daily_loss_limits[account_size])
            
            # Drawdown type (same as evaluation)
            rules['drawdown_type'] = account_info.get('drawdown_type', DrawdownType.EOD)
            
            logger.info(f"Using fallback funded rules: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error in fallback funded rules: {e}")
            return {}