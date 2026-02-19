"""
Data schema definitions for trading rule extraction
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from .enums import DrawdownType, PayoutFrequency, Status, Platform, Broker

@dataclass
class TradingRule:
    """Complete trading rule data structure for one firm + account size"""
    
    # Metadata
    firm_name: str
    account_size: str  # e.g., "$25,000", "€50,000"
    account_size_usd: float  # Converted to USD
    website_url: str
    broker: Optional[Broker] = None
    platform: Optional[Platform] = None
    last_updated: datetime = field(default_factory=datetime.now)
    status: Status = Status.OK
    
    # Evaluation Phase
    evaluation_target_usd: Optional[float] = None
    evaluation_max_drawdown_usd: Optional[float] = None
    evaluation_daily_loss_usd: Optional[float] = None
    evaluation_drawdown_type: Optional[DrawdownType] = None
    evaluation_min_days: Optional[int] = None
    evaluation_consistency: Optional[bool] = None
    
    # Funded Phase
    funded_max_drawdown_usd: Optional[float] = None
    funded_daily_loss_usd: Optional[float] = None
    funded_drawdown_type: Optional[DrawdownType] = None
    
    # Payout
    profit_split_percent: Optional[float] = None
    payout_frequency: Optional[PayoutFrequency] = None
    min_payout_usd: Optional[float] = None
    
    # Fees
    evaluation_fee_usd: Optional[float] = None
    reset_fee_usd: Optional[float] = None
    
    # Raw data for debugging
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Google Sheets export"""
        return {
            'Firm Name': self.firm_name,
            'Account Size': self.account_size,
            'Account Size (USD)': self.account_size_usd,
            'Website URL': self.website_url,
            'Broker': self.broker.value if self.broker else None,
            'Platform': self.platform.value if self.platform else None,
            'Last Updated': self.last_updated.strftime('%Y-%m-%d %H:%M:%S'),
            'Status': self.status.value,
            
            # Evaluation Phase
            'Evaluation Target (USD)': self.evaluation_target_usd,
            'Evaluation Max Drawdown (USD)': self.evaluation_max_drawdown_usd,
            'Evaluation Daily Loss (USD)': self.evaluation_daily_loss_usd,
            'Evaluation Drawdown Type': self.evaluation_drawdown_type.value if self.evaluation_drawdown_type else None,
            'Evaluation Min Days': self.evaluation_min_days,
            'Evaluation Consistency': self.evaluation_consistency,
            
            # Funded Phase
            'Funded Max Drawdown (USD)': self.funded_max_drawdown_usd,
            'Funded Daily Loss (USD)': self.funded_daily_loss_usd,
            'Funded Drawdown Type': self.funded_drawdown_type.value if self.funded_drawdown_type else None,
            
            # Payout
            'Profit Split (%)': self.profit_split_percent,
            'Payout Frequency': self.payout_frequency.value if self.payout_frequency else None,
            'Min Payout (USD)': self.min_payout_usd,
            
            # Fees
            'Evaluation Fee (USD)': self.evaluation_fee_usd,
            'Reset Fee (USD)': self.reset_fee_usd,
        }

@dataclass
class SiteConfig:
    """Configuration for each website to scrape"""
    name: str
    url: str
    extractor_class: str
    enabled: bool = True
    timeout: int = 30
    retry_attempts: int = 2
    notes: str = ""