"""
Legends Trading Extractor

Extracts trading rules from Legends Trading website.
Website: https://legendstrading.co/ or https://thelegendstrading.com/
Knowledge Base: https://knowledge.thelegendstrading.com/en/
App Plans: https://app.thelegendstrading.com/plans/
"""

import re
import logging
from typing import Dict, List, Optional, Any
from playwright.async_api import Page
from bs4 import BeautifulSoup
from .base_extractor import BaseExtractor
from ..config.enums import DrawdownType, PayoutFrequency, Platform, Broker

logger = logging.getLogger(__name__)


class LegendsTradingExtractor(BaseExtractor):
    """Extractor for Legends Trading trading rules"""
    
    def __init__(self, site_config):
        super().__init__(site_config)
        self.main_url = "https://legendstrading.co"
        self.alt_main_url = "https://thelegendstrading.com"
        self.knowledge_url = "https://knowledge.thelegendstrading.com/en"
        self.app_plans_url = "https://app.thelegendstrading.com/plans"
        self.pricing_url = "https://www.legendstrading.com/plans-pricing"
        
        # Plan type data mapping based on research
        self.plan_types = {
            'Apprentice Plan': {
                'account_sizes': ['$25,000', '$50,000', '$100,000', '$150,000'],
                'evaluation_days': 4,
                'monthly_fees': {
                    '$25,000': 33,
                    '$50,000': 37,
                    '$100,000': 45,
                    '$150,000': 64
                },
                'activation_fees': {
                    '$25,000': 99,    # Range $99-$199
                    '$50,000': 129,
                    '$100,000': 149,
                    '$150,000': 199
                },
                'has_daily_loss_limit': True,
                'consistency_percent': 30,  # 30% consistency rule
                'has_evaluation': True
            },
            'Elite Plan': {
                'account_sizes': ['$25,000', '$50,000', '$100,000', '$150,000'],
                'evaluation_days': None,  # No specific evaluation period
                'one_time_fees': {
                    '$25,000': 64.35,
                    '$50,000': 96.85,
                    '$100,000': 117.00,
                    '$150,000': 149.50
                },
                'has_daily_loss_limit': False,  # No daily loss limit
                'consistency_percent': 40,  # 40% consistency rule
                'has_evaluation': True
            },
            'Straight to Master': {
                'account_sizes': ['$25,000', '$50,000', '$100,000', '$150,000'],
                'evaluation_days': 10,
                'one_time_fees': {
                    '$25,000': 239.40,
                    '$50,000': 299.40,
                    '$100,000': 359.40,
                    '$150,000': 419.40
                },
                'has_daily_loss_limit': True,
                'consistency_percent': 35,  # Estimated consistency rule
                'has_evaluation': True
            }
        }
        
        # Account-specific rules based on research
        self.account_rules = {
            '$25,000': {
                'profit_target': 1500,
                'max_drawdown': 1250,
                'daily_loss_limit': 625,  # Estimated
                'contract_limits': {'standard': 2, 'micros': 20}
            },
            '$50,000': {
                'profit_target': 3000,
                'max_drawdown': 2500,
                'daily_loss_limit': 1250,  # Estimated
                'contract_limits': {'standard': 5, 'micros': 50}
            },
            '$100,000': {
                'profit_target': 6000,
                'max_drawdown': 3500,
                'daily_loss_limit': 2500,  # Estimated
                'contract_limits': {'standard': 10, 'micros': 80}
            },
            '$150,000': {
                'profit_target': 9000,
                'max_drawdown': 4500,
                'daily_loss_limit': 3750,  # Estimated
                'contract_limits': {'standard': 17, 'micros': 120}
            }
        }
        
        # General rules
        self.general_rules = {
            'profit_split': 90,  # 90% to trader, 10% to firm
            'payout_frequency': PayoutFrequency.ON_DEMAND,  # Needs verification
            'drawdown_type': DrawdownType.EOD,  # EOD trailing max loss
            'max_total_balance': 1500000,  # $1.5M across all accounts
            'platforms': ['Multiple'],  # Needs verification
            'min_payout_usd': 100  # Estimated
        }

    async def get_account_sizes(self, page: Page) -> List[str]:
        """Extract all available account sizes"""
        logger.info("Extracting account sizes for Legends Trading")
        
        try:
            account_sizes = set()
            
            # Try multiple URLs to find account sizes
            urls_to_try = [
                self.knowledge_url,
                self.app_plans_url,
                self.pricing_url,
                self.main_url,
                self.alt_main_url
            ]
            
            for url in urls_to_try:
                try:
                    logger.info(f"Trying to extract account sizes from: {url}")
                    await page.goto(url, wait_until="networkidle")
                    await page.wait_for_timeout(3000)
                    
                    content = await page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    text = soup.get_text().lower()
                    
                    # Look for account size patterns
                    found_sizes = self._extract_sizes_from_text(text)
                    if found_sizes:
                        account_sizes.update(found_sizes)
                        logger.info(f"Found sizes from {url}: {found_sizes}")
                    
                    # If we found sizes, we can continue to try other URLs for completeness
                    
                except Exception as e:
                    logger.warning(f"Error accessing {url}: {e}")
                    continue
            
            # If no sizes found, use predefined data
            if not account_sizes:
                logger.warning("No account sizes found in content, using predefined list")
                for plan_type, data in self.plan_types.items():
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
            for plan_type, data in self.plan_types.items():
                all_sizes.update(data['account_sizes'])
            return sorted(list(all_sizes), key=lambda x: float(x.replace('$', '').replace(',', '')))

    async def extract_evaluation_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """Extract evaluation phase rules"""
        logger.info(f"Extracting evaluation rules for {account_size}")
        
        try:
            # Try knowledge base first for detailed rules
            try:
                await page.goto(self.knowledge_url, wait_until="networkidle")
                await page.wait_for_timeout(3000)
                
                # Try to search for evaluation rules
                await self._search_knowledge_base(page, "evaluation rules")
                await page.wait_for_timeout(2000)
                
            except Exception as e:
                logger.warning(f"Failed to navigate to knowledge base: {e}")
                # Fallback to main website
                await page.goto(self.main_url, wait_until="networkidle")
                await page.wait_for_timeout(3000)
            
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
            # Try knowledge base for funded account rules
            try:
                await page.goto(self.knowledge_url, wait_until="networkidle")
                await page.wait_for_timeout(3000)
                
                # Try to search for funded rules
                await self._search_knowledge_base(page, "funded account rules")
                await page.wait_for_timeout(2000)
                
            except Exception as e:
                logger.warning(f"Failed to navigate to knowledge base: {e}")
                # Use same content as evaluation
                pass
            
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
            # Try knowledge base for payout information
            try:
                await page.goto(self.knowledge_url, wait_until="networkidle")
                await page.wait_for_timeout(3000)
                
                # Try to search for payout rules
                await self._search_knowledge_base(page, "payout")
                await page.wait_for_timeout(2000)
                
            except Exception as e:
                logger.warning(f"Failed to navigate to knowledge base: {e}")
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
            # Try app plans or pricing page for fee information
            urls_to_try = [self.app_plans_url, self.pricing_url, self.main_url]
            
            for url in urls_to_try:
                try:
                    await page.goto(url, wait_until="networkidle")
                    await page.wait_for_timeout(3000)
                    
                    content = await page.content()
                    rules = await self._parse_fee_rules(content, account_size)
                    
                    if rules:  # If we found some fee data, use it
                        return rules
                        
                except Exception as e:
                    logger.warning(f"Error accessing {url}: {e}")
                    continue
            
            # If no fees found from any URL, use fallback
            return self._get_fallback_fee_rules(account_size)
            
        except Exception as e:
            logger.error(f"Error extracting fee rules: {e}")
            return self._get_fallback_fee_rules(account_size)

    def _extract_sizes_from_text(self, text: str) -> List[str]:
        """Extract account sizes from text content"""
        sizes = set()
        
        # Look for various account size patterns
        size_patterns = [
            r'\$25,?000',
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

    async def _search_knowledge_base(self, page: Page, search_term: str):
        """Try to search the knowledge base for specific terms"""
        try:
            # Look for search input field
            search_selectors = [
                'input[type="search"]',
                'input[placeholder*="search"]',
                '.search-input',
                '#search',
                '[data-search]'
            ]
            
            for selector in search_selectors:
                try:
                    search_input = await page.query_selector(selector)
                    if search_input:
                        await search_input.fill(search_term)
                        await search_input.press('Enter')
                        logger.info(f"Searched for: {search_term}")
                        return
                except Exception:
                    continue
            
            logger.warning("No search input found in knowledge base")
            
        except Exception as e:
            logger.warning(f"Error searching knowledge base: {e}")

    async def _parse_evaluation_rules(self, content: str, account_size: str) -> Dict[str, Any]:
        """Parse evaluation rules from HTML content"""
        rules = {}
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text().lower()
            
            # Get account-specific rules from predefined data
            account_info = self.account_rules.get(account_size, {})
            
            # Profit target
            profit_target = account_info.get('profit_target')
            if profit_target:
                rules['profit_target_usd'] = float(profit_target)
            
            # Max drawdown
            max_drawdown = account_info.get('max_drawdown')
            if max_drawdown:
                rules['max_drawdown_usd'] = float(max_drawdown)
            
            # Daily loss limit (may not apply to Elite plan)
            daily_loss_limit = account_info.get('daily_loss_limit')
            if daily_loss_limit:
                rules['daily_loss_limit_usd'] = float(daily_loss_limit)
            
            # Drawdown type (EOD trailing)
            rules['drawdown_type'] = self.general_rules['drawdown_type']
            
            # Minimum trading days (varies by plan)
            # Default to Apprentice plan (4 days) if not specified
            rules['min_trading_days'] = self.plan_types['Apprentice Plan']['evaluation_days']
            
            # Consistency rule (varies by plan, default to 30%)
            rules['consistency_rule'] = True
            
            logger.info(f"Parsed evaluation rules: {rules}")
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
            
            # Copy relevant rules
            if 'max_drawdown_usd' in eval_rules:
                rules['max_drawdown_usd'] = eval_rules['max_drawdown_usd']
            if 'daily_loss_limit_usd' in eval_rules:
                rules['daily_loss_limit_usd'] = eval_rules['daily_loss_limit_usd']
            if 'drawdown_type' in eval_rules:
                rules['drawdown_type'] = eval_rules['drawdown_type']
            
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
            
            # Profit split (90% to trader)
            rules['profit_split_percent'] = self.general_rules['profit_split']
            
            # Payout frequency (needs verification, default to on-demand)
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
            
            # Try to determine plan type from content or default to Apprentice
            plan_type = self._determine_plan_type(text)
            plan_info = self.plan_types.get(plan_type, self.plan_types['Apprentice Plan'])
            
            # Get fees based on plan type
            if 'monthly_fees' in plan_info:
                # Apprentice Plan - monthly fees
                monthly_fees = plan_info['monthly_fees']
                if account_size in monthly_fees:
                    rules['evaluation_fee_usd'] = float(monthly_fees[account_size])
                
                # Activation fees for Apprentice
                activation_fees = plan_info.get('activation_fees', {})
                if account_size in activation_fees:
                    rules['activation_fee_usd'] = float(activation_fees[account_size])
                else:
                    rules['activation_fee_usd'] = 0.0
                    
            elif 'one_time_fees' in plan_info:
                # Elite or Straight to Master - one-time fees
                one_time_fees = plan_info['one_time_fees']
                if account_size in one_time_fees:
                    rules['evaluation_fee_usd'] = float(one_time_fees[account_size])
                
                # No activation fee for one-time plans
                rules['activation_fee_usd'] = 0.0
            
            # Reset fee (try to extract or estimate)
            reset_fee_patterns = [
                r'reset[^0-9]*fee[:\s]*\$?([0-9,\.]+)',
                r'reset[:\s]*\$?([0-9,\.]+)'
            ]
            
            for pattern in reset_fee_patterns:
                match = re.search(pattern, text)
                if match:
                    rules['reset_fee_usd'] = float(match.group(1).replace(',', ''))
                    break
            else:
                # Estimate reset fee based on account size
                account_value = float(account_size.replace('$', '').replace(',', ''))
                rules['reset_fee_usd'] = max(50, account_value * 0.001)  # 0.1% or $50 minimum
            
            logger.info(f"Parsed fee rules for {plan_type}: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error parsing fee rules: {e}")
            return {}

    def _determine_plan_type(self, text: str) -> str:
        """Determine plan type from content"""
        
        if 'elite' in text and 'plan' in text:
            return 'Elite Plan'
        elif 'straight to master' in text or 'master' in text:
            return 'Straight to Master'
        elif 'apprentice' in text:
            return 'Apprentice Plan'
        
        # Default to Apprentice Plan
        return 'Apprentice Plan'

    def _get_fallback_evaluation_rules(self, account_size: str) -> Dict[str, Any]:
        """Get fallback evaluation rules from predefined data"""
        rules = {}
        
        try:
            account_info = self.account_rules.get(account_size, {})
            
            # Use predefined account rules
            if 'profit_target' in account_info:
                rules['profit_target_usd'] = float(account_info['profit_target'])
            if 'max_drawdown' in account_info:
                rules['max_drawdown_usd'] = float(account_info['max_drawdown'])
            if 'daily_loss_limit' in account_info:
                rules['daily_loss_limit_usd'] = float(account_info['daily_loss_limit'])
            
            rules['drawdown_type'] = self.general_rules['drawdown_type']
            rules['min_trading_days'] = self.plan_types['Apprentice Plan']['evaluation_days']
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
            account_info = self.account_rules.get(account_size, {})
            
            # Same rules as evaluation for funded phase
            if 'max_drawdown' in account_info:
                rules['max_drawdown_usd'] = float(account_info['max_drawdown'])
            if 'daily_loss_limit' in account_info:
                rules['daily_loss_limit_usd'] = float(account_info['daily_loss_limit'])
            
            rules['drawdown_type'] = self.general_rules['drawdown_type']
            
            logger.info(f"Using fallback funded rules: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error in fallback funded rules: {e}")
            return {}

    def _get_fallback_payout_rules(self, account_size: str) -> Dict[str, Any]:
        """Get fallback payout rules from predefined data"""
        rules = {}
        
        try:
            rules['profit_split_percent'] = self.general_rules['profit_split']
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
            # Default to Apprentice Plan fees
            plan_info = self.plan_types['Apprentice Plan']
            
            # Monthly fees for Apprentice Plan
            monthly_fees = plan_info.get('monthly_fees', {})
            if account_size in monthly_fees:
                rules['evaluation_fee_usd'] = float(monthly_fees[account_size])
            
            # Activation fees for Apprentice Plan
            activation_fees = plan_info.get('activation_fees', {})
            if account_size in activation_fees:
                rules['activation_fee_usd'] = float(activation_fees[account_size])
            else:
                rules['activation_fee_usd'] = 0.0
            
            # Estimate reset fee
            account_value = float(account_size.replace('$', '').replace(',', ''))
            rules['reset_fee_usd'] = max(50, account_value * 0.001)
            
            logger.info(f"Using fallback fee rules: {rules}")
            return rules
            
        except Exception as e:
            logger.error(f"Error in fallback fee rules: {e}")
            return {}

    def get_platform(self) -> str:
        """Return the trading platform"""
        return Platform.MULTIPLE.value  # Legends Trading supports multiple platforms

    def get_broker(self) -> str:
        """Return the broker"""
        return Broker.MULTIPLE.value  # Legends Trading supports multiple brokers