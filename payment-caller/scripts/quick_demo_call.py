"""
Quick demo call script - initiates a single test call from Google Sheet data.
"""
import asyncio
import sys
import os
from datetime import date

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.vapi_service import vapi_service
from services.google_sheets import google_sheets_service
from database.database import get_db
from database.models import Client, Invoice, CallLog, CallStatus, PaymentStatus
from utils.logger import logger


async def make_demo_call():
    """Make a demo call using the first pending payment from the Google Sheet."""

    print("=" * 60)
    print("MAKING DEMO CALL")
    print("=" * 60)

    # Get the client from database
    with get_db() as db:
        client = db.query(Client).filter(
            Client.google_sheet_id != None
        ).first()

        if not client:
            print("✗ No client found in database!")
            print("  Please add a client through the dashboard first.")
            return

        # Store values before session closes
        client_id = client.id
        client_name = client.client_name
        company_name = client.company_name
        contact_number = client.contact_number
        sheet_id = client.google_sheet_id

        print(f"\nClient: {client_name}")
        print(f"Company: {company_name}")
        print(f"Contact: {contact_number}")
        print(f"Sheet ID: {sheet_id[:20]}...")

    # Get pending payments from Google Sheet
    print("\n📊 Fetching pending payments from Google Sheet...")
    try:
        pending_payments = google_sheets_service.get_pending_payments(sheet_id=sheet_id)

        if not pending_payments:
            print("✗ No pending payments found in Google Sheet!")
            return

        # Use the first pending payment
        payment = pending_payments[0]

        print(f"\n✓ Found {len(pending_payments)} pending payment(s)")
        print(f"\nUsing first payment:")
        print(f"  Invoice ID: {payment['invoice_id']}")
        print(f"  Amount Due: ₹{payment['amount_due']:,.2f}")
        print(f"  Due Date: {payment['due_date']}")
        print(f"  Contact: {payment['contact_number']}")

    except Exception as e:
        print(f"✗ Error fetching Google Sheet data: {e}")
        return

    # Create or get invoice in database
    with get_db() as db:
        invoice = db.query(Invoice).filter(
            Invoice.invoice_id == payment['invoice_id']
        ).first()

        if not invoice:
            invoice = Invoice(
                client_id=client_id,
                invoice_id=payment['invoice_id'],
                amount_due=payment['amount_due'],
                due_date=payment['due_date'],
                payment_status=PaymentStatus.PENDING
            )
            db.add(invoice)
            db.flush()
            print(f"\n✓ Created invoice record in database")

        invoice_id_db = invoice.id

    # Make the call
    print("\n🔔 Initiating call via Vapi.ai...")
    print("   (This will call the number from the Google Sheet)")
    print("   Please keep your phone ready!\n")

    try:
        call_id = await vapi_service.make_outbound_call(
            client_name=payment['client_name'],
            company_name=payment.get('company_name', company_name) or company_name,
            contact_number=payment['contact_number'],  # Using number from Google Sheet
            invoice_id=payment['invoice_id'],
            amount_due=payment['amount_due'],
            due_date=payment['due_date']
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
            print(f"  1. The number {payment['contact_number']} will receive a call")
            print("  2. An AI agent will speak in Hindi/Hinglish")
            print(f"  3. It will mention invoice {payment['invoice_id']} for ₹{payment['amount_due']:,.2f}")
            print("  4. After the call, webhook will receive the transcript")
            print("  5. Gemini AI will analyze the conversation")
            print("  6. Google Sheet will be updated with results")
            print("\n💡 Check the dashboard (http://localhost:8501) for call logs!")
            print("   Or check logs/app.log for detailed progress")

        else:
            print("✗ Failed to initiate call")
            print("  Check logs/app.log for errors")

    except Exception as e:
        logger.error(f"Error making demo call: {e}")
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(make_demo_call())
