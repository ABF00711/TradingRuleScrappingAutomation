"""
Test script for My Funded Futures extractor
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from propfirm_scraper.core.browser import BrowserManager
from propfirm_scraper.extractors.myfundedfutures import MyFundedFuturesExtractor
from propfirm_scraper.core.logger import setup_logger
from propfirm_scraper.config.schema import SiteConfig

logger = setup_logger()

async def test_myfundedfutures_extractor():
    """Test the My Funded Futures extractor"""
    
    print("=" * 60)
    print("TESTING MY FUNDED FUTURES EXTRACTOR")
    print("=" * 60)
    
    browser_manager = None
    
    try:
        # Initialize browser manager
        print("\n1. Initializing browser...")
        browser_manager = BrowserManager(headless=False)  # Set to False for debugging
        await browser_manager.start()
        
        # Create site config
        print("2. Creating site configuration...")
        site_config = SiteConfig(
            name="My Funded Futures",
            url="https://help.myfundedfutures.com/en/",
            extractor_class="MyFundedFuturesExtractor"
        )
        
        # Initialize extractor
        print("3. Initializing My Funded Futures extractor...")
        extractor = MyFundedFuturesExtractor(site_config)
        
        # Create a page and navigate to the website
        print("4. Creating page and navigating to website...")
        page = await browser_manager.new_page()
        await page.goto(site_config.url, wait_until="networkidle")
        
        # Test the full extraction process
        print("\n5. Running full extraction process...")
        try:
            trading_rules = await extractor.extract_all_rules(page)
            print(f"   Successfully extracted {len(trading_rules)} trading rules")
            
            # Print summary of extracted rules
            for i, rule in enumerate(trading_rules[:5]):  # Show first 5 rules
                print(f"\n   Rule {i+1}:")
                print(f"     Firm: {rule.firm_name}")
                print(f"     Account Size: {rule.account_size}")
                print(f"     Status: {rule.status}")
                print(f"     Profit Target: ${rule.evaluation_target_usd:,.0f}" if rule.evaluation_target_usd else "     Profit Target: N/A")
                print(f"     Max Drawdown: ${rule.evaluation_max_drawdown_usd:,.0f}" if rule.evaluation_max_drawdown_usd else "     Max Drawdown: N/A")
                print(f"     Profit Split: {rule.profit_split_percent}%" if rule.profit_split_percent else "     Profit Split: N/A")
            
            if len(trading_rules) > 5:
                print(f"   ... and {len(trading_rules) - 5} more rules")
                
        except Exception as e:
            print(f"   ERROR in full extraction: {e}")
            import traceback
            traceback.print_exc()
        
        # Close the page
        await page.close()
        
        print("\n" + "=" * 60)
        print("MY FUNDED FUTURES EXTRACTOR TEST COMPLETED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nERROR during testing: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if browser_manager:
            print("\n6. Closing browser...")
            await browser_manager.close()

if __name__ == "__main__":
    asyncio.run(test_myfundedfutures_extractor())