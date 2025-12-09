#!/usr/bin/env python
"""
Script to list all tables in the database and show their contents
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path('agent/.env')
load_dotenv(dotenv_path=env_path)

import psycopg2

def main():
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found")
        return

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    print(f"🔍 Listing ALL tables in database...\n")

    # Get all tables
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)

    tables = cursor.fetchall()

    print(f"📋 Found {len(tables)} tables:\n")

    for (table_name,) in tables:
        # Count rows in each table
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  ✓ {table_name}: {count} rows")

            # If it's a session-related table, show sample data
            if 'session' in table_name.lower() and count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
                columns = [desc[0] for desc in cursor.description]
                print(f"      Columns: {', '.join(columns)}")

        except Exception as e:
            print(f"  ⚠️  {table_name}: Error - {str(e)}")

    conn.close()

if __name__ == "__main__":
    main()
