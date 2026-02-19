"""
PropFirm Trading Rules Scraper - Main Entry Point
Complete automation for all 13 prop firm websites
"""
import asyncio
import logging
import yaml
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from propfirm_scraper.core.logger import setup_logger
from propfirm_scraper.core.browser import BrowserManager
from propfirm_scraper.config.schema import SiteConfig, TradingRule
from propfirm_scraper.config.enums import Status

# Import extractors
from propfirm_scraper.extractors.apex import ApexExtractor
from propfirm_scraper.extractors.tradeify import TradeifyExtractor

# Import exporters
from propfirm_scraper.exporters.csv_exporter import CSVExporter

logger = setup_logger()

# Try to import Google Sheets exporter
try:
    from propfirm_scraper.exporters.google_sheets import GoogleSheetsExporter
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Google Sheets not available: {e}")
    GOOGLE_SHEETS_AVAILABLE = False

class PropFirmScraper:
    """Complete PropFirm Trading Rules Scraper"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.config_path = "propfirm_scraper/config/sites.yaml"
        self.sites_config = {}
        self.global_settings = {}
        self.browser_manager = None
        self.results: List[TradingRule] = []
        
        # Google Sheets configuration
        self.sheet_id = "1V72k3xmBrppWC7fzMBIBYh2Ghh1HHP_2GTEf8BDaKGk"
        self.service_account_file = "service_account/tradingruleautomation-62475a2ca73b.json"
        
        # Statistics
        self.stats = {
            'total_sites': 0,
            'successful_sites': 0,
            'failed_sites': 0,
            'login_required_sites': 0,
            'not_implemented_sites': 0,
            'total_rules': 0
        }
    
    def print_header(self):
        """Print scraper header"""
        print("=" * 80)
        print("🚀 PROPFIRM TRADING RULES SCRAPER")
        print("=" * 80)
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Target: All 13 prop firm websites")
        print(f"Export: Google Sheets + CSV backup")
        print("=" * 80)
    
    def load_config(self):
        """Load sites configuration"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self.sites_config = config.get('sites', {})
            self.global_settings = config.get('settings', {})
            self.stats['total_sites'] = len(self.sites_config)
            
            logger.info(f"Loaded configuration for {len(self.sites_config)} sites")
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def get_extractor_class(self, extractor_name: str):
        """Get extractor class by name"""
        extractor_mapping = {
            'ApexExtractor': ApexExtractor,
            'TradeifyExtractor': TradeifyExtractor,
            # All others are not implemented yet
            'LucidExtractor': None,
            'MyFundedFuturesExtractor': None,
            'FundedNextExtractor': None,
            'AlphaFuturesExtractor': None,
            'TopOneFuturesExtractor': None,
            'BlueGuardianFuturesExtractor': None,
            'TradingPitExtractor': None,
            'LegendsTradingExtractor': None,
            'E8MarketsExtractor': None,
            'TakeProfitTraderExtractor': None,
            'TradeDayExtractor': None,
        }
        
        return extractor_mapping.get(extractor_name)
    
    async def scrape_site(self, site_name: str, site_config: Dict[str, Any]) -> List[TradingRule]:
        """Scrape a single website"""
        try:
            print(f"\n[{site_name}] Starting extraction...")
            
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
                print(f"[{site_name}] Skipped (disabled)")
                return []
            
            # Get extractor class
            extractor_class = self.get_extractor_class(config.extractor_class)
            
            if not extractor_class:
                print(f"[{site_name}] ⚠️  Not Implemented")
                rule = TradingRule(
                    firm_name=config.name,
                    account_size="Not Implemented",
                    account_size_usd=0.0,
                    website_url=config.url,
                    status=Status.NOT_IMPLEMENTED
                )
                rule.raw_data = {'error': 'Extractor not implemented'}
                return [rule]
            
            # Create page - let extractor handle navigation
            page = await self.browser_manager.new_page()
            
            try:
                # Create extractor and run extraction
                extractor = extractor_class(config)
                trading_rules = await extractor.extract_all_rules(page)
                
                if trading_rules:
                    print(f"[{site_name}] ✅ Success - {len(trading_rules)} rules extracted")
                else:
                    print(f"[{site_name}] ❌ No data extracted")
                
                return trading_rules
                
            except Exception as e:
                logger.error(f"Extraction failed for {site_name}: {e}")
                print(f"[{site_name}] ❌ Failed: {str(e)}")
                
                # Create failed rule
                rule = TradingRule(
                    firm_name=config.name,
                    account_size="Unknown",
                    account_size_usd=0.0,
                    website_url=config.url,
                    status=Status.FAILED
                )
                rule.raw_data = {'error': str(e)}
                return [rule]
                
            finally:
                await page.close()
            
        except Exception as e:
            logger.error(f"Failed to process {site_name}: {e}")
            print(f"[{site_name}] ❌ Error: {str(e)}")
            return []
    
    async def scrape_all_sites(self):
        """Scrape all configured websites"""
        try:
            # Initialize browser
            self.browser_manager = BrowserManager(
                headless=self.global_settings.get('headless', True),
                timeout=self.global_settings.get('page_timeout', 30000)
            )
            
            await self.browser_manager.start()
            print("🌐 Browser started successfully")
            
            # Process sites sequentially for better error handling
            all_results = []
            
            for i, (site_name, site_config) in enumerate(self.sites_config.items(), 1):
                try:
                    print(f"\n[{i}/{len(self.sites_config)}] Processing: {site_config['name']}")
                    
                    site_results = await self.scrape_site(site_name, site_config)
                    all_results.extend(site_results)
                    
                    # Small delay between sites
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error processing site {site_name}: {e}")
                    continue
            
            self.results = all_results
            
        except Exception as e:
            logger.error(f"Failed to scrape sites: {e}")
            raise
        
        finally:
            if self.browser_manager:
                await self.browser_manager.close()
                print("🌐 Browser closed")
    
    def calculate_stats(self):
        """Calculate scraping statistics"""
        # Count by status
        status_counts = {}
        firm_counts = {}
        
        for rule in self.results:
            status = rule.status.value
            firm = rule.firm_name
            
            status_counts[status] = status_counts.get(status, 0) + 1
            
            if firm not in firm_counts:
                firm_counts[firm] = {'total': 0, 'status': status}
            firm_counts[firm]['total'] += 1
        
        # Calculate site-level stats
        for firm_data in firm_counts.values():
            status = firm_data['status']
            if status == 'OK':
                self.stats['successful_sites'] += 1
            elif status == 'FAILED':
                self.stats['failed_sites'] += 1
            elif status == 'LOGIN_REQUIRED':
                self.stats['login_required_sites'] += 1
            elif status == 'NOT_IMPLEMENTED':
                self.stats['not_implemented_sites'] += 1
        
        self.stats['total_rules'] = len(self.results)
    
    def export_results(self):
        """Export results to Google Sheets or CSV"""
        try:
            if not self.results:
                print("⚠️  No results to export")
                return None
            
            # Try Google Sheets first
            if GOOGLE_SHEETS_AVAILABLE:
                try:
                    print("📤 Exporting to Google Sheets...")
                    
                    exporter = GoogleSheetsExporter(
                        sheet_id=self.sheet_id,
                        service_account_file=self.service_account_file
                    )
                    
                    sheet_url = exporter.export_all(self.results)
                    print(f"✅ Google Sheets: {sheet_url}")
                    return sheet_url
                    
                except Exception as e:
                    logger.error(f"Google Sheets export failed: {e}")
                    print(f"❌ Google Sheets failed: {e}")
                    print("📤 Falling back to CSV...")
            
            # Fallback to CSV export
            csv_exporter = CSVExporter()
            csv_file = csv_exporter.export_to_csv(self.results)
            summary_file = csv_exporter.export_summary(self.results)
            
            print(f"✅ CSV exported: {csv_file}")
            print(f"✅ Summary: {summary_file}")
            
            return csv_file
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            print(f"❌ Export failed: {e}")
            return None
    
    def print_summary(self):
        """Print final summary"""
        duration = datetime.now() - self.start_time
        
        print("\n" + "=" * 80)
        print("📊 SCRAPING SUMMARY")
        print("=" * 80)
        print(f"Duration: {duration.total_seconds():.1f} seconds")
        print(f"Sites Processed: {self.stats['total_sites']}")
        print(f"✅ Successful: {self.stats['successful_sites']}")
        print(f"❌ Failed: {self.stats['failed_sites']}")
        print(f"🔐 Login Required: {self.stats['login_required_sites']}")
        print(f"⚠️  Not Implemented: {self.stats['not_implemented_sites']}")
        print(f"📋 Total Rules: {self.stats['total_rules']}")
        
        if self.stats['total_sites'] > 0:
            success_rate = (self.stats['successful_sites'] / self.stats['total_sites']) * 100
            print(f"🎯 Success Rate: {success_rate:.1f}%")
    
    def print_detailed_results(self):
        """Print detailed results by firm"""
        print("\n" + "=" * 80)
        print("📋 DETAILED RESULTS")
        print("=" * 80)
        
        # Group by firm
        firms = {}
        for rule in self.results:
            firm_name = rule.firm_name
            if firm_name not in firms:
                firms[firm_name] = []
            firms[firm_name].append(rule)
        
        for firm_name, rules in firms.items():
            print(f"\n🏢 {firm_name}")
            
            for rule in rules:
                status_emoji = '✅' if rule.status.value == 'OK' else '❌' if rule.status.value == 'FAILED' else '⚠️'
                print(f"   {status_emoji} {rule.account_size} - {rule.status.value}")
                
                if rule.status.value == 'OK':
                    if rule.evaluation_target_usd:
                        print(f"      Target: ${rule.evaluation_target_usd:,.0f}")
                    if rule.evaluation_max_drawdown_usd:
                        print(f"      Drawdown: ${rule.evaluation_max_drawdown_usd:,.0f}")
                    if rule.profit_split_percent:
                        print(f"      Split: {rule.profit_split_percent}%")
    
    async def run(self):
        """Main execution method"""
        try:
            self.print_header()
            
            # Load configuration
            print("📋 Loading configuration...")
            self.load_config()
            
            # Scrape all sites
            print("🚀 Starting extraction...")
            await self.scrape_all_sites()
            
            # Calculate statistics
            self.calculate_stats()
            
            # Export results
            print("\n📤 Exporting results...")
            export_result = self.export_results()
            
            # Print results
            self.print_summary()
            self.print_detailed_results()
            
            print("\n" + "=" * 80)
            print("🎉 SCRAPING COMPLETED!")
            print("=" * 80)
            
            if export_result:
                if export_result.startswith('http'):
                    print("✅ Check your Google Sheet for complete data")
                else:
                    print("✅ Check CSV files in propfirm_scraper/data/")
            
        except Exception as e:
            logger.error(f"Scraper failed: {e}")
            print(f"❌ Scraper failed: {e}")
            raise

async def main():
    """Entry point"""
    print("🚀 PropFirm Trading Rules Scraper")
    print("=" * 50)
    
    try:
        scraper = PropFirmScraper()
        await scraper.run()
        
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())