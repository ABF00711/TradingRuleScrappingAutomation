"""
Utility functions for data extraction and processing
"""
import re
import logging
from typing import Optional, Union, List
from ..config.enums import DrawdownType, PayoutFrequency, Platform, Broker

logger = logging.getLogger(__name__)

def extract_number(text: str) -> Optional[float]:
    """
    Extract numeric value from text
    
    Examples:
    - "10%" -> 10.0
    - "$25,000" -> 25000.0
    - "5.5%" -> 5.5
    - "2-3 days" -> 2.0 (first number)
    """
    if not text:
        return None
    
    # Clean the text
    text = str(text).strip().replace(',', '').replace('$', '').replace('€', '').replace('£', '')
    
    # Look for percentage
    percent_match = re.search(r'([0-9]+\.?[0-9]*)\s*%', text)
    if percent_match:
        try:
            return float(percent_match.group(1))
        except ValueError:
            pass
    
    # Look for any number
    number_match = re.search(r'([0-9]+\.?[0-9]*)', text)
    if number_match:
        try:
            return float(number_match.group(1))
        except ValueError:
            pass
    
    return None

def extract_percentage(text: str) -> Optional[float]:
    """
    Extract percentage value from text
    
    Examples:
    - "80%" -> 80.0
    - "90% profit split" -> 90.0
    - "5.5%" -> 5.5
    """
    if not text:
        return None
    
    percent_match = re.search(r'([0-9]+\.?[0-9]*)\s*%', str(text))
    if percent_match:
        try:
            return float(percent_match.group(1))
        except ValueError:
            pass
    
    return None

