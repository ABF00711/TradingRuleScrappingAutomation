"""
Run the complete PropFirm scraper
"""
import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def main():
    """Run the complete scraper"""
    try:
        print("PROPFIRM TRADING RULES SCRAPER")
        print("=" * 50)
        
        from propfirm_scraper.main import PropFirmScraper
        
        # Create and run scraper
        scraper = PropFirmScraper()
        await scraper.run()
        
    except Exception as e:
        print(f"Scraper failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())