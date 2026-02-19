# PropFirm Trading Rules Scraper

A comprehensive Playwright-based web scraping system that collects structured trading rule data from prop firm websites and exports to Google Sheets.

## 🎯 Project Overview

This scraper automates the collection of trading rules from 13+ prop firm websites, normalizes the data, converts currencies to USD, and exports everything to a Google Sheet for analysis.

### Key Features

- **Automated Web Scraping**: Uses Playwright for robust browser automation
- **Multi-Site Support**: Configurable extractors for different prop firm websites
- **Data Normalization**: Converts all monetary values to USD with strict enum classification
- **Google Sheets Integration**: Automatically populates and overwrites Google Sheets
- **Error Handling**: Gracefully handles login requirements and missing data
- **Fallback Mechanisms**: Uses search fields and chatbots when needed

## 📁 Project Structure

```
propfirm_scraper/
│
├── main.py                 # Main execution script
│
├── core/                   # Core utilities
│   ├── browser.py          # Playwright browser management
│   ├── logger.py           # Logging configuration
│   ├── utils.py            # Data extraction utilities
│   └── currency_converter.py  # Currency conversion
│
├── extractors/             # Website-specific extractors
│   ├── base_extractor.py   # Abstract base class
│   ├── apex.py            # Apex Trader Funding
│   ├── tradeify.py        # Tradeify
│   └── ...                # Other extractors
│
├── config/                 # Configuration files
│   ├── sites.yaml         # Website configurations
│   ├── enums.py           # Strict enum definitions
│   └── schema.py          # Data schemas
│
├── exporters/              # Data export modules
│   └── google_sheets.py   # Google Sheets exporter
│
├── fallback/               # Fallback mechanisms
│   └── chatbot.py         # Chatbot integration
│
├── data/                   # Data storage
│   └── raw/               # Raw JSON files
│
└── logs/                   # Log files
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
playwright install
```

### 2. Set Up Google Sheets API

1. Create a Google Cloud project
2. Enable Google Sheets API
3. Create a service account and download JSON credentials
4. Place credentials in `service_account/` folder
5. Share your Google Sheet with the service account email

### 3. Configure Target Sheet

Update the sheet ID in `main.py`:
```python
self.sheet_id = "YOUR_GOOGLE_SHEET_ID"
```

### 4. Run the Scraper

```bash
cd propfirm_scraper
python main.py
```

## 📊 Data Structure

Each row in the output represents one firm + account size combination:

### Metadata
- Firm Name
- Account Size (original)
- Account Size (USD)
- Website URL
- Broker
- Platform
- Last Updated
- Status

### Evaluation Phase
- Evaluation Target (USD)
- Evaluation Max Drawdown (USD)
- Evaluation Daily Loss (USD)
- Evaluation Drawdown Type (ENUM)
- Evaluation Min Days
- Evaluation Consistency (BOOLEAN)

### Funded Phase
- Funded Max Drawdown (USD)
- Funded Daily Loss (USD)
- Funded Drawdown Type (ENUM)

### Payout
- Profit Split (%)
- Payout Frequency (ENUM)
- Min Payout (USD)

### Fees
- Evaluation Fee (USD)
- Reset Fee (USD)

## 🔧 Configuration

### Adding New Websites

1. Add site configuration to `config/sites.yaml`
2. Create new extractor class inheriting from `BaseExtractor`
3. Implement required methods for data extraction

### Enum Values

Strict enums are defined in `config/enums.py`:

- **Drawdown Type**: TRAILING, STATIC, EOD, HYBRID
- **Payout Frequency**: WEEKLY, BIWEEKLY, MONTHLY, ON_DEMAND
- **Status**: OK, MISSING_DATA, LOGIN_REQUIRED, FAILED

## 🧪 Testing

Run the setup verification:

```bash
python test_setup.py
```

This will test:
- Module imports
- Currency conversion
- Utility functions
- Google Sheets configuration
- YAML configuration loading

## 📝 Logging

Logs are saved to `propfirm_scraper/logs/` with timestamps. The logger captures:
- Scraping progress
- Errors and warnings
- Data extraction details
- Export status

## 🔄 Current Status

**Phase 1 Complete**: ✅ Project setup and foundation
- Complete folder structure
- Core utilities and browser management
- Google Sheets integration
- Configuration system
- Base extractor framework

**Next Phase**: Website-specific extractors implementation

## 🎯 Target Websites

Currently configured for 13 prop firm websites:
- Apex Trader Funding
- Lucid Trading
- Tradeify
- My Funded Futures
- Funded Next
- Alpha Futures
- Top One Futures
- Blue Guardian Futures
- The Trading Pit
- Legends Trading
- E8 Markets
- Take Profit Trader
- Trade Day

## 🔒 Security Notes

- Service account credentials are stored locally
- No sensitive data is logged
- Browser runs in sandboxed environment
- Respectful scraping with delays between requests

## 📈 Output

The scraper generates:
- **Google Sheet**: Live data with all extracted rules
- **Raw JSON files**: Backup data for debugging
- **Log files**: Detailed execution logs
- **Summary report**: Status and statistics
