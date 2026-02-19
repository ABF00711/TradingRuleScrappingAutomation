"""
Test script for Blue Guardian Futures extractor
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from propfirm_scraper.core.browser import BrowserManager
from propfirm_scraper.extractors.blueguardianfutures import BlueGuardianFuturesExtractor
from propfirm_scraper.core.logger import setup_logger
from propfirm_scraper.config.schema import SiteConfig

logger = setup_logger()

async def test_blueguardianfutures_extractor():
    """Test the Blue Guardian Futures extractor"""
    
    print("=" * 60)
    print("TESTING BLUE GUARDIAN FUTURES EXTRACTOR")
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
            name="Blue Guardian Futures",
            url="https://blueguardianfutures.com/",
            extractor_class="BlueGuardianFuturesExtractor"
        )
        
        # Initialize extractor
        print("3. Initializing Blue Guardian Futures extractor...")
        extractor = BlueGuardianFuturesExtractor(site_config)
        
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
            for i, rule in enumerate(trading_rules):
                print(f"\n   Rule {i+1}:")
                print(f"     Firm: {rule.firm_name}")
                print(f"     Account Size: {rule.account_size}")
                print(f"     Status: {rule.status}")
                print(f"     Profit Target: ${rule.evaluation_target_usd:,.0f}" if rule.evaluation_target_usd else "     Profit Target: N/A")
                print(f"     Max Drawdown: ${rule.evaluation_max_drawdown_usd:,.0f}" if rule.evaluation_max_drawdown_usd else "     Max Drawdown: N/A")
                print(f"     Daily Loss Limit: ${rule.evaluation_daily_loss_usd:,.0f}" if rule.evaluation_daily_loss_usd else "     Daily Loss Limit: None")
                print(f"     Drawdown Type: {rule.evaluation_drawdown_type}" if rule.evaluation_drawdown_type else "     Drawdown Type: N/A")
                print(f"     Min Trading Days: {rule.evaluation_min_days}" if rule.evaluation_min_days else "     Min Trading Days: None")
                print(f"     Consistency Rule: {rule.evaluation_consistency}" if rule.evaluation_consistency is not None else "     Consistency Rule: N/A")
                print(f"     Profit Split: {rule.profit_split_percent}%" if rule.profit_split_percent else "     Profit Split: N/A")
                print(f"     Payout Frequency: {rule.payout_frequency}" if rule.payout_frequency else "     Payout Frequency: N/A")
                print(f"     Evaluation Fee: ${rule.evaluation_fee_usd:,.0f}" if rule.evaluation_fee_usd else "     Evaluation Fee: N/A")
                
        except Exception as e:
            print(f"   ERROR in full extraction: {e}")
            import traceback
            traceback.print_exc()
        
        # Close the page
        await page.close()
        
        print("\n" + "=" * 60)
        print("BLUE GUARDIAN FUTURES EXTRACTOR TEST COMPLETED")
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
    asyncio.run(test_blueguardianfutures_extractor())