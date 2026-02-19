"""
Quick and Easy PropFirm Scraper
Run this to scrape all websites and export to Google Sheets
"""
import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def print_intro():
    """Print introduction"""
    print("🚀 PropFirm Trading Rules Scraper")
    print("=" * 50)
    print("This will:")
    print("✅ Scrape all 13 prop firm websites")
    print("✅ Extract trading rules and account data")
    print("✅ Export to Google Sheets automatically")
    print("✅ Create CSV backup files")
    print("✅ Generate summary reports")
    print()
    print("Currently implemented extractors:")
    print("✅ Apex Trader Funding (2 account sizes)")
    print("✅ Tradeify (3 account sizes)")
    print("⚠️  11 other sites (will show 'Not Implemented')")
    print()

async def main():
    """Main execution"""
    print_intro()
    
    # Ask user confirmation
    response = input("Ready to start scraping? (y/n): ").lower().strip()
    
    if response != 'y':
        print("Scraping cancelled.")
        return
    
    print("\n🚀 Starting complete scraper...")
    print("This may take 5-10 minutes depending on website response times.")
    print()
    
    try:
        # Import and run the complete scraper
        from scrape_all import CompletePropFirmScraper
        
        scraper = CompletePropFirmScraper()
        await scraper.run()
        
    except KeyboardInterrupt:
        print("\n⚠️  Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Please check your setup and try again")

if __name__ == "__main__":
    asyncio.run(main())