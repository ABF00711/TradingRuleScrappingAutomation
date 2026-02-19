"""
CSV exporter for trading rule data (fallback for Google Sheets)
"""
import csv
import logging
from typing import List
from datetime import datetime
from pathlib import Path

from ..config.schema import TradingRule

logger = logging.getLogger(__name__)

class CSVExporter:
    """Export trading rule data to CSV file"""
    
    def __init__(self, output_dir: str = "propfirm_scraper/data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_headers(self) -> List[str]:
        """Get column headers for the CSV"""
        return [
            'Firm Name',
            'Account Size',
            'Account Size (USD)',
            'Website URL',
            'Broker',
            'Platform',
            'Last Updated',
            'Status',
            'Evaluation Target (USD)',
            'Evaluation Max Drawdown (USD)',
            'Evaluation Daily Loss (USD)',
            'Evaluation Drawdown Type',
            'Evaluation Min Days',
            'Evaluation Consistency',
            'Funded Max Drawdown (USD)',
            'Funded Daily Loss (USD)',
            'Funded Drawdown Type',
            'Profit Split (%)',
            'Payout Frequency',
            'Min Payout (USD)',
            'Evaluation Fee (USD)',
            'Reset Fee (USD)'
        ]
    
    def export_to_csv(self, trading_rules: List[TradingRule], filename: str = None) -> str:
        """
        Export trading rules to CSV file
        
        Args:
            trading_rules: List of TradingRule objects
            filename: Optional custom filename
            
        Returns:
            Path to the created CSV file
        """
        try:
            if not trading_rules:
                logger.warning("No trading rules to export")
                return ""
            
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"trading_rules_{timestamp}.csv"
            
            filepath = self.output_dir / filename
            
            # Get headers
            headers = self._get_headers()
            
            # Write CSV file
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write headers
                writer.writerow(headers)
                
                # Write data rows
                for rule in trading_rules:
                    rule_dict = rule.to_dict()
                    row = [rule_dict.get(header, '') for header in headers]
                    writer.writerow(row)
            
            logger.info(f"Exported {len(trading_rules)} trading rules to {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            raise
    
    def export_summary(self, trading_rules: List[TradingRule]) -> str:
        """Export a summary report"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trading_rules_summary_{timestamp}.txt"
            filepath = self.output_dir / filename
            
            # Count by status
            status_counts = {}
            for rule in trading_rules:
                status = rule.status.value
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count by firm
            firm_counts = {}
            for rule in trading_rules:
                firm = rule.firm_name
                firm_counts[firm] = firm_counts.get(firm, 0) + 1
            
            # Write summary
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("TRADING RULES SCRAPING SUMMARY\n")
                f.write("=" * 50 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total rules extracted: {len(trading_rules)}\n\n")
                
                f.write("STATUS BREAKDOWN:\n")
                f.write("-" * 20 + "\n")
                for status, count in status_counts.items():
                    f.write(f"{status}: {count}\n")
                
                f.write("\nFIRM BREAKDOWN:\n")
                f.write("-" * 20 + "\n")
                for firm, count in firm_counts.items():
                    f.write(f"{firm}: {count}\n")
                
                f.write("\nDETAILED RESULTS:\n")
                f.write("-" * 20 + "\n")
                for rule in trading_rules:
                    f.write(f"\n{rule.firm_name} - {rule.account_size}\n")
                    f.write(f"  Status: {rule.status.value}\n")
                    f.write(f"  URL: {rule.website_url}\n")
                    if rule.evaluation_target_usd:
                        f.write(f"  Evaluation Target: ${rule.evaluation_target_usd:,.2f}\n")
                    if rule.profit_split_percent:
                        f.write(f"  Profit Split: {rule.profit_split_percent}%\n")
            
            logger.info(f"Summary report saved to {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to export summary: {e}")
            raise