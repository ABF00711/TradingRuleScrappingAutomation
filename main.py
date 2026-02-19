"""
Normalized PropFirm Trading Rules Scraper
Generic system that works with any prop firm website
"""
import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import re

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from propfirm_scraper.core.logger import setup_logger
from propfirm_scraper.core.generic_extractor import GenericExtractor
from propfirm_scraper.core.website_loader import WebsiteLoader
from propfirm_scraper.config.schema import TradingRule
from propfirm_scraper.config.enums import Status
from propfirm_scraper.exporters.csv_exporter import CSVExporter

logger = setup_logger()

# Try to import Google Sheets exporter
try:
    from propfirm_scraper.exporters.google_sheets import GoogleSheetsExporter
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Google Sheets not available: {e}")
    GOOGLE_SHEETS_AVAILABLE = False

class NormalizedPropFirmScraper:
    """Normalized scraper that works with any prop firm website"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.websites_file = "Websites.txt"
        self.websites = []
        self.results: List[TradingRule] = []
        
        # Google Sheets configuration
        self.sheet_id = "1V72k3xmBrppWC7fzMBIBYh2Ghh1HHP_2GTEf8BDaKGk"
        self.service_account_file = "service_account/tradingruleautomation-62475a2ca73b.json"
        
        # Statistics
        self.stats = {
            'total_sites': 0,
            'successful_sites': 0,
            'failed_sites': 0,
            'http_success': 0,
            'browser_success': 0,
            'chatbot_success': 0,
            'total_rules': 0
        }
    
    def print_header(self):
        """Print scraper header"""
        print("=" * 80)
        print("NORMALIZED PROPFIRM SCRAPER")
        print("=" * 80)
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Input: {self.websites_file}")
        print(f"Method: HTTP -> Browser -> Chatbot -> Manual")
        print(f"Export: Google Sheets + CSV backup")
        print("=" * 80)
    
    def load_websites(self):
        """Load websites from websites.txt file"""
        try:
            if not Path(self.websites_file).exists():
                raise FileNotFoundError(f"{self.websites_file} not found")
            
            with open(self.websites_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            self.websites = []
            for line in lines:
                url = line.strip()
                if url and url.startswith('http'):
                    # Extract firm name from URL
                    parsed = urlparse(url)
                    domain = parsed.netloc.lower()
                    
                    # Extract firm name from domain
                    firm_name = self.extract_firm_name(domain)
                    
                    self.websites.append({
                        'url': url,
                        'firm_name': firm_name,
                        'domain': domain
                    })
            
            self.stats['total_sites'] = len(self.websites)
            logger.info(f"Loaded {len(self.websites)} websites from {self.websites_file}")
            
            # Print loaded websites
            print(f"\nLoaded {len(self.websites)} websites:")
            for i, site in enumerate(self.websites, 1):
                print(f"  {i:2d}. {site['firm_name']} - {site['url']}")
            
        except Exception as e:
            logger.error(f"Failed to load websites: {e}")
            raise
    
    def extract_firm_name(self, domain: str) -> str:
        """Extract firm name from domain"""
        # Remove common prefixes and suffixes
        domain = domain.replace('www.', '').replace('help.', '').replace('support.', '')
        domain = domain.replace('knowledge.', '').replace('helpfutures.', '')
        
        # Split by dots and take main part
        parts = domain.split('.')
        if len(parts) >= 2:
            main_part = parts[0]
        else:
            main_part = domain
        
        # Convert to readable name
        name_mappings = {
            'apextraderfunding': 'Apex Trader Funding',
            'lucidtrading': 'Lucid Trading',
            'tradeify': 'Tradeify',
            'myfundedfutures': 'My Funded Futures',
            'fundednext': 'Funded Next',
            'alpha-futures': 'Alpha Futures',
            'intercom': 'Top One Futures',
            'blueguardianfutures': 'Blue Guardian Futures',
            'thetradingpit': 'The Trading Pit',
            'thelegendstrading': 'Legends Trading',
            'e8markets': 'E8 Markets',
            'takeprofittraderhelp': 'Take Profit Trader',
            'tradeday': 'Trade Day'
        }
        
        # Check for exact matches first
        for key, name in name_mappings.items():
            if key in main_part.lower():
                return name
        
        # Fallback: capitalize and clean
        return main_part.replace('-', ' ').replace('_', ' ').title()
    
    async def scrape_website(self, website: Dict[str, Any]) -> List[TradingRule]:
        """Scrape a single website using normalized approach"""
        firm_name = website['firm_name']
        url = website['url']
        
        try:
            print(f"\n[{firm_name}] Starting extraction...")
            print(f"    URL: {url}")
            
            # Initialize website loader
            loader = WebsiteLoader()
            
            # Step 1: Try HTTP request first (fastest)
            print(f"    Trying HTTP request...")
            http_content = await loader.load_with_http(url)
            
            if http_content:
                print(f"    HTTP successful")
                extractor = GenericExtractor(firm_name, url)
                rules = await extractor.extract_from_html(http_content)
                
                if rules:
                    self.stats['http_success'] += 1
                    print(f"    Extracted {len(rules)} rules via HTTP")
                    return rules
            
            # Step 2: Try browser automation
            print(f"    Trying browser automation...")
            browser_content = await loader.load_with_browser(url)
            
            if browser_content:
                print(f"    Browser successful")
                extractor = GenericExtractor(firm_name, url)
                rules = await extractor.extract_from_browser_content(browser_content)
                
                if rules:
                    self.stats['browser_success'] += 1
                    print(f"    Extracted {len(rules)} rules via Browser")
                    return rules
            
            # Step 3: Try chatbot integration (if available)
            print(f"    Trying chatbot integration...")
            chatbot_data = await loader.try_chatbot_extraction(url)
            
            if chatbot_data:
                print(f"    Chatbot successful")
                extractor = GenericExtractor(firm_name, url)
                rules = await extractor.extract_from_chatbot_data(chatbot_data)
                
                if rules:
                    self.stats['chatbot_success'] += 1
                    print(f"    Extracted {len(rules)} rules via Chatbot")
                    return rules
            
            # Step 4: Manual fallback - create placeholder
            print(f"    All methods failed, creating placeholder")
            rule = TradingRule(
                firm_name=firm_name,
                account_size="Manual Review Required",
                account_size_usd=0.0,
                website_url=url,
                status=Status.MISSING_DATA
            )
            rule.raw_data = {
                'error': 'All extraction methods failed',
                'note': 'Manual review required - website structure not recognized'
            }
            
            return [rule]
            
        except Exception as e:
            logger.error(f"Error processing {firm_name}: {e}")
            print(f"    ERROR: {str(e)}")
            
            # Create failed rule
            rule = TradingRule(
                firm_name=firm_name,
                account_size="Error",
                account_size_usd=0.0,
                website_url=url,
                status=Status.FAILED
            )
            rule.raw_data = {'error': str(e)}
            
            return [rule]
    
    async def scrape_all_websites(self):
        """Scrape all websites using normalized approach"""
        try:
            print("\nStarting normalized extraction...")
            
            all_results = []
            
            for i, website in enumerate(self.websites, 1):
                try:
                    print(f"\n[{i}/{len(self.websites)}] Processing: {website['firm_name']}")
                    
                    site_results = await self.scrape_website(website)
                    
                    # Debug: check what we got
                    logger.debug(f"Site results type: {type(site_results)}, length: {len(site_results) if site_results else 0}")
                    
                    # Flatten any nested lists
                    if site_results:
                        for result in site_results:
                            if isinstance(result, list):
                                # If we got a nested list, flatten it
                                logger.warning(f"Found nested list in results for {website['firm_name']}")
                                all_results.extend(result)
                            else:
                                # Normal case - individual rule
                                all_results.append(result)
                    
                    # Update stats
                    if site_results and site_results[0].status == Status.OK:
                        self.stats['successful_sites'] += 1
                    else:
                        self.stats['failed_sites'] += 1
                    
                    # Small delay between sites
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error processing {website['firm_name']}: {e}")
                    self.stats['failed_sites'] += 1
                    continue
            
            self.results = all_results
            self.stats['total_rules'] = len(self.results)
            
        except Exception as e:
            logger.error(f"Failed to scrape websites: {e}")
            raise
    
    def export_results(self):
        """Export results to Google Sheets or CSV"""
        try:
            if not self.results:
                print("WARNING: No results to export")
                return None
            
            # Try Google Sheets first
            if GOOGLE_SHEETS_AVAILABLE:
                try:
                    print("[OUTBOX] Exporting to Google Sheets...")
                    
                    exporter = GoogleSheetsExporter(
                        sheet_id=self.sheet_id,
                        service_account_file=self.service_account_file
                    )
                    
                    sheet_url = exporter.export_all(self.results)
                    print(f"SUCCESS: Google Sheets: {sheet_url}")
                    return sheet_url
                    
                except Exception as e:
                    logger.error(f"Google Sheets export failed: {e}")
                    print(f"ERROR: Google Sheets failed: {e}")
                    print("[OUTBOX] Falling back to CSV...")
            
            # Fallback to CSV export
            csv_exporter = CSVExporter()
            csv_file = csv_exporter.export_to_csv(self.results)
            summary_file = csv_exporter.export_summary(self.results)
            
            print(f"[SUCCESS] CSV exported: {csv_file}")
            print(f"[SUCCESS] Summary: {summary_file}")
            
            return csv_file
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            print(f"[ERROR] Export failed: {e}")
            return None
    
    def print_summary(self):
        """Print final summary"""
        duration = datetime.now() - self.start_time
        
        print("\n" + "=" * 80)
        print("[CHART] EXTRACTION SUMMARY")
        print("=" * 80)
        print(f"Duration: {duration.total_seconds():.1f} seconds")
        print(f"Sites Processed: {self.stats['total_sites']}")
        print(f"[SUCCESS] Successful: {self.stats['successful_sites']}")
        print(f"[ERROR] Failed: {self.stats['failed_sites']}")
        print(f"[CLIPBOARD] Total Rules: {self.stats['total_rules']}")
        
        print(f"\n🔧 Method Breakdown:")
        print(f"[SATELLITE] HTTP Success: {self.stats['http_success']}")
        print(f"[GLOBE] Browser Success: {self.stats['browser_success']}")
        print(f"[ROBOT] Chatbot Success: {self.stats['chatbot_success']}")
        
        if self.stats['total_sites'] > 0:
            success_rate = (self.stats['successful_sites'] / self.stats['total_sites']) * 100
            print(f"[TARGET] Success Rate: {success_rate:.1f}%")
    
    def print_detailed_results(self):
        """Print detailed results"""
        print("\n" + "=" * 80)
        print("[CLIPBOARD] DETAILED RESULTS")
        print("=" * 80)
        
        # Group by firm with safety checks
        firms = {}
        for rule in self.results:
            # Safety check for nested lists or invalid objects
            if isinstance(rule, list):
                logger.error(f"Found nested list in results: {rule}")
                continue
            
            if not hasattr(rule, 'firm_name'):
                logger.error(f"Invalid rule object without firm_name: {type(rule)}")
                continue
            
            firm_name = rule.firm_name
            if firm_name not in firms:
                firms[firm_name] = []
            firms[firm_name].append(rule)
        
        for firm_name, rules in firms.items():
            print(f"\n[BUILDING] {firm_name}")
            
            for rule in rules:
                # Safety check for nested lists
                if isinstance(rule, list):
                    logger.error(f"Found nested list in results for {firm_name}: {rule}")
                    continue
                
                # Safety check for rule object
                if not hasattr(rule, 'status') or not hasattr(rule, 'account_size'):
                    logger.error(f"Invalid rule object for {firm_name}: {type(rule)}")
                    continue
                
                status_emoji = '[SUCCESS]' if rule.status.value == 'OK' else '[ERROR]' if rule.status.value == 'FAILED' else '[WARNING]'
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
            
            # Load websites from file
            print("[CLIPBOARD] Loading websites...")
            self.load_websites()
            
            if not self.websites:
                print("[ERROR] No websites found in websites.txt")
                return
            
            # Scrape all websites
            await self.scrape_all_websites()
            
            # Export results
            print("\n[OUTBOX] Exporting results...")
            export_result = self.export_results()
            
            # Print results
            self.print_summary()
            self.print_detailed_results()
            
            print("\n" + "=" * 80)
            print("[CELEBRATION] SCRAPING COMPLETED!")
            print("=" * 80)
            print("[SUCCESS] System is now fully normalized and user-configurable")
            print("[SUCCESS] Add any prop firm website to websites.txt")
            print("[SUCCESS] No coding required for new sites")
            
            if export_result:
                if export_result.startswith('http'):
                    print("[SUCCESS] Check your Google Sheet for complete data")
                else:
                    print("[SUCCESS] Check CSV files in propfirm_scraper/data/")
            
        except Exception as e:
            logger.error(f"Scraper failed: {e}")
            print(f"[ERROR] Scraper failed: {e}")
            raise

async def main():
    """Entry point"""
    print("[ROCKET] Normalized PropFirm Trading Rules Scraper")
    print("=" * 50)
    print("[SUCCESS] Works with ANY prop firm website")
    print("[SUCCESS] User-configurable via websites.txt")
    print("[SUCCESS] No coding required for new sites")
    print("=" * 50)
    
    try:
        scraper = NormalizedPropFirmScraper()
        await scraper.run()
        
    except KeyboardInterrupt:
        print("\n[WARNING]  Interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())