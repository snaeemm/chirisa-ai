#!/usr/bin/env python
"""
Script to delete ADK sessions and events for user shahzeb.naeem
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

    print(f"🔍 Checking ADK data for user '{user_id}'...\n")

    # Count sessions from ADK sessions table
    cursor.execute("SELECT COUNT(*) FROM sessions WHERE user_id = %s", (user_id,))
    session_count = cursor.fetchone()[0]

    # Get session IDs for this user
    cursor.execute("SELECT id FROM sessions WHERE user_id = %s", (user_id,))
    session_ids = [row[0] for row in cursor.fetchall()]

    # Count events for these sessions
    if session_ids:
        placeholders = ','.join(['%s'] * len(session_ids))
        cursor.execute(f"SELECT COUNT(*) FROM events WHERE session_id IN ({placeholders})", session_ids)
        event_count = cursor.fetchone()[0]
    else:
        event_count = 0

    # Count reports
    cursor.execute("SELECT COUNT(*) FROM reports")
    report_count = cursor.fetchone()[0]

    # Count app_states for this user
    cursor.execute("SELECT COUNT(*) FROM app_states WHERE user_id = %s", (user_id,))
    app_state_count = cursor.fetchone()[0]

    # Count user_states for this user
    cursor.execute("SELECT COUNT(*) FROM user_states WHERE user_id = %s", (user_id,))
    user_state_count = cursor.fetchone()[0]

    print(f"📊 Current database state for '{user_id}':")
    print(f"  ✓ ADK Sessions: {session_count}")
    print(f"  ✓ ADK Events: {event_count}")
    print(f"  ✓ App States: {app_state_count}")
    print(f"  ✓ User States: {user_state_count}")
    print(f"  ✓ Total Reports (all users): {report_count}")
    print()

    # Sample some sessions
    if session_count > 0:
        cursor.execute("SELECT id, user_id, create_time FROM sessions WHERE user_id = %s LIMIT 3", (user_id,))
        sample_sessions = cursor.fetchall()
        print(f"📋 Sample sessions:")
        for session_id, uid, created in sample_sessions:
            print(f"  - ID: {session_id[:30]}... | User: {uid} | Created: {created}")
        print()

    if session_count == 0 and report_count == 0:
        print("✅ No data found for this user!")
        conn.close()
        return

    print(f"🗑️  Deleting all data for user '{user_id}'...")
    print()

    # Delete events first (foreign key to sessions)
    if session_ids:
        placeholders = ','.join(['%s'] * len(session_ids))
        cursor.execute(f"DELETE FROM events WHERE session_id IN ({placeholders})", session_ids)
        deleted_events = cursor.rowcount
        print(f"  ✓ Deleted {deleted_events} events")
    else:
        deleted_events = 0
        print(f"  ⊘ No events to delete")

    # Delete sessions
    cursor.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
    deleted_sessions = cursor.rowcount
    print(f"  ✓ Deleted {deleted_sessions} sessions")

    # Delete app_states
    cursor.execute("DELETE FROM app_states WHERE user_id = %s", (user_id,))
    deleted_app_states = cursor.rowcount
    print(f"  ✓ Deleted {deleted_app_states} app states")

    # Delete user_states
    cursor.execute("DELETE FROM user_states WHERE user_id = %s", (user_id,))
    deleted_user_states = cursor.rowcount
    print(f"  ✓ Deleted {deleted_user_states} user states")

    # Delete ALL reports (no user_id field)
    cursor.execute("DELETE FROM reports")
    deleted_reports = cursor.rowcount
    print(f"  ✓ Deleted {deleted_reports} reports (ALL reports)")

    # Clear top scores cache
    cursor.execute("DELETE FROM top_scores_cache")
    print(f"  ✓ Cleared top scores cache")

    # Commit all changes
    conn.commit()
    print()
    print(f"✅ Successfully deleted all data for user '{user_id}':")
    print(f"   • {deleted_sessions} sessions removed")
    print(f"   • {deleted_events} events removed")
    print(f"   • {deleted_app_states} app states removed")
    print(f"   • {deleted_user_states} user states removed")
    print(f"   • {deleted_reports} reports removed")
    print()
    print("🎉 Database cleaned successfully!")

    conn.close()

if __name__ == "__main__":
    main()
