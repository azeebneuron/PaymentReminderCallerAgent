"""
Call orchestrator service - main logic for managing payment reminder calls.
"""
import asyncio
from typing import List, Dict
from datetime import datetime, time
from database.database import get_db
from database.models import Client, Invoice, CallLog, CallStatus, PaymentStatus
from services.vapi_service import vapi_service
from services.google_sheets import google_sheets_service
from services.response_parser import response_parser
from config.settings import settings
from utils.logger import logger
import pytz


class CallOrchestrator:
    """Orchestrates the entire call workflow."""
    
    def __init__(self):
        self.timezone = pytz.timezone(settings.timezone)
    
    def is_business_hours(self) -> bool:
        """Check if current time is within business hours."""
        now = datetime.now(self.timezone).time()
        return settings.business_start_time <= now <= settings.business_end_time
    
    async def process_pending_payments(self, sheet_id: str = None):
        """
        Main workflow: Process all pending payments and make calls.

        Args:
            sheet_id: Optional Google Sheet ID to process. If None, uses default from settings.
        """
        logger.info("=" * 60)
        logger.info("Starting payment follow-up process")
        logger.info("=" * 60)

        # Check business hours
        if not self.is_business_hours():
            logger.warning("Outside business hours. Skipping calls.")
            return

        try:
            # Get pending payments from Google Sheets
            pending_payments = google_sheets_service.get_pending_payments(sheet_id=sheet_id)

            if not pending_payments:
                logger.info("No pending payments found")
                return

            logger.info(f"Found {len(pending_payments)} pending payments")

            # Sync with database
            await self.sync_to_database(pending_payments, sheet_id=sheet_id)

            # Make calls with rate limiting
            await self.make_calls_with_rate_limit(pending_payments)

            logger.info("Payment follow-up process completed")

        except Exception as e:
            logger.error(f"Error in payment follow-up process: {e}")

    async def process_multiple_sheets(self, sheet_ids: List[str]):
        """
        Process multiple Google Sheets for different clients.

        Args:
            sheet_ids: List of Google Sheet IDs to process
        """
        logger.info(f"Processing {len(sheet_ids)} client sheets")

        for idx, sheet_id in enumerate(sheet_ids, 1):
            logger.info(f"Processing sheet {idx}/{len(sheet_ids)}: {sheet_id}")
            try:
                await self.process_pending_payments(sheet_id=sheet_id)
            except Exception as e:
                logger.error(f"Error processing sheet {sheet_id}: {e}")
                continue
    
    async def sync_to_database(self, payments: List[Dict], sheet_id: str = None):
        """
        Sync payment data to database.

        Args:
            payments: List of payment dicts from Google Sheets
            sheet_id: Google Sheet ID these payments came from
        """
        with get_db() as db:
            for payment in payments:
                # Check if client exists
                client = db.query(Client).filter(
                    Client.contact_number == payment['contact_number']
                ).first()

                if not client:
                    # Create new client
                    client = Client(
                        client_name=payment['client_name'],
                        company_name=payment['company_name'],
                        contact_number=payment['contact_number'],
                        google_sheet_id=sheet_id or settings.google_sheet_id
                    )
                    db.add(client)
                    db.flush()
                else:
                    # Update sheet_id if provided and client exists
                    if sheet_id and client.google_sheet_id != sheet_id:
                        client.google_sheet_id = sheet_id

                # Check if invoice exists
                invoice = db.query(Invoice).filter(
                    Invoice.invoice_id == payment['invoice_id']
                ).first()

                if not invoice:
                    # Create new invoice
                    invoice = Invoice(
                        client_id=client.id,
                        invoice_id=payment['invoice_id'],
                        amount_due=payment['amount_due'],
                        due_date=payment['due_date'],
                        payment_status=PaymentStatus.PENDING
                    )
                    db.add(invoice)
                    db.flush()

                # Store row number and invoice ID for later update
                payment['db_invoice_id'] = invoice.id
                payment['db_client_id'] = client.id
    
    async def make_calls_with_rate_limit(self, payments: List[Dict]):
        """
        Make calls with rate limiting to avoid overwhelming the system.
        
        Args:
            payments: List of payment dicts
        """
        rate_limit = settings.call_rate_limit_per_minute
        delay_between_calls = 60 / rate_limit  # seconds
        
        for i, payment in enumerate(payments):
            logger.info(f"Processing call {i+1}/{len(payments)}")
            
            # Make the call
            await self.make_single_call(payment)
            
            # Rate limiting delay (except for last call)
            if i < len(payments) - 1:
                logger.info(f"Waiting {delay_between_calls:.1f}s before next call...")
                await asyncio.sleep(delay_between_calls)
    
    async def make_single_call(self, payment: Dict):
        """
        Make a single call and handle the outcome.
        
        Args:
            payment: Payment dict with all required information
        """
        try:
            logger.info(f"Calling {payment['client_name']} for invoice {payment['invoice_id']}")
            
            # Make the call via Vapi
            call_id = await vapi_service.make_outbound_call(
                client_name=payment['client_name'],
                company_name=payment['company_name'],
                contact_number=payment['contact_number'],
                invoice_id=payment['invoice_id'],
                amount_due=payment['amount_due'],
                due_date=payment['due_date']
            )
            
            if call_id:
                # Save initial call log
                with get_db() as db:
                    call_log = CallLog(
                        invoice_id=payment['db_invoice_id'],
                        vapi_call_id=call_id,
                        call_status=CallStatus.IN_PROGRESS
                    )
                    db.add(call_log)
                
                logger.info(f"Call initiated successfully. Call ID: {call_id}")
            else:
                logger.error(f"Failed to initiate call for {payment['client_name']}")
                
        except Exception as e:
            logger.error(f"Error making call: {e}")
    
    def process_call_webhook(self, webhook_data: Dict):
        """
        Process webhook data from Vapi after call ends.

        Args:
            webhook_data: Webhook payload from Vapi
        """
        try:
            message = webhook_data.get('message', {})
            message_type = message.get('type')

            logger.info(f"Processing webhook type: {message_type}")

            if message_type == 'status-update':
                self._handle_status_update(message)
            elif message_type == 'end-of-call-report':
                self._handle_end_of_call(message)
            elif message_type == 'transcript':
                logger.debug(f"Transcript update: {message}")
            else:
                logger.warning(f"Unknown webhook message type: {message_type}")

        except Exception as e:
            logger.error(f"Error processing call webhook: {e}")

    def _handle_status_update(self, message: Dict):
        """
        Handle status-update webhook messages.

        Args:
            message: Webhook message data
        """
        try:
            call_data = message.get('call', {})
            call_id = call_data.get('id')
            status = message.get('status')

            if not call_id:
                logger.error("No call ID in status update")
                return

            logger.info(f"Call {call_id} status update: {status}")

            # Update call status in database
            with get_db() as db:
                call_log = db.query(CallLog).filter(
                    CallLog.vapi_call_id == call_id
                ).first()

                if call_log:
                    # Map Vapi status to our CallStatus enum
                    status_mapping = {
                        'queued': CallStatus.IN_PROGRESS,
                        'ringing': CallStatus.IN_PROGRESS,
                        'in-progress': CallStatus.IN_PROGRESS,
                        'forwarding': CallStatus.IN_PROGRESS,
                        'ended': CallStatus.COMPLETED,
                    }

                    mapped_status = status_mapping.get(status, CallStatus.IN_PROGRESS)
                    call_log.call_status = mapped_status
                    logger.info(f"Updated call {call_id} status to {mapped_status}")
                else:
                    logger.warning(f"Call log not found for call ID: {call_id}")

        except Exception as e:
            logger.error(f"Error handling status update: {e}")

    def _handle_end_of_call(self, message: Dict):
        """
        Handle end-of-call-report webhook messages.
        This processes the call transcript, generates summary, and updates records.

        Args:
            message: Webhook message data
        """
        try:
            call_data = message.get('call', {})
            call_id = call_data.get('id')

            if not call_id:
                logger.error("No call ID in end-of-call report")
                return

            logger.info(f"Processing end-of-call report for call {call_id}")

            # Extract call information
            transcript = message.get('transcript', '')
            summary = message.get('summary', '')
            recording_url = call_data.get('recordingUrl')
            started_at = call_data.get('startedAt', 0)
            ended_at = call_data.get('endedAt', 0)
            duration = ended_at - started_at if ended_at and started_at else 0
            cost = call_data.get('cost', 0)

            if not transcript:
                logger.warning(f"No transcript found for call {call_id}")
                transcript = "No transcript available"

            # Parse the outcome using Gemini
            logger.info(f"Parsing call outcome with Gemini for call {call_id}")
            parsed_outcome = response_parser.parse_call_outcome(transcript, summary)

            # Generate human-readable summary
            response_summary = response_parser.generate_summary(parsed_outcome)
            logger.info(f"Generated summary: {response_summary}")

            # Update database
            with get_db() as db:
                call_log = db.query(CallLog).filter(
                    CallLog.vapi_call_id == call_id
                ).first()

                if call_log:
                    # Update call log
                    call_log.call_status = CallStatus.COMPLETED
                    call_log.call_duration = duration
                    call_log.transcript = transcript
                    call_log.summary = response_summary
                    call_log.recording_url = recording_url
                    call_log.cost = cost

                    # Update parsed outcomes
                    call_log.payment_promised = parsed_outcome.get('payment_promised', False)
                    call_log.payment_promise_date = parsed_outcome.get('payment_promise_date')
                    call_log.needs_invoice_resend = parsed_outcome.get('needs_invoice_resend', False)
                    call_log.customer_disputed = parsed_outcome.get('customer_disputed', False)
                    call_log.dispute_reason = parsed_outcome.get('dispute_reason')
                    call_log.next_follow_up_date = parsed_outcome.get('next_follow_up_date')
                    call_log.language_detected = parsed_outcome.get('language_detected')
                    call_log.customer_sentiment = parsed_outcome.get('customer_sentiment')
                    call_log.call_outcome = parsed_outcome.get('call_outcome')

                    # Update invoice status if paid
                    if parsed_outcome.get('payment_status') == 'paid':
                        invoice = call_log.invoice
                        invoice.payment_status = PaymentStatus.PAID
                        logger.info(f"Marked invoice {invoice.invoice_id} as PAID")

                    # Get invoice and client for Google Sheets update
                    invoice = call_log.invoice
                    client = invoice.client

                    # Update Google Sheets with client's sheet_id and all parsed data
                    logger.info(f"Updating Google Sheet for invoice {invoice.invoice_id}")
                    self._update_google_sheet_from_call(
                        invoice_id=invoice.invoice_id,
                        call_made_on=call_log.call_made_on,
                        response_summary=response_summary,
                        next_follow_up_date=call_log.next_follow_up_date,
                        payment_status=parsed_outcome.get('payment_status'),
                        client_sheet_id=client.google_sheet_id,
                        parsed_outcome=parsed_outcome,  # Pass full parsed data
                        recording_url=call_log.recording_url
                    )

                    logger.info(f"Successfully processed end-of-call report for call {call_id}")
                else:
                    logger.warning(f"Call log not found for call ID: {call_id}")

        except Exception as e:
            logger.error(f"Error handling end-of-call report: {e}", exc_info=True)
    
    def _update_google_sheet_from_call(
        self,
        invoice_id: str,
        call_made_on: datetime,
        response_summary: str,
        next_follow_up_date,
        payment_status: str,
        client_sheet_id: str = None,
        parsed_outcome: Dict = None,
        recording_url: str = None
    ):
        """
        Update Google Sheet after call processing.

        Args:
            invoice_id: Invoice ID to find in sheet
            call_made_on: Timestamp of call
            response_summary: Summary of call
            next_follow_up_date: Next follow-up date
            payment_status: Payment status
            client_sheet_id: Client's Google Sheet ID
            parsed_outcome: Full parsed outcome from Gemini
            recording_url: URL to call recording
        """
        try:
            # Use client's sheet_id or default
            sheet = google_sheets_service.get_sheet(client_sheet_id)
            worksheet = sheet.sheet1

            # Get all data as raw values to avoid duplicate header issues
            all_data = worksheet.get_all_values()

            # Find the invoice column index and row
            invoice_col_idx = None
            header_row_idx = None

            # Look for header row containing 'Invoice' keyword
            for idx, row in enumerate(all_data):
                row_text = ' '.join([str(cell).lower() for cell in row])
                if 'invoice' in row_text and ('date' in row_text or 'amount' in row_text):
                    header_row_idx = idx
                    # Find invoice column
                    for col_idx, cell in enumerate(row):
                        if 'invoice' in str(cell).lower() and ('id' in str(cell).lower() or 'no' in str(cell).lower() or 'ref' in str(cell).lower()):
                            invoice_col_idx = col_idx
                            break
                    break

            if header_row_idx is None or invoice_col_idx is None:
                logger.warning(f"Could not find invoice column in sheet. Header row: {header_row_idx}, Invoice col: {invoice_col_idx}")
                return

            # Search for invoice ID in the data rows
            for row_idx in range(header_row_idx + 1, len(all_data)):
                row = all_data[row_idx]

                # Skip summary rows
                if any(keyword in str(row).lower() for keyword in ['outstanding', 'sum', 'total', 'contact']):
                    break

                if invoice_col_idx < len(row):
                    cell_value = str(row[invoice_col_idx]).strip()
                    if cell_value == invoice_id:
                        # Found the invoice row (1-indexed)
                        row_number = row_idx + 1

                        logger.info(f"Found invoice {invoice_id} at row {row_number}")

                        # Extract data from parsed_outcome
                        payment_promise_date = parsed_outcome.get('payment_promise_date') if parsed_outcome else None
                        customer_sentiment = parsed_outcome.get('customer_sentiment') if parsed_outcome else None

                        # Update the sheet with full data
                        google_sheets_service.update_payment_status(
                            row_number=row_number,
                            call_made_on=call_made_on,
                            response_summary=response_summary,
                            next_follow_up_date=next_follow_up_date,
                            payment_status=payment_status,
                            sheet_id=client_sheet_id,
                            payment_promise_date=payment_promise_date,
                            customer_sentiment=customer_sentiment,
                            total_calls_made=1,
                            recording_url=recording_url
                        )
                        return

            logger.warning(f"Invoice {invoice_id} not found in sheet")

        except Exception as e:
            logger.error(f"Error updating Google Sheet: {e}", exc_info=True)


# Global instance
call_orchestrator = CallOrchestrator()