"""
Test script to verify the setup is working correctly
"""
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all modules can be imported"""
    try:
        print("Testing imports...")
        
        # Test config imports
        from propfirm_scraper.config.enums import DrawdownType, PayoutFrequency, Status
        from propfirm_scraper.config.schema import TradingRule, SiteConfig
        print("+ Config modules imported successfully")
        
        # Test core imports
        from propfirm_scraper.core.currency_converter import converter
        from propfirm_scraper.core.utils import extract_number, extract_percentage
        from propfirm_scraper.core.logger import setup_logger
        print("+ Core modules imported successfully")
        
        # Test extractor imports
        from propfirm_scraper.extractors.base_extractor import BaseExtractor
        print("+ Extractor modules imported successfully")
        
        # Test exporter imports
        from propfirm_scraper.exporters.google_sheets import GoogleSheetsExporter
        print("+ Exporter modules imported successfully")
        
        print("SUCCESS: All imports successful!")
        return True
        
    except ImportError as e:
        print(f"ERROR: Import failed: {e}")
        return False

def test_currency_converter():
    """Test currency conversion functionality"""
    try:
        print("\nTesting currency converter...")
        
        from propfirm_scraper.core.currency_converter import converter
        
        # Test USD conversion
        usd_amount = converter.parse_and_convert("$25,000")
        assert usd_amount == 25000.0, f"Expected 25000.0, got {usd_amount}"
        
        # Test EUR conversion
        eur_amount = converter.parse_and_convert("€50,000")
        assert eur_amount == 54000.0, f"Expected 54000.0, got {eur_amount}"  # 50000 * 1.08
        
        # Test GBP conversion
        gbp_amount = converter.parse_and_convert("£10,000")
        assert gbp_amount == 12500.0, f"Expected 12500.0, got {gbp_amount}"  # 10000 * 1.25
        
        print("+ Currency conversion working correctly")
        print(f"  $25,000 -> ${usd_amount:,.2f}")
        print(f"  €50,000 -> ${eur_amount:,.2f}")
        print(f"  £10,000 -> ${gbp_amount:,.2f}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Currency converter test failed: {e}")
        return False

def test_utils():
    """Test utility functions"""
    try:
        print("\nTesting utility functions...")
        
        from propfirm_scraper.core.utils import extract_number, extract_percentage, classify_drawdown_type
        
        # Test number extraction
        assert extract_number("$25,000") == 25000.0
        assert extract_number("10%") == 10.0
        assert extract_percentage("80%") == 80.0
        
        # Test drawdown classification
        from propfirm_scraper.config.enums import DrawdownType
        assert classify_drawdown_type("trailing drawdown") == DrawdownType.TRAILING
        assert classify_drawdown_type("static drawdown") == DrawdownType.STATIC
        
        print("+ Utility functions working correctly")
        return True
        
    except Exception as e:
        print(f"ERROR: Utility functions test failed: {e}")
        return False

def test_google_sheets_config():
    """Test Google Sheets configuration"""
    try:
        print("\nTesting Google Sheets configuration...")
        
        service_account_file = "service_account/tradingruleautomation-62475a2ca73b.json"
        
        if os.path.exists(service_account_file):
            print("+ Service account file found")
            
            # Test if we can create the exporter (without actually connecting)
            from propfirm_scraper.exporters.google_sheets import GoogleSheetsExporter
            
            sheet_id = "1V72k3xmBrppWC7fzMBIBYh2Ghh1HHP_2GTEf8BDaKGk"
            print(f"+ Sheet ID configured: {sheet_id}")
            print("+ Google Sheets configuration looks good")
            
            return True
        else:
            print(f"ERROR: Service account file not found: {service_account_file}")
            return False
            
    except Exception as e:
        print(f"ERROR: Google Sheets configuration test failed: {e}")
        return False

def test_config_loading():
    """Test YAML configuration loading"""
    try:
        print("\nTesting configuration loading...")
        
        import yaml
        
        config_file = "propfirm_scraper/config/sites.yaml"
        
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            sites = config.get('sites', {})
            settings = config.get('settings', {})
            
            print(f"+ Configuration loaded: {len(sites)} sites configured")
            print(f"+ Global settings loaded: {len(settings)} settings")
            
            # Show first few sites
            for i, (site_name, site_config) in enumerate(list(sites.items())[:3]):
                print(f"  - {site_config['name']}: {site_config['url'][:50]}...")
            
            return True
        else:
            print(f"ERROR: Configuration file not found: {config_file}")
            return False
            
    except Exception as e:
        print(f"ERROR: Configuration loading test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("SETUP VERIFICATION TESTS")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_currency_converter,
        test_utils,
        test_google_sheets_config,
        test_config_loading,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("All tests passed! Setup is ready.")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Install Playwright browsers: playwright install")
        print("3. Share Google Sheet with service account email")
        print("4. Start implementing website extractors")
    else:
        print("Some tests failed. Please fix the issues above.")
    
    return passed == total

if __name__ == "__main__":
    main()