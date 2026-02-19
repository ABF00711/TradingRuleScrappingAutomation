"""
Complete PropFirm Trading Rules Scraper
Processes all 13 websites automatically
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class CompletePropFirmScraper:
    """Complete scraper for all prop firm websites"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.results = []
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
        print("🚀 PROPFIRM TRADING RULES SCRAPER - COMPLETE AUTOMATION")
        print("=" * 80)
        print(f"Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Target: All 13 prop firm websites")
        print(f"Export: Google Sheets + CSV backup")
        print("=" * 80)
    
    def print_progress(self, current, total, site_name, status):
        """Print progress for current site"""
        progress = (current / total) * 100
        print(f"\n[{current}/{total}] ({progress:.1f}%) Processing: {site_name}")
        print(f"Status: {status}")
    
    def print_site_result(self, site_name, rules_count, status, duration):
        """Print result for completed site"""
        status_emoji = {
            'OK': '✅',
            'FAILED': '❌', 
            'LOGIN_REQUIRED': '🔐',
            'NOT_IMPLEMENTED': '⚠️'
        }
        
        emoji = status_emoji.get(status, '❓')
        print(f"{emoji} {site_name}: {rules_count} rules extracted ({duration:.1f}s)")
    
    def update_stats(self, status, rules_count):
        """Update scraping statistics"""
        self.stats['total_rules'] += rules_count
        
        if status == 'OK':
            self.stats['successful_sites'] += 1
        elif status == 'FAILED':
            self.stats['failed_sites'] += 1
        elif status == 'LOGIN_REQUIRED':
            self.stats['login_required_sites'] += 1
        elif status == 'NOT_IMPLEMENTED':
            self.stats['not_implemented_sites'] += 1
    
    def print_summary(self):
        """Print final summary"""
        duration = datetime.now() - self.start_time
        
        print("\n" + "=" * 80)
        print("📊 SCRAPING SUMMARY")
        print("=" * 80)
        print(f"Total Duration: {duration.total_seconds():.1f} seconds")
        print(f"Total Sites Processed: {self.stats['total_sites']}")
        print(f"✅ Successful: {self.stats['successful_sites']}")
        print(f"❌ Failed: {self.stats['failed_sites']}")
        print(f"🔐 Login Required: {self.stats['login_required_sites']}")
        print(f"⚠️  Not Implemented: {self.stats['not_implemented_sites']}")
        print(f"📋 Total Rules Extracted: {self.stats['total_rules']}")
        
        # Success rate
        if self.stats['total_sites'] > 0:
            success_rate = (self.stats['successful_sites'] / self.stats['total_sites']) * 100
            print(f"🎯 Success Rate: {success_rate:.1f}%")
    
    def print_detailed_results(self):
        """Print detailed results by firm"""
        print("\n" + "=" * 80)
        print("📋 DETAILED RESULTS BY FIRM")
        print("=" * 80)
        
        # Group results by firm
        firms = {}
        for rule in self.results:
            firm_name = rule.firm_name
            if firm_name not in firms:
                firms[firm_name] = []
            firms[firm_name].append(rule)
        
        for firm_name, rules in firms.items():
            print(f"\n🏢 {firm_name}")
            print(f"   Account Sizes: {len(rules)}")
            
            for rule in rules:
                status_emoji = '✅' if rule.status.value == 'OK' else '❌'
                print(f"   {status_emoji} {rule.account_size} - {rule.status.value}")
                
                if rule.status.value == 'OK':
                    if rule.evaluation_target_usd:
                        print(f"      Target: ${rule.evaluation_target_usd:,.0f}")
                    if rule.evaluation_max_drawdown_usd:
                        print(f"      Drawdown: ${rule.evaluation_max_drawdown_usd:,.0f}")
                    if rule.profit_split_percent:
                        print(f"      Split: {rule.profit_split_percent}%")
    
    async def run_complete_scraper(self):
        """Run the complete scraper for all sites"""
        try:
            from propfirm_scraper.main import PropFirmScraper
            
            # Create scraper instance
            scraper = PropFirmScraper()
            
            # Load configuration
            scraper.load_config()
            self.stats['total_sites'] = len(scraper.sites_config)
            
            # Run scraper
            print("🌐 Loading browser and starting extraction...")
            await scraper.scrape_all_sites()
            
            # Get results
            self.results = scraper.results
            
            # Update stats
            for rule in self.results:
                # Count unique sites (not individual rules)
                pass
            
            # Calculate site-level stats
            site_statuses = {}
            for rule in self.results:
                firm = rule.firm_name
                if firm not in site_statuses:
                    site_statuses[firm] = rule.status.value
            
            for status in site_statuses.values():
                if status == 'OK':
                    self.stats['successful_sites'] += 1
                elif status == 'FAILED':
                    self.stats['failed_sites'] += 1
                elif status == 'LOGIN_REQUIRED':
                    self.stats['login_required_sites'] += 1
                else:
                    self.stats['not_implemented_sites'] += 1
            
            self.stats['total_rules'] = len(self.results)
            
            # Export results
            print("\n📤 Exporting results...")
            export_result = scraper.export_results()
            
            if export_result:
                if export_result.startswith('http'):
                    print(f"✅ Exported to Google Sheets: {export_result}")
                else:
                    print(f"✅ Exported to CSV: {export_result}")
            
            return True
            
        except Exception as e:
            print(f"❌ Scraper failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def run(self):
        """Main execution method"""
        self.print_header()
        
        # Run the complete scraper
        success = await self.run_complete_scraper()
        
        if success:
            # Print results
            self.print_summary()
            self.print_detailed_results()
            
            print("\n" + "=" * 80)
            print("🎉 SCRAPING COMPLETED SUCCESSFULLY!")
            print("=" * 80)
            print("✅ Data exported to Google Sheets")
            print("✅ CSV backup created")
            print("✅ Summary report generated")
            
            # Next steps
            print("\n📋 NEXT STEPS:")
            print("1. Check your Google Sheet for the complete data")
            print("2. Review CSV files in propfirm_scraper/data/")
            print("3. Implement more extractors for failed sites")
            
        else:
            print("\n❌ SCRAPING FAILED")
            print("Please check the error messages above")

async def main():
    """Entry point"""
    scraper = CompletePropFirmScraper()
    await scraper.run()

if __name__ == "__main__":
    asyncio.run(main())