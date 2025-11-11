"""
Migration script to add google_sheet_id column to clients table.
Run this once to update existing database.
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import engine, get_db
from database.models import Client
from config.settings import settings
from utils.logger import logger
from sqlalchemy import text


def migrate_add_google_sheet_id():
    """Add google_sheet_id column to clients table if it doesn't exist."""
    try:
        logger.info("Starting migration: Add google_sheet_id to clients table")

        # Check if column already exists
        with engine.connect() as conn:
            # Get table info
            result = conn.execute(text("PRAGMA table_info(clients)"))
            columns = [row[1] for row in result]

            if 'google_sheet_id' in columns:
                logger.info("Column google_sheet_id already exists. Migration not needed.")
                return

            # Add the column
            logger.info("Adding google_sheet_id column to clients table...")
            conn.execute(text(
                "ALTER TABLE clients ADD COLUMN google_sheet_id VARCHAR(255)"
            ))
            conn.commit()

            logger.info("Column added successfully!")

            # Update existing clients with default sheet ID from settings
            logger.info(f"Updating existing clients with default sheet ID: {settings.google_sheet_id}")
            with get_db() as db:
                clients = db.query(Client).filter(Client.google_sheet_id == None).all()
                for client in clients:
                    client.google_sheet_id = settings.google_sheet_id
                    logger.info(f"Updated client {client.client_name} with default sheet ID")

            logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error(f"Error during migration: {e}")
        raise


if __name__ == "__main__":
    migrate_add_google_sheet_id()
