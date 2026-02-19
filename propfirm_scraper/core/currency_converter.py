"""
Currency conversion utilities with hardcoded exchange rates
"""
import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Hardcoded exchange rates (as of February 2026)
# These are approximate rates for one-time conversion
EXCHANGE_RATES = {
    'EUR': 1.08,   # 1 EUR = 1.08 USD
    'GBP': 1.25,   # 1 GBP = 1.25 USD
    'CAD': 0.74,   # 1 CAD = 0.74 USD
    'AUD': 0.63,   # 1 AUD = 0.63 USD
    'CHF': 1.12,   # 1 CHF = 1.12 USD
    'JPY': 0.0067, # 1 JPY = 0.0067 USD
    'USD': 1.0     # 1 USD = 1.0 USD (base)
}

class CurrencyConverter:
    """Convert various currencies to USD using hardcoded rates"""
    
    def __init__(self):
        self.rates = EXCHANGE_RATES
    
    def extract_currency_amount(self, text: str) -> Tuple[Optional[float], Optional[str]]:
        """
        Extract currency amount and currency code from text
        
        Examples:
        - "$25,000" -> (25000.0, "USD")
        - "€50,000" -> (50000.0, "EUR")
        - "£10,000" -> (10000.0, "GBP")
        - "25000 USD" -> (25000.0, "USD")
        """
        if not text:
            return None, None
        
        # Clean the text
        text = str(text).strip().replace(',', '').replace(' ', '')
        
        # Currency symbol patterns
        currency_patterns = [
            (r'\$([0-9]+\.?[0-9]*)', 'USD'),  # $25000 or $25000.50
            (r'€([0-9]+\.?[0-9]*)', 'EUR'),   # €25000
            (r'£([0-9]+\.?[0-9]*)', 'GBP'),   # £25000
            (r'([0-9]+\.?[0-9]*)USD', 'USD'), # 25000USD
            (r'([0-9]+\.?[0-9]*)EUR', 'EUR'), # 25000EUR
            (r'([0-9]+\.?[0-9]*)GBP', 'GBP'), # 25000GBP
            (r'([0-9]+\.?[0-9]*)CAD', 'CAD'), # 25000CAD
            (r'([0-9]+\.?[0-9]*)AUD', 'AUD'), # 25000AUD
            (r'([0-9]+\.?[0-9]*)CHF', 'CHF'), # 25000CHF
        ]
        
        for pattern, currency in currency_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount = float(match.group(1))
                    return amount, currency
                except ValueError:
                    continue
        
        # Try to extract just a number (assume USD)
        number_match = re.search(r'([0-9]+\.?[0-9]*)', text)
        if number_match:
            try:
                amount = float(number_match.group(1))
                return amount, 'USD'
            except ValueError:
                pass
        
        return None, None
    
    def convert_to_usd(self, amount: float, from_currency: str) -> Optional[float]:
        """Convert amount from given currency to USD"""
        if not amount or not from_currency:
            return None
        
        from_currency = from_currency.upper()
        
        if from_currency not in self.rates:
            logger.warning(f"Unknown currency: {from_currency}, assuming USD")
            return amount
        
        usd_amount = amount * self.rates[from_currency]
        logger.debug(f"Converted {amount} {from_currency} to {usd_amount:.2f} USD")
        
        return round(usd_amount, 2)
    
    def parse_and_convert(self, text: str) -> Optional[float]:
        """
        Parse text for currency amount and convert to USD
        
        Args:
            text: Text containing currency amount (e.g., "$25,000", "€50,000")
            
        Returns:
            Amount in USD or None if parsing failed
        """
        amount, currency = self.extract_currency_amount(text)
        
        if amount is None or currency is None:
            return None
        
        return self.convert_to_usd(amount, currency)
    
    def format_usd(self, amount: Optional[float]) -> str:
        """Format USD amount for display"""
        if amount is None:
            return ""
        
        return f"${amount:,.2f}"

# Global instance
converter = CurrencyConverter()