# agent.py - Data Center Site Analysis Orchestrator
# Follow https://google.github.io/adk-docs/get-started/quickstart/ to learn the setup

import os
import re
from google.adk.agents import LlmAgent, ParallelAgent
from google.adk.tools import FunctionTool, AgentTool
from google.adk.runners import Runner
import googlemaps
from dotenv import load_dotenv

from .models import LocationContext, AgentInput
# Database functions are now handled by fast wrapper functions
from .database import (
    list_saved_reports, get_report_by_id, search_reports, get_top_reports,
    get_database_stats, delete_report, init_database
)

load_dotenv()

from .power_agent import power_agent
from .network_agent import network_agent
from .climate_agent import climate_agent
from .site_civil_agent import site_civil_agent
from .mechanical_thermal_agent import mechanical_thermal_agent
from .regulatory_esg_agent import regulatory_esg_agent
from .market_competition_agent import market_competition_agent
# Synthesis agent
from .synthesis_agents import datacenter_report_tool
from .database_agent import database_agent
from .search_agent import search_agent
from google.adk.sessions import DatabaseSessionService


# Configure output keys for each agent
power_agent.output_key = "power_result"
network_agent.output_key = "network_result"
climate_agent.output_key = "climate_result"
site_civil_agent.output_key = "site_civil_result"
mechanical_thermal_agent.output_key = "mechanical_thermal_result"
regulatory_esg_agent.output_key = "regulatory_esg_result"
market_competition_agent.output_key = "market_competition_result"

# Configuration - API Keys from environment
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

# Debug: Log which API key is being used (first 15 chars only for security)
print(f"[DEBUG] GEMINI_API_KEY loaded: {GEMINI_API_KEY[:15] if GEMINI_API_KEY else 'None'}...")
print(f"[DEBUG] GOOGLE_MAPS_API_KEY loaded: {GOOGLE_MAPS_API_KEY[:15] if GOOGLE_MAPS_API_KEY else 'None'}...")

# Validate required environment variables
if not GOOGLE_MAPS_API_KEY:
    raise ValueError("GOOGLE_MAPS_API_KEY environment variable is required")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is required")

# Google Maps client for location resolution
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)


def maps_tool(location_query: str) -> LocationContext:
    """Simple Google Maps API wrapper for location resolution.

    Args:
        location_query: Location string (address, coordinates, city name)

    Returns:
        LocationContext: Structured location data
    """
    try:
        # Enhanced coordinate parsing to handle multiple formats
        coord_pattern_simple = r'^[-+]?[0-9]*\.?[0-9]+\s*,\s*[-+]?[0-9]*\.?[0-9]+$'
        coord_pattern_degrees = r'^[-+]?[0-9]*\.?[0-9]+\s*°?\s*[NS]?\s*,\s*[-+]?[0-9]*\.?[0-9]+\s*°?\s*[EW]?$'

        location_stripped = location_query.strip()

        # Check for coordinate formats (simple decimal or with degree symbols/directions)
        if re.match(coord_pattern_simple, location_stripped) or re.match(coord_pattern_degrees, location_stripped, re.IGNORECASE):

            # Parse coordinates with degree symbols and directional indicators
            def parse_coordinate_component(coord_str: str) -> float:
                """Parse a single coordinate component handling degrees and directions"""
                coord_str = coord_str.strip()

                # Remove degree symbol
                coord_str = coord_str.replace('°', '')

                # Extract direction (N, S, E, W) - case insensitive
                direction = None
                for char in ['N', 'S', 'E', 'W', 'n', 's', 'e', 'w']:
                    if char in coord_str:
                        direction = char.upper()
                        coord_str = coord_str.replace(char, '').strip()
                        break

                # Convert to float
                value = float(coord_str)

                # Apply direction (S and W are negative)
                if direction in ['S', 'W']:
                    value = -abs(value)
                elif direction in ['N', 'E']:
                    value = abs(value)

                return value

            coords = [c.strip() for c in location_stripped.split(',')]
            lat = parse_coordinate_component(coords[0])
            lng = parse_coordinate_component(coords[1])

            # Validate coordinate ranges
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                raise ValueError(f"Invalid coordinate ranges: lat={lat}, lng={lng}")

            reverse_result = gmaps.reverse_geocode((lat, lng))
            if reverse_result:
                place = reverse_result[0]
                country = next((c['long_name'] for c in place['address_components']
                               if 'country' in c['types']), "Unknown")
                location = place.get('formatted_address', f"{lat}, {lng}")
            else:
                country = "Unknown"
                location = f"{lat}, {lng}"
        else:
            # Direct geocoding for location names
            result = gmaps.geocode(location_query)
            if not result:
                raise ValueError(f"Location not found: {location_query}")

            place = result[0]
            lat = place['geometry']['location']['lat']
            lng = place['geometry']['location']['lng']
            country = next((c['long_name'] for c in place['address_components']
                           if 'country' in c['types']), "Unknown")
            location = place['formatted_address']

        return LocationContext(
            lat=lat,
            lng=lng,
            country=country,
            location=location,
            justification=None
        )
    except Exception as e:
        raise ValueError(f"Location resolution failed: {str(e)}")



