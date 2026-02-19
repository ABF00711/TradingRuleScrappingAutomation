"""
Main execution script for the PropFirm Trading Rules Scraper
"""
import asyncio
import logging
import yaml
from pathlib import Path
from typing import List, Dict, Any

from .core.logger import setup_logger
from .core.browser import BrowserManager
from .config.schema import SiteConfig, TradingRule
from .config.enums import Status
from .exporters.csv_exporter import CSVExporter

# Import extractors
from .extractors.apex import ApexExtractor
from .extractors.tradeify import TradeifyExtractor
from .extractors.myfundedfutures import MyFundedFuturesExtractor
from .extractors.fundednext import FundedNextExtractor
from .extractors.alphafutures import AlphaFuturesExtractor
from .extractors.takeprofittrader import TakeProfitTraderExtractor
from .extractors.e8markets import E8MarketsExtractor
from .extractors.lucidtrading import LucidTradingExtractor
from .extractors.toponefutures import TopOneFuturesExtractor
from .extractors.blueguardianfutures import BlueGuardianFuturesExtractor
# ... other extractors will be added here

logger = setup_logger()

# Try to import Google Sheets exporter, fallback to CSV if not available
try:
    from .exporters.google_sheets import GoogleSheetsExporter
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Google Sheets not available: {e}")
    GOOGLE_SHEETS_AVAILABLE = False

