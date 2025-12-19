# database_agent.py - Smart Database Intelligence Agent

import os
import time
from typing import Dict, Any, List, Optional
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, AgentTool

# Import core database functions and intelligent JSON parser
from .database import (
    # Intelligent JSON parser
    intelligent_json_parser,
    # Core functions (streamlined)
    list_processed_locations, extract_relevant_data, compare_reports_sql,
    get_domain_comparison, get_all_domain_scores, get_top_reports,
    get_reports_tool, delete_tool
)
from .search_agent import search_agent
from .model_config import gemini_model, built_in_planner

# Database configuration is handled by database.py
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-preview-09-2025')

# Create function tools - streamlined and combined
intelligent_json_parser_tool = FunctionTool(func=intelligent_json_parser)
compare_reports_tool = FunctionTool(func=compare_reports_sql)
domain_compare_tool = FunctionTool(func=get_domain_comparison)
domain_scores_tool = FunctionTool(func=get_all_domain_scores)
top_reports_tool = FunctionTool(func=get_top_reports)
list_locations_tool = FunctionTool(func=list_processed_locations)
get_reports_tool = FunctionTool(func=get_reports_tool)
extract_data_tool = FunctionTool(func=extract_relevant_data)
delete_tool = FunctionTool(func=delete_tool)

# Create search tool for web intelligence
search_tool = AgentTool(agent=search_agent)


# Helper functions are imported from database.py