# --- LOCATION AGENT WITH SMART DATACENTER INTELLIGENCE ---
location_agent = LlmAgent(
    name="LocationIntelligenceAgent",
    model=GEMINI_MODEL,
    instruction="""You are a datacenter location intelligence specialist with access to Google Maps API and deep knowledge of datacenter infrastructure requirements.

Your task is to intelligently resolve location queries and provide datacenter site analysis based on user input.

You can also have fruitful discussions with the user to discuss anything on datacentres.

**For all location queries:**
- Use maps_tool to get basic location coordinates and information
- Return the LocationContext object directly

**For simple queries** (addresses, coordinates, city names like "Alaska"):
- Use maps_tool to resolve the location
- Return the LocationContext with basic information

**For optimization queries** ("best datacenter location in UAE", "optimal site in Singapore"):
- First use maps_tool to understand the general region (e.g., get UAE coordinates)
- Then use your datacenter expertise to suggest optimal locations within that region
- Consider datacenter-specific factors like:
  - Power infrastructure availability (substations, industrial zones)
  - Network connectivity (fiber routes, telecom hubs)
  - Regulatory environment (industrial permits, data regulations)
  - Economic factors (incentives, free trade zones)
  - Risk factors (natural disasters, geopolitical stability)
- IMPORTANT: Provide detailed justification explaining why this specific location is optimal

**Your Intelligence:** You make the decisions about what constitutes an optimal datacenter location, not the tool. The tool just provides basic geocoding.

**Creativity:** When user seems to be interested in more depth or asks you to search the internet, use your expert knowledge and reply back: If needed use only your expert knowledge, otherwise a mix of expert knowledge and database.

Always return a structured LocationContext object with coordinates, country, location details, and detailed justification explaining your location selection reasoning.""",
    tools=[FunctionTool(func=maps_tool)],
    description="PREREQUISITE: Intelligent location analysis that must be called first to establish location context before any technical domain analysis. Uses Maps API and datacenter expertise for optimal site selection.",
    output_schema=LocationContext,
    output_key="location_context"
)

# --- DATABASE TOOLS ---
# Create database operation tools
database_list_tool = FunctionTool(func=list_saved_reports)
database_get_tool = FunctionTool(func=get_report_by_id)
database_search_tool = FunctionTool(func=search_reports)
database_top_tool = FunctionTool(func=get_top_reports)
database_stats_tool = FunctionTool(func=get_database_stats)
database_delete_tool = FunctionTool(func=delete_report)

# --- 1. Direct Approach Only ---
# Root agent uses custom parallel function and report generation

