#!/usr/bin/env python
"""
Script to delete ALL sessions, events, and reports from database
(Since most sessions have user_id='user', we'll just delete everything)
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

    # Count everything
    cursor.execute("SELECT COUNT(*) FROM sessions")
    session_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM events")
    event_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM reports")
    report_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM app_states")
    app_state_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM user_states")
    user_state_count = cursor.fetchone()[0]

    print(f"📊 Current database state:")
    print(f"  ✓ ADK Sessions: {session_count}")
    print(f"  ✓ ADK Events: {event_count}")
    print(f"  ✓ App States: {app_state_count}")
    print(f"  ✓ User States: {user_state_count}")
    print(f"  ✓ Reports: {report_count}")
    print()

    # Show user_id distribution
    cursor.execute("SELECT user_id, COUNT(*) FROM sessions GROUP BY user_id")
    user_distribution = cursor.fetchall()
    print(f"📋 Sessions by user_id:")
    for user_id, count in user_distribution:
        print(f"  - '{user_id}': {count} sessions")
    print()

    if session_count == 0 and report_count == 0:
        print("✅ Database is already clean!")
        conn.close()
        return

    print(f"⚠️  DELETING ALL DATA...")
    print()

    # Delete events first (foreign key constraint)
    cursor.execute("DELETE FROM events")
    deleted_events = cursor.rowcount
    print(f"  ✓ Deleted {deleted_events} events")

    # Delete sessions
    cursor.execute("DELETE FROM sessions")
    deleted_sessions = cursor.rowcount
    print(f"  ✓ Deleted {deleted_sessions} sessions")

    # Delete app_states
    cursor.execute("DELETE FROM app_states")
    deleted_app_states = cursor.rowcount
    print(f"  ✓ Deleted {deleted_app_states} app states")

    # Delete user_states
    cursor.execute("DELETE FROM user_states")
    deleted_user_states = cursor.rowcount
    print(f"  ✓ Deleted {deleted_user_states} user states")

    # Delete reports
    cursor.execute("DELETE FROM reports")
    deleted_reports = cursor.rowcount
    print(f"  ✓ Deleted {deleted_reports} reports")

    # Clear top scores cache
    cursor.execute("DELETE FROM top_scores_cache")
    print(f"  ✓ Cleared top scores cache")

    # Commit all changes
    conn.commit()
    print()
    print(f"✅ Successfully deleted ALL data:")
    print(f"   • {deleted_sessions} sessions removed")
    print(f"   • {deleted_events} events removed")
    print(f"   • {deleted_app_states} app states removed")
    print(f"   • {deleted_user_states} user states removed")
    print(f"   • {deleted_reports} reports removed")
    print()
    print("🎉 Database is now completely clean! Ready for fresh testing.")

    conn.close()

if __name__ == "__main__":
    main()
