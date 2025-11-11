"""
Database setup script.
Run this to initialize the database tables.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database import init_database
from services.google_sheets import google_sheets_service
from utils.logger import logger


def main():
    """Setup database and verify connections."""
    
    print("=" * 60)
    print("AI PAYMENT CALLER - DATABASE SETUP")
    print("=" * 60)
    print()
    
    # Step 1: Initialize database
    print("📦 Step 1: Creating database tables...")
    try:
        init_database()
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating database: {e}")
        return
    
    print()
    
    # Step 2: Test Google Sheets connection
    print("Step 2: Testing Google Sheets connection...")
    try:
        google_sheets_service.add_call_log_column_if_missing()
        print("Google Sheets connection successful!")
        
        # Try to read data
        pending = google_sheets_service.get_pending_payments()
        print(f"Found {len(pending)} pending payments in the sheet")
        
    except Exception as e:
        print(f"Warning: Could not connect to Google Sheets: {e}")
        print("   Make sure credentials.json is in the root directory")
    
    print()
    
    # Step 3: Summary
    print("=" * 60)
    print("Setup Complete!")
    print()
    print("Next Steps:")
    print("  1. Configure your .env file with Vapi credentials")
    print("  2. Start the API server: uvicorn api.main:app --reload")
    print("  3. Start the dashboard: streamlit run dashboard/app.py")
    print("  4. Test a call: python scripts/test_call.py")
    print("=" * 60)


if __name__ == "__main__":
    main()