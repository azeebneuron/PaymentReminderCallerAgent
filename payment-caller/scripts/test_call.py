"""
Test script to make a single test call.
Run this to verify Vapi integration is working.
"""
import asyncio
import sys
from pathlib import Path
from datetime import date

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.vapi_service import vapi_service
from utils.logger import logger
from config.settings import settings


async def test_single_call():
    """Test making a single call."""
    
    print("=" * 60)
    print("AI PAYMENT CALLER - TEST CALL")
    print("=" * 60)
    print()
    
    # Test data
    test_data = {
        "client_name": "Bipul Kumar",
        "company_name": "Cartoon Company",
        "contact_number": "+919955994798",  # Replace with your test number
        "invoice_id": "INV-TEST-001",
        "amount_due": 50000.00,
        "due_date": date(2024, 10, 1)
    }
    
    print("Test Call Details:")
    print(f"  Client: {test_data['client_name']}")
    print(f"  Company: {test_data['company_name']}")
    print(f"  Phone: {test_data['contact_number']}")
    print(f"  Invoice: {test_data['invoice_id']}")
    print(f"  Amount: ₹{test_data['amount_due']:,.2f}")
    print(f"  Due Date: {test_data['due_date']}")
    print()
    
    # Confirm
    confirm = input("WARNING: This will make a REAL phone call. Continue? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("Test cancelled.")
        return
    
    print()
    print("📞 Initiating call...")
    print()
    
    try:
        # Make the call
        call_id = await vapi_service.make_outbound_call(
            client_name=test_data['client_name'],
            company_name=test_data['company_name'],
            contact_number=test_data['contact_number'],
            invoice_id=test_data['invoice_id'],
            amount_due=test_data['amount_due'],
            due_date=test_data['due_date']
        )
        
        if call_id:
            print("Call initiated successfully!")
            print(f"Call ID: {call_id}")
            print()
            print("Next Steps:")
            print("1. Answer the call on your phone")
            print("2. Interact with the AI assistant")
            print("3. After the call, check the webhook endpoint for results")
            print(f"4. Webhook URL: {settings.webhook_url}")
            print()
            print("Tip: You can check call status at:")
            print(f"GET {settings.api_base_url}/calls/status/{call_id}")
        else:
            print("Failed to initiate call.")
            print("Check the logs for details.")
    
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Test call failed: {e}")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_single_call())