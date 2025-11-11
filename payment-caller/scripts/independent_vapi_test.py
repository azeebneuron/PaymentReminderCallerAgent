"""
Independent test script for Vapi.ai outbound calls.
Does NOT require Google Sheets, OpenAI, or Database setup.
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import date
from dotenv import load_dotenv

# --- Setup Project Path ---
# Add the parent directory (ai-payment-caller) to the Python path
# This allows importing modules like 'services', 'config', etc.
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))
# --- End Setup Project Path ---

# --- Import necessary components AFTER setting path ---
from config.settings import Settings # Needs dotenv loaded first
from services.vapi_service import vapi_service
from utils.logger import logger
# --- End Imports ---

async def run_test():
    """Initiates a single outbound test call using Vapi."""

    print("============================================================")
    print(" VAPI.AI INDEPENDENT CALL TEST ")
    print("============================================================")
    print("This script will attempt to make a real phone call.")
    print("Ensure VAPI_API_KEY and VAPI_PHONE_NUMBER_ID are set in your .env file.")
    print("-" * 60)

    # --- Load Environment Variables ---
    # Load variables from .env file in the project root
    dotenv_path = project_root / '.env'
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path)
        logger.info(f"Loaded environment variables from: {dotenv_path}")
    else:
        logger.error(f".env file not found at {dotenv_path}. Cannot proceed.")
        print(f"Error: '.env' file not found at {project_root}. Please create it.")
        return

    # Instantiate settings to access environment variables
    try:
        settings = Settings()
        # Verify essential Vapi settings are present
        if not settings.vapi_api_key or settings.vapi_api_key == 'your_vapi_api_key_here':
            raise ValueError("VAPI_API_KEY is not set or is using the default example value.")
        if not settings.vapi_phone_number_id or settings.vapi_phone_number_id == 'your_phone_number_id_here':
            raise ValueError("VAPI_PHONE_NUMBER_ID is not set or is using the default example value.")
        logger.info("Vapi settings loaded successfully.")
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        print(f"Error loading settings: {e}")
        print("   Please check your '.env' file for required Vapi variables.")
        return
    # --- End Load Environment Variables ---


    # --- Test Data ---
    # !! IMPORTANT: Replace contact_number with a phone number you can answer !!
    test_call_data = {
        "client_name": "Rahul Singh",
        "company_name": "Contigo Solutionss",
        "contact_number": "+918210073691", 
        "invoice_id": "ABC-4567",
        "amount_due": 8000,
        "due_date": date(2025, 10, 20) # Example date
    }
    # --- End Test Data ---

    print("\nAttempting to call:")
    print(f"Number: {test_call_data['contact_number']}")
    print(f"Client: {test_call_data['client_name']}")
    print(f"Company: {test_call_data['company_name']}")
    print(f"Invoice: {test_call_data['invoice_id']} (Amount: ₹{test_call_data['amount_due']:.2f})")
    print("-" * 60)

    # --- User Confirmation ---
    confirm = input("Proceed with making this call? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("\nTest cancelled by user.")
        return

    print("\nInitiating call via Vapi.ai...")
    try:
        # --- Make the Call ---
        # Pass the settings object explicitly if vapi_service needs it internally
        # (Assuming vapi_service uses the global `settings` instance for now)
        call_id = await vapi_service.make_outbound_call(
            client_name=test_call_data['client_name'],
            company_name=test_call_data['company_name'],
            contact_number=test_call_data['contact_number'],
            invoice_id=test_call_data['invoice_id'],
            amount_due=test_call_data['amount_due'],
            due_date=test_call_data['due_date']
        )
        # --- End Make the Call ---

        if call_id:
            logger.info(f"Test call initiated successfully. Vapi Call ID: {call_id}")
            print("\nCall initiated successfully!")
            print(f"Vapi Call ID: {call_id}")
            print("\nPlease answer the call on your phone.")
            print("You should hear the AI agent start speaking.")
            print("\nNote: This test only initiates the call.")
            print("Webhook processing, response parsing, and database logging are bypassed.")
            # Provide info on how to check status if needed
            print(f"\nYou *can* manually check Vapi's API for status if needed:")
            print(f"GET https://api.vapi.ai/call/{call_id} (using your API key)")

        else:
            logger.error("Failed to initiate test call. Vapi service returned None.")
            print("\nFailed to initiate call. Check the logs/console for details.")
            print("   Possible reasons: Invalid API key, incorrect Phone ID, invalid number format, Vapi service issue.")

    except Exception as e:
        logger.exception("An error occurred during the test call:")
        print(f"\nAn unexpected error occurred: {e}")
        print("   Check the application logs (`logs/app.log`) for more details.")

    print("\n============================================================")
    print(" Test Finished ")
    print("============================================================")


if __name__ == "__main__":
    # Ensure requirements are installed
    try:
        import httpx
        import phonenumbers
        import dotenv
    except ImportError as e:
        print(f"Missing dependency: {e.name}")
        print("Please run 'pip install -r requirements.txt' from the project root.")
        sys.exit(1)

    # Run the async test function
    asyncio.run(run_test())