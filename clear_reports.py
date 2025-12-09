#!/usr/bin/env python3
"""
Clear all reports from database for fresh testing.
"""

from agent.database import delete_tool, get_database_stats

def main():
    print("=" * 80)
    print("CLEARING ALL REPORTS FROM DATABASE")
    print("=" * 80)

    # Get current stats
    print("\n📊 Current Database Status:")
    stats_result = get_database_stats()
    if stats_result["status"] == "success":
        stats = stats_result["data"]
        print(f"  Total Reports: {stats['total_reports']}")
        print(f"  Average Score: {stats['average_score']}")
        print(f"  Rating Distribution: {stats['rating_distribution']}")

    # Confirm deletion
    print("\n⚠️  WARNING: This will delete ALL reports from the database!")
    confirm = input("Type 'DELETE ALL' to confirm: ")

    if confirm.strip() == "DELETE ALL":
        print("\n🗑️  Deleting all reports...")
        result = delete_tool(delete_all=True)

        if result.get("success"):
            print(f"✅ {result['message']}")
            print(f"   Deleted {result['deleted_count']} reports")
            print("\n🎉 Database cleared! Ready for fresh testing with 9-agent system.")
        else:
            print(f"❌ {result['message']}")
    else:
        print("\n❌ Deletion cancelled. No changes made.")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
