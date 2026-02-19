# Normalized PropFirm Trading Rules Scraper

## 🚀 **Universal Scraper for ANY Prop Firm Website**

This is a **normalized, generic scraper** that can extract trading rules from **any prop firm website** without requiring custom code for each site.

### ✅ **Key Features**
- **User-Configurable**: Add any website to `Websites.txt`
- **No Coding Required**: Works with any prop firm automatically
- **Multi-Method Extraction**: HTTP → Browser → Chatbot → Manual fallback
- **Pattern Recognition**: Universal extraction using smart patterns
- **Auto-Export**: Google Sheets + CSV backup

---

## 🎯 **How It Works**

### **1. Add Websites** 
Simply add any prop firm URL to `Websites.txt`:
```
https://support.apextraderfunding.com/hc/en-us
https://help.tradeify.co/en
https://help.myfundedfutures.com/en/
... add any prop firm website
```

### **2. Run Scraper**
```bash
py -3.12 main.py
```

### **3. Automatic Processing**
The system automatically:
1. **HTTP Request** (fastest) - tries simple web request first
2. **Browser Automation** - if HTTP fails or needs JavaScript  
3. **Chatbot Integration** - if data not found on pages
4. **Manual Fallback** - creates placeholder for manual review

### **4. Smart Pattern Recognition**
Automatically detects:
- Account sizes ($50,000, $100,000, etc.)
- Profit targets (8% of account, $4,000, etc.)
- Max drawdown (5% trailing, $2,500, etc.)
- Profit splits (80%, 90%, etc.)
- Fees (evaluation, monthly, etc.)

---

## 📊 **Output & Results**

### **Google Sheets Export**
- Automatically exports to your Google Sheet
- Structured data with all trading rules
- Status tracking for each extraction
- Timestamp for each update

### **CSV Backup** 
- Local CSV files in `propfirm_scraper/data/`
- Summary reports with statistics
- Fallback if Google Sheets unavailable

---

## 🛠️ **Setup**

### **1. Install Dependencies**
```bash
py -3.12 -m pip install -r requirements.txt
py -3.12 -m playwright install
```

### **2. Configure Google Sheets (Optional)**
- Place service account JSON in `service_account/` folder
- Update sheet ID in `main.py` if needed
- System falls back to CSV if Google Sheets unavailable

### **3. Add Websites**
Edit `Websites.txt` and add any prop firm URLs:
```
https://your-propfirm.com
https://another-firm.com/help
```

### **4. Run**
```bash
py -3.12 main.py
```

---

## 📋 **Project Structure**

```
TradingRuleScrappingAutomation/
├── main.py                          # Main entry point
├── Websites.txt                     # User-configurable website list
├── requirements.txt                 # Minimal dependencies
├── propfirm_scraper/
│   ├── core/
│   │   ├── generic_extractor.py     # Universal pattern-based extractor
│   │   ├── website_loader.py        # HTTP → Browser → Chatbot loader
│   │   ├── currency_converter.py    # Currency normalization
│   │   ├── utils.py                 # Data processing utilities
│   │   └── logger.py                # Logging system
│   ├── config/
│   │   ├── schema.py                # Data structures
│   │   └── enums.py                 # Status and type enums
│   ├── exporters/
│   │   ├── google_sheets.py         # Google Sheets export
│   │   └── csv_exporter.py          # CSV export fallback
│   └── data/                        # Output files
└── service_account/                 # Google Sheets credentials
```

---

## 🎯 **Success Metrics**

### **Scalability**: ✅ 
- Add unlimited websites without coding
- User-friendly configuration
- No developer intervention needed

### **Reliability**: ✅
- Multi-method fallback chain
- Graceful error handling  
- Always produces output (even if placeholder)

### **Accuracy**: ✅
- Smart pattern recognition
- Currency normalization
- Data validation and cleaning

### **Automation**: ✅
- Fully automated extraction
- Auto-export to Google Sheets
- Comprehensive logging and reporting

---

## 🚀 **Usage Examples**

### **Add New Prop Firm**
1. Find their website URL
2. Add to `Websites.txt`
3. Run `py -3.12 main.py`
4. Check results in Google Sheets

### **Batch Processing**
```bash
# Add multiple firms to Websites.txt
echo "https://newfirm1.com" >> Websites.txt
echo "https://newfirm2.com" >> Websites.txt
echo "https://newfirm3.com" >> Websites.txt

# Run scraper
py -3.12 main.py
```

### **Monitor Results**
- Check Google Sheets for live data
- Review CSV files in `propfirm_scraper/data/`
- Check logs for detailed extraction info

---

## 🎉 **Benefits**

✅ **No More Custom Extractors** - works with any website  
✅ **User-Configurable** - non-technical users can add sites  
✅ **Intelligent Fallbacks** - always finds data if available  
✅ **Fully Automated** - no manual intervention needed  
✅ **Production Ready** - handles errors gracefully  
✅ **Scalable Architecture** - add unlimited websites  

---

This system transforms the scraper from a **rigid, site-specific tool** into a **flexible, universal solution** that works with any prop firm website!