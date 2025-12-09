#!/usr/bin/env python3
"""Check if location field in database contains corrupted data."""

import json
from agent.database import _get_report_summary_rows, get_report_by_id

# Get all reports
reports_result = _get_report_summary_rows(order_clause="created_at DESC")

if reports_result.get("status") == "success":
    reports = reports_result.get("data", [])

    print(f"Checking {len(reports)} reports for corrupted location data...\n")

    for report in reports:
        report_id = report["id"]
        location = report.get("location", "")

        # Check if location contains dict-like patterns
        if "{" in str(location) or "category" in str(location):
            print(f"⚠️  CORRUPTED DATA FOUND:")
            print(f"   Report ID: {report_id}")
            print(f"   Location field: {location[:200]}...")
            print()

            # Get full report to see raw_data
            full_report = get_report_by_id(report_id)
            if full_report.get("status") == "success":
                raw_data = full_report["data"].get("raw_data", {})
                if isinstance(raw_data, str):
                    raw_data = json.loads(raw_data)

                print(f"   Raw location: {raw_data.get('location', 'N/A')[:200]}")
                print(f"   Type: {type(raw_data.get('location'))}")
                print("\n" + "="*80 + "\n")

    print("✅ Check complete!")
else:
    print(f"❌ Error: {reports_result.get('message')}")
