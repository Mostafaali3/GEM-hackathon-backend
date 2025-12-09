"""
Database Migration Script for NFC Access System
Run this to recreate the database with the new NFC fields.

WARNING: This will delete the existing database and create a new one.
Only run in development!
"""
import os
from database import create_db_and_tables

if __name__ == "__main__":
    # Delete existing database
    db_file = "museum_system.db"
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"✓ Deleted existing database: {db_file}")
    
    # Create new database with updated schema
    create_db_and_tables()
    print("✓ Created new database with NFC fields!")
    print("\nNew Visitor fields added:")
    print("  - virtual_nfc_id: Optional[str] (unique, indexed)")
    print("  - physical_card_id: Optional[str] (unique, indexed)")
