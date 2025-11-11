"""
Quick test call script for Rahul's number.
"""
import asyncio
import sys
import os
from datetime import date

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.vapi_service import vapi_service
from database.database import get_db
from database.models import Client, Invoice, CallLog, CallStatus, PaymentStatus
from utils.logger import logger


async def make_test_call():
    """Make a test call to Rahul's number."""

    print("=" * 60)
    print("MAKING TEST CALL TO +918210073691")
    print("=" * 60)

    # Get client from database and store values
    with get_db() as db:
        client = db.query(Client).filter(
            Client.contact_number == "+918210073691"
        ).first()

        if not client:
            print("✗ Client not found in database!")
            return

        # Store values before session closes
        client_name = client.client_name
        company_name = client.company_name
        contact_number = client.contact_number
        sheet_id = client.google_sheet_id
        client_id = client.id

        print(f"\nClient: {client_name}")
        print(f"Contact: {contact_number}")
        print(f"Sheet ID: {sheet_id}")

        # Find or create test invoice
        test_invoice_id = "TEST-2025-001"
        invoice = db.query(Invoice).filter(
            Invoice.invoice_id == test_invoice_id
        ).first()

        if not invoice:
            invoice = Invoice(
                client_id=client_id,
                invoice_id=test_invoice_id,
                amount_due=55696.00,
                due_date=date(2025, 6, 9),
                payment_status=PaymentStatus.PENDING
            )
            db.add(invoice)
            db.flush()
            print(f"\n✓ Created test invoice: {test_invoice_id}")

        invoice_id_db = invoice.id

    # Make the call
    print("\n🔔 Initiating call via Vapi.ai...")
    print("   Please answer your phone!\n")

    try:
        call_id = await vapi_service.make_outbound_call(
            client_name=client_name,
            company_name=company_name or "Contigo Solutions",
            contact_number=contact_number,
            invoice_id=test_invoice_id,
            amount_due=55696.00,
            due_date=date(2025, 6, 9)
        )

        if call_id:
            # Save call log
            with get_db() as db:
                call_log = CallLog(
                    invoice_id=invoice_id_db,
                    vapi_call_id=call_id,
                    call_status=CallStatus.IN_PROGRESS
                )
                db.add(call_log)

            print("✓ CALL INITIATED SUCCESSFULLY!")
            print(f"\nVapi Call ID: {call_id}")
            print("\nWhat will happen:")
            print("  1. You'll receive a call on +918210073691")
            print("  2. An AI agent will speak in Hindi/Hinglish")
            print("  3. It will mention invoice TEST-2025-001 for ₹55,696")
            print("  4. After the call, webhook will receive the transcript")
            print("  5. Gemini AI will analyze the conversation")
            print("  6. Google Sheet will be updated with results")
            print("\nCheck logs/app.log for detailed progress!")

        else:
            print("✗ Failed to initiate call")
            print("  Check logs/app.log for errors")

    except Exception as e:
        logger.error(f"Error making test call: {e}")
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(make_test_call())
