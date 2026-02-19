"""
Test Google Sheets connection and export
"""
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_google_sheets():
    """Test Google Sheets connection"""
    try:
        print("Testing Google Sheets Connection")
        print("=" * 50)
        
        from propfirm_scraper.exporters.google_sheets import GoogleSheetsExporter
        from propfirm_scraper.config.schema import TradingRule
        from propfirm_scraper.config.enums import Status, DrawdownType, PayoutFrequency
        from datetime import datetime
        
        # Test connection
        sheet_id = "1V72k3xmBrppWC7fzMBIBYh2Ghh1HHP_2GTEf8BDaKGk"
        service_account_file = "service_account/tradingruleautomation-62475a2ca73b.json"
        
        print(f"Sheet ID: {sheet_id}")
        print(f"Service Account File: {service_account_file}")
        
        # Create exporter
        exporter = GoogleSheetsExporter(
            sheet_id=sheet_id,
            service_account_file=service_account_file
        )
        
        # Get sheet info
        sheet_info = exporter.get_sheet_info()
        if sheet_info:
            print(f"✅ Connected to sheet: {sheet_info['title']}")
            print(f"   URL: {sheet_info['url']}")
        else:
            print("❌ Failed to connect to sheet")
            return False
        
        # Create test data
        test_rule = TradingRule(
            firm_name="Test Firm",
            account_size="$50,000",
            account_size_usd=50000.0,
            website_url="https://example.com",
            evaluation_target_usd=4000.0,
            evaluation_max_drawdown_usd=2500.0,
            evaluation_drawdown_type=DrawdownType.STATIC,
            evaluation_min_days=10,
            profit_split_percent=90.0,
            payout_frequency=PayoutFrequency.BIWEEKLY,
            min_payout_usd=500.0,
            evaluation_fee_usd=247.0,
            reset_fee_usd=90.0,
            status=Status.OK
        )
        
        # Test export
        print("\nTesting export...")
        sheet_url = exporter.export_all([test_rule])
        
        print(f"✅ Test export successful!")
        print(f"   Check your sheet: {sheet_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Google Sheets test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_google_sheets()
    if success:
        print("\n🎉 Google Sheets is ready!")
    else:
        print("\n❌ Please fix Google Sheets setup before proceeding")
        print("\nMake sure you've:")
        print("1. Shared the sheet with: propfirm-scraper@tradingruleautomation.iam.gserviceaccount.com")
        print("2. Given 'Editor' permissions")
        print("3. Service account file is in the correct location")