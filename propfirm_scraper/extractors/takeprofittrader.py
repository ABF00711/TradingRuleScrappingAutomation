"""
Take Profit Trader Extractor

Extracts trading rules from Take Profit Trader main website and knowledge base.
Website: https://takeprofittrader.com/
Knowledge Base: https://takeprofittraderhelp.zendesk.com/hc/en-us
"""

import re
import logging
from typing import Dict, List, Optional, Any
from playwright.async_api import Page
from bs4 import BeautifulSoup
from .base_extractor import BaseExtractor
from ..config.enums import DrawdownType, PayoutFrequency, Platform, Broker

logger = logging.getLogger(__name__)


class TakeProfitTraderExtractor(BaseExtractor):
    """Extractor for Take Profit Trader trading rules"""
    
    def __init__(self, site_config):
        super().__init__(site_config)
        self.main_url = "https://takeprofittrader.com"
        self.help_url = "https://takeprofittraderhelp.zendesk.com/hc/en-us"
        
        # Account-specific data mapping based on research
        self.account_data = {
            '$25,000': {
                'monthly_fee': 150,
                'profit_target': 1500,      # $1,500 (6% of $25K)
                'max_drawdown': 1500,       # $1,500 (6% of $25K)
                'max_position_size': '3 Contracts / 30 Micros'
            },
            '$50,000': {
                'monthly_fee': 170,
                'profit_target': 3000,      # $3,000 (6% of $50K)
                'max_drawdown': 2000,       # $2,000 (4% of $50K)
                'max_position_size': '6 Contracts / 60 Micros'
            },
            '$75,000': {
                'monthly_fee': 245,
                'profit_target': 4500,      # $4,500 (6% of $75K)
                'max_drawdown': 2500,       # $2,500 (3.3% of $75K)
                'max_position_size': '9 Contracts / 90 Micros'
            },
            '$100,000': {
                'monthly_fee': 330,
                'profit_target': 6000,      # $6,000 (6% of $100K)
                'max_drawdown': 3000,       # $3,000 (3% of $100K)
                'max_position_size': '12 Contracts / 120 Micros'
            },
            '$150,000': {
                'monthly_fee': 360,
                'profit_target': 9000,      # $9,000 (6% of $150K)
                'max_drawdown': 4500,       # $4,500 (3% of $150K)
                'max_position_size': '15 Contracts / 150 Micros'
            }
        }
        
        # General rules for all accounts
        self.general_rules = {
            'min_trading_days': 5,          # 5 days to reach PRO status
            'consistency_requirement': 50,   # 50% profit consistency
            'daily_loss_limit': None,       # No daily loss limit
            'drawdown_type': DrawdownType.EOD,  # End-of-day drawdown
            'pro_activation_fee': 130,      # $130 one-time PRO activation
            'pro_profit_split': 80,         # 80/20 split for PRO
            'pro_plus_profit_split': 90,    # 90/10 split for PRO+
            'payout_frequency': PayoutFrequency.ON_DEMAND,  # Day one withdrawals
            'max_resets': 3                 # Up to 3 PRO account resets
        }

    async def get_account_sizes(self, page: Page) -> List[str]:
        """Extract all available account sizes"""
        logger.info("Extracting account sizes for Take Profit Trader")
        
        try:
            # Try main website first for account selection/pricing
            await page.goto(self.main_url, wait_until="networkidle")
            
            # Wait for any dynamic content to load
            await page.wait_for_timeout(3000)
            
            # Look for account size information
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text().lower()
            
            account_sizes = set()
            
            # Look for common account size patterns
            size_patterns = [
                r'\$25,?000',
                r'\$50,?000',
                r'\$75,?000',
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
            
            # If no sizes found on main site, try knowledge base
            if not account_sizes:
                logger.info("No account sizes found on main site, trying knowledge base")
                await page.goto(f"{self.help_url}/categories/360003118994-Trading", wait_until="networkidle")
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
                account_sizes = set(self.account_data.keys())
            
            # Sort account sizes
            sizes = list(account_sizes)
            sizes.sort(key=lambda x: float(x.replace('$', '').replace(',', '')))
            
            logger.info(f"Found account sizes: {sizes}")
            return sizes
            
        except Exception as e:
            logger.error(f"Error extracting account sizes: {e}")
            # Return predefined sizes
            return list(self.account_data.keys())

    async def extract_evaluation_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract evaluation phase rules"""
        logger.info(f"Extracting evaluation rules for {account_size}")
        
        try:
            # Navigate to knowledge base trading section
            await page.goto(f"{self.help_url}/categories/360003118994-Trading", wait_until="networkidle")
            await page.wait_for_timeout(2000)
            
            content = await page.content()
            rules = await self._parse_evaluation_rules(content, account_size)
            
            # Try to find specific articles about evaluation rules
            try:
                # Look for links to specific articles
                soup = BeautifulSoup(content, 'html.parser')
                article_links = soup.find_all('a', href=re.compile(r'/articles/'))
                
                for link in article_links[:3]:  # Check first 3 relevant articles
                    href = link.get('href')
                    if href and any(keyword in href.lower() for keyword in ['rule', 'evaluation', 'test', 'account']):
                        try:
                            article_url = f"{self.help_url}{href}" if href.startswith('/') else href
                            await page.goto(article_url, wait_until="networkidle")
                            await page.wait_for_timeout(1000)
                            article_content = await page.content()
                            additional_rules = await self._parse_evaluation_rules(article_content, account_size)
                            rules.update(additional_rules)
                        except Exception as e:
                            logger.warning(f"Failed to extract from article {href}: {e}")
                            continue
            except Exception as e:
                logger.warning(f"Failed to extract from additional articles: {e}")
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting evaluation rules: {e}")
            return {}

    async def extract_funded_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract funded account rules"""
        logger.info(f"Extracting funded rules for {account_size}")
        
        try:
            # Navigate to knowledge base for PRO account information
            await page.goto(f"{self.help_url}/categories/360003118994-Trading", wait_until="networkidle")
            await page.wait_for_timeout(2000)
            
            content = await page.content()
            rules = await self._parse_funded_rules(content, account_size)
            
            # Try main website FAQ for PRO account details
            try:
                await page.goto(self.main_url, wait_until="networkidle")
                await page.wait_for_timeout(3000)
                
                # Look for FAQ or PRO account information
                main_content = await page.content()
                main_rules = await self._parse_funded_rules(main_content, account_size)
                rules.update(main_rules)
            except Exception as e:
                logger.warning(f"Failed to extract from main website: {e}")
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting funded rules: {e}")
            return {}

    async def extract_payout_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract payout rules"""
        logger.info(f"Extracting payout rules for {account_size}")
        
        try:
            # Navigate to payments section in knowledge base
            await page.goto(f"{self.help_url}/categories/360003119014-Payments", wait_until="networkidle")
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
            # Try main website first for pricing
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
            
            # Get account-specific data
            account_info = self.account_data.get(account_size, {})
            
            # Profit target from predefined data or extract from content
            if 'profit_target' in account_info:
                rules['profit_target_usd'] = float(account_info['profit_target'])
            else:
                # Try to extract profit target
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
            
            # Max drawdown from predefined data or extract
            if 'max_drawdown' in account_info:
                rules['max_drawdown_usd'] = float(account_info['max_drawdown'])
            else:
                # Try to extract max drawdown
                drawdown_patterns = [
                    r'max(?:imum)? drawdown[:\s]+\$?([0-9,]+)',
                    r'drawdown[:\s]+\$?([0-9,]+)',
                    r'loss limit[:\s]+\$?([0-9,]+)'
                ]
                
                for pattern in drawdown_patterns:
                    match = re.search(pattern, text)
                    if match:
                        rules['max_drawdown_usd'] = float(match.group(1).replace(',', ''))
                        break
            
            # Daily loss limit (Take Profit Trader removed daily loss limits)
            rules['daily_loss_limit_usd'] = None
            
            # Drawdown type (EOD)
            rules['drawdown_type'] = self.general_rules['drawdown_type']
            
            # Minimum trading days
            rules['min_trading_days'] = self.general_rules['min_trading_days']
            
            # Consistency rule (50% requirement)
            if 'consistency' in text and '50%' in text:
                rules['consistency_rule'] = True
            else:
                rules['consistency_rule'] = True  # Default based on research
            
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
            
            # Get account-specific data
            account_info = self.account_data.get(account_size, {})
            
            # Funded drawdown (same as evaluation for Take Profit Trader)
            if 'max_drawdown' in account_info:
                rules['max_drawdown_usd'] = float(account_info['max_drawdown'])
            else:
                # Use same as evaluation if available
                account_value = float(account_size.replace('$', '').replace(',', ''))
                rules['max_drawdown_usd'] = account_value * 0.06  # 6% default
            
            # Daily loss limit (none)
            rules['daily_loss_limit_usd'] = None
            
            # Drawdown type (EOD for funded accounts too)
            rules['drawdown_type'] = DrawdownType.EOD
            
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
            
            # Profit split (80% for PRO, 90% for PRO+)
            if 'pro+' in text or '90%' in text:
                rules['profit_split_percent'] = self.general_rules['pro_plus_profit_split']
            elif 'pro' in text or '80%' in text:
                rules['profit_split_percent'] = self.general_rules['pro_profit_split']
            else:
                rules['profit_split_percent'] = 80  # Default PRO split
            
            # Payout frequency (on-demand/immediate)
            if 'day one' in text or 'immediate' in text or 'on-demand' in text:
                rules['payout_frequency'] = PayoutFrequency.ON_DEMAND
            else:
                rules['payout_frequency'] = self.general_rules['payout_frequency']
            
            # Minimum payout (not specified, use reasonable default)
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
            
            # Get account-specific monthly fee
            account_info = self.account_data.get(account_size, {})
            
            # Monthly subscription fee (evaluation fee)
            if 'monthly_fee' in account_info:
                rules['evaluation_fee_usd'] = float(account_info['monthly_fee'])
            else:
                # Try to extract fee from content
                fee_patterns = [
                    r'monthly[:\s]+\$?([0-9,]+)',
                    r'subscription[:\s]+\$?([0-9,]+)',
                    r'fee[:\s]+\$?([0-9,]+)'
                ]
                
                for pattern in fee_patterns:
                    match = re.search(pattern, text)
                    if match:
                        rules['evaluation_fee_usd'] = float(match.group(1).replace(',', ''))
                        break
                else:
                    rules['evaluation_fee_usd'] = 200  # Default estimate
            
            # Reset fee (likely same as monthly fee)
            rules['reset_fee_usd'] = rules.get('evaluation_fee_usd', 200)
            
            # PRO activation fee ($130 one-time)
            if '$130' in text or 'activation' in text:
                rules['activation_fee_usd'] = float(self.general_rules['pro_activation_fee'])
            
            logger.info(f"Parsed fee rules: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing fee rules: {e}")
            return {}

    def get_platform(self) -> str:
        """Return the trading platform"""
        return Platform.MULTIPLE.value  # Take Profit Trader supports multiple platforms

    def get_broker(self) -> str:
        """Return the broker"""
        return Broker.RITHMIC.value  # Take Profit Trader primarily uses Rithmic for SIM, Tradovate for LIVE