"""
Utility script to manage clients and their Google Sheet IDs.
"""
import sys
import os
import asyncio

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import get_db
from database.models import Client
from services.call_orchestrator import call_orchestrator
from utils.logger import logger


def list_clients():
    """List all clients and their Google Sheet IDs."""
    print("\n" + "=" * 80)
    print("CLIENT LIST")
    print("=" * 80)

    with get_db() as db:
        clients = db.query(Client).all()

        if not clients:
            print("No clients found in database.")
            return

        print(f"\nTotal clients: {len(clients)}\n")
        print(f"{'ID':<5} {'Client Name':<30} {'Contact':<15} {'Sheet ID':<45}")
        print("-" * 95)

        for client in clients:
            sheet_id = client.google_sheet_id or "Not set"
            print(f"{client.id:<5} {client.client_name[:29]:<30} {client.contact_number:<15} {sheet_id[:44]:<45}")

    print("\n")


def add_client(client_name: str, contact_number: str, sheet_id: str, company_name: str = None):
    """
    Add a new client with their Google Sheet ID.

    Args:
        client_name: Name of the client
        contact_number: Contact number (will be formatted to E.164)
        sheet_id: Google Sheet ID for this client
        company_name: Optional company name
    """
    try:
        # Format contact number
        if not contact_number.startswith('+'):
            contact_number = f"+91{contact_number.replace(' ', '').replace('-', '')}"

        with get_db() as db:
            # Check if client already exists
            existing = db.query(Client).filter(Client.contact_number == contact_number).first()

            if existing:
                print(f"Client with contact {contact_number} already exists!")
                print(f"Updating sheet ID to: {sheet_id}")
                existing.google_sheet_id = sheet_id
                if company_name:
                    existing.company_name = company_name
                logger.info(f"Updated client {client_name}")
            else:
                # Create new client
                client = Client(
                    client_name=client_name,
                    company_name=company_name or client_name,
                    contact_number=contact_number,
                    google_sheet_id=sheet_id
                )
                db.add(client)
                logger.info(f"Added new client {client_name}")

            print(f"✓ Client '{client_name}' configured successfully!")
            print(f"  Contact: {contact_number}")
            print(f"  Sheet ID: {sheet_id}")

    except Exception as e:
        logger.error(f"Error adding client: {e}")
        print(f"✗ Error: {e}")


def update_sheet_id(client_id: int, sheet_id: str):
    """
    Update Google Sheet ID for a client.

    Args:
        client_id: Database ID of the client
        sheet_id: New Google Sheet ID
    """
    try:
        with get_db() as db:
            client = db.query(Client).filter(Client.id == client_id).first()

            if not client:
                print(f"Client with ID {client_id} not found!")
                return

            client.google_sheet_id = sheet_id
            print(f"✓ Updated sheet ID for client '{client.client_name}'")
            print(f"  New Sheet ID: {sheet_id}")
            logger.info(f"Updated sheet ID for client {client.client_name}")

    except Exception as e:
        logger.error(f"Error updating sheet ID: {e}")
        print(f"✗ Error: {e}")


async def sync_all_sheets():
    """Sync data from all client sheets."""
    print("\n" + "=" * 80)
    print("SYNCING ALL CLIENT SHEETS")
    print("=" * 80 + "\n")

    with get_db() as db:
        clients = db.query(Client).filter(Client.google_sheet_id != None).all()

        if not clients:
            print("No clients with sheet IDs found.")
            return

        sheet_ids = [client.google_sheet_id for client in clients]
        unique_sheet_ids = list(set(sheet_ids))

        print(f"Found {len(unique_sheet_ids)} unique sheets to process\n")

        await call_orchestrator.process_multiple_sheets(unique_sheet_ids)

        print("\n✓ All sheets synced successfully!")


def main():
    """Main CLI interface."""
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python manage_clients.py list")
        print("  python manage_clients.py add <name> <contact> <sheet_id> [company_name]")
        print("  python manage_clients.py update <client_id> <sheet_id>")
        print("  python manage_clients.py sync")
        print("\nExamples:")
        print("  python manage_clients.py list")
        print("  python manage_clients.py add 'John Doe' 9876543210 '1yxzgb_goUqun-dJ48SbG2q2vgn9LOy1a2jZCrNnK1-g'")
        print("  python manage_clients.py update 1 '1yxzgb_goUqun-dJ48SbG2q2vgn9LOy1a2jZCrNnK1-g'")
        print("  python manage_clients.py sync")
        return

    command = sys.argv[1]

    if command == "list":
        list_clients()

    elif command == "add":
        if len(sys.argv) < 5:
            print("Error: Missing arguments")
            print("Usage: python manage_clients.py add <name> <contact> <sheet_id> [company_name]")
            return

        name = sys.argv[2]
        contact = sys.argv[3]
        sheet_id = sys.argv[4]
        company = sys.argv[5] if len(sys.argv) > 5 else None

        add_client(name, contact, sheet_id, company)

    elif command == "update":
        if len(sys.argv) < 4:
            print("Error: Missing arguments")
            print("Usage: python manage_clients.py update <client_id> <sheet_id>")
            return

        try:
            client_id = int(sys.argv[2])
            sheet_id = sys.argv[3]
            update_sheet_id(client_id, sheet_id)
        except ValueError:
            print("Error: client_id must be a number")

    elif command == "sync":
        asyncio.run(sync_all_sheets())

    else:
        print(f"Unknown command: {command}")
        print("Available commands: list, add, update, sync")


if __name__ == "__main__":
    main()
