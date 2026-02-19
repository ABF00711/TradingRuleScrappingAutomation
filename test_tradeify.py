"""
Test script for Tradeify extractor
"""
import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_tradeify_extractor():
    """Test the Tradeify extractor"""
    try:
        print("Testing Tradeify Extractor")
        print("=" * 50)
        
        # Import required modules
        from propfirm_scraper.core.logger import setup_logger
        from propfirm_scraper.core.browser import BrowserManager
        from propfirm_scraper.config.schema import SiteConfig
        from propfirm_scraper.extractors.tradeify import TradeifyExtractor
        
        # Setup logger
        logger = setup_logger()
        
        # Create site config for Tradeify
        tradeify_config = SiteConfig(
            name="Tradeify",
            url="https://help.tradeify.co/en",
            extractor_class="TradeifyExtractor",
            enabled=True,
            timeout=30,
            retry_attempts=2,
            notes="Test run"
        )
        
        # Create browser manager
        browser_manager = BrowserManager(headless=False, timeout=30000)
        
        print("Starting browser...")
        await browser_manager.start()
        
        # Create page and load website
        page = await browser_manager.new_page()
        print(f"Loading website: {tradeify_config.url}")
        await browser_manager.load_page(tradeify_config.url, page)
        
        # Check if login is required
        login_required = await browser_manager.detect_login_page(page)
        print(f"Login detection result: {login_required}")
        
        if login_required:
            print("Login required - cannot proceed")
            await page.close()
            await browser_manager.close()
            return
        
        print("Website loaded successfully - no login required")
        
        # Create extractor
        extractor = TradeifyExtractor(tradeify_config)
        
        # Test complete extraction
        print("\nTesting complete extraction for all account sizes...")
        trading_rules = await extractor.extract_all_rules(page)
        
        print(f"\nExtraction completed!")
        print(f"Total rules extracted: {len(trading_rules)}")
        
        # Display summary
        for i, rule in enumerate(trading_rules):
            print(f"\nRule {i+1}:")
            print(f"  Firm: {rule.firm_name}")
            print(f"  Account Size: {rule.account_size}")
            print(f"  Status: {rule.status.value}")
            print(f"  Evaluation Target: ${rule.evaluation_target_usd:,.2f}" if rule.evaluation_target_usd else "  Evaluation Target: N/A")
            print(f"  Max Drawdown: ${rule.evaluation_max_drawdown_usd:,.2f}" if rule.evaluation_max_drawdown_usd else "  Max Drawdown: N/A")
            print(f"  Daily Loss: ${rule.evaluation_daily_loss_usd:,.2f}" if rule.evaluation_daily_loss_usd else "  Daily Loss: N/A")
            print(f"  Profit Split: {rule.profit_split_percent}%" if rule.profit_split_percent else "  Profit Split: N/A")
            print(f"  Min Days: {rule.evaluation_min_days}" if rule.evaluation_min_days else "  Min Days: N/A")
        
        # Close browser
        await page.close()
        await browser_manager.close()
        
        print(f"\nTest completed successfully!")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_tradeify_extractor())