"""
Simple test to verify package installation
"""
import sys

def test_imports():
    """Test importing all required packages"""
    packages_to_test = [
        ('playwright', 'playwright'),
        ('beautifulsoup4', 'bs4'),
        ('pyyaml', 'yaml'),
        ('google-api-python-client', 'googleapiclient'),
        ('google-auth', 'google.auth'),
        ('requests', 'requests'),
        ('urllib3', 'urllib3'),
        ('colorama', 'colorama'),
        ('python-dotenv', 'dotenv'),
        ('jsonschema', 'jsonschema'),
        ('python-dateutil', 'dateutil'),
    ]
    
    print("Testing package imports...")
    
    failed_packages = []
    
    for package_name, import_name in packages_to_test:
        try:
            __import__(import_name)
            print(f"✓ {package_name} - OK")
        except ImportError as e:
            print(f"✗ {package_name} - FAILED: {e}")
            failed_packages.append(package_name)
    
    if failed_packages:
        print(f"\nFailed packages: {', '.join(failed_packages)}")
        print("Please install missing packages with: pip install -r requirements.txt")
        return False
    else:
        print("\n✓ All packages imported successfully!")
        return True

def test_beautifulsoup():
    """Test BeautifulSoup with built-in parser"""
    try:
        from bs4 import BeautifulSoup
        
        # Test with built-in html.parser
        html = "<html><body><p>Test</p></body></html>"
        soup = BeautifulSoup(html, 'html.parser')
        
        if soup.find('p').text == 'Test':
            print("✓ BeautifulSoup with html.parser - OK")
            return True
        else:
            print("✗ BeautifulSoup parsing failed")
            return False
            
    except Exception as e:
        print(f"✗ BeautifulSoup test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("PACKAGE INSTALLATION TEST")
    print("=" * 50)
    
    success = True
    
    # Test imports
    if not test_imports():
        success = False
    
    print()
    
    # Test BeautifulSoup
    if not test_beautifulsoup():
        success = False
    
    print("\n" + "=" * 50)
    
    if success:
        print("SUCCESS: All packages are working correctly!")
        print("\nNext steps:")
        print("1. Run: playwright install")
        print("2. Share Google Sheet with service account")
        print("3. Start implementing extractors")
    else:
        print("FAILED: Some packages are not working correctly.")
        print("Please fix the issues above before proceeding.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)