def clean_currency(text: str) -> str:
    """
    Clean currency text by removing extra whitespace and normalizing
    
    Examples:
    - "$ 25,000 " -> "$25,000"
    - "€ 50000" -> "€50,000"
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', str(text).strip())
    
    # Add commas to large numbers
    def add_commas(match):
        number = match.group(1)
        if len(number) > 3:
            return f"{int(number):,}"
        return number
    
    text = re.sub(r'([0-9]{4,})', add_commas, text)
    
    return text

def classify_drawdown_type(text: str) -> Optional[DrawdownType]:
    """
    Classify drawdown type based on text description
    
    Examples:
    - "trailing drawdown" -> DrawdownType.TRAILING
    - "static drawdown" -> DrawdownType.STATIC
    - "end of day" -> DrawdownType.EOD
    """
    if not text:
        return None
    
    text = str(text).lower()
    
    # Check for specific keywords
    if any(word in text for word in ['trailing', 'trail']):
        return DrawdownType.TRAILING
    elif any(word in text for word in ['static', 'fixed', 'absolute']):
        return DrawdownType.STATIC
    elif any(word in text for word in ['eod', 'end of day', 'daily close', 'close of day']):
        return DrawdownType.EOD
    elif any(word in text for word in ['hybrid', 'combination', 'mixed']):
        return DrawdownType.HYBRID
    
    return None

def classify_payout_frequency(text: str) -> Optional[PayoutFrequency]:
    """
    Classify payout frequency based on text description
    
    Examples:
    - "weekly payouts" -> PayoutFrequency.WEEKLY
    - "bi-weekly" -> PayoutFrequency.BIWEEKLY
    - "monthly" -> PayoutFrequency.MONTHLY
    - "on demand" -> PayoutFrequency.ON_DEMAND
    """
    if not text:
        return None
    
    text = str(text).lower()
    
    if any(word in text for word in ['weekly', 'week', '7 days']):
        if any(word in text for word in ['bi', 'bi-weekly', 'biweekly', '2 weeks', 'two weeks']):
            return PayoutFrequency.BIWEEKLY
        return PayoutFrequency.WEEKLY
    elif any(word in text for word in ['monthly', 'month', '30 days']):
        return PayoutFrequency.MONTHLY
    elif any(word in text for word in ['on demand', 'on-demand', 'instant', 'immediate', 'anytime']):
        return PayoutFrequency.ON_DEMAND
    elif any(word in text for word in ['biweekly', 'bi-weekly', '2 weeks', 'two weeks', '14 days']):
        return PayoutFrequency.BIWEEKLY
    
    return None

def classify_platform(text: str) -> Optional[Platform]:
    """
    Classify trading platform based on text description
    """
    if not text:
        return None
    
    text = str(text).lower()
    
    if 'mt4' in text or 'metatrader 4' in text:
        return Platform.MT4
    elif 'mt5' in text or 'metatrader 5' in text:
        return Platform.MT5
    elif 'ctrader' in text or 'c-trader' in text:
        return Platform.CTRADER
    elif 'ninjatrader' in text or 'ninja trader' in text:
        return Platform.NINJA_TRADER
    elif 'tradingview' in text or 'trading view' in text:
        return Platform.TRADING_VIEW
    elif any(word in text for word in ['proprietary', 'custom', 'own platform']):
        return Platform.PROPRIETARY
    elif any(word in text for word in ['multiple', 'various', 'several']):
        return Platform.MULTIPLE
    
    return Platform.UNKNOWN

def classify_broker(text: str) -> Optional[Broker]:
    """
    Classify broker based on text description
    """
    if not text:
        return None
    
    text = str(text).lower()
    
    if 'purple trading' in text or 'purple' in text:
        return Broker.PURPLE_TRADING
    elif 'eightcap' in text or '8cap' in text:
        return Broker.EIGHTCAP
    elif 'match trader' in text or 'matchtrader' in text:
        return Broker.MATCH_TRADER
    elif 'topstep' in text:
        return Broker.TOPSTEP
    elif 'rithmic' in text:
        return Broker.RITHMIC
    elif 'cqg' in text:
        return Broker.CQG
    elif any(word in text for word in ['multiple', 'various', 'several']):
        return Broker.MULTIPLE
    
    return Broker.UNKNOWN

def extract_days(text: str) -> Optional[int]:
    """
    Extract number of days from text
    
    Examples:
    - "minimum 5 days" -> 5
    - "2-3 days" -> 2
    - "at least 10 trading days" -> 10
    """
    if not text:
        return None
    
    text = str(text).lower()
    
    # Look for patterns like "5 days", "minimum 5 days", etc.
    day_patterns = [
        r'minimum\s+([0-9]+)\s+days?',
        r'at least\s+([0-9]+)\s+days?',
        r'([0-9]+)\s+days?',
        r'([0-9]+)\s+trading\s+days?',
    ]
    
    for pattern in day_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    
    return None

def parse_boolean(text: str) -> Optional[bool]:
    """
    Parse boolean value from text
    
    Examples:
    - "Yes" -> True
    - "No" -> False
    - "Required" -> True
    - "Not required" -> False
    """
    if not text:
        return None
    
    text = str(text).lower().strip()
    
    true_values = ['yes', 'true', 'required', 'mandatory', 'enabled', 'active', '1']
    false_values = ['no', 'false', 'not required', 'optional', 'disabled', 'inactive', '0']
    
    if any(val in text for val in true_values):
        return True
    elif any(val in text for val in false_values):
        return False
    
    return None

def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', str(text).strip())
    
    # Remove special characters that might interfere
    text = re.sub(r'[^\w\s\-\.\,\%\$\€\£\(\)]', '', text)
    
    return text

def extract_account_sizes(text: str) -> List[str]:
    """
    Extract account sizes from text
    
    Examples:
    - "$25,000, $50,000, $100,000" -> ["$25,000", "$50,000", "$100,000"]
    - "25K, 50K, 100K" -> ["$25,000", "$50,000", "$100,000"]
    """
    if not text:
        return []
    
    sizes = []
    
    # Look for currency amounts
    currency_patterns = [
        r'\$([0-9,]+)',  # $25,000
        r'€([0-9,]+)',   # €25,000
        r'£([0-9,]+)',   # £25,000
        r'([0-9,]+)K',   # 25K
    ]
    
    for pattern in currency_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if 'K' in match:
                # Convert K to thousands
                number = re.sub(r'[^\d]', '', match)
                if number:
                    sizes.append(f"${int(number) * 1000:,}")
            else:
                sizes.append(f"${match}")
    
    return list(set(sizes))  # Remove duplicates