class PropFirmScraper:
    """Main scraper orchestrator"""
    
    def __init__(self, config_path: str = "propfirm_scraper/config/sites.yaml"):
        self.config_path = config_path
        self.sites_config = {}
        self.browser_manager = None
        self.results: List[TradingRule] = []
        
        # Google Sheets configuration
        self.sheet_id = "1V72k3xmBrppWC7fzMBIBYh2Ghh1HHP_2GTEf8BDaKGk"
        self.service_account_file = "service_account/tradingruleautomation-62475a2ca73b.json"
    
    def load_config(self):
        """Load sites configuration from YAML file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self.sites_config = config.get('sites', {})
            self.global_settings = config.get('settings', {})
            
            logger.info(f"Loaded configuration for {len(self.sites_config)} sites")
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def get_extractor_class(self, extractor_name: str):
        """Get extractor class by name"""
        extractor_mapping = {
            'ApexExtractor': ApexExtractor,
            'LucidExtractor': LucidTradingExtractor,
            'TradeifyExtractor': TradeifyExtractor,
            'MyFundedFuturesExtractor': MyFundedFuturesExtractor,
            'FundedNextExtractor': FundedNextExtractor,
            'AlphaFuturesExtractor': AlphaFuturesExtractor,
            'TopOneFuturesExtractor': TopOneFuturesExtractor,
            'BlueGuardianFuturesExtractor': BlueGuardianFuturesExtractor,
            'TradingPitExtractor': None,  # TODO: Implement
            'LegendsTradingExtractor': None,  # TODO: Implement
            'E8MarketsExtractor': E8MarketsExtractor,
            'TakeProfitTraderExtractor': TakeProfitTraderExtractor,
            'TradeDayExtractor': None,  # TODO: Implement
        }
        
        return extractor_mapping.get(extractor_name)
    
    async def scrape_site(self, site_name: str, site_config: Dict[str, Any]) -> List[TradingRule]:
        """Scrape a single website"""
        try:
            logger.info(f"Starting scrape for {site_name}")
            
            # Create site config object
            config = SiteConfig(
                name=site_config['name'],
                url=site_config['url'],
                extractor_class=site_config['extractor_class'],
                enabled=site_config.get('enabled', True),
                timeout=site_config.get('timeout', 30),
                retry_attempts=site_config.get('retry_attempts', 2),
                notes=site_config.get('notes', '')
            )
            
            if not config.enabled:
                logger.info(f"Skipping disabled site: {site_name}")
                return []
            
            # Get extractor class
            extractor_class = self.get_extractor_class(config.extractor_class)
            
            if not extractor_class:
                logger.warning(f"Extractor not implemented yet: {config.extractor_class}")
                # Create placeholder rule
                rule = TradingRule(
                    firm_name=config.name,
                    account_size="Unknown",
                    account_size_usd=0.0,
                    website_url=config.url,
                    status=Status.FAILED
                )
                rule.raw_data = {'error': 'Extractor not implemented'}
                return [rule]
            
            # Create page and load website
            page = await self.browser_manager.new_page()
            await self.browser_manager.load_page(config.url, page)
            
            # Check if login is required
            if await self.browser_manager.detect_login_page(page):
                logger.warning(f"Login required for {site_name}, skipping")
                rule = TradingRule(
                    firm_name=config.name,
                    account_size="Unknown",
                    account_size_usd=0.0,
                    website_url=config.url,
                    status=Status.LOGIN_REQUIRED
                )
                await page.close()
                return [rule]
            
            # Expand accordions to reveal content
            await self.browser_manager.expand_accordions(page)
            
            # Create extractor and run extraction
            extractor = extractor_class(config)
            trading_rules = await extractor.extract_all_rules(page)
            
            # Close page
            await page.close()
            
            logger.info(f"Completed scrape for {site_name}: {len(trading_rules)} rules extracted")
            return trading_rules
            
        except Exception as e:
            logger.error(f"Failed to scrape {site_name}: {e}")
            
            # Create failed rule
            rule = TradingRule(
                firm_name=site_config.get('name', site_name),
                account_size="Unknown",
                account_size_usd=0.0,
                website_url=site_config.get('url', ''),
                status=Status.FAILED
            )
            rule.raw_data = {'error': str(e)}
            return [rule]
    
    async def scrape_all_sites(self):
        """Scrape all configured websites"""
        try:
            logger.info("Starting scrape of all sites")
            
            # Initialize browser
            self.browser_manager = BrowserManager(
                headless=self.global_settings.get('headless', True),
                timeout=self.global_settings.get('page_timeout', 30000)
            )
            
            await self.browser_manager.start()
            
            # Process sites
            all_results = []
            
            for site_name, site_config in self.sites_config.items():
                try:
                    site_results = await self.scrape_site(site_name, site_config)
                    all_results.extend(site_results)
                    
                    # Small delay between sites
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error processing site {site_name}: {e}")
                    continue
            
            self.results = all_results
            logger.info(f"Completed scraping all sites: {len(self.results)} total rules")
            
        except Exception as e:
            logger.error(f"Failed to scrape sites: {e}")
            raise
        
        finally:
            if self.browser_manager:
                await self.browser_manager.close()
    
    def export_results(self):
        """Export results to Google Sheets or CSV (fallback)"""
        try:
            if not self.results:
                logger.warning("No results to export")
                return None
            
            # Try Google Sheets first
            if GOOGLE_SHEETS_AVAILABLE:
                try:
                    logger.info("Exporting results to Google Sheets")
                    
                    # Create exporter
                    exporter = GoogleSheetsExporter(
                        sheet_id=self.sheet_id,
                        service_account_file=self.service_account_file
                    )
                    
                    # Export data
                    sheet_url = exporter.export_all(self.results)
                    
                    logger.info(f"Google Sheets export completed: {sheet_url}")
                    return sheet_url
                    
                except Exception as e:
                    logger.error(f"Google Sheets export failed: {e}")
                    logger.info("Falling back to CSV export")
            
            # Fallback to CSV export
            logger.info("Exporting results to CSV")
            
            csv_exporter = CSVExporter()
            csv_file = csv_exporter.export_to_csv(self.results)
            summary_file = csv_exporter.export_summary(self.results)
            
            logger.info(f"CSV export completed: {csv_file}")
            logger.info(f"Summary report: {summary_file}")
            
            return csv_file
            
        except Exception as e:
            logger.error(f"Failed to export results: {e}")
            raise
    
    def print_summary(self):
        """Print summary of results"""
        if not self.results:
            logger.info("No results to summarize")
            return
        
        # Count by status
        status_counts = {}
        for rule in self.results:
            status = rule.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count by firm
        firm_counts = {}
        for rule in self.results:
            firm = rule.firm_name
            firm_counts[firm] = firm_counts.get(firm, 0) + 1
        
        logger.info("=== SCRAPING SUMMARY ===")
        logger.info(f"Total rules extracted: {len(self.results)}")
        logger.info("Status breakdown:")
        for status, count in status_counts.items():
            logger.info(f"  {status}: {count}")
        
        logger.info("Firm breakdown:")
        for firm, count in firm_counts.items():
            logger.info(f"  {firm}: {count}")
    
    async def run(self):
        """Main execution method"""
        try:
            logger.info("=== PROPFIRM SCRAPER STARTED ===")
            
            # Load configuration
            self.load_config()
            
            # Scrape all sites
            await self.scrape_all_sites()
            
            # Print summary
            self.print_summary()
            
            # Export results
            export_result = self.export_results()
            
            logger.info("=== SCRAPING COMPLETED SUCCESSFULLY ===")
            if export_result:
                if export_result.startswith('http'):
                    logger.info(f"Google Sheets: {export_result}")
                else:
                    logger.info(f"CSV file: {export_result}")
            
        except Exception as e:
            logger.error(f"Scraper failed: {e}")
            raise

async def main():
    """Entry point"""
    scraper = PropFirmScraper()
    await scraper.run()

if __name__ == "__main__":
    asyncio.run(main())