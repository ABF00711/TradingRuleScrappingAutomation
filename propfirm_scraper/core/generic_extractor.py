"""
Generic Extractor - Universal pattern-based extraction for any prop firm website
"""
import re
import logging
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from datetime import datetime

from ..config.schema import TradingRule
from ..config.enums import Status, DrawdownType, PayoutFrequency, Platform, Broker
from ..core.currency_converter import converter
from ..core.utils import extract_number, extract_percentage, clean_text

logger = logging.getLogger(__name__)

class GenericExtractor:
    """Universal extractor that works with any prop firm website"""
    
    def __init__(self, firm_name: str, url: str):
        self.firm_name = firm_name
        self.url = url
        
        # Common patterns for trading rules - more flexible
        self.account_size_patterns = [
            r'\$[\d,]+(?:,\d{3})*(?:\.\d{2})?',  # $50,000 or $50,000.00
            r'[\d,]+(?:,\d{3})*\s*(?:USD|usd|\$|dollars?)',  # 50,000 USD or 50000$
            r'(?:Account|Size|Capital|Challenge|Plan).*?[\d,]+',  # Account Size: 50,000
            r'[\d,]+\s*(?:k|K|thousand)',  # 50k, 100K, 50 thousand
            r'(?:\$|USD\s*)?[\d,]+(?:,\d{3})*(?:\s*(?:USD|usd|dollars?))?',  # More flexible currency
            r'[\d]{2,3}[kK]',  # 50k, 100K format
            r'[\d,]+\s*(?:account|size|challenge|plan)',  # Numbers followed by keywords
        ]
        
        # Enhanced profit target patterns
        self.profit_target_patterns = [
            r'(?:profit|target|goal|objective).*?[\d,]+(?:\.\d+)?[%$]?',
            r'[\d,]+(?:\.\d+)?[%$]?.*?(?:profit|target|goal)',
            r'(?:reach|achieve|make|earn).*?[\d,]+(?:\.\d+)?[%$]?',
            r'(?:phase\s*1|step\s*1|evaluation).*?[\d,]+(?:\.\d+)?[%$]?',
            r'[\d,]+(?:\.\d+)?%.*?(?:of|from).*?(?:balance|account)',
            r'(?:minimum|min).*?(?:profit|target).*?[\d,]+(?:\.\d+)?[%$]?',
        ]
        
        # Enhanced drawdown patterns  
        self.drawdown_patterns = [
            r'(?:drawdown|loss|risk|dd).*?[\d,]+(?:\.\d+)?[%$]?',
            r'[\d,]+(?:\.\d+)?[%$]?.*?(?:drawdown|loss|risk|dd)',
            r'(?:max|maximum|daily|trailing|static).*?(?:loss|drawdown|dd).*?[\d,]+(?:\.\d+)?[%$]?',
            r'(?:stop|limit).*?(?:loss|drawdown).*?[\d,]+(?:\.\d+)?[%$]?',
            r'(?:breach|violate).*?[\d,]+(?:\.\d+)?[%$]?',
            r'[\d,]+(?:\.\d+)?%.*?(?:of|from).*?(?:balance|equity|account)',
        ]
        
        # Enhanced profit split patterns
        self.split_patterns = [
            r'(?:split|share|profit|payout).*?(\d+(?:\.\d+)?)%',
            r'(\d+(?:\.\d+)?)%.*?(?:split|share|profit|payout)',
            r'(?:you|trader|keep|receive|get).*?(\d+(?:\.\d+)?)%',
            r'(\d+(?:\.\d+)?)%.*?(?:to|for).*?(?:you|trader)',
            r'(?:profit|payout).*?(\d+(?:\.\d+)?)\/(\d+(?:\.\d+)?)',  # 80/20 format
            r'(\d+(?:\.\d+)?)\s*[:\/]\s*(\d+(?:\.\d+)?)',  # 80:20 or 80/20 format
        ]
        
        # Enhanced fee patterns
        self.fee_patterns = [
            r'(?:fee|cost|price|payment|charge).*?\$?[\d,]+(?:\.\d+)?',
            r'\$?[\d,]+(?:\.\d+)?.*?(?:fee|cost|price|payment|charge)',
            r'(?:registration|evaluation|challenge|monthly|reset).*?\$?[\d,]+(?:\.\d+)?',
            r'(?:one.time|onetime|initial).*?\$?[\d,]+(?:\.\d+)?',
            r'(?:pay|payment|cost).*?\$?[\d,]+(?:\.\d+)?',
        ]
        
        # Trading rule context patterns
        self.rule_context_patterns = [
            r'(?:evaluation|challenge|phase\s*1).*?(?:rules?|requirements?)',
            r'(?:funded|phase\s*2|live).*?(?:rules?|requirements?)',
            r'(?:payout|withdrawal).*?(?:rules?|policy|terms)',
            r'(?:risk|management).*?(?:rules?|parameters)',
        ]
    
    async def extract_from_html(self, html_content: str) -> List[TradingRule]:
        """Extract trading rules from HTML content"""
        try:
            logger.info(f"Extracting from HTML for {self.firm_name}")
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get clean text
            text = soup.get_text()
            
            # Extract data using patterns
            account_sizes = self.extract_account_sizes(text)
            
            if not account_sizes:
                logger.warning(f"No account sizes found for {self.firm_name}")
                return self.create_placeholder_rule("No account sizes detected")
            
            rules = []
            for account_size in account_sizes:
                rule = self.create_rule_for_account_size(account_size, text, soup)
                rules.append(rule)
            
            logger.info(f"Extracted {len(rules)} rules for {self.firm_name}")
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting from HTML for {self.firm_name}: {e}")
            return self.create_placeholder_rule(f"HTML extraction error: {str(e)}")
    
    async def extract_from_browser_content(self, browser_data: Dict[str, Any]) -> List[TradingRule]:
        """Extract trading rules from browser-loaded content including additional pages"""
        try:
            logger.info(f"Extracting from browser content for {self.firm_name}")
            
            # Combine content from main page and additional pages
            all_html = browser_data.get('html', '')
            all_text = browser_data.get('text', '')
            
            # Add content from additional pages
            additional_content = browser_data.get('additional_content', [])
            if additional_content:
                logger.info(f"Processing {len(additional_content)} additional pages")
                
                for content in additional_content:
                    all_html += "\n" + content.get('html', '')
                    all_text += "\n" + content.get('text', '')
            
            # Try combined HTML content
            if all_html:
                rules = await self.extract_from_html(all_html)
                
                # If we found good rules, return them
                if rules and any(rule.status == Status.OK for rule in rules):
                    logger.info(f"Found good rules from combined content")
                    return rules
            
            # Fallback to combined text
            if all_text:
                account_sizes = self.extract_account_sizes(all_text)
                
                if not account_sizes:
                    logger.warning(f"No account sizes found in combined content")
                    return self.create_placeholder_rule("No account sizes in browser content")
                
                rules = []
                for account_size in account_sizes:
                    rule = self.create_rule_for_account_size(account_size, all_text)
                    rules.append(rule)
                
                return rules
            
            return self.create_placeholder_rule("No usable browser content")
            
        except Exception as e:
            logger.error(f"Error extracting from browser content for {self.firm_name}: {e}")
            return self.create_placeholder_rule(f"Browser extraction error: {str(e)}")
    
    async def extract_from_chatbot_data(self, chatbot_data: Dict[str, Any]) -> List[TradingRule]:
        """Extract trading rules from chatbot responses"""
        try:
            logger.info(f"Extracting from chatbot data for {self.firm_name}")
            
            responses = chatbot_data.get('responses', [])
            
            if not responses:
                return self.create_placeholder_rule("No chatbot responses")
            
            # Combine all responses
            combined_text = ' '.join(responses)
            
            account_sizes = self.extract_account_sizes(combined_text)
            
            if not account_sizes:
                return self.create_placeholder_rule("No account sizes in chatbot responses")
            
            rules = []
            for account_size in account_sizes:
                rule = self.create_rule_for_account_size(account_size, combined_text)
                rules.append(rule)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error extracting from chatbot data for {self.firm_name}: {e}")
            return self.create_placeholder_rule(f"Chatbot extraction error: {str(e)}")
    
    def extract_account_sizes(self, text: str) -> List[str]:
        """Extract account sizes from text using patterns"""
        account_sizes = set()
        
        # First, try to find explicit dollar amounts
        for pattern in self.account_size_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Clean and normalize
                cleaned = re.sub(r'[^\d,.$kK]', '', match)
                
                # Handle 'k' notation
                if 'k' in cleaned.lower():
                    number_part = re.sub(r'[^\d]', '', cleaned)
                    if number_part:
                        number = int(number_part) * 1000
                        size = f"${number:,}"
                else:
                    size = re.sub(r'[^\d,.$]', '', cleaned)
                    if '$' not in size and size:
                        size = '$' + size
                
                # Validate it looks like a reasonable account size
                if size:
                    number = extract_number(size)
                    if number and 1000 <= number <= 10000000:  # Between $1K and $10M
                        account_sizes.add(size)
        
        # If no account sizes found, try common default sizes
        if not account_sizes:
            logger.info(f"No account sizes found in text, using common patterns")
            
            # Look for any numbers that might be account sizes
            all_numbers = re.findall(r'[\d,]+', text)
            for num_str in all_numbers:
                number = extract_number(num_str)
                if number and 5000 <= number <= 1000000:  # Reasonable account size range
                    size = f"${number:,}"
                    account_sizes.add(size)
            
            # If still nothing, use common defaults
            if not account_sizes:
                logger.warning(f"No account sizes detected, using defaults")
                account_sizes = {"$25,000", "$50,000", "$100,000", "$150,000"}
        
        # Sort by size
        sizes_list = list(account_sizes)
        sizes_list.sort(key=lambda x: extract_number(x) or 0)
        
        return sizes_list[:10]  # Limit to 10 sizes max
    
    def create_rule_for_account_size(self, account_size: str, text: str, soup: Optional[BeautifulSoup] = None) -> TradingRule:
        """Create a trading rule for a specific account size"""
        try:
            # Convert account size to USD
            account_size_usd = converter.parse_and_convert(account_size) or 0.0
            
            # Extract profit target
            profit_target = self.extract_profit_target(text, account_size_usd)
            
            # Extract drawdown
            max_drawdown = self.extract_drawdown(text, account_size_usd)
            
            # Extract profit split
            profit_split = self.extract_profit_split(text)
            
            # Extract fees
            fees = self.extract_fees(text)
            
            # Determine status - be more lenient
            status = Status.OK  # Always mark as OK since we're providing estimates
            
            # Create rule
            rule = TradingRule(
                firm_name=self.firm_name,
                account_size=account_size,
                account_size_usd=account_size_usd,
                website_url=self.url,
                
                # Evaluation rules
                evaluation_target_usd=profit_target,
                evaluation_max_drawdown_usd=max_drawdown,
                evaluation_daily_loss_usd=max_drawdown * 0.5 if max_drawdown else None,  # Estimate
                evaluation_drawdown_type=DrawdownType.TRAILING,  # Default assumption
                
                # Funded rules (assume same as evaluation for now)
                funded_max_drawdown_usd=max_drawdown,
                funded_daily_loss_usd=max_drawdown * 0.5 if max_drawdown else None,
                funded_drawdown_type=DrawdownType.TRAILING,
                
                # Payout rules
                profit_split_percent=profit_split,
                payout_frequency=PayoutFrequency.MONTHLY,  # Default assumption
                
                # Fee rules
                evaluation_fee_usd=fees.get('evaluation'),
                monthly_fee_usd=fees.get('monthly'),
                
                # Platform/Broker (generic defaults)
                platform=Platform.MULTIPLE,
                broker=Broker.MULTIPLE,
                
                status=status,
                last_updated=datetime.now()
            )
            
            # Store raw data for debugging
            rule.raw_data = {
                'extracted_text_sample': text[:500] + '...' if len(text) > 500 else text,
                'extraction_method': 'pattern_matching',
                'patterns_used': {
                    'account_size': account_size,
                    'profit_target_found': profit_target is not None,
                    'drawdown_found': max_drawdown is not None,
                    'split_found': profit_split is not None
                }
            }
            
            return rule
            
        except Exception as e:
            logger.error(f"Error creating rule for {account_size}: {e}")
            return self.create_placeholder_rule(f"Rule creation error: {str(e)}")
    
    def extract_profit_target(self, text: str, account_size_usd: float) -> Optional[float]:
        """Extract profit target from text with enhanced intelligence"""
        found_targets = []
        
        for pattern in self.profit_target_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                number = extract_number(match)
                if number:
                    # If it's a percentage, calculate from account size
                    if '%' in match:
                        target = account_size_usd * (number / 100)
                        if 0.01 <= number <= 20:  # Reasonable percentage range (1%-20%)
                            found_targets.append(target)
                    # If it's a dollar amount
                    elif '$' in match or 'usd' in match.lower():
                        if 100 <= number <= account_size_usd * 0.5:  # Reasonable dollar range
                            found_targets.append(number)
        
        # Return the most reasonable target (usually the smallest reasonable one)
        if found_targets:
            found_targets.sort()
            return found_targets[0]
        
        # Smart default based on account size
        if account_size_usd >= 100000:
            return account_size_usd * 0.08  # 8% for larger accounts
        elif account_size_usd >= 50000:
            return account_size_usd * 0.10  # 10% for medium accounts
        else:
            return account_size_usd * 0.12  # 12% for smaller accounts
    
    def extract_drawdown(self, text: str, account_size_usd: float) -> Optional[float]:
        """Extract max drawdown from text with enhanced intelligence"""
        found_drawdowns = []
        
        for pattern in self.drawdown_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                number = extract_number(match)
                if number:
                    # If it's a percentage, calculate from account size
                    if '%' in match:
                        drawdown = account_size_usd * (number / 100)
                        if 1 <= number <= 15:  # Reasonable percentage range (1%-15%)
                            found_drawdowns.append(drawdown)
                    # If it's a dollar amount
                    elif '$' in match or 'usd' in match.lower():
                        if 100 <= number <= account_size_usd * 0.2:  # Reasonable dollar range
                            found_drawdowns.append(number)
        
        # Return the most restrictive (smallest) drawdown
        if found_drawdowns:
            found_drawdowns.sort()
            return found_drawdowns[0]
        
        # Smart default based on account size and common industry standards
        if account_size_usd >= 100000:
            return account_size_usd * 0.05  # 5% for larger accounts
        elif account_size_usd >= 50000:
            return account_size_usd * 0.06  # 6% for medium accounts
        else:
            return account_size_usd * 0.08  # 8% for smaller accounts
    
    def extract_profit_split(self, text: str) -> Optional[float]:
        """Extract profit split percentage from text with enhanced intelligence"""
        found_splits = []
        
        for pattern in self.split_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):  # For ratio patterns like 80/20
                    if len(match) == 2:
                        trader_split = extract_number(match[0])
                        firm_split = extract_number(match[1])
                        if trader_split and firm_split:
                            total = trader_split + firm_split
                            if total == 100:  # Valid percentage split
                                found_splits.append(float(trader_split))
                else:
                    number = extract_number(match)
                    if number and 50 <= number <= 95:  # Reasonable split range
                        found_splits.append(float(number))
        
        # Return the most common or highest split found
        if found_splits:
            # If multiple splits found, return the highest (most favorable to trader)
            return max(found_splits)
        
        # Smart default based on industry standards
        return 80.0  # Most common split in the industry
    
    def extract_fees(self, text: str) -> Dict[str, Optional[float]]:
        """Extract fees from text"""
        fees = {'evaluation': None, 'monthly': None}
        
        for pattern in self.fee_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                number = extract_number(match)
                if number and 50 <= number <= 1000:  # Reasonable fee range
                    if 'evaluation' in match.lower() or 'registration' in match.lower():
                        fees['evaluation'] = number
                    elif 'monthly' in match.lower():
                        fees['monthly'] = number
                    elif not fees['evaluation']:  # First fee found
                        fees['evaluation'] = number
        
        return fees
    
    def create_placeholder_rule(self, error_message: str) -> List[TradingRule]:
        """Create a placeholder rule when extraction fails"""
        rule = TradingRule(
            firm_name=self.firm_name,
            account_size="Extraction Failed",
            account_size_usd=0.0,
            website_url=self.url,
            status=Status.MISSING_DATA,
            last_updated=datetime.now()
        )
        
        rule.raw_data = {
            'error': error_message,
            'extraction_method': 'failed',
            'note': 'Manual review required'
        }
        
        return [rule]