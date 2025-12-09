#!/usr/bin/env python
"""
Script to check what's in the database for user shahzeb.naeem
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

    user_id = 'shahzeb.naeem'

    print(f"🔍 Checking database for user '{user_id}'...\n")

    # Check sessions
    cursor.execute("SELECT session_id, user_id, created_at, last_activity FROM custom_sessions WHERE user_id = %s", (user_id,))
    sessions = cursor.fetchall()
    print(f"📋 Sessions ({len(sessions)}):")
    for session in sessions[:5]:  # Show first 5
        print(f"  - Session ID: {session[0][:20]}... | User: {session[1]} | Created: {session[2]}")
    if len(sessions) > 5:
        print(f"  ... and {len(sessions) - 5} more")
    print()

    # Check ALL sessions (not just for this user)
    cursor.execute("SELECT COUNT(*), user_id FROM custom_sessions GROUP BY user_id")
    all_sessions = cursor.fetchall()
    print(f"📊 All sessions by user_id:")
    for count, uid in all_sessions:
        user_display = uid if uid else "(NULL)"
        print(f"  - '{user_display}': {count} sessions")
    print()

    # Get TOTAL session count
    cursor.execute("SELECT COUNT(*) FROM custom_sessions")
    total = cursor.fetchone()[0]
    print(f"📈 TOTAL sessions in database: {total}")
    print()

    # Check messages
    cursor.execute("""
        SELECT COUNT(*)
        FROM custom_messages
        WHERE session_id IN (SELECT session_id FROM custom_sessions WHERE user_id = %s)
    """, (user_id,))
    message_count = cursor.fetchone()[0]
    print(f"💬 Messages for {user_id}: {message_count}\n")

    # Check reports
    cursor.execute("SELECT COUNT(*) FROM reports")
    report_count = cursor.fetchone()[0]
    print(f"📄 Total reports: {report_count}\n")

    # Sample a few session IDs to see their structure
    cursor.execute("SELECT session_id FROM custom_sessions LIMIT 3")
    sample_sessions = cursor.fetchall()
    print(f"🔬 Sample session IDs:")
    for session in sample_sessions:
        print(f"  - {session[0]}")

    conn.close()

if __name__ == "__main__":
    main()