# --- 5. Root Agent for ADK Interface ---
root_agent = LlmAgent(
    name="DataCenterSiteAnalyzer",
    model=GEMINI_MODEL,
    instruction="""You are a professional, blazing fast/efficient datacenter site analysis consultant. Your role is to orchestrate comprehensive location analysis using specialized agents and tools.

**Nice Gesture:** Tell user what you're upto, but be concise so as to focus on results and speed.


**CRITICAL WORKFLOW RULES:**
- LocationContext with coordinates (lat, lng), country, and location must be established before any analysis
- AUTOMATIC database checking and smart routing based on existing reports
- **NEW: Smart Database Agent Auto-Routing** - NO permission asking for external agent calls

**Your intelligent decision logic:**
1. **Check if LocationContext exists** with lat, lng, country in the current session
2. **AUTOMATICALLY check database for existing reports** using SmartDatabaseIntelligence agent
3. **Smart routing with AUTO-EXECUTION:**

2.  **Route Based on Intent:**
    * For **ANY** query that involves stored data (e.g., listing reports, comparisons, or data for a known location), **you MUST delegate entirely to the `database_agent`**. Pass the full user query as the argument.
    * For **new site analysis** requests (e.g., "analyze a new location," "find the best location in a region"), route to the `LocationIntelligenceAgent`, then call relevant agent or just answer frm your general and expert knowledge.
    * For explicit **report generation** requests (e.g., "generate a report for a new city"), **you MUST first route to `LocationIntelligenceAgent` and then automatically route the result to `datacenter_report_tool`**.
    * For **specific domain analysis** on a new location (e.g., "analyze power for a new city"), **you MUST first route to `LocationIntelligenceAgent` and then automatically route the result to the specific domain agent with standard quick analysis context**.
    * **For escalations from database_agent:** When database agent says user needs general knowledge, use your knowledge to find the requested information.
    * **For general data center conversations:** Topics like industry trends, strategic planning, general knowledge - use your expertise to provide helpful responses.
    * **For calling domain agents:** Never forget to give location context like lat, long, country, city of the location to get info on.
3.  **Trust Your Specialized Agents:** Do not try to re-validate, re-process, or "cross-check" the output of other agents. They are designed to provide the correct and final output for their specific tasks.

   **AUTO-ROUTING INTELLIGENCE:**
   - When SmartDatabaseIntelligence requests external agents → **IMMEDIATELY EXECUTE**
   - Pattern: "Please call [agent] for [location] [analysis]" → Auto-call that agent
   - NO user confirmation needed for external agent coordination
   - Save new results automatically via database agent

5.  **Be Flexible and Helpful:** You are a data center expert, not just a tool router:
    * For queries outside your specialized tools (trends, general questions, planning discussions), use your knowledge and provide expert commentary
    * Don't say "I don't have a tool for that" - be resourceful and find ways to help
    * Engage in meaningful conversations about data center industry, strategy, and planning
    * When database agent escalates for more information, immediately use your knowledge provide comprehensive answers

**MANDATORY OUTPUT FORMAT:**
* When `datacenter_report_tool` returns its comprehensive executive response, YOU MUST present it directly to the user without modification or summary.
* The report tool returns a fully formatted executive briefing - DO NOT summarize, truncate, or modify it.
* For other tool outputs, synthesize the results from different agents (e.g., location and domain data) into a clear and concise response.
* If a tool returns an error, gracefully report the issue to the user.

**Do not mention function names to user, and when user intends to dig into more detail like *I want a web search on this or more info*, use your expert knowledge whether on its own, or whether backed up by database knowledge.**

**Remember:** Your job is to be the intelligent traffic controller, final presenter, AND helpful data center expert who can discuss any aspect of the industry. When the datacenter_report_tool completes, its output IS your response - present it immediately.""",
    tools=[
        # One-shot parallel analysis and report generation
        datacenter_report_tool,                      # Complete pipeline: parallel analysis → report generation
        AgentTool(agent=location_agent),             # Location intelligence
        # Web search for real-time market intelligence
        AgentTool(agent=search_agent),               # Google Search for current data and trends
        # Individual domain agents for specific questions (7 agents per Expert Spec)
        AgentTool(agent=power_agent),
        AgentTool(agent=network_agent),
        AgentTool(agent=climate_agent),
        AgentTool(agent=site_civil_agent),
        AgentTool(agent=mechanical_thermal_agent),
        AgentTool(agent=regulatory_esg_agent),
        AgentTool(agent=market_competition_agent),
        # Intelligent database agent for all database operations
        AgentTool(agent=database_agent),
    ],
    description="Professional datacenter site analysis orchestrator with intelligent location selection and comprehensive technical analysis"
)

# --- 5. ADK Runner Setup with Persistent Sessions ---

# Initialize PostgreSQL session service for persistent conversations
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    # Connection pool settings to handle Neon's connection timeouts
    # pool_pre_ping=True: Test connections before use (handles stale SSL connections)
    # pool_recycle=300: Recycle connections after 5 minutes to prevent stale connections
    session_service = DatabaseSessionService(
        db_url=DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=5,
        max_overflow=10
    )
    print("✅ PostgreSQL session persistence enabled (Neon)")
else:
    session_service = None
    print("⚠️  No DATABASE_URL - sessions will be ephemeral")

def main():
    """Main function to run the ADK agent with persistent sessions"""
    # Initialize database tables before starting
    print("📊 Initializing PostgreSQL database...")
    init_database()

    runner = Runner(
        agent=root_agent,
        app_name="data-center-analyzer",
        session_service=session_service  # Enable persistent sessions
    )

    print("🏢 Data Center Site Analyzer - Starting ADK interface...")
    print("🌐 Web UI and API will be available shortly...")
    if session_service:
        print("💾 Sessions are persistent - conversations never lost!")
    runner.run()

if __name__ == "__main__":
    main()

# Make root_agent available for import
__all__ = ['root_agent', 'maps_tool']