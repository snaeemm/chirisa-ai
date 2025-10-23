# database.py - Database Operations for Data Center Analysis Reports (PostgreSQL)

import os
import json
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables FIRST - use absolute path so it works from any working directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Import PostgreSQL driver
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    raise ImportError("psycopg2 is required. Install it with: pip install psycopg2-binary")

# Assume a simple Pydantic model for demonstration
class OverallSuitability(BaseModel):
    composite_score: float
    rating: str

class ReportSchema(BaseModel):
    location: str
    country: str
    analysis_date: str
    overall_suitability: OverallSuitability
    # Add other fields as needed for your full report structure

# Database configuration - PostgreSQL only
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is required. "
        "Set it in your .env file with your PostgreSQL connection string."
    )

if not PSYCOPG2_AVAILABLE:
    raise ImportError("psycopg2 is required but not installed")

# Always use PostgreSQL
USE_POSTGRES = True

def get_db_connection():
    """Get PostgreSQL database connection with automatic retry logic"""
    max_retries = 3
    retry_delays = [0.5, 1.0, 2.0]  # Progressive delays in seconds

    for attempt in range(max_retries):
        try:
            return psycopg2.connect(DATABASE_URL)
        except (psycopg2.OperationalError, psycopg2.DatabaseError) as e:
            if attempt == max_retries - 1:
                # Last attempt failed, log and raise
                logging.error(f"PostgreSQL connection failed after {max_retries} attempts: {str(e)}")
                raise
            else:
                # Silent retry with progressive delay
                time.sleep(retry_delays[attempt])
                continue
        except Exception as e:
            # Non-connection related errors, don't retry
            logging.error(f"Unexpected database error: {str(e)}")
            raise

def get_placeholder():
    """Get parameter placeholder for PostgreSQL"""
    return '%s'

