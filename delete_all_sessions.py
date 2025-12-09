#!/usr/bin/env python
"""
Script to delete ALL sessions and reports from the database (nuclear option)
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

    print(f"🔍 Checking ALL data in database...\n")

    # Count ALL sessions (regardless of user_id)
    cursor.execute("SELECT COUNT(*) FROM custom_sessions")
    total_sessions = cursor.fetchone()[0]

    # Count ALL messages
    cursor.execute("SELECT COUNT(*) FROM custom_messages")
    total_messages = cursor.fetchone()[0]

    # Count ALL reports
    cursor.execute("SELECT COUNT(*) FROM reports")
    total_reports = cursor.fetchone()[0]

    # Check uploaded_files if it exists
    try:
        cursor.execute("SELECT COUNT(*) FROM uploaded_files")
        total_files = cursor.fetchone()[0]
        has_files_table = True
    except psycopg2.errors.UndefinedTable:
        total_files = 0
        has_files_table = False
        conn.rollback()

    print(f"📊 Current database state:")
    print(f"  ✓ Total Sessions: {total_sessions}")
    print(f"  ✓ Total Messages: {total_messages}")
    print(f"  ✓ Total Files: {total_files}" + (" (table doesn't exist)" if not has_files_table else ""))
    print(f"  ✓ Total Reports: {total_reports}")
    print()

    # Sample some sessions to see what user_ids look like
    cursor.execute("SELECT session_id, user_id, created_at FROM custom_sessions LIMIT 5")
    sample_sessions = cursor.fetchall()
    if sample_sessions:
        print(f"📋 Sample sessions:")
        for session_id, user_id, created_at in sample_sessions:
            print(f"  - ID: {session_id[:30]}... | User: {user_id or '(NULL)'} | Created: {created_at}")
        print()

    if total_sessions == 0 and total_messages == 0 and total_reports == 0:
        print("✅ Database is already clean!")
        conn.close()
        return

    print(f"⚠️  DELETING ALL DATA FROM DATABASE...")
    print()

    # Delete ALL uploaded files
    if has_files_table:
        cursor.execute("DELETE FROM uploaded_files")
        deleted_files = cursor.rowcount
        print(f"  ✓ Deleted {deleted_files} uploaded files")
    else:
        deleted_files = 0
        print(f"  ⊘ Skipped uploaded_files (table doesn't exist)")

    # Delete ALL messages (will be cascaded from sessions delete, but let's be explicit)
    cursor.execute("DELETE FROM custom_messages")
    deleted_messages = cursor.rowcount
    print(f"  ✓ Deleted {deleted_messages} messages")

    # Delete ALL sessions
    cursor.execute("DELETE FROM custom_sessions")
    deleted_sessions = cursor.rowcount
    print(f"  ✓ Deleted {deleted_sessions} sessions")

    # Delete ALL reports
    cursor.execute("DELETE FROM reports")
    deleted_reports = cursor.rowcount
    print(f"  ✓ Deleted {deleted_reports} reports")

    # Clear top scores cache
    try:
        cursor.execute("DELETE FROM top_scores_cache")
        print(f"  ✓ Cleared top scores cache")
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        print(f"  ⊘ Skipped top_scores_cache (table doesn't exist)")

    # Commit all changes
    conn.commit()
    print()
    print(f"✅ Successfully deleted ALL data from database:")
    print(f"   • {deleted_sessions} sessions removed")
    print(f"   • {deleted_messages} messages removed")
    print(f"   • {deleted_files} files removed")
    print(f"   • {deleted_reports} reports removed")
    print()
    print("🎉 Database is now completely clean!")

    conn.close()

if __name__ == "__main__":
    main()
