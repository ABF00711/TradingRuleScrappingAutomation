"""
Base extractor class for all website extractors
"""
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from playwright.async_api import Page
from bs4 import BeautifulSoup

from ..config.schema import TradingRule, SiteConfig
from ..config.enums import Status
from ..core.currency_converter import converter
from ..core.utils import extract_number, extract_percentage, classify_drawdown_type, classify_payout_frequency

logger = logging.getLogger(__name__)

class BaseExtractor(ABC):
    """Abstract base class for all website extractors"""
    
    def __init__(self, site_config: SiteConfig):
        self.site_config = site_config
        self.firm_name = site_config.name
        self.base_url = site_config.url
        self.raw_data = {}
    
    @abstractmethod
    async def get_account_sizes(self, page: Page) -> List[str]:
        """
        Extract all available account sizes from the website
        
        Returns:
            List of account size strings (e.g., ["$25,000", "$50,000", "$100,000"])
        """
        pass
    
    @abstractmethod
    async def extract_evaluation_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """
        Extract evaluation phase rules for a specific account size
        
        Returns:
            Dictionary with evaluation rules:
            {
                'target_usd': float,
                'max_drawdown_usd': float,
                'daily_loss_usd': float,
                'drawdown_type': DrawdownType,
                'min_days': int,
                'consistency': bool
            }
        """
        pass
    
    @abstractmethod
    async def extract_funded_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """
        Extract funded phase rules for a specific account size
        
        Returns:
            Dictionary with funded rules:
            {
                'max_drawdown_usd': float,
                'daily_loss_usd': float,
                'drawdown_type': DrawdownType
            }
        """
        pass
    
    @abstractmethod
    async def extract_payout_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """
        Extract payout rules for a specific account size
        
        Returns:
            Dictionary with payout rules:
            {
                'profit_split_percent': float,
                'payout_frequency': PayoutFrequency,
                'min_payout_usd': float
            }
        """
        pass
    
    @abstractmethod
    async def extract_fee_rules(self, page: Page, account_size: str) -> Dict[str, Any]:
        """
        Extract fee rules for a specific account size
        
        Returns:
            Dictionary with fee rules:
            {
                'evaluation_fee_usd': float,
                'reset_fee_usd': float
            }
        """
        pass
    
    async def extract_broker_platform(self, page: Page) -> Dict[str, Any]:
        """
        Extract broker and platform information (optional override)
        
        Returns:
            Dictionary with broker/platform info:
            {
                'broker': Broker,
                'platform': Platform
            }
        """
        return {'broker': None, 'platform': None}
    
    async def extract_all_rules(self, page: Page) -> List[TradingRule]:
        """
        Extract all trading rules for all account sizes
        
        This is the main method that orchestrates the extraction process
        """
        trading_rules = []
        
        try:
            logger.info(f"Starting extraction for {self.firm_name}")
            
            # Get account sizes
            account_sizes = await self.get_account_sizes(page)
            
            if not account_sizes:
                logger.warning(f"No account sizes found for {self.firm_name}")
                # Create a single rule with missing data status
                rule = TradingRule(
                    firm_name=self.firm_name,
                    account_size="Unknown",
                    account_size_usd=0.0,
                    website_url=self.base_url,
                    status=Status.MISSING_DATA
                )
                return [rule]
            
            # Extract broker and platform info (common for all account sizes)
            broker_platform = await self.extract_broker_platform(page)
            
            # Filter account sizes to minimum 50K USD
            filtered_account_sizes = []
            for account_size in account_sizes:
                account_size_usd = converter.parse_and_convert(account_size) or 0.0
                if account_size_usd >= 50000:  # Minimum 50K USD
                    filtered_account_sizes.append(account_size)
                else:
                    logger.info(f"Skipping {account_size} (${account_size_usd:,.0f}) - below 50K minimum")
            
            if not filtered_account_sizes:
                logger.warning(f"No account sizes >= 50K found for {self.firm_name}")
                # Create a single rule with missing data status
                rule = TradingRule(
                    firm_name=self.firm_name,
                    account_size="No accounts >= $50K",
                    account_size_usd=0.0,
                    website_url=self.base_url,
                    status=Status.MISSING_DATA
                )
                return [rule]
            
            # Extract rules for each filtered account size
            for account_size in filtered_account_sizes:
                try:
                    logger.info(f"Extracting rules for {self.firm_name} - {account_size}")
                    
                    # Convert account size to USD
                    account_size_usd = converter.parse_and_convert(account_size) or 0.0
                    
                    # Extract all rule types
                    evaluation_rules = await self.extract_evaluation_rules(page, account_size)
                    funded_rules = await self.extract_funded_rules(page, account_size)
                    payout_rules = await self.extract_payout_rules(page, account_size)
                    fee_rules = await self.extract_fee_rules(page, account_size)
                    
                    # Create trading rule object
                    rule = TradingRule(
                        firm_name=self.firm_name,
                        account_size=account_size,
                        account_size_usd=account_size_usd,
                        website_url=self.base_url,
                        broker=broker_platform.get('broker'),
                        platform=broker_platform.get('platform'),
                        
                        # Evaluation rules
                        evaluation_target_usd=evaluation_rules.get('profit_target_usd') or evaluation_rules.get('target_usd'),
                        evaluation_max_drawdown_usd=evaluation_rules.get('max_drawdown_usd'),
                        evaluation_daily_loss_usd=evaluation_rules.get('daily_loss_limit_usd'),
                        evaluation_drawdown_type=evaluation_rules.get('drawdown_type'),
                        evaluation_min_days=evaluation_rules.get('min_trading_days') or evaluation_rules.get('min_days'),
                        evaluation_consistency=evaluation_rules.get('consistency_rule') or evaluation_rules.get('consistency'),
                        
                        # Funded rules
                        funded_max_drawdown_usd=funded_rules.get('max_drawdown_usd'),
                        funded_daily_loss_usd=funded_rules.get('daily_loss_limit_usd'),
                        funded_drawdown_type=funded_rules.get('drawdown_type'),
                        
                        # Payout rules
                        profit_split_percent=payout_rules.get('profit_split_percent'),
                        payout_frequency=payout_rules.get('payout_frequency'),
                        min_payout_usd=payout_rules.get('min_payout_usd'),
                        
                        # Fee rules
                        evaluation_fee_usd=fee_rules.get('evaluation_fee_usd'),
                        reset_fee_usd=fee_rules.get('reset_fee_usd'),
                        
                        # Store raw data for debugging
                        raw_data={
                            'account_size': account_size,
                            'evaluation': evaluation_rules,
                            'funded': funded_rules,
                            'payout': payout_rules,
                            'fees': fee_rules,
                            'broker_platform': broker_platform
                        }
                    )
                    
                    # Validate and set status
                    rule.status = self._validate_rule(rule)
                    
                    trading_rules.append(rule)
                    
                except Exception as e:
                    logger.error(f"Failed to extract rules for {account_size}: {e}")
                    
                    # Create rule with failed status
                    rule = TradingRule(
                        firm_name=self.firm_name,
                        account_size=account_size,
                        account_size_usd=converter.parse_and_convert(account_size) or 0.0,
                        website_url=self.base_url,
                        status=Status.FAILED
                    )
                    trading_rules.append(rule)
            
            logger.info(f"Extracted {len(trading_rules)} rules for {self.firm_name}")
            
        except Exception as e:
            logger.error(f"Failed to extract rules for {self.firm_name}: {e}")
            
            # Create rule with failed status
            rule = TradingRule(
                firm_name=self.firm_name,
                account_size="Unknown",
                account_size_usd=0.0,
                website_url=self.base_url,
                status=Status.FAILED
            )
            trading_rules.append(rule)
        
        return trading_rules
    
    def _validate_rule(self, rule: TradingRule) -> Status:
        """
        Validate a trading rule and determine its status
        
        Returns:
            Status enum indicating the validation result
        """
        # Check if critical fields are missing
        critical_fields = [
            rule.evaluation_target_usd,
            rule.evaluation_max_drawdown_usd,
            rule.profit_split_percent
        ]
        
        missing_critical = sum(1 for field in critical_fields if field is None)
        
        if missing_critical > 1:  # Allow one missing critical field
            return Status.MISSING_DATA
        
        return Status.OK
    
    async def save_raw_data(self, data: Dict[str, Any], account_size: str = "all"):
        """Save raw extracted data to JSON file for debugging"""
        try:
            # Create data directory if it doesn't exist
            data_dir = Path("propfirm_scraper/data/raw")
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            firm_name_clean = self.firm_name.lower().replace(" ", "_").replace("-", "_")
            filename = f"{firm_name_clean}_{account_size}_{timestamp}.json"
            
            filepath = data_dir / filename
            
            # Save data
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Raw data saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save raw data: {e}")
    
    # Helper methods for common extraction patterns
    
    async def find_text_by_keywords(self, page: Page, keywords: List[str]) -> Optional[str]:
        """Find text on page that contains any of the given keywords"""
        try:
            content = await page.content()
            content_lower = content.lower()
            
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    # Try to find the specific element containing this keyword
                    elements = await page.query_selector_all(f"text=/{keyword}/i")
                    if elements:
                        return await elements[0].text_content()
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding text by keywords: {e}")
            return None
    
    async def extract_table_data(self, page: Page, table_selector: str = "table") -> List[Dict[str, str]]:
        """Extract data from HTML table"""
        try:
            tables = await page.query_selector_all(table_selector)
            
            if not tables:
                return []
            
            table_data = []
            
            for table in tables:
                rows = await table.query_selector_all("tr")
                
                if not rows:
                    continue
                
                # Get headers from first row
                header_row = rows[0]
                headers = []
                header_cells = await header_row.query_selector_all("th, td")
                
                for cell in header_cells:
                    text = await cell.text_content()
                    headers.append(text.strip() if text else "")
                
                # Get data rows
                for row in rows[1:]:
                    cells = await row.query_selector_all("td")
                    
                    if len(cells) != len(headers):
                        continue
                    
                    row_data = {}
                    for i, cell in enumerate(cells):
                        text = await cell.text_content()
                        row_data[headers[i]] = text.strip() if text else ""
                    
                    table_data.append(row_data)
            
            return table_data
            
        except Exception as e:
            logger.error(f"Error extracting table data: {e}")
            return []
    
    async def parse_html_content(self, page: Page) -> BeautifulSoup:
        """Parse page HTML content using BeautifulSoup with built-in parser"""
        try:
            html_content = await page.content()
            # Use html.parser (built-in) instead of lxml to avoid compilation issues
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup
            
        except Exception as e:
            logger.error(f"Error parsing HTML content: {e}")
            return BeautifulSoup("", 'html.parser')