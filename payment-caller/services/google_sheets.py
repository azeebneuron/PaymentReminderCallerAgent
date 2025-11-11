"""
Google Sheets integration service for reading and updating payment data.
"""
import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Optional
from datetime import datetime, date
from config.settings import settings
from utils.logger import logger


class GoogleSheetsService:
    """Service for interacting with Google Sheets."""

    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    def __init__(self):
        self.client = None
        self._sheet_cache = {}  # Cache sheets by ID
        self._initialize()

    def _initialize(self):
        """Initialize Google Sheets client."""
        try:
            creds = Credentials.from_service_account_file(
                settings.google_sheets_credentials_file,
                scopes=self.SCOPES
            )
            self.client = gspread.authorize(creds)
            logger.info("Google Sheets client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Google Sheets: {e}")
            raise

    def get_sheet(self, sheet_id: Optional[str] = None):
        """
        Get a Google Sheet by ID.

        Args:
            sheet_id: Google Sheet ID. If None, uses default from settings.

        Returns:
            gspread.Spreadsheet object
        """
        if not sheet_id:
            sheet_id = settings.google_sheet_id

        # Check cache first
        if sheet_id in self._sheet_cache:
            return self._sheet_cache[sheet_id]

        try:
            sheet = self.client.open_by_key(sheet_id)
            self._sheet_cache[sheet_id] = sheet
            logger.info(f"Loaded Google Sheet: {sheet_id}")
            return sheet
        except Exception as e:
            logger.error(f"Error loading Google Sheet {sheet_id}: {e}")
            raise
    
    def get_pending_payments(self, sheet_id: Optional[str] = None) -> List[Dict]:
        """
        Get all pending payments from the sheet.
        Handles Contigo Solutions format with header rows and contact section.

        Args:
            sheet_id: Google Sheet ID. If None, uses default from settings.

        Returns:
            List of dicts with payment information
        """
        try:
            sheet = self.get_sheet(sheet_id)
            worksheet = sheet.sheet1  # First worksheet
            
            # Get all data as raw values (not records)
            all_data = worksheet.get_all_values()
            
            # Find the header row (contains "Date", "Invoice", etc.)
            # =================================================================
            # === ADJUST THIS: Set the row number for your headers           ===
            # =================================================================
            #
            # Replace the dynamic finding logic with a fixed row index.
            # NOTE: This is 0-indexed (Row 1 = 0, Row 5 = 4)
            #
            header_row_idx = 10  # <<<--- ADJUST THIS (e.g., 4 if headers are on row 5)
            #
            # =================================================================

            if header_row_idx is None or header_row_idx >= len(all_data):
                logger.error(f"Could not find header row at index {header_row_idx}")
                return []
            
            # Extract headers
            headers = all_data[header_row_idx]
            
            # =================================================================
            # === ADJUST THIS: Set the column numbers for your data          ===
            # =================================================================
            #
            # Replace the dynamic finding logic with fixed column indices.
            # NOTE: This is 0-indexed (Column A = 0, Column B = 1, etc.)
            #
            # e.g., if "Bill Date" is in Column B, set date_col = 1
            date_col = 4       # <<<--- ADJUST THIS (Column for Invoice Date)
            
            # e.g., if "Bill No." is in Column C, set invoice_col = 2
            invoice_col = 6    # <<<--- ADJUST THIS (Column for Invoice ID/No.)
            
            # e.g., if "Amount Due" is in Column F, set pending_col = 5
            pending_col = 1    # <<<--- ADJUST THIS (Column for Pending Amount)
            
            # e.g., if "Due Date" is in Column G, set due_date_col = 6
            due_date_col = 7   # <<<--- ADJUST THIS (Column for Due Date)
            #
            # =================================================================
            
            if None in [date_col, invoice_col, pending_col]:
                logger.error("Could not find required columns in sheet (check hard-coded values)")
                return []
            
            # Extract client and contact info (from top and bottom of sheet)
            client_name = self._extract_client_name(all_data)
            company_name = self._extract_company_name(all_data)
            contact_number = self._extract_contact_number(all_data)
            
            # Process data rows
            pending = []
            
            data_start_idx = header_row_idx + 1
            
            for idx, row in enumerate(all_data[data_start_idx:], start=data_start_idx):
                # Skip if row is empty
                if not any(row):
                    continue
                
                # Get invoice number
                invoice_id = row[invoice_col] if invoice_col < len(row) else ''
                
                # Skip if no invoice number
                if not invoice_id or invoice_id == '':
                    continue
                
                # Skip summary rows (Outstanding, Total, etc.)
                if any(keyword in str(invoice_id).lower() for keyword in ['outstanding', 'total', 'amount', 'contact']):
                    continue
                
                try:
                    # Parse pending amount
                    pending_amount = self._parse_amount(row[pending_col] if pending_col < len(row) else '0')
                    
                    # Only process if amount is pending
                    if pending_amount <= 0:
                        continue
                    
                    # Parse dates
                    invoice_date_str = row[date_col] if date_col < len(row) else ''
                    invoice_date = self._parse_date(invoice_date_str)
                    
                    due_date_str = row[due_date_col] if due_date_col and due_date_col < len(row) else ''
                    due_date = self._parse_date(due_date_str)
                    
                    payment_data = {
                        'client_name': client_name,
                        'company_name': company_name,
                        'contact_number': contact_number,
                        'invoice_id': str(invoice_id).strip(),
                        'amount_due': pending_amount,
                        'due_date': due_date or invoice_date,
                        'payment_status': 'pending',
                        'row_number': idx + 1  # Google Sheets row number (1-indexed)
                    }
                    
                    # Only add if has essential data
                    if payment_data['contact_number'] and payment_data['invoice_id']:
                        pending.append(payment_data)
                    
                except Exception as e:
                    logger.warning(f"Error parsing row {idx}: {e}")
                    continue
            
            logger.info(f"Found {len(pending)} pending payments")
            return pending
            
        except Exception as e:
            logger.error(f"Error getting pending payments: {e}")
            return []
    
    def _extract_client_name(self, all_data: List[List]) -> str:
        """Extract client name from sheet header."""
        # Look for company name in first 15 rows
        # Usually appears prominently after company header
        for row in all_data[:15]:
            row_text = ' '.join([str(cell) for cell in row if cell])
            
            # Skip if it's the main company header (CONTIGO SOLUTIONS)
            if 'CONTIGO' in row_text.upper() or 'PVT LTD' in row_text.upper():
                continue
            
            # Look for company-like names (contains capital letters, possibly "Coatings", "Industries", etc.)
            if row_text and len(row_text) > 5 and any(c.isupper() for c in row_text):
                # Additional checks to avoid picking up headers
                if not any(keyword in row_text.lower() for keyword in ['bill', 'details', 'pending', 'date', 'invoice']):
                    # Clean up the name
                    clean_name = row_text.strip()
                    if clean_name and len(clean_name) < 100:  # Reasonable name length
                        return clean_name
        
        return "Client"
    
    def _extract_company_name(self, all_data: List[List]) -> str:
        """Extract company name (same as client name for now)."""
        return self._extract_client_name(all_data)
    
    def _extract_contact_number(self, all_data: List[List]) -> str:
        """Extract primary contact number from contact details section."""
        # Look for "Mobile No." or numbers in bottom section
        for idx, row in enumerate(all_data):
            for col_idx, cell in enumerate(row):
                cell_str = str(cell).lower()
                
                # Found "Mobile No." label
                if 'mobile' in cell_str and 'no' in cell_str:
                    # Next cell or next row should have the number
                    # Try same row first
                    if col_idx + 1 < len(row):
                        number = str(row[col_idx + 1]).strip()
                        if self._is_valid_mobile(number):
                            return self._format_mobile(number)
                    
                    # Try next row, same column
                    if idx + 1 < len(all_data) and col_idx < len(all_data[idx + 1]):
                        number = str(all_data[idx + 1][col_idx]).strip()
                        if self._is_valid_mobile(number):
                            return self._format_mobile(number)
        
        # Fallback: scan for any 10-digit number
        for row in all_data:
            for cell in row:
                cell_str = str(cell).strip()
                if self._is_valid_mobile(cell_str):
                    return self._format_mobile(cell_str)
        
        logger.warning("Could not extract contact number from sheet")
        return ""
    
    def _is_valid_mobile(self, number: str) -> bool:
        """Check if string is a valid 10-digit mobile number."""
        cleaned = number.replace(' ', '').replace('-', '').replace('+91', '')
        return cleaned.isdigit() and len(cleaned) == 10
    
    def _format_mobile(self, number: str) -> str:
        """Format mobile number to E.164 format."""
        cleaned = number.replace(' ', '').replace('-', '').replace('+91', '')
        return f"+91{cleaned}"
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """
        Parse date from various formats.
        Handles: 25-Apr-25, 25/04/2025, 2025-04-25, etc.
        """
        if not date_str or date_str == '':
            return None
        
        try:
            # Try DD-MMM-YY format (25-Apr-25)
            return datetime.strptime(str(date_str), '%d-%b-%y').date()
        except:
            pass
        
        try:
            # Try DD-MMM-YYYY format (25-Apr-2025)
            return datetime.strptime(str(date_str), '%d-%b-%Y').date()
        except:
            pass
        
        try:
            # Try DD/MM/YYYY format
            return datetime.strptime(str(date_str), '%d/%m/%Y').date()
        except:
            pass
        
        try:
            # Try YYYY-MM-DD format
            return datetime.strptime(str(date_str), '%Y-%m-%d').date()
        except:
            pass
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def _parse_amount(self, amount: str) -> float:
        """
        Parse amount from various formats.
        Handles: ₹55,696.00, 55696, 55,696, etc.
        """
        if not amount or amount == '':
            return 0.0
        
        try:
            # Remove currency symbols, commas, and spaces
            amount_str = str(amount).replace('₹', '').replace('Rs', '').replace(',', '').replace(' ', '').strip()
            
            # Remove any non-numeric characters except decimal point
            cleaned = ''.join(c for c in amount_str if c.isdigit() or c == '.')
            
            if cleaned:
                return float(cleaned)
            return 0.0
        except:
            logger.warning(f"Could not parse amount: {amount}")
            return 0.0
    
    def update_payment_status(
        self,
        row_number: int,
        call_made_on: datetime,
        response_summary: str,
        next_follow_up_date: Optional[date] = None,
        payment_status: Optional[str] = None,
        sheet_id: Optional[str] = None,
        payment_promise_date: Optional[date] = None,
        customer_sentiment: str = None,
        total_calls_made: int = 1,
        recording_url: str = None
    ):
        """
        Update payment status and call tracking info in the sheet.
        Writes to columns J-Q (new tracking columns).

        Args:
            row_number: Row number to update (1-indexed)
            call_made_on: Timestamp of call
            response_summary: Summary of call
            next_follow_up_date: Next follow-up date if applicable
            payment_status: Updated payment status (will_pay, paid, etc.)
            sheet_id: Google Sheet ID. If None, uses default from settings.
            payment_promise_date: Date customer promised to pay
            customer_sentiment: Sentiment from call (positive, neutral, negative)
            total_calls_made: Number of calls made so far
            recording_url: URL to call recording
        """
        try:
            sheet = self.get_sheet(sheet_id)
            worksheet = sheet.sheet1

            logger.info(f"Updating row {row_number} with call data")

            # Get current row to check existing call count
            current_row = worksheet.row_values(row_number)
            existing_calls = 0
            if len(current_row) >= 15:  # Column O (index 14)
                try:
                    existing_calls = int(current_row[14]) if current_row[14] else 0
                except:
                    existing_calls = 0

            # Increment total calls
            new_total_calls = existing_calls + 1

            # Map payment_status to user-friendly text
            status_map = {
                'paid': 'Payment Made',
                'will_pay': 'Promised Payment',
                'disputed': 'Disputed',
                'no_response': 'No Answer',
                'other': 'Needs Follow-up'
            }
            call_status = status_map.get(payment_status, 'Called')

            # Prepare updates for columns J-Q
            updates = {
                'J': call_made_on.strftime('%Y-%m-%d %H:%M:%S'),  # Last Call Date
                'K': call_status,                                  # Call Status
                'L': payment_promise_date.strftime('%Y-%m-%d') if payment_promise_date else '',  # Promise Date
                'M': next_follow_up_date.strftime('%Y-%m-%d') if next_follow_up_date else '',   # Next Follow-up
                'N': response_summary[:200] if response_summary else '',  # Call Summary (truncated)
                'O': new_total_calls,                              # Total Calls Made
                'P': (customer_sentiment or 'neutral').title(),    # Customer Sentiment
                'Q': recording_url if recording_url else 'See Database'  # Transcript Link
            }

            # Batch update all columns
            logger.info(f"Writing to columns J-Q for row {row_number}")
            for col_letter, value in updates.items():
                cell_address = f"{col_letter}{row_number}"
                worksheet.update(values=[[value]], range_name=cell_address)

            logger.info(f"✓ Successfully updated row {row_number} in Google Sheet")
            logger.info(f"  Call Status: {call_status}")
            logger.info(f"  Next Follow-up: {updates['M']}")
            logger.info(f"  Total Calls: {new_total_calls}")

        except Exception as e:
            logger.error(f"Error updating Google Sheet: {e}", exc_info=True)
    
    def _find_or_add_column(self, worksheet, headers: List, column_name: str, header_row_idx: int) -> Optional[int]:
        """Find column index or add new column if not exists."""
        try:
            # Find existing column
            for idx, header in enumerate(headers):
                if column_name.lower() in str(header).lower():
                    return idx + 1  # 1-indexed for Google Sheets
            
            # Column doesn't exist, add it
            next_col = len(headers) + 1
            cell_address = self._cell_address(header_row_idx + 1, next_col)
            worksheet.update(cell_address, [[column_name]])
            logger.info(f"Added new column: {column_name}")
            
            return next_col
            
        except Exception as e:
            logger.error(f"Error finding/adding column {column_name}: {e}")
            return None
    
    def _cell_address(self, row: int, col: int) -> str:
        """Convert row, col numbers to A1 notation."""
        # Convert column number to letter (1->A, 2->B, 27->AA, etc.)
        col_letter = ''
        while col > 0:
            col -= 1
            col_letter = chr(65 + (col % 26)) + col_letter
            col //= 26
        
        return f"{col_letter}{row}"
    
    def add_call_log_column_if_missing(self):
        """Ensure required columns exist in the sheet."""
        try:
            worksheet = self.sheet.sheet1
            headers = worksheet.row_values(1)
            
            required_columns = [
                'Call Made On',
                'Response Summary',
                'Next Follow-Up Date',
                'Payment Status'
            ]
            
            columns_to_add = [col for col in required_columns if col not in headers]
            
            if columns_to_add:
                # Add missing columns
                current_col_count = len(headers)
                for col in columns_to_add:
                    current_col_count += 1
                    worksheet.update_cell(1, current_col_count, col)
                
                logger.info(f"Added missing columns: {columns_to_add}")
            
        except Exception as e:
            logger.error(f"Error adding columns: {e}")


# Global instance
google_sheets_service = GoogleSheetsService()