def init_database():
    """Initialize PostgreSQL database with optimized schema"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create reports table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id SERIAL PRIMARY KEY,
            location TEXT NOT NULL,
            country TEXT NOT NULL,
            analysis_date TEXT NOT NULL,
            composite_score REAL,
            rating TEXT,
            raw_data JSONB NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            pdf_data BYTEA,
            pdf_generated_at TIMESTAMP
        )
    """)

    # Add PDF columns if they don't exist (for existing tables)
    try:
        cursor.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS pdf_data BYTEA")
        cursor.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS pdf_generated_at TIMESTAMP")
    except Exception:
        # Columns might already exist
        pass

    # Create indexes for reports
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_location ON reports(location)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_country ON reports(country)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_score ON reports(composite_score)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_created ON reports(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_raw_data ON reports USING GIN(raw_data)")

    # Create top_scores_cache table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS top_scores_cache (
            location TEXT PRIMARY KEY,
            composite_score REAL NOT NULL,
            rating TEXT,
            analysis_date TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_score ON top_scores_cache(composite_score DESC)")

    # Create custom_sessions table (renamed to avoid ADK conflict)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            session_metadata JSONB
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_custom_session_user ON custom_sessions(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_custom_session_activity ON custom_sessions(last_activity DESC)")

    # Create custom_messages table (renamed to avoid ADK conflict)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_messages (
            message_id SERIAL PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            token_count INTEGER,
            FOREIGN KEY (session_id) REFERENCES custom_sessions(session_id) ON DELETE CASCADE
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_custom_message_session ON custom_messages(session_id, timestamp)")

    # Create uploaded_files table for file upload tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploaded_files (
            id SERIAL PRIMARY KEY,
            session_id TEXT NOT NULL,
            user_id TEXT,
            filename TEXT NOT NULL,
            file_type TEXT,
            document_type TEXT,
            text_content TEXT,
            file_size_bytes INTEGER,
            gemini_file_uri TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES custom_sessions(session_id) ON DELETE CASCADE
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploaded_files_session ON uploaded_files(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploaded_files_user ON uploaded_files(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_uploaded_files_date ON uploaded_files(uploaded_at DESC)")

    conn.commit()
    conn.close()
    print(f"✅ PostgreSQL database initialized successfully")

def _get_report_summary_rows(where_clause: Optional[str] = None, params: Optional[tuple] = None, order_clause: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
    """Helper function to fetch report summary rows with flexible filtering and ordering."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT id, location, country, analysis_date, composite_score, rating, created_at
            FROM reports
        """

        if where_clause:
            query += f" WHERE {where_clause}"
        if order_clause:
            query += f" ORDER BY {order_clause}"
        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query, params or ())
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "location": row[1],
                "country": row[2],
                "analysis_date": row[3],
                "composite_score": round(row[4], 1) if row[4] else -1,
                "rating": row[5],
                "created_at": row[6]
            })

        return {
            "status": "success",
            "data": results,
            "message": f"Retrieved {len(results)} reports"
        }

    except Exception as e:
        return {
            "status": "error",
            "data": [],
            "message": f"Database error in helper function: {str(e)}"
        }

def save_report_to_database(report_object: ReportSchema) -> Dict[str, Any]:
    """Save a ReportSchema object to the database with structured response"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        ph = get_placeholder()

        # Extract key data for fast querying
        location = report_object.location
        country = report_object.country
        analysis_date = report_object.analysis_date
        composite_score = report_object.overall_suitability.composite_score
        rating = report_object.overall_suitability.rating

        # Handle raw_data for PostgreSQL (JSONB)
        raw_data = json.dumps(report_object.model_dump())

        # Upsert logic to handle both new and existing locations
        cursor.execute(f"SELECT id FROM reports WHERE location = {ph}", (location,))
        existing_id = cursor.fetchone()

        if existing_id:
            cursor.execute(f"""
                UPDATE reports
                SET country = {ph}, analysis_date = {ph}, composite_score = {ph}, rating = {ph}, raw_data = {ph}
                WHERE id = {ph}
            """, (country, analysis_date, composite_score, rating, raw_data, existing_id[0]))
            report_id = existing_id[0]
            message = f"Report for {location} updated successfully"
        else:
            cursor.execute(f"""
                INSERT INTO reports (location, country, analysis_date, composite_score, rating, raw_data)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """, (location, country, analysis_date, composite_score, rating, raw_data))
            report_id = cursor.lastrowid
            message = f"Report for {location} saved successfully"

        conn.commit()
        conn.close()

        # Update the top scores cache after successful save
        update_top_scores_cache()

        return {
            "status": "success",
            "message": message,
            "data": {
                "report_id": report_id,
                "location": location,
                "composite_score": composite_score,
                "rating": rating
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to save report: {str(e)}",
            "data": None
        }

def get_report_by_id(report_id: int) -> Dict[str, Any]:
    """Retrieve complete report by database ID with structured response"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        ph = get_placeholder()
        cursor.execute(f"SELECT raw_data, location, composite_score, rating FROM reports WHERE id = {ph}", (report_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {
                "status": "error",
                "message": f"Report with ID {report_id} not found.",
                "data": None
            }

        raw_data = row[0]

        return {
            "status": "success",
            "message": f"Retrieved report #{report_id}",
            "data": {
                "id": report_id,
                "location": row[1],
                "composite_score": round(row[2], 1) if row[2] else -1,
                "rating": row[3],
                "raw_data": raw_data
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving report: {str(e)}",
            "data": None
        }

def list_saved_reports() -> str:
    """List summary of all saved reports with key information"""
    result = _get_report_summary_rows(order_clause="created_at DESC", limit=50)

    if result["status"] == "error":
        return f"❌ Error retrieving reports: {result['message']}"

    if not result["data"]:
        return "📋 No reports found in the database yet. Generate your first comprehensive analysis to see it appear here!"

    return f"📊 Found {len(result['data'])} saved reports:\n\n" + json.dumps(result["data"], indent=2)

def search_reports(location_query: str) -> str:
    """Search reports by location name, country, or rating"""
    search_term = f"%{location_query}%"
    where_clause = "location LIKE ? OR country LIKE ? OR rating LIKE ?"
    params = (search_term, search_term, search_term)

    result = _get_report_summary_rows(
        where_clause=where_clause,
        params=params,
        order_clause="composite_score DESC, created_at DESC",
        limit=20
    )

    if result["status"] == "error":
        return f"❌ Error searching reports: {result['message']}"

    if not result["data"]:
        return f"🔍 No reports found matching '{location_query}'. Try searching for a location name, country, or rating (Excellent, Good, Moderate, Poor)."

    return f"🎯 Found {len(result['data'])} matches for '{location_query}':\n\n" + json.dumps(result["data"], indent=2)


def delete_report(report_id: int) -> Dict[str, Any]:
    """Delete a report by ID with structured response"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        ph = get_placeholder()

        cursor.execute(f"SELECT location FROM reports WHERE id = {ph}", (report_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return {
                "status": "error",
                "message": f"Report with ID {report_id} not found.",
                "data": None
            }

        location = row[0]
        cursor.execute(f"DELETE FROM reports WHERE id = {ph}", (report_id,))
        conn.commit()
        conn.close()

        return {
            "status": "success",
            "message": f"Report #{report_id} for {location} deleted successfully.",
            "data": {
                "deleted_report_id": report_id,
                "location": location
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error deleting report: {str(e)}",
            "data": None
        }

def get_database_stats() -> Dict[str, Any]:
    """Get database statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM reports")
        total_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT rating, COUNT(*)
            FROM reports
            WHERE rating IS NOT NULL
            GROUP BY rating
            ORDER BY COUNT(*) DESC
        """)
        rating_stats = cursor.fetchall()

        cursor.execute("SELECT AVG(composite_score) FROM reports WHERE composite_score > 0")
        avg_score = cursor.fetchone()[0]

        conn.close()

        stats = {
            "total_reports": total_count,
            "average_score": round(avg_score, 2) if avg_score else 0,
            "rating_distribution": dict(rating_stats)
        }

        return {
            "status": "success",
            "message": "Database statistics retrieved successfully",
            "data": stats
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error getting database stats: {str(e)}",
            "data": None
        }

def get_reports_by_location(location: str) -> Dict[str, Any]:
    """Get all reports for a specific location with full JSON data for agent analysis"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        ph = get_placeholder()

        cursor.execute(f"""
            SELECT id, location, country, analysis_date, composite_score, rating, raw_data, created_at
            FROM reports
            WHERE location LIKE {ph} OR country LIKE {ph}
            ORDER BY created_at DESC
        """, (f"%{location}%", f"%{location}%"))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {
                "status": "error",
                "message": f"No reports found for location '{location}'",
                "data": []
            }

        reports = []
        for row in rows:
            try:
                raw_data_json = row[6]
                reports.append({
                    "id": row[0],
                    "location": row[1],
                    "country": row[2],
                    "analysis_date": row[3],
                    "composite_score": round(row[4], 1) if row[4] else -1,
                    "rating": row[5],
                    "full_report": raw_data_json,
                    "created_at": row[7]
                })
            except (json.JSONDecodeError, TypeError):
                continue

        return {
            "status": "success",
            "message": f"Found {len(reports)} reports for '{location}'",
            "data": reports
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving reports for location: {str(e)}",
            "data": []
        }

def intelligent_json_parser(query_description: str) -> Dict[str, Any]:
    """Intelligent JSON parser that can extract ANY data from reports based on natural language query."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get all reports
        cursor.execute("SELECT location, raw_data FROM reports")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {
                "status": "no_data",
                "message": "No reports found in database",
                "data": []
            }

        # Parse each report and extract relevant data
        extracted_data = []
        for location, raw_data_str in rows:
            try:
                report_data = raw_data_str

                # Extract basic info that's always useful
                basic_info = {
                    "location": location,
                    "overall_score": report_data.get("overall_suitability", {}).get("composite_score", "N/A"),
                    "overall_rating": report_data.get("overall_suitability", {}).get("rating", "N/A")
                }

                # Extract domain analysis (this is where most requested data lives)
                domain_analysis = report_data.get("domain_analysis", {})
                for domain_name, domain_data in domain_analysis.items():
                    if isinstance(domain_data, dict):
                        basic_info[f"{domain_name}_score"] = domain_data.get("score", "N/A")
                        basic_info[f"{domain_name}_summary"] = domain_data.get("summary", "")
                        basic_info[f"{domain_name}_key_findings"] = domain_data.get("key_findings", [])

                # Extract executive summary highlights
                exec_summary = report_data.get("executive_summary", {})
                basic_info["key_strengths"] = exec_summary.get("key_strengths", [])
                basic_info["key_challenges"] = exec_summary.get("key_challenges", [])

                # Include the full raw data for complex queries
                basic_info["full_report"] = report_data

                extracted_data.append(basic_info)

            except (json.JSONDecodeError, TypeError):
                continue

        return {
            "status": "success",
            "message": f"Extracted data from {len(extracted_data)} reports for query: {query_description}",
            "data": extracted_data,
            "query": query_description
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error in intelligent JSON parser: {str(e)}",
            "data": []
        }

def find_missing_data(query_description: str) -> Dict[str, Any]:
    """Simple function to detect if we need to call domain agents for missing data."""
    try:
        # Use the intelligent parser to see what we have
        result = intelligent_json_parser(query_description)

        if result["status"] == "no_data" or not result["data"]:
            return {
                "status": "missing",
                "message": "No reports found in database. Need fresh analysis.",
                "request": f"Root Agent, please generate reports for the requested analysis: {query_description}"
            }

        # Check if we have good data for the query
        data = result["data"]
        has_useful_data = False

        for report in data:
            # Check if we have domain scores beyond "N/A"
            for key, value in report.items():
                if "_score" in key and value != "N/A" and value != "":
                    has_useful_data = True
                    break

        if not has_useful_data:
            return {
                "status": "missing",
                "message": "Reports exist but lack detailed analysis for this query.",
                "request": f"Root Agent, please analyze specific factors for: {query_description}"
            }

        return {
            "status": "found",
            "message": "Sufficient data available",
            "data": data
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error checking for missing data: {str(e)}"
        }


def get_domain_from_query(query: str) -> Optional[str]:
    """
    Map user query to appropriate domain for targeted analysis.
    Returns the best matching domain name or None if no match found.
    """
    query_lower = query.lower()

    # Multi-word phrases (check these first for priority)
    multi_word_mappings = {
        'hyperscaler_attractiveness': ['labor cost', 'labour cost', 'real estate cost', 'land cost', 'business climate'],
        'regulatory_compliance': ['data protection', 'gdpr compliance'],
        'network_connectivity': ['subsea cables', 'submarine cables'],
        'climate_environmental': ['natural disaster'],
        'esg_sustainability': ['carbon neutral']
    }

    # Check multi-word phrases first (priority matching)
    for domain, phrases in multi_word_mappings.items():
        if any(phrase in query_lower for phrase in phrases):
            return domain

    # Single word keyword mapping (matches database_agent.py for consistency)
    domain_mappings = {
        'power_infrastructure': ['power', 'electricity', 'grid', 'energy', 'electrical', 'substation', 'transmission', 'distribution', 'generator', 'ups', 'pue', 'renewable', 'solar', 'wind', 'diesel', 'utility', 'capacity'],
        'network_connectivity': ['network', 'connectivity', 'internet', 'fiber', 'subsea', 'submarine', 'undersea', 'overhead', 'cable', 'bandwidth', 'latency', 'peering', 'transit', 'terrestrial', 'exchange', 'ix'],
        'climate_environmental': ['climate', 'weather', 'temperature', 'cooling', 'environmental', 'humidity', 'precipitation', 'flooding', 'hurricane', 'tornado', 'seismic', 'earthquake'],
        'operational_risk': ['risk', 'security', 'disaster', 'stability', 'geopolitical', 'political', 'terrorism', 'crime', 'outage', 'safety'],
        'esg_sustainability': ['esg', 'sustainability', 'carbon', 'environment', 'emissions', 'green', 'sustainable', 'co2'],
        'regulatory_compliance': ['regulatory', 'compliance', 'legal', 'regulation', 'law', 'gdpr', 'privacy', 'protection', 'permits', 'zoning', 'planning'],
        'hyperscaler_attractiveness': ['hyperscaler', 'labor', 'labour', 'talent', 'market', 'cost', 'skilled', 'wages', 'salaries', 'salary', 'estate', 'land', 'property', 'incentives', 'tax', 'economic', 'attractiveness']
    }

    # Find the best matching domain
    for domain, keywords in domain_mappings.items():
        if any(keyword in query_lower for keyword in keywords):
            return domain

    return None

def update_top_scores_cache() -> None:
    """
    Update the top_scores_cache table with the latest data from reports.
    This provides lightning-fast access to overall scores without JSON parsing.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Clear existing cache
        cursor.execute("DELETE FROM top_scores_cache")

        # Repopulate cache with latest data
        cursor.execute("""
            INSERT INTO top_scores_cache (location, composite_score, rating, analysis_date)
            SELECT location, composite_score, rating, analysis_date
            FROM reports
            WHERE composite_score IS NOT NULL
        """)

        conn.commit()
        conn.close()

    except Exception as e:
        print(f"⚠️ Error updating top scores cache: {str(e)}")

def get_top_reports() -> Dict[str, Any]:
    """
    Lightning-fast retrieval of all locations ranked by their overall composite score
    from the pre-computed cache table.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query the fast cache table instead of the large reports table
        cursor.execute("""
            SELECT
                location,
                composite_score,
                rating,
                analysis_date
            FROM top_scores_cache
            ORDER BY composite_score DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {
                "status": "no_data",
                "message": "No overall scores found in the database.",
                "data": []
            }

        scores_data = []
        for location, score, rating, date in rows:
            scores_data.append({
                "location": location,
                "overall_score": score,
                "rating": rating,
                "analysis_date": date
            })

        return {
            "status": "success",
            "message": f"Retrieved {len(scores_data)} overall scores.",
            "data": scores_data
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving overall scores: {str(e)}",
            "data": []
        }

def delete_tool(location: Optional[str] = None, report_id: Optional[int] = None, delete_all: bool = False) -> Dict[str, Any]:
    """
    Delete reports from database based on parameters.

    Args:
        location: Delete all reports for this location
        report_id: Delete specific report by ID
        delete_all: Delete all reports from database

    Returns:
        Dict with deletion results
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    ph = get_placeholder()

    try:
        deleted_count = 0

        if delete_all:
            # Delete all reports - count reports first
            cursor.execute("SELECT COUNT(*) FROM reports")
            deleted_count = cursor.fetchone()[0]
            cursor.execute("DELETE FROM reports")
            message = f"Deleted all reports ({deleted_count} reports removed)"

        elif report_id:
            # Delete specific report by ID - get location first for better message
            cursor.execute(f"SELECT location FROM reports WHERE id = {ph}", (report_id,))
            row = cursor.fetchone()
            if row:
                location_name = row[0]
                cursor.execute(f"DELETE FROM reports WHERE id = {ph}", (report_id,))
                deleted_count = 1
                message = f"Report #{report_id} for {location_name} deleted successfully"
            else:
                deleted_count = 0
                message = f"Report ID {report_id} not found"

        elif location:
            # Delete all reports for location - count first
            cursor.execute(f"SELECT COUNT(*) FROM reports WHERE location = {ph}", (location,))
            deleted_count = cursor.fetchone()[0]
            cursor.execute(f"DELETE FROM reports WHERE location = {ph}", (location,))
            message = f"Deleted {deleted_count} reports for {location}" if deleted_count > 0 else f"No reports found for {location}"

        else:
            # No parameters provided - safe default
            return {"success": False, "message": "No deletion parameters provided"}

        conn.commit()

        # Update the top scores cache after successful deletion
        update_top_scores_cache()

        return {
            "success": True,
            "message": message,
            "deleted_count": deleted_count
        }

    except Exception as e:
        conn.rollback()
        return {
            "success": False,
            "message": f"Database deletion failed: {str(e)}",
            "deleted_count": 0
        }
    finally:
        conn.close()

def list_processed_locations() -> Dict[str, Any]:
    """Get list of all processed locations with basic info"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT location, country, composite_score, rating, analysis_date
            FROM reports
            ORDER BY location ASC
        """)

        rows = cursor.fetchall()
        conn.close()

        locations = []
        for row in rows:
            locations.append({
                "location": row[0],
                "country": row[1],
                "composite_score": round(row[2], 1) if row[2] else -1,
                "rating": row[3],
                "analysis_date": row[4]
            })

        return {
            "status": "success",
            "message": f"Found {len(locations)} processed locations",
            "data": locations
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error listing locations: {str(e)}",
            "data": []
        }


def get_reports_tool(location: Optional[str] = None, report_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Combined tool to get reports by location name or specific report by ID.

    Args:
        location: Get all reports for this location (fuzzy search)
        report_id: Get specific report by database ID

    Returns:
        Dict with report data
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        ph = get_placeholder()

        if report_id:
            # Get specific report by ID
            cursor.execute(f"SELECT raw_data, location, composite_score, rating FROM reports WHERE id = {ph}", (report_id,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                return {
                    "status": "error",
                    "message": f"Report with ID {report_id} not found",
                    "data": None
                }

            try:
                report_data = row[0]
                return {
                    "status": "success",
                    "message": f"Retrieved report #{report_id} for {row[1]}",
                    "data": {
                        "report_id": report_id,
                        "location": row[1],
                        "composite_score": row[2],
                        "rating": row[3],
                        "full_report": report_data
                    }
                }
            except (json.JSONDecodeError, TypeError):
                return {
                    "status": "error",
                    "message": f"Error parsing report data for ID {report_id}",
                    "data": None
                }

        elif location:
            # Get reports by location (fuzzy search)
            cursor.execute(f"""
                SELECT id, location, country, analysis_date, composite_score, rating, raw_data, created_at
                FROM reports
                WHERE location LIKE {ph} OR country LIKE {ph}
                ORDER BY created_at DESC
            """, (f"%{location}%", f"%{location}%"))

            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return {
                    "status": "error",
                    "message": f"No reports found for location: {location}",
                    "data": []
                }

            reports = []
            for row in rows:
                try:
                    report_data = row[6] if (not row[6]) else json.loads(row[6])
                    if not report_data:
                        report_data = {}
                    reports.append({
                        "id": row[0],
                        "location": row[1],
                        "country": row[2],
                        "analysis_date": row[3],
                        "composite_score": row[4],
                        "rating": row[5],
                        "full_report": report_data,
                        "created_at": row[7]
                    })
                except (json.JSONDecodeError, TypeError):
                    continue

            return {
                "status": "success",
                "message": f"Found {len(reports)} reports for location: {location}",
                "data": reports
            }
        else:
            return {
                "status": "error",
                "message": "Must provide either location or report_id parameter",
                "data": None
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving reports: {str(e)}",
            "data": None
        }

def extract_relevant_data(query: str, domain: Optional[str] = None, detail_level: str = "summary") -> Dict[str, Any]:
    """Extract relevant data from reports using JSON functions for fast parsing"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        ph = get_placeholder()

        if domain:
                # PostgreSQL JSONB operators
                cursor.execute(f"""
                    SELECT
                        location,
                        (raw_data->'domain_analysis'->{ph}->>'score')::float as domain_score,
                        raw_data->'domain_analysis'->{ph}->>'summary' as domain_summary,
                        raw_data->'domain_analysis'->{ph}->'key_findings' as key_findings,
                        composite_score,
                        rating
                    FROM reports
                    WHERE raw_data->'domain_analysis'->{ph} IS NOT NULL
                    ORDER BY composite_score DESC
                """, (domain, domain, domain, domain))
        else:
            # Extract all relevant data
            cursor.execute("""
                SELECT
                    location,
                    raw_data,
                    composite_score,
                    rating
                FROM reports
                ORDER BY composite_score DESC
            """)

        rows = cursor.fetchall()
        conn.close()

        extracted = []
        for row in rows:
            if domain:
                key_findings = row[3] if isinstance(row[3], list) else (json.loads(row[3]) if row[3] else [])
                data = {
                    "location": row[0],
                    "domain_score": round(float(row[1]), 1) if row[1] else -1,
                    "overall_score": round(row[4], 1) if row[4] else -1,
                    "rating": row[5]
                }

                if detail_level == "summary":
                    data["top_findings"] = key_findings[:3] if key_findings else []
                else:
                    data["domain_summary"] = row[2]
                    data["key_findings"] = key_findings

                extracted.append(data)
            else:
                try:
                    if detail_level == "summary":
                        extracted.append({
                            "location": row[0],
                            "overall_score": round(row[2], 1) if row[2] else -1,
                            "rating": row[3]
                        })
                    else:
                        full_data = row[1]
                        extracted.append({
                            "location": row[0],
                            "overall_score": round(row[2], 1) if row[2] else -1,
                            "rating": row[3],
                            "full_report": full_data
                        })
                except (json.JSONDecodeError, TypeError):
                    continue

        return {
            "status": "success",
            "message": f"Extracted data for {len(extracted)} locations",
            "data": extracted,
            "detail_level": detail_level
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error extracting data: {str(e)}",
            "data": []
        }

def compare_reports_sql(locations: Optional[List[str]] = None, detail_level: str = "summary") -> Dict[str, Any]:
    """Fast SQL-based report comparison using JSON functions"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        ph = get_placeholder()

        if locations:
            placeholders = ",".join([ph for _ in locations])
            query = f"""
                SELECT
                    location,
                    composite_score,
                    rating,
                    raw_data->'executive_summary'->'key_strengths' as strengths,
                    raw_data->'executive_summary'->'key_challenges' as challenges,
                    raw_data
                FROM reports
                WHERE location IN ({placeholders})
                ORDER BY composite_score DESC
            """
            cursor.execute(query, locations)
        else:
            cursor.execute("""
                SELECT
                    location,
                    composite_score,
                    rating,
                    raw_data->'executive_summary'->'key_strengths' as strengths,
                    raw_data->'executive_summary'->'key_challenges' as challenges,
                    raw_data
                FROM reports
                ORDER BY composite_score DESC
            """)
        rows = cursor.fetchall()
        conn.close()

        comparisons = []
        for row in rows:
            comparison_data = {
                "location": row[0],
                "overall_score": round(row[1], 1) if row[1] else -1,
                "rating": row[2]
            }

            # Parse strengths and challenges
            strengths = row[3] if isinstance(row[3], list) else (json.loads(row[3]) if row[3] else [])
            challenges = row[4] if isinstance(row[4], list) else (json.loads(row[4]) if row[4] else [])

            if detail_level == "summary":
                comparison_data["top_strengths"] = strengths[:2] if strengths else []
                comparison_data["main_challenges"] = challenges[:2] if challenges else []
            else:
                comparison_data["key_strengths"] = strengths
                comparison_data["key_challenges"] = challenges
                try:
                    full_report = row[5]
                    comparison_data["full_analysis"] = full_report.get("domain_analysis", {})
                except (json.JSONDecodeError, TypeError):
                    pass

            comparisons.append(comparison_data)

        return {
            "status": "success",
            "message": f"Compared {len(comparisons)} reports",
            "data": comparisons,
            "detail_level": detail_level
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error comparing reports: {str(e)}",
            "data": []
        }

def get_domain_comparison(domain: str, locations: Optional[List[str]] = None, detail_level: str = "summary") -> Dict[str, Any]:
    """Fast domain-specific comparison using JSON functions"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        ph = get_placeholder()

        if locations:
            placeholders = ",".join([ph for _ in locations])
            query = f"""
                SELECT
                    location,
                    (raw_data->'domain_analysis'->{ph}->>'score')::float as domain_score,
                    raw_data->'domain_analysis'->{ph}->>'summary' as domain_summary,
                    raw_data->'domain_analysis'->{ph}->'key_findings' as key_findings,
                    composite_score,
                    rating
                FROM reports
                WHERE location IN ({placeholders})
                AND raw_data->'domain_analysis'->{ph} IS NOT NULL
                ORDER BY (raw_data->'domain_analysis'->{ph}->>'score')::float DESC
            """
            params = [domain, domain, domain] + locations + [domain, domain]
            cursor.execute(query, params)
        else:
            cursor.execute(f"""
                SELECT
                    location,
                    (raw_data->'domain_analysis'->{ph}->>'score')::float as domain_score,
                    raw_data->'domain_analysis'->{ph}->>'summary' as domain_summary,
                    raw_data->'domain_analysis'->{ph}->'key_findings' as key_findings,
                    composite_score,
                    rating
                FROM reports
                WHERE raw_data->'domain_analysis'->{ph} IS NOT NULL
                ORDER BY (raw_data->'domain_analysis'->{ph}->>'score')::float DESC
            """, (domain, domain, domain, domain, domain))
        rows = cursor.fetchall()
        conn.close()

        comparisons = []
        for row in rows:
            comparison_data = {
                "location": row[0],
                "domain_score": round(float(row[1]), 1) if row[1] else -1,
                "overall_score": round(row[4], 1) if row[4] else -1,
                "rating": row[5]
            }

            # Parse key findings
            key_findings = row[3] if isinstance(row[3], list) else (json.loads(row[3]) if row[3] else [])

            if detail_level == "summary":
                comparison_data["top_finding"] = key_findings[0] if key_findings else "No specific findings available"
            else:
                comparison_data["domain_summary"] = row[2]
                comparison_data["key_findings"] = key_findings

            comparisons.append(comparison_data)

        return {
            "status": "success",
            "message": f"Domain comparison for {domain}: {len(comparisons)} locations",
            "data": comparisons,
            "domain": domain,
            "detail_level": detail_level
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error in domain comparison: {str(e)}",
            "data": []
        }

def get_all_domain_scores(domain: Optional[str] = None) -> Dict[str, Any]:
    """Get all domain scores, optionally filtered by domain"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        ph = get_placeholder()

        if domain:
                cursor.execute(f"""
                    SELECT
                        location,
                        (raw_data->'domain_analysis'->{ph}->>'score')::float as score,
                        composite_score,
                        rating
                    FROM reports
                    WHERE raw_data->'domain_analysis'->{ph} IS NOT NULL
                    ORDER BY (raw_data->'domain_analysis'->{ph}->>'score')::float DESC
                """, (domain, domain, domain))
        else:
            # Get all domain scores from all reports
            cursor.execute("""
                SELECT
                    location,
                    raw_data,
                    composite_score,
                    rating
                FROM reports
                ORDER BY composite_score DESC
            """)

        rows = cursor.fetchall()
        conn.close()

        domain_scores = []
        if domain:
            for row in rows:
                domain_scores.append({
                    "location": row[0],
                    "domain": domain,
                    "score": row[1],
                    "overall_score": round(row[2], 1) if row[2] else -1,
                    "rating": row[3]
                })
        else:
            # Extract all domain scores from JSON
            for row in rows:
                try:
                    report_data = row[1]
                    domain_analysis = report_data.get("domain_analysis", {})
                    for domain_name, domain_data in domain_analysis.items():
                        if isinstance(domain_data, dict) and "score" in domain_data:
                            domain_scores.append({
                                "location": row[0],
                                "domain": domain_name,
                                "score": domain_data["score"],
                                "overall_score": round(row[2], 1) if row[2] else -1,
                                "rating": row[3]
                            })
                except (json.JSONDecodeError, TypeError):
                    continue

        return {
            "status": "success",
            "message": f"Retrieved {len(domain_scores)} domain scores",
            "data": domain_scores
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving domain scores: {str(e)}",
            "data": []
        }


# ======================================================================================
# PDF STORAGE FUNCTIONS
# ======================================================================================

def save_pdf_to_database(report_id: int, pdf_data: bytes) -> Dict[str, Any]:
    """Save PDF data to the database for a specific report"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Update the report with PDF data
        cursor.execute("""
            UPDATE reports
            SET pdf_data = %s, pdf_generated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (pdf_data, report_id))

        conn.commit()
        conn.close()

        if cursor.rowcount > 0:
            return {
                "status": "success",
                "message": f"PDF saved for report {report_id}",
                "report_id": report_id
            }
        else:
            return {
                "status": "error",
                "message": f"Report {report_id} not found"
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error saving PDF to database: {str(e)}"
        }


def get_pdf_from_database(report_id: int) -> Dict[str, Any]:
    """Retrieve PDF data from database for a specific report"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT pdf_data, pdf_generated_at, location
            FROM reports
            WHERE id = %s AND pdf_data IS NOT NULL
        """, (report_id,))

        result = cursor.fetchone()
        conn.close()

        if result:
            pdf_data, generated_at, location = result
            return {
                "status": "success",
                "pdf_data": pdf_data,
                "generated_at": generated_at,
                "location": location
            }
        else:
            return {
                "status": "error",
                "message": f"No PDF found for report {report_id}"
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving PDF from database: {str(e)}"
        }


def check_pdf_exists(report_id: int) -> bool:
    """Check if PDF exists for a report"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM reports
            WHERE id = %s AND pdf_data IS NOT NULL
        """, (report_id,))

        count = cursor.fetchone()[0]
        conn.close()

        return count > 0

    except Exception:
        return False


# Don't auto-initialize on import to avoid DNS issues in WSL
# Call init_database() explicitly when needed or in agent.py main()