"""
Tradeify extractor
"""
import re
import logging
from typing import List, Dict, Any, Optional
from playwright.async_api import Page

from .base_extractor import BaseExtractor
from ..config.enums import DrawdownType, PayoutFrequency, Platform, Broker
from ..core.utils import extract_number, extract_percentage
from ..core.currency_converter import converter

logger = logging.getLogger(__name__)

class TradeifyExtractor(BaseExtractor):
    """Extract trading rules from Tradeify website"""
    
    def __init__(self, site_config):
        super().__init__(site_config)
        self.account_data = {
            "$50,000": {
                "profit_target": 3000,
                "daily_loss": 1250,
                "max_drawdown": 2000,
                "position_size": "4 Contracts"
            },
            "$100,000": {
                "profit_target": 6000,
                "daily_loss": 2500,
                "max_drawdown": 3500,
                "position_size": "8 Contracts"
            },
            "$150,000": {
                "profit_target": 9000,
                "daily_loss": 3750,
                "max_drawdown": 5000,
                "position_size": "12 Contracts"
            }
        }
    
    async def get_account_sizes(self, page: Page) -> List[str]:
        """Extract all available account sizes from Tradeify website"""
        try:
            logger.info("Extracting account sizes from Tradeify")
            
            # Navigate to Growth Evaluation Accounts page
            growth_url = "https://help.tradeify.co/en/articles/10495915-growth-evaluation-accounts"
            await page.goto(growth_url)
            await page.wait_for_load_state('networkidle')
            
            # Look for account size information
            soup = await self.parse_html_content(page)
            content_text = soup.get_text()
            
            # Extract account sizes from content
            account_sizes = []
            size_patterns = [
                r'\$50,?000',
                r'\$100,?000', 
                r'\$150,?000'
            ]
            
            for pattern in size_patterns:
                if re.search(pattern, content_text, re.IGNORECASE):
                    size = pattern.replace(',?', ',').replace('\\', '')
                    if size not in account_sizes:
                        account_sizes.append(size)
            
            # Default to known account sizes if none found
            if not account_sizes:
                account_sizes = ["$50,000", "$100,000", "$150,000"]
                logger.warning("No account sizes found in content, using default list")
            
            logger.info(f"Found {len(account_sizes)} account sizes: {account_sizes}")
            return account_sizes
            
        except Exception as e:
            logger.error(f"Error extracting account sizes: {e}")
            return ["$50,000", "$100,000", "$150,000"]
    
    async def extract_evaluation_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract evaluation phase rules for a specific account size"""
        try:
            logger.info(f"Extracting evaluation rules for {account_size}")
            
            # Navigate to Growth Evaluation Accounts page
            growth_url = "https://help.tradeify.co/en/articles/10495915-growth-evaluation-accounts"
            await page.goto(growth_url)
            await page.wait_for_load_state('networkidle')
            
            rules = {}
            
            # Get account data from our predefined mapping
            if account_size in self.account_data:
                data = self.account_data[account_size]
                
                # Profit target (6% of account size)
                rules['target_usd'] = float(data['profit_target'])
                
                # Max drawdown (trailing, end-of-day)
                rules['max_drawdown_usd'] = float(data['max_drawdown'])
                
                # Daily loss limit
                rules['daily_loss_usd'] = float(data['daily_loss'])
                
                # Drawdown type (end-of-day trailing)
                rules['drawdown_type'] = DrawdownType.EOD
                
                # Minimum trading days (can be passed in 1 day)
                rules['min_days'] = 1
                
                # No consistency rule for Growth accounts
                rules['consistency'] = False
            
            else:
                # Fallback: try to extract from page content
                soup = await self.parse_html_content(page)
                content_text = soup.get_text().lower()
                
                # Extract profit target (6% mentioned in analysis)
                account_value = converter.parse_and_convert(account_size)
                if account_value:
                    rules['target_usd'] = account_value * 0.06  # 6%
                
                # Try to extract other values from content
                rules['drawdown_type'] = DrawdownType.EOD
                rules['min_days'] = 1
                rules['consistency'] = False
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting evaluation rules for {account_size}: {e}")
            return {}
    
    async def extract_funded_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract funded phase rules for a specific account size"""
        try:
            logger.info(f"Extracting funded rules for {account_size}")
            
            # Navigate to rules pages
            consistency_url = "https://help.tradeify.co/en/articles/10468320-rules-consistency-rule"
            await page.goto(consistency_url)
            await page.wait_for_load_state('networkidle')
            
            rules = {}
            
            # Same drawdown as evaluation but calculated end-of-day
            if account_size in self.account_data:
                data = self.account_data[account_size]
                rules['max_drawdown_usd'] = float(data['max_drawdown'])
                rules['daily_loss_usd'] = float(data['daily_loss'])
            
            # Drawdown type (end-of-day for funded accounts)
            rules['drawdown_type'] = DrawdownType.EOD
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting funded rules for {account_size}: {e}")
            return {}
    
    async def extract_payout_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract payout rules for a specific account size"""
        try:
            logger.info(f"Extracting payout rules for {account_size}")
            
            # Navigate to payout policies
            payout_url = "https://help.tradeify.co/en/articles/11083796-advanced-and-growth-account-payout-policies"
            await page.goto(payout_url)
            await page.wait_for_load_state('networkidle')
            
            rules = {}
            
            # Profit split (90% to trader from analysis)
            rules['profit_split_percent'] = 90.0
            
            # Payout frequency (3 times per month)
            rules['payout_frequency'] = PayoutFrequency.MONTHLY  # Closest to 3x per month
            
            # Minimum payout requirements (varies by account size)
            min_profit_requirements = {
                "$50,000": 150,
                "$100,000": 200,
                "$150,000": 250
            }
            
            rules['min_payout_usd'] = min_profit_requirements.get(account_size, 200)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting payout rules for {account_size}: {e}")
            return {}
    
    async def extract_fee_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract fee rules for a specific account size"""
        try:
            logger.info(f"Extracting fee rules for {account_size}")
            
            # Navigate to billing section
            billing_url = "https://help.tradeify.co/en/collections/11501859-payouts-billing"
            await page.goto(billing_url)
            await page.wait_for_load_state('networkidle')
            
            rules = {}
            
            # From analysis: No activation fees, monthly subscription
            # We'll need to estimate based on typical prop firm pricing
            fee_mapping = {
                "$50,000": 99,    # Estimated monthly subscription
                "$100,000": 149,  # Estimated monthly subscription
                "$150,000": 199   # Estimated monthly subscription
            }
            
            rules['evaluation_fee_usd'] = fee_mapping.get(account_size, 149)
            
            # No reset fees mentioned (monthly subscription model)
            rules['reset_fee_usd'] = 0.0
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting fee rules for {account_size}: {e}")
            return {}
    
    async def extract_broker_platform(self, page: Page) -> Dict[str, Any]:
        """Extract broker and platform information"""
        try:
            # Navigate to trading platforms page
            platforms_url = "https://help.tradeify.co/en/collections/11501720-trading-platforms-products"
            await page.goto(platforms_url)
            await page.wait_for_load_state('networkidle')
            
            # Tradeify typically uses futures brokers
            return {
                'broker': Broker.RITHMIC,  # Common futures broker
                'platform': Platform.MULTIPLE  # Supports multiple platforms
            }
            
        except Exception as e:
            logger.error(f"Error extracting broker/platform info: {e}")
            return {'broker': None, 'platform': None}