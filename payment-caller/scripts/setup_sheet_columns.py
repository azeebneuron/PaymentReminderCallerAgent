"""
One-time script to add new tracking columns to Google Sheet.
This adds columns for call tracking and prevents duplicate calls.
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.google_sheets import google_sheets_service
from utils.logger import logger


def setup_call_tracking_columns(sheet_id=None):
    """Add call tracking columns to the sheet."""

    print("=" * 80)
    print("SETTING UP CALL TRACKING COLUMNS")
    print("=" * 80)

    try:
        # Get the sheet
        sheet = google_sheets_service.get_sheet(sheet_id)
        worksheet = sheet.sheet1

        print(f"\n✓ Connected to sheet: {sheet.title}")
        print(f"  Worksheet: {worksheet.title}")

        # Get current data to find header row
        all_data = worksheet.get_all_values()

        # Find header row (Row 11 in your structure)
        header_row_idx = None
        for idx, row in enumerate(all_data):
            row_text = ' '.join([str(cell).lower() for cell in row if cell])
            if 'date' in row_text and 'invoice' in row_text and 'pending' in row_text:
                header_row_idx = idx + 1  # 1-indexed
                print(f"\n✓ Found header row at: Row {header_row_idx}")
                break

        if not header_row_idx:
            print("\n✗ Could not find header row!")
            return False

        # Define new columns to add
        new_columns = [
            'Last Call Date',
            'Call Status',
            'Payment Promise Date',
            'Next Follow-up Date',
            'Call Summary',
            'Total Calls Made',
            'Customer Sentiment',
            'Transcript Link'
        ]

        print(f"\n📋 Adding {len(new_columns)} new columns:")
        for i, col in enumerate(new_columns, start=10):  # Starting from column J (10)
            print(f"   Column {chr(64+i)}: {col}")

        # Add headers (Row 11, starting from column J)
        start_col = 'J'
        end_col = chr(ord('J') + len(new_columns) - 1)
        range_notation = f"{start_col}{header_row_idx}:{end_col}{header_row_idx}"

        print(f"\n📝 Writing to range: {range_notation}")

        # Check if columns already exist
        header_row = all_data[header_row_idx - 1]
        if len(header_row) >= 10 and header_row[9]:  # Column J
            print(f"\n⚠️  Column J already has data: '{header_row[9]}'")
            response = input("Overwrite existing columns? (yes/no): ")
            if response.lower() != 'yes':
                print("Cancelled.")
                return False

        # Update the sheet
        worksheet.update(range_notation, [new_columns])

        print(f"\n✅ Successfully added columns!")

        # Also update Row 12 (sub-headers if needed)
        # You can add sub-descriptions here if wanted

        print("\n" + "=" * 80)
        print("SETUP COMPLETE!")
        print("=" * 80)
        print("\nNew columns added:")
        print("  J - Last Call Date")
        print("  K - Call Status")
        print("  L - Payment Promise Date")
        print("  M - Next Follow-up Date")
        print("  N - Call Summary")
        print("  O - Total Calls Made")
        print("  P - Customer Sentiment")
        print("  Q - Transcript Link")
        print("\nThe system will now:")
        print("  ✓ Update these columns after each call")
        print("  ✓ Skip calls if Next Follow-up Date is in future")
        print("  ✓ Track number of call attempts")
        print("  ✓ Prevent calling same customer multiple times per day")

        return True

    except Exception as e:
        logger.error(f"Error setting up columns: {e}")
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Setup call tracking columns in Google Sheet')
    parser.add_argument('--sheet-id', help='Google Sheet ID (optional, uses default from settings)')
    args = parser.parse_args()

    success = setup_call_tracking_columns(args.sheet_id)
    sys.exit(0 if success else 1)
