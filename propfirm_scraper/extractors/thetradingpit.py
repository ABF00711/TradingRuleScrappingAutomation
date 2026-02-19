"""
The Trading Pit Extractor

Extracts trading rules from The Trading Pit website.
Website: https://thetradingpit.com/
CFDs: https://thetradingpit.com/cfds-prop-trading
Futures: https://thetradingpit.com/futures
Trading Rules: https://thetradingpit.com/trading-rules
FAQ: https://thetradingpit.com/faq
"""

import re
import logging
from typing import Dict, List, Optional, Any
from playwright.async_api import Page
from bs4 import BeautifulSoup
from .base_extractor import BaseExtractor
from ..config.enums import DrawdownType, PayoutFrequency, Platform, Broker

logger = logging.getLogger(__name__)


class TheTradingPitExtractor(BaseExtractor):
    """Extractor for The Trading Pit trading rules"""
    
    def __init__(self, site_config):
        super().__init__(site_config)
        self.main_url = "https://thetradingpit.com"
        self.cfds_url = "https://thetradingpit.com/cfds-prop-trading"
        self.futures_url = "https://thetradingpit.com/futures"
        self.rules_url = "https://thetradingpit.com/trading-rules"
        self.faq_url = "https://thetradingpit.com/faq"
        
        # Product type data mapping based on research
        self.product_types = {
            'CFDs Prime': {
                'account_sizes': ['$5,000', '$10,000', '$20,000', '$50,000', '$100,000', '$200,000'],
                'profit_split': 80,
                'min_payout_usd': 100,
                'payout_frequency': PayoutFrequency.BIWEEKLY,  # Every 14 days
                'min_trading_days_payout': 5,  # 5 unique trading days per payout
                'min_profitable_days_challenge': 3,  # 3 profitable days for challenge
                'profitable_day_threshold_percent': 0.5,  # 0.5% of initial balance
                'inactivity_days': 21,
                'max_accounts': 4,
                'max_total_balance': 400000,
                'drawdown_type': DrawdownType.STATIC,  # Static max drawdown
                'daily_drawdown_time': '16:15 CT',
                'news_trading_prohibited': ['$100,000', '$200,000'],  # Only for larger accounts
                'has_evaluation': True
            },
            'Futures Prime': {
                'account_sizes': ['$50,000', '$100,000', '$150,000'],
                'profit_targets': {
                    '$50,000': 3000,
                    '$100,000': 6000,
                    '$150,000': 9000
                },
                'daily_pause_limits': {
                    '$50,000': 1000,
                    '$100,000': 2000,
                    '$150,000': 3000
                },
                'max_drawdowns': {
                    '$50,000': 2000,
                    '$100,000': 3000,
                    '$150,000': 4500
                },
                'challenge_fees': {
                    '$50,000': 99,
                    '$100,000': 189,
                    '$150,000': 289
                },
                'reset_fees': {
                    '$50,000': 79,
                    '$100,000': 149,
                    '$150,000': 229
                },
                'extend_fees': {
                    '$50,000': 99,
                    '$100,000': 189,
                    '$150,000': 289
                },
                'activation_fee': 129,
                'contract_limits': {
                    '$50,000': {'standard': 5, 'micros': 50},
                    '$100,000': {'standard': 10, 'micros': 100},
                    '$150,000': {'standard': 15, 'micros': 150}
                },
                'profit_split': 80,
                'min_payout_usd': 200,
                'payout_frequency': PayoutFrequency.WEEKLY,  # Every 7 days after 2nd payout
                'min_trading_days_challenge': 3,  # 3 unique trading days per phase
                'consistency_rule_percent': 40,  # 40% of profit target (best day limit)
                'inactivity_days': 21,
                'max_accounts': 5,
                'overnight_positions_closed': '15:55 CT',
                'drawdown_type': DrawdownType.TRAILING,  # Trailing on EOD Balance
                'daily_pause_time': '16:15 CT',
                'news_trading_allowed': True,  # News trading allowed for Futures
                'has_evaluation': True
            }
        }
        
        # General rules
        self.general_rules = {
            'withdrawal_fee_percent': 1,  # 1% fee on profit share
            'payout_processing': '1 business day review + 24 hours processing',
            'scaling_plan_cfds': {
                'min_months_active': 2,
                'min_payouts': 2,
                'min_profit_percent': 10,
                'scale_increase_percent': 25
            },
            'scaling_plan_futures': {
                'based_on': 'end-of-day profit',
                'calculation_time': '16:00 CT'
            }
        }

    async def get_account_sizes(self, page: Page) -> List[str]:
        """Extract all available account sizes"""
        logger.info("Extracting account sizes for The Trading Pit")
        
        try:
            account_sizes = set()
            
            # First, try to get Futures account sizes (static content)
            try:
                await page.goto(self.futures_url, wait_until="networkidle")
                await page.wait_for_timeout(3000)
                
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                text = soup.get_text().lower()
                
                # Look for Futures account sizes
                futures_sizes = self._extract_sizes_from_text(text)
                account_sizes.update(futures_sizes)
                
                logger.info(f"Found Futures account sizes: {futures_sizes}")
                
            except Exception as e:
                logger.warning(f"Error extracting Futures account sizes: {e}")
            
            # Then, try to get CFDs account sizes (dynamic content)
            try:
                await page.goto(self.cfds_url, wait_until="networkidle")
                await page.wait_for_timeout(5000)  # Wait longer for dynamic content
                
                # Try to interact with account size selectors
                try:
                    # Look for account size buttons or dropdowns
                    size_selectors = await page.query_selector_all('button, select option, .account-size, [data-size]')
                    for selector in size_selectors:
                        text = await selector.inner_text()
                        if '$' in text and any(char.isdigit() for char in text):
                            size = self._normalize_account_size(text)
                            if size:
                                account_sizes.add(size)
                except Exception as e:
                    logger.warning(f"Error interacting with CFDs selectors: {e}")
                
                # Also parse the page content
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                text = soup.get_text().lower()
                
                cfds_sizes = self._extract_sizes_from_text(text)
                account_sizes.update(cfds_sizes)
                
                logger.info(f"Found CFDs account sizes: {cfds_sizes}")
                
            except Exception as e:
                logger.warning(f"Error extracting CFDs account sizes: {e}")
            
            # If no sizes found, use predefined data
            if not account_sizes:
                logger.warning("No account sizes found in content, using predefined list")
                for product_type, data in self.product_types.items():
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
            for product_type, data in self.product_types.items():
                all_sizes.update(data['account_sizes'])
            return sorted(list(all_sizes), key=lambda x: float(x.replace('$', '').replace(',', '')))

    async def extract_evaluation_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract evaluation phase rules"""
        logger.info(f"Extracting evaluation rules for {account_size}")
        
        try:
            # Determine product type based on account size
            product_type = self._determine_product_type(account_size)
            
            if product_type == 'Futures Prime':
                # Navigate to futures page for static data
                await page.goto(self.futures_url, wait_until="networkidle")
                await page.wait_for_timeout(3000)
                
                content = await page.content()
                rules = await self._parse_futures_evaluation_rules(content, account_size)
            else:
                # Navigate to CFDs page for dynamic data
                await page.goto(self.cfds_url, wait_until="networkidle")
                await page.wait_for_timeout(5000)
                
                content = await page.content()
                rules = await self._parse_cfds_evaluation_rules(content, account_size)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting evaluation rules: {e}")
            return self._get_fallback_evaluation_rules(account_size)

    async def extract_funded_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract funded account rules"""
        logger.info(f"Extracting funded rules for {account_size}")
        
        try:
            # Determine product type
            product_type = self._determine_product_type(account_size)
            
            if product_type == 'Futures Prime':
                # Use same content as evaluation for Futures
                await page.goto(self.futures_url, wait_until="networkidle")
                await page.wait_for_timeout(3000)
                
                content = await page.content()
                rules = await self._parse_futures_funded_rules(content, account_size)
            else:
                # Use same content as evaluation for CFDs
                await page.goto(self.cfds_url, wait_until="networkidle")
                await page.wait_for_timeout(5000)
                
                content = await page.content()
                rules = await self._parse_cfds_funded_rules(content, account_size)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting funded rules: {e}")
            return self._get_fallback_funded_rules(account_size)

    async def extract_payout_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract payout rules"""
        logger.info(f"Extracting payout rules for {account_size}")
        
        try:
            # Try trading rules page for detailed payout info
            try:
                await page.goto(self.rules_url, wait_until="networkidle")
                await page.wait_for_timeout(3000)
            except Exception as e:
                logger.warning(f"Failed to navigate to trading rules: {e}")
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
            # Determine product type
            product_type = self._determine_product_type(account_size)
            
            if product_type == 'Futures Prime':
                # Futures has static pricing
                await page.goto(self.futures_url, wait_until="networkidle")
                await page.wait_for_timeout(3000)
                
                content = await page.content()
                rules = await self._parse_futures_fee_rules(content, account_size)
            else:
                # CFDs may have dynamic pricing
                await page.goto(self.cfds_url, wait_until="networkidle")
                await page.wait_for_timeout(5000)
                
                content = await page.content()
                rules = await self._parse_cfds_fee_rules(content, account_size)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting fee rules: {e}")
            return self._get_fallback_fee_rules(account_size)

    def _extract_sizes_from_text(self, text: str) -> List[str]:
        """Extract account sizes from text content"""
        sizes = set()
        
        # Look for various account size patterns
        size_patterns = [
            r'\$5,?000',
            r'\$10,?000',
            r'\$20,?000',
            r'\$50,?000',
            r'\$100,?000',
            r'\$150,?000',
            r'\$200,?000'
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

    def _determine_product_type(self, account_size: str) -> str:
        """Determine product type based on account size"""
        
        # Convert account size to numeric value
        try:
            size_value = float(account_size.replace('$', '').replace(',', ''))
        except ValueError:
            return 'CFDs Prime'  # Default
        
        # Futures Prime account sizes: $50K, $100K, $150K
        if size_value in [50000, 100000, 150000]:
            return 'Futures Prime'
        
        # CFDs Prime account sizes: $5K, $10K, $20K, $50K, $100K, $200K
        # Note: $50K and $100K can be both, but we'll check context or default to CFDs
        return 'CFDs Prime'

    async def _parse_futures_evaluation_rules(self, content: str, account_size: str) -> Dict[str, Any]:
        """Parse Futures evaluation rules from HTML content"""
        rules = {}
        
        try:
            product_info = self.product_types['Futures Prime']
            
            # Get profit target from predefined data
            profit_targets = product_info.get('profit_targets', {})
            if account_size in profit_targets:
                rules['profit_target_usd'] = float(profit_targets[account_size])
            
            # Get max drawdown from predefined data
            max_drawdowns = product_info.get('max_drawdowns', {})
            if account_size in max_drawdowns:
                rules['max_drawdown_usd'] = float(max_drawdowns[account_size])
            
            # Get daily pause limit (similar to daily loss limit)
            daily_pause_limits = product_info.get('daily_pause_limits', {})
            if account_size in daily_pause_limits:
                rules['daily_loss_limit_usd'] = float(daily_pause_limits[account_size])
            
            # Drawdown type
            rules['drawdown_type'] = product_info.get('drawdown_type', DrawdownType.TRAILING)
            
            # Minimum trading days
            rules['min_trading_days'] = product_info.get('min_trading_days_challenge', 3)
            
            # Consistency rule
            consistency_percent = product_info.get('consistency_rule_percent', 40)
            if rules.get('profit_target_usd'):
                rules['consistency_rule'] = True
            else:
                rules['consistency_rule'] = False
            
            logger.info(f"Parsed Futures evaluation rules: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing Futures evaluation rules: {e}")
            return {}

    async def _parse_cfds_evaluation_rules(self, content: str, account_size: str) -> Dict[str, Any]:
        """Parse CFDs evaluation rules from HTML content"""
        rules = {}
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text().lower()
            
            product_info = self.product_types['CFDs Prime']
            
            # Try to extract profit target from content
            profit_target_patterns = [
                rf'profit target[:\s]*\$?([0-9,]+)',
                rf'target[:\s]*\$?([0-9,]+)',
                rf'{account_size.replace("$", "").replace(",", "")}[^0-9]*target[:\s]*\$?([0-9,]+)'
            ]
            
            for pattern in profit_target_patterns:
                match = re.search(pattern, text)
                if match:
                    rules['profit_target_usd'] = float(match.group(1).replace(',', ''))
                    break
            
            # Try to extract drawdown from content
            drawdown_patterns = [
                rf'drawdown[:\s]*\$?([0-9,]+)',
                rf'max[^0-9]*drawdown[:\s]*\$?([0-9,]+)',
                rf'maximum[^0-9]*drawdown[:\s]*\$?([0-9,]+)'
            ]
            
            for pattern in drawdown_patterns:
                match = re.search(pattern, text)
                if match:
                    rules['max_drawdown_usd'] = float(match.group(1).replace(',', ''))
                    break
            
            # Try to extract daily drawdown
            daily_patterns = [
                rf'daily[^0-9]*drawdown[:\s]*\$?([0-9,]+)',
                rf'daily[^0-9]*limit[:\s]*\$?([0-9,]+)'
            ]
            
            for pattern in daily_patterns:
                match = re.search(pattern, text)
                if match:
                    rules['daily_loss_limit_usd'] = float(match.group(1).replace(',', ''))
                    break
            
            # Drawdown type
            rules['drawdown_type'] = product_info.get('drawdown_type', DrawdownType.STATIC)
            
            # Minimum profitable days
            rules['min_trading_days'] = product_info.get('min_profitable_days_challenge', 3)
            
            # Consistency rule (CFDs don't have explicit consistency rule like Futures)
            rules['consistency_rule'] = False
            
            logger.info(f"Parsed CFDs evaluation rules: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing CFDs evaluation rules: {e}")
            return {}

    async def _parse_futures_funded_rules(self, content: str, account_size: str) -> Dict[str, Any]:
        """Parse Futures funded rules from HTML content"""
        rules = {}
        
        try:
            product_info = self.product_types['Futures Prime']
            
            # Same drawdown rules as evaluation
            max_drawdowns = product_info.get('max_drawdowns', {})
            if account_size in max_drawdowns:
                rules['max_drawdown_usd'] = float(max_drawdowns[account_size])
            
            # Same daily pause limits as evaluation
            daily_pause_limits = product_info.get('daily_pause_limits', {})
            if account_size in daily_pause_limits:
                rules['daily_loss_limit_usd'] = float(daily_pause_limits[account_size])
            
            # Drawdown type (same as evaluation)
            rules['drawdown_type'] = product_info.get('drawdown_type', DrawdownType.TRAILING)
            
            logger.info(f"Parsed Futures funded rules: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing Futures funded rules: {e}")
            return {}

    async def _parse_cfds_funded_rules(self, content: str, account_size: str) -> Dict[str, Any]:
        """Parse CFDs funded rules from HTML content"""
        rules = {}
        
        try:
            # Same rules as evaluation for CFDs
            eval_rules = await self._parse_cfds_evaluation_rules(content, account_size)
            
            # Copy relevant rules
            if 'max_drawdown_usd' in eval_rules:
                rules['max_drawdown_usd'] = eval_rules['max_drawdown_usd']
            if 'daily_loss_limit_usd' in eval_rules:
                rules['daily_loss_limit_usd'] = eval_rules['daily_loss_limit_usd']
            if 'drawdown_type' in eval_rules:
                rules['drawdown_type'] = eval_rules['drawdown_type']
            
            logger.info(f"Parsed CFDs funded rules: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing CFDs funded rules: {e}")
            return {}

    async def _parse_payout_rules(self, content: str, account_size: str) -> Dict[str, Any]:
        """Parse payout rules from HTML content"""
        rules = {}
        
        try:
            # Determine product type
            product_type = self._determine_product_type(account_size)
            product_info = self.product_types[product_type]
            
            # Profit split (80% for both CFDs and Futures)
            rules['profit_split_percent'] = product_info.get('profit_split', 80)
            
            # Payout frequency
            rules['payout_frequency'] = product_info.get('payout_frequency', PayoutFrequency.BIWEEKLY)
            
            # Minimum payout
            rules['min_payout_usd'] = product_info.get('min_payout_usd', 100)
            
            logger.info(f"Parsed payout rules for {product_type}: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing payout rules: {e}")
            return {}

    async def _parse_futures_fee_rules(self, content: str, account_size: str) -> Dict[str, Any]:
        """Parse Futures fee rules from HTML content"""
        rules = {}
        
        try:
            product_info = self.product_types['Futures Prime']
            
            # Challenge fee
            challenge_fees = product_info.get('challenge_fees', {})
            if account_size in challenge_fees:
                rules['evaluation_fee_usd'] = float(challenge_fees[account_size])
            
            # Activation fee
            rules['activation_fee_usd'] = float(product_info.get('activation_fee', 129))
            
            # Reset fee
            reset_fees = product_info.get('reset_fees', {})
            if account_size in reset_fees:
                rules['reset_fee_usd'] = float(reset_fees[account_size])
            
            logger.info(f"Parsed Futures fee rules: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing Futures fee rules: {e}")
            return {}

    async def _parse_cfds_fee_rules(self, content: str, account_size: str) -> Dict[str, Any]:
        """Parse CFDs fee rules from HTML content"""
        rules = {}
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text().lower()
            
            # Try to extract fees from content
            fee_patterns = [
                rf'fee[:\s]*\$?([0-9,]+)',
                rf'price[:\s]*\$?([0-9,]+)',
                rf'cost[:\s]*\$?([0-9,]+)',
                rf'{account_size.replace("$", "").replace(",", "")}[^0-9]*\$?([0-9,]+)'
            ]
            
            for pattern in fee_patterns:
                match = re.search(pattern, text)
                if match:
                    rules['evaluation_fee_usd'] = float(match.group(1).replace(',', ''))
                    break
            
            # CFDs typically don't have activation fee
            rules['activation_fee_usd'] = 0.0
            
            # Reset fee (try to extract or use reasonable default)
            reset_patterns = [
                rf'reset[^0-9]*fee[:\s]*\$?([0-9,]+)',
                rf'reset[:\s]*\$?([0-9,]+)'
            ]
            
            for pattern in reset_patterns:
                match = re.search(pattern, text)
                if match:
                    rules['reset_fee_usd'] = float(match.group(1).replace(',', ''))
                    break
            else:
                # Default reset fee based on account size
                account_value = float(account_size.replace('$', '').replace(',', ''))
                rules['reset_fee_usd'] = max(50, account_value * 0.001)  # 0.1% or $50 minimum
            
            logger.info(f"Parsed CFDs fee rules: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing CFDs fee rules: {e}")
            return {}

    def _get_fallback_evaluation_rules(self, account_size: str) -> Dict[str, Any]:
        """Get fallback evaluation rules from predefined data"""
        rules = {}
        
        try:
            product_type = self._determine_product_type(account_size)
            product_info = self.product_types[product_type]
            
            if product_type == 'Futures Prime':
                # Use predefined Futures data
                profit_targets = product_info.get('profit_targets', {})
                if account_size in profit_targets:
                    rules['profit_target_usd'] = float(profit_targets[account_size])
                
                max_drawdowns = product_info.get('max_drawdowns', {})
                if account_size in max_drawdowns:
                    rules['max_drawdown_usd'] = float(max_drawdowns[account_size])
                
                daily_pause_limits = product_info.get('daily_pause_limits', {})
                if account_size in daily_pause_limits:
                    rules['daily_loss_limit_usd'] = float(daily_pause_limits[account_size])
            
            # Common rules
            rules['drawdown_type'] = product_info.get('drawdown_type', DrawdownType.STATIC)
            rules['min_trading_days'] = product_info.get('min_trading_days_challenge', 3)
            rules['consistency_rule'] = product_type == 'Futures Prime'
            
            logger.info(f"Using fallback evaluation rules for {product_type}: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error in fallback evaluation rules: {e}")
            return {}

    def _get_fallback_funded_rules(self, account_size: str) -> Dict[str, Any]:
        """Get fallback funded rules from predefined data"""
        rules = {}
        
        try:
            product_type = self._determine_product_type(account_size)
            product_info = self.product_types[product_type]
            
            if product_type == 'Futures Prime':
                # Use predefined Futures data
                max_drawdowns = product_info.get('max_drawdowns', {})
                if account_size in max_drawdowns:
                    rules['max_drawdown_usd'] = float(max_drawdowns[account_size])
                
                daily_pause_limits = product_info.get('daily_pause_limits', {})
                if account_size in daily_pause_limits:
                    rules['daily_loss_limit_usd'] = float(daily_pause_limits[account_size])
            
            # Common rules
            rules['drawdown_type'] = product_info.get('drawdown_type', DrawdownType.STATIC)
            
            logger.info(f"Using fallback funded rules for {product_type}: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error in fallback funded rules: {e}")
            return {}

    def _get_fallback_payout_rules(self, account_size: str) -> Dict[str, Any]:
        """Get fallback payout rules from predefined data"""
        rules = {}
        
        try:
            product_type = self._determine_product_type(account_size)
            product_info = self.product_types[product_type]
            
            rules['profit_split_percent'] = product_info.get('profit_split', 80)
            rules['payout_frequency'] = product_info.get('payout_frequency', PayoutFrequency.BIWEEKLY)
            rules['min_payout_usd'] = product_info.get('min_payout_usd', 100)
            
            logger.info(f"Using fallback payout rules for {product_type}: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error in fallback payout rules: {e}")
            return {}

    def _get_fallback_fee_rules(self, account_size: str) -> Dict[str, Any]:
        """Get fallback fee rules from predefined data"""
        rules = {}
        
        try:
            product_type = self._determine_product_type(account_size)
            product_info = self.product_types[product_type]
            
            if product_type == 'Futures Prime':
                # Use predefined Futures fees
                challenge_fees = product_info.get('challenge_fees', {})
                if account_size in challenge_fees:
                    rules['evaluation_fee_usd'] = float(challenge_fees[account_size])
                
                rules['activation_fee_usd'] = float(product_info.get('activation_fee', 129))
                
                reset_fees = product_info.get('reset_fees', {})
                if account_size in reset_fees:
                    rules['reset_fee_usd'] = float(reset_fees[account_size])
            else:
                # CFDs - estimate fees based on account size
                account_value = float(account_size.replace('$', '').replace(',', ''))
                rules['evaluation_fee_usd'] = max(100, account_value * 0.01)  # 1% or $100 minimum
                rules['activation_fee_usd'] = 0.0
                rules['reset_fee_usd'] = max(50, account_value * 0.001)  # 0.1% or $50 minimum
            
            logger.info(f"Using fallback fee rules for {product_type}: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error in fallback fee rules: {e}")
            return {}

    def get_platform(self) -> str:
        """Return the trading platform"""
        return Platform.MULTIPLE.value  # The Trading Pit supports multiple platforms

    def get_broker(self) -> str:
        """Return the broker"""
        return Broker.MULTIPLE.value  # The Trading Pit supports multiple brokers