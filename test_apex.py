"""
Test script for Apex Trader Funding extractor
"""
import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_apex_extractor():
    """Test the Apex extractor"""
    try:
        print("Testing Apex Trader Funding Extractor")
        print("=" * 50)
        
        # Import required modules
        from propfirm_scraper.core.logger import setup_logger
        from propfirm_scraper.core.browser import BrowserManager
        from propfirm_scraper.config.schema import SiteConfig
        from propfirm_scraper.extractors.apex import ApexExtractor
        
        # Setup logger
        logger = setup_logger()
        
        # Create site config for Apex
        apex_config = SiteConfig(
            name="Apex Trader Funding",
            url="https://support.apextraderfunding.com/hc/en-us",
            extractor_class="ApexExtractor",
            enabled=True,
            timeout=30,
            retry_attempts=2,
            notes="Test run"
        )
        
        # Create browser manager
        browser_manager = BrowserManager(headless=False, timeout=30000)  # Use non-headless for testing
        
        print("Starting browser...")
        try:
            await browser_manager.start()
        except Exception as e:
            print(f"Failed to start browser: {e}")
            print("Make sure Playwright browsers are installed: py -3.12 -m playwright install")
            return
        
        # Create page and load website
        page = await browser_manager.new_page()
        print(f"Loading website: {apex_config.url}")
        await browser_manager.load_page(apex_config.url, page)
        
        # Check if login is required
        login_required = await browser_manager.detect_login_page(page)
        print(f"Login detection result: {login_required}")
        
        if login_required:
            print("❌ Login required - cannot proceed")
            print(f"Current URL: {page.url}")
            print(f"Page title: {await page.title()}")
            await page.close()
            await browser_manager.close()
            return
        
        print("✅ Website loaded successfully - no login required")
        
        # Expand accordions
        await browser_manager.expand_accordions(page)
        
        # Create extractor
        extractor = ApexExtractor(apex_config)
        
        # Test account sizes extraction
        print("\n1. Testing account sizes extraction...")
        account_sizes = await extractor.get_account_sizes(page)
        print(f"Found account sizes: {account_sizes}")
        
        # Test extraction for first account size
        if account_sizes:
            test_size = account_sizes[0]
            print(f"\n2. Testing rule extraction for {test_size}...")
            
            # Extract evaluation rules
            print("   - Extracting evaluation rules...")
            eval_rules = await extractor.extract_evaluation_rules(page, test_size)
            print(f"     Evaluation rules: {eval_rules}")
            
            # Extract funded rules
            print("   - Extracting funded rules...")
            funded_rules = await extractor.extract_funded_rules(page, test_size)
            print(f"     Funded rules: {funded_rules}")
            
            # Extract payout rules
            print("   - Extracting payout rules...")
            payout_rules = await extractor.extract_payout_rules(page, test_size)
            print(f"     Payout rules: {payout_rules}")
            
            # Extract fee rules
            print("   - Extracting fee rules...")
            fee_rules = await extractor.extract_fee_rules(page, test_size)
            print(f"     Fee rules: {fee_rules}")
            
            # Extract broker/platform info
            print("   - Extracting broker/platform info...")
            broker_platform = await extractor.extract_broker_platform(page)
            print(f"     Broker/Platform: {broker_platform}")
        
        # Test complete extraction
        print(f"\n3. Testing complete extraction for all account sizes...")
        trading_rules = await extractor.extract_all_rules(page)
        
        print(f"\n✅ Extraction completed!")
        print(f"Total rules extracted: {len(trading_rules)}")
        
        # Display summary
        for i, rule in enumerate(trading_rules):
            print(f"\nRule {i+1}:")
            print(f"  Firm: {rule.firm_name}")
            print(f"  Account Size: {rule.account_size}")
            print(f"  Status: {rule.status.value}")
            print(f"  Evaluation Target: ${rule.evaluation_target_usd:,.2f}" if rule.evaluation_target_usd else "  Evaluation Target: N/A")
            print(f"  Max Drawdown: ${rule.evaluation_max_drawdown_usd:,.2f}" if rule.evaluation_max_drawdown_usd else "  Max Drawdown: N/A")
            print(f"  Profit Split: {rule.profit_split_percent}%" if rule.profit_split_percent else "  Profit Split: N/A")
        
        # Close browser
        await page.close()
        await browser_manager.close()
        
        print(f"\n🎉 Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_apex_extractor())