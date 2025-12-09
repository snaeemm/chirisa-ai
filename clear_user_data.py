#!/usr/bin/env python
"""
Script to delete all sessions, messages, uploaded files, and reports for user shahzeb.naeem
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path('agent/.env')
load_dotenv(dotenv_path=env_path)

import psycopg2

def main():
    # Connect to database
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in environment variables")
        return

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # User to delete
    user_id = 'shahzeb.naeem'

    print(f"🔍 Checking data for user '{user_id}'...")
    print()

    # Count sessions
    cursor.execute("SELECT COUNT(*) FROM custom_sessions WHERE user_id = %s", (user_id,))
    session_count = cursor.fetchone()[0]

    # Count messages
    cursor.execute("""
        SELECT COUNT(*)
        FROM custom_messages
        WHERE session_id IN (SELECT session_id FROM custom_sessions WHERE user_id = %s)
    """, (user_id,))
    message_count = cursor.fetchone()[0]

    # Count uploaded files (if table exists)
    try:
        cursor.execute("SELECT COUNT(*) FROM uploaded_files WHERE user_id = %s", (user_id,))
        file_count = cursor.fetchone()[0]
        has_uploaded_files_table = True
    except psycopg2.errors.UndefinedTable:
        file_count = 0
        has_uploaded_files_table = False
        conn.rollback()  # Clear the error state

    # Count reports
    cursor.execute("SELECT COUNT(*) FROM reports")
    report_count = cursor.fetchone()[0]

    print(f"📊 Current database state:")
    print(f"  ✓ Sessions for {user_id}: {session_count}")
    print(f"  ✓ Messages for {user_id}: {message_count}")
    print(f"  ✓ Uploaded Files for {user_id}: {file_count}" + (" (table doesn't exist)" if not has_uploaded_files_table else ""))
    print(f"  ✓ Total Reports (all users): {report_count}")
    print()

    # Confirm deletion
    print(f"🗑️  Deleting all data for user '{user_id}'...")
    print()

    # Delete uploaded files for user (if table exists)
    if has_uploaded_files_table:
        cursor.execute("DELETE FROM uploaded_files WHERE user_id = %s", (user_id,))
        deleted_files = cursor.rowcount
        print(f"  ✓ Deleted {deleted_files} uploaded files")
    else:
        deleted_files = 0
        print(f"  ⊘ Skipped uploaded_files (table doesn't exist)")

    # Delete messages (cascade from sessions)
    cursor.execute("""
        DELETE FROM custom_messages
        WHERE session_id IN (SELECT session_id FROM custom_sessions WHERE user_id = %s)
    """, (user_id,))
    deleted_messages = cursor.rowcount
    print(f"  ✓ Deleted {deleted_messages} messages")

    # Delete sessions for user
    cursor.execute("DELETE FROM custom_sessions WHERE user_id = %s", (user_id,))
    deleted_sessions = cursor.rowcount
    print(f"  ✓ Deleted {deleted_sessions} sessions")

    # Delete ALL reports (since reports table doesn't have user_id)
    cursor.execute("DELETE FROM reports")
    deleted_reports = cursor.rowcount
    print(f"  ✓ Deleted {deleted_reports} reports (ALL reports)")

    # Clear top scores cache (if table exists)
    try:
        cursor.execute("DELETE FROM top_scores_cache")
        print(f"  ✓ Cleared top scores cache")
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        print(f"  ⊘ Skipped top_scores_cache (table doesn't exist)")

    # Commit all changes
    conn.commit()
    print()
    print(f"✅ Successfully deleted all data for user '{user_id}':")
    print(f"   • {deleted_sessions} sessions removed")
    print(f"   • {deleted_messages} messages removed")
    print(f"   • {deleted_files} files removed")
    print(f"   • {deleted_reports} reports removed")
    print()
    print("🎉 Database cleaned successfully!")

    conn.close()

if __name__ == "__main__":
    main()