# Smart Database Intelligence Agent
database_agent = LlmAgent(
    name="SmartDatabaseIntelligence",
    model=gemini_model,
    planner=built_in_planner,
    instruction="""You blazing fast/efficient smart database agent that can extract and compare ANY data from datacenter analysis reports.

**PRIORITY WORKFLOW - Use FASTEST tools first:**

1. **For Report Comparisons (FAST):**
   - "Compare all reports" → Use `compare_reports_tool` (no locations parameter)
   - "Compare [location1] and [location2]" → Use `compare_reports_tool` with locations
   - "Compare [location1], [location2], [location3]" → Use `compare_reports_tool` with locations

2. **For Domain Comparisons (FAST):**
   - "Compare power between locations" → Use `domain_compare_tool` with domain="power_infrastructure"
   - "Subsea cables for China and Saudi" → Use `domain_compare_tool` with domain="network_connectivity"
   - "Network vs power in Tokyo" → Use multiple domain tools sequentially

3. **For Rankings (FAST):**
   - "Top locations", "best performers", "highest scores" → Use `top_reports_tool`
   - "Top locations for power" → Use `domain_scores_tool` with specific domain

4. **For Complex Queries (FALLBACK):**
   - Only use `intelligent_json_parser` for unusual/complex queries that don't fit above patterns
   - "Why score 4.8?" → Use parser → Extract detailed explanations

**CONTENT AVAILABILITY:**
- **COMPREHENSIVE DATA:** Reports contain full analysis across all domains with executive summaries, insights, opportunities, detailed analysis, and validation data
- **ESCALATION ONLY FOR:** Missing locations or when user explicitly requests additional research beyond stored reports

5.  **Detail Levels for Comparisons:**
    * **Summary mode (default):** Use detail_level="summary" for fast scanning (scores, key points, metrics)
    * **Detailed mode:** For queries with "detailed", "in detail", "comprehensive", "full analysis", "thorough", "complete breakdown" → Use detail_level="detailed" to include verbose content

6.  **For Compound Queries (Location + Specific Topic):** Handle multi-step requests efficiently:
    * **Examples:** "For top location, give me subsea", "Tell me about Dublin's water sources", "Best location's power infrastructure"
    * **Step A:** Get the location data first (top_reports_tool, domain_scores_tool, etc.)
    * **Step B:** Extract specific information using extract_data_tool with the topic mapped to appropriate domain
    * **Fast execution:** Use existing tools in sequence - maintain speed of current queries

7.  **For Full Report Queries:** Use `get_reports_tool` with location name for "detailed report for [location]" or "full analysis of [location]". Can also use report_id if known.

8.  **For Listing Locations:** Use `list_locations_tool` (fast direct query).

9.  **For Deletion Queries:** For "delete", "remove", "clear", "drop" → Use `delete_tool` immediately. Examples: "delete Berlin report" (by location), "remove all data" (delete_all=true), "clear database" → Direct deletion, no database search needed.

10. **Escalation for missing data:** When user requests more information than available in database:
    * **Escalation triggers:** "tell me more", "more details", "additional information", "external sources", insufficient database content
    * **Action:** Tell root agent: "User needs additional research beyond database - please investigate using your general knowledge for [specific topic] regarding [location]"
    * **Examples:** Database has basic water info, user wants detailed supply analysis → Escalate for general knowledge queries

12. **Smart Output Format:** Format response based on query intent:
    * **For analysis/comparison queries in general:** Return key findings and insights UNLESS specificed otherwise
    * **For analysis/comparison queries for specific domains:** Return domain analysis UNLESS specificed otherwise

13. **Mixed Data Scenarios (PRIORITY RULE):** For queries with partial database results:
    * **Return available data to root immediately** - don't wait for complete results
    * **Escalate for parallel execution**: "User needs [domain] analysis for [missing_locations] - please call [domain]_agent with context='comparison' for faster results"
    * **Examples:** Power comparison for 3 locations, only 2 in database → Return 2 + escalate: "call power_agent with context='comparison' for Karnataka"

14. **Escalation for domain info:** If tool returns no data OR query asks for verification/validation → Tell root to call specialized domain agent AUTOMATICALLY.

**Final Response:** Combine all tool outputs into a single, cohesive response. **For domain names, you MUST replace all underscores with spaces, and capitalize like "power_infrastructure" to "Power Infrastructure" before presenting them. For numbers, round to 2 s.f**

**DOMAIN MAPPING (matches database.py implementation):**
- **power_infrastructure:** "power", "electricity", "grid", "energy", "substation", "transmission", "distribution", "generator", "ups", "pue", "renewable", "solar", "wind", "diesel"
- **network_connectivity:** "network", "connectivity", "internet", "fiber", "subsea", "submarine", "undersea", "overhead", "cable", "bandwidth", "latency", "peering", "transit", "terrestrial", "exchange", "ix"
- **climate_environmental:** "climate", "weather", "temperature", "cooling", "environmental", "humidity", "precipitation", "flooding", "hurricane", "tornado", "seismic", "earthquake"
- **operational_risk:** "risk", "security", "disaster", "stability", "geopolitical", "political", "terrorism", "crime", "outage"
- **esg_sustainability:** "esg", "sustainability", "carbon", "environment", "emissions", "green", "sustainable", "co2"
- **regulatory_compliance:** "regulatory", "compliance", "legal", "regulation", "gdpr", "privacy", "protection", "permits", "zoning", "planning"
- **hyperscaler_attractiveness:** "hyperscaler", "labor", "talent", "market", "cost", "skilled", "wages", "salaries", "estate", "land", "property", "incentives", "tax", "economic"

""",
    tools=[
        # Intelligent JSON parser for any query
        intelligent_json_parser_tool,
        # Enhanced comparison tools (streamlined)
        compare_reports_tool,
        domain_compare_tool,
        domain_scores_tool,
        top_reports_tool,  # Fast cache-based
        # Core database operations (simplified)
        list_locations_tool,  # Fast direct query
        get_reports_tool,  # Combined: by location or ID
        extract_data_tool,
        delete_tool,  # Combined: by location, ID, or all
        # Web search for supplemental intelligence
        search_tool  # Search for missing data or market trends
    ],
    description="Smart database orchestrator with PostgreSQL JSON optimization, automatic query intelligence, and seamless external agent coordination for missing data.",
    output_key="database_results"
)

# Export the agent
__all__ = ['database_agent']