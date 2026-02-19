"""
Google Sheets exporter for trading rule data
"""
import os
import logging
from typing import List, Dict, Any
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..config.schema import TradingRule

logger = logging.getLogger(__name__)

class GoogleSheetsExporter:
    """Export trading rule data to Google Sheets"""
    
    def __init__(self, sheet_id: str, service_account_file: str):
        self.sheet_id = sheet_id
        self.service_account_file = service_account_file
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Sheets API using service account"""
        try:
            # Define the scope
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
            
            # Load credentials from service account file
            credentials = Credentials.from_service_account_file(
                self.service_account_file, 
                scopes=SCOPES
            )
            
            # Build the service
            self.service = build('sheets', 'v4', credentials=credentials)
            logger.info("Successfully authenticated with Google Sheets API")
            
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Sheets API: {e}")
            raise
    
    def _get_headers(self) -> List[str]:
        """Get column headers for the sheet"""
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
    
    def clear_sheet(self, sheet_name: str = "Sheet1"):
        """Clear all data from the sheet"""
        try:
            # Clear all data
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.sheet_id,
                range=f"{sheet_name}!A:Z",
                body={}
            ).execute()
            
            logger.info(f"Cleared sheet: {sheet_name}")
            
        except HttpError as e:
            logger.error(f"Failed to clear sheet: {e}")
            raise
    
    def write_headers(self, sheet_name: str = "Sheet1"):
        """Write column headers to the sheet"""
        try:
            headers = self._get_headers()
            
            # Write headers
            self.service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range=f"{sheet_name}!A1:V1",
                valueInputOption='RAW',
                body={'values': [headers]}
            ).execute()
            
            logger.info("Headers written to sheet")
            
        except HttpError as e:
            logger.error(f"Failed to write headers: {e}")
            raise
    
    def write_data(self, trading_rules: List[TradingRule], sheet_name: str = "Sheet1"):
        """Write trading rule data to the sheet"""
        try:
            if not trading_rules:
                logger.warning("No trading rules to write")
                return
            
            # Convert trading rules to rows
            rows = []
            for rule in trading_rules:
                rule_dict = rule.to_dict()
                row = [rule_dict.get(header, '') for header in self._get_headers()]
                rows.append(row)
            
            # Write data starting from row 2 (after headers)
            range_name = f"{sheet_name}!A2:V{len(rows) + 1}"
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range=range_name,
                valueInputOption='RAW',
                body={'values': rows}
            ).execute()
            
            logger.info(f"Written {len(rows)} rows of data to sheet")
            
        except HttpError as e:
            logger.error(f"Failed to write data: {e}")
            raise
    
    def export_all(self, trading_rules: List[TradingRule], sheet_name: str = "Sheet1"):
        """Complete export process: clear, write headers, write data"""
        try:
            logger.info("Starting Google Sheets export...")
            
            # Clear existing data
            self.clear_sheet(sheet_name)
            
            # Write headers
            self.write_headers(sheet_name)
            
            # Write data
            self.write_data(trading_rules, sheet_name)
            
            logger.info(f"Successfully exported {len(trading_rules)} trading rules to Google Sheets")
            
            # Return the sheet URL
            sheet_url = f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/edit"
            return sheet_url
            
        except Exception as e:
            logger.error(f"Failed to export to Google Sheets: {e}")
            raise
    
    def get_sheet_info(self):
        """Get basic information about the sheet"""
        try:
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=self.sheet_id
            ).execute()
            
            return {
                'title': sheet_metadata.get('properties', {}).get('title', 'Unknown'),
                'sheet_id': self.sheet_id,
                'url': f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/edit"
            }
            
        except HttpError as e:
            logger.error(f"Failed to get sheet info: {e}")
            return None