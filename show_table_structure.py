#!/usr/bin/env python
"""
Script to show the structure of all tables
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
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    tables = ['sessions', 'events', 'app_states', 'user_states', 'reports']

    for table_name in tables:
        print(f"\n{'='*60}")
        print(f"📋 Table: {table_name}")
        print('='*60)

        cursor.execute(f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """)

        columns = cursor.fetchall()
        print("Columns:")
        for col_name, col_type in columns:
            print(f"  - {col_name}: {col_type}")

        # Show sample data
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"\nTotal rows: {count}")

        if count > 0:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
            sample = cursor.fetchone()
            col_names = [desc[0] for desc in cursor.description]
            print("\nSample row:")
            for i, col_name in enumerate(col_names):
                value = sample[i]
                if isinstance(value, str) and len(value) > 50:
                    value = value[:50] + "..."
                print(f"  - {col_name}: {value}")

    conn.close()

if __name__ == "__main__":
    main()
