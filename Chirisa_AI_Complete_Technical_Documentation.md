# Chirisa AI – Complete Technical Documentation

**Data Centre Intelligence Platform (MVP v1)**
Generated: 2025-01-02

---

## 1. Executive Overview

Chirisa AI is an intelligent multi-agent system designed to analyze data centre location viability across 7 specialized domains. The system combines Google Gemini AI, PostgreSQL database persistence, and an interactive Streamlit interface to provide comprehensive site assessments with confidence scoring, comparative analysis, and strategic recommendations.

### 1.1 Key Capabilities

- **Multi-agent orchestration** with parallel execution across 7 domain specialists
- **Persistent database storage** with historical query and report tracking
- **Interactive web interface** with session management and real-time updates
- **Comparative analysis and ranking** across all analyzed locations
- **Confidence scoring** with data gap identification and third-party verification requirements
- **Strategic synthesis** with cross-domain insights and Phase 1 deployment planning
- **Authentication layer** with username/password protection

---

## 2. System Architecture

### 2.1 Technology Stack

**Frontend: Streamlit**
- Interactive web UI with real-time updates
- Session persistence across browser sessions
- Multi-page navigation (Assistant, Reports)
- Responsive layout with sidebar navigation
- Authentication layer with username/password protection

**Backend Orchestration: Google ADK (Agent Development Kit)**
- Multi-agent coordination and routing
- Session service for conversation persistence
- Tool integration framework (FunctionTool, AgentTool)
- Database-backed session management

**AI Layer: Google Gemini (gemini-2.5-flash / gemini-2.0-flash-exp)**
- 9 specialized AI agents (orchestrator, 7 domains, insights)
- Structured JSON output with Pydantic validation
- Retry logic with enhanced prompt instructions
- Parallel execution for domain agents

**Database: PostgreSQL (Neon Cloud)**
- JSONB schema for flexible report storage
- GIN indexes for fast JSON queries
- Session and message persistence
- Top scores caching for performance

**External APIs:**
- **Google Maps API** - geocoding, reverse geocoding, location resolution
- **Google Generative AI API** - all agent intelligence
- **Future**: Energy APIs, ESG datasets, BGP routing databases

### 2.2 Agent Architecture

**Orchestrator Agent (Root Agent)**
- Routes queries based on intent classification
- Coordinates between domain agents and database agent
- Handles general data centre conversations
- Manages report generation workflow
- Synthesizes multi-agent responses

**Domain Specialist Agents (7 agents):**

1. **Power Infrastructure Agent**
   - Grid reliability (SAIDI/SAIFI metrics)
   - Power capacity and scalability (MW available, transmission lines)
   - Generation mix and sustainability (renewable %, PPA options)
   - Connection process and timelines
   - Electricity costs (USD/kWh) and 20-year projections

2. **Network Connectivity Agent**
   - Fiber infrastructure density and coverage
   - Subsea cable landing points and capacities
   - International connectivity (Tbps, peering)
   - Domestic peering and IXP participation
   - Latency performance and CDN presence
   - Bandwidth costs (USD/Mbps/month)

3. **Climate & Environmental Agent**
   - Temperature and humidity patterns
   - Cooling strategy and PUE calculations
   - Free cooling hours annually
   - Seismic and geological stability
   - Flood risk and hydrological analysis
   - Wind, storm, and climate extremes

4. **Operational Risk Agent**
   - Geopolitical stability assessment
   - Physical security and crime rates
   - Disaster recovery capabilities
   - Business continuity planning
   - Supply chain resilience

5. **ESG & Sustainability Agent**
   - Carbon footprint analysis
   - Environmental compliance
   - Green energy availability
   - Sustainability certifications
   - Corporate ESG alignment

6. **Regulatory Compliance Agent**
   - Data protection laws (GDPR, etc.)
   - Permitting and zoning requirements
   - Construction regulations
   - Import/export restrictions
   - Tax and incentive structures

7. **Hyperscaler Attractiveness Agent**
   - Labor market and talent availability
   - Real estate costs and availability
   - Economic incentives and tax breaks
   - Market competitiveness
   - Infrastructure maturity

**Database Agent**
- Retrieves historical reports from PostgreSQL
- Performs comparative analysis across locations
- Extracts specific domain metrics
- Ranks locations by overall or domain scores
- Handles deletions and database management
- Automatically escalates to domain agents for missing data

**Insights Agent (Cross-Domain Synthesis)**
- Aggregates all 7 domain agent outputs
- Identifies strategic opportunities from cross-domain patterns
- Generates executive summary with strengths, challenges, opportunities
- Creates Phase 1 deployment plan with capacity, timeline, investment
- Produces go/no-go recommendation with confidence assessment
- Normalizes composite scoring across domains

### 2.3 Data Flow Architecture

```
User Query → Orchestrator Agent
  ↓
Intent Classification (location analysis | database query | general conversation)
  ↓
┌─────────────────────┬──────────────────────┬─────────────────────┐
│ Location Analysis   │ Database Query       │ General Conversation│
│  ↓                  │  ↓                   │  ↓                  │
│ Location Agent      │ Database Agent       │ Expert Knowledge    │
│  ↓                  │  ↓                   │  ↓                  │
│ Parallel Domain     │ Historical Reports   │ Conversational      │
│ Execution (7)       │ Comparative Analysis │ Response            │
│  ↓                  │  ↓                   │                     │
│ Results → Insights  │ Extract Metrics      │                     │
│ Agent               │ Top/Worst Rankings   │                     │
│  ↓                  │  ↓                   │                     │
│ Report Schema       │ Structured Results   │                     │
│  ↓                  │  ↓                   │                     │
│ Save to DB          │ Return to User       │                     │
│  ↓                  │                      │                     │
│ Executive Summary   │                      │                     │
│  ↓                  │                      │                     │
└─ User Response ─────┴──────────────────────┴─────────────────────┘
```

---

## 3. Database Schema & Optimization

### 3.1 PostgreSQL Tables

**reports** (Primary table for analysis results)
```sql
CREATE TABLE reports (
    id SERIAL PRIMARY KEY,
    location TEXT NOT NULL,                  -- Formatted address
    country TEXT NOT NULL,                   -- Country name
    analysis_date TEXT NOT NULL,             -- YYYY-MM-DD format
    composite_score REAL,                    -- 1.0-5.0 overall score
    rating TEXT,                             -- Excellent/Good/Moderate/Poor
    raw_data JSONB NOT NULL,                 -- Complete report with all domain analyses
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pdf_data BYTEA,                          -- Optional PDF storage
    pdf_generated_at TIMESTAMP
);

CREATE INDEX idx_location ON reports(location);
CREATE INDEX idx_country ON reports(country);
CREATE INDEX idx_score ON reports(composite_score);
CREATE INDEX idx_created ON reports(created_at);
CREATE INDEX idx_raw_data ON reports USING GIN(raw_data);  -- Fast JSON queries
```

**top_scores_cache** (Performance optimization table)
```sql
CREATE TABLE top_scores_cache (
    location TEXT PRIMARY KEY,
    composite_score REAL NOT NULL,
    rating TEXT,
    analysis_date TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cache_score ON top_scores_cache(composite_score DESC);
```

**custom_sessions** (ADK session persistence, renamed to avoid conflicts)
```sql
CREATE TABLE custom_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_metadata JSONB
);

CREATE INDEX idx_custom_session_user ON custom_sessions(user_id);
CREATE INDEX idx_custom_session_activity ON custom_sessions(last_activity DESC);
```

**custom_messages** (Message history, renamed to avoid ADK conflicts)
```sql
CREATE TABLE custom_messages (
    message_id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,                      -- user/assistant/system
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    token_count INTEGER,
    FOREIGN KEY (session_id) REFERENCES custom_sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX idx_custom_message_session ON custom_messages(session_id, timestamp);
```

### 3.2 JSONB Query Optimization

The `raw_data` column uses PostgreSQL JSONB for flexible querying:

- **GIN index** for fast path queries: `raw_data @> '{"domain": {"metric": value}}'`
- **JSON extraction operators**: `raw_data->'domain_analysis'->'power_infrastructure'->>'score'`
- **Aggregation support**: `SELECT AVG((raw_data->'overall_suitability'->>'composite_score')::float)`
- **Full-text search** capability on nested JSON strings
- **Supports partial updates** without full rewrite

---

## 4. Agent Implementation Details

### 4.1 Prompt Engineering Strategy

**Domain Agent Prompts:**

Each domain agent receives a comprehensive system instruction including:
- Role definition (senior consultant in specific domain)
- Analysis methodology (quantitative data, benchmarking, scoring)
- Required output structure (JSON schema with subsections)
- Scoring guidelines (1.0-5.0 scale with global benchmarks)
- Data quality requirements (assumptions, data gaps, verification needs)
- Response mode detection (concise vs. comprehensive based on context)

**Example Power Agent Prompt Structure:**
```
You are a senior energy and infrastructure consultant specializing in powering hyperscale data center projects.

Analyze these specific factors:
- Grid Reliability & Resiliency: SAIDI/SAIFI metrics, uptime records >99.9%
- Power Capacity & Scalability: MW available, transmission proximity
- Generation Mix & Sustainability: renewable %, baseload stability
- Connection Process & Timeline: interconnection steps, approval timeframes
- Electricity Costs: industrial rates (USD/kWh), market structure
- Cost Model: 20-year projections, escalation rates
- Industrial Heritage: proximity to facilities, existing infrastructure

Sub-Score: X.X/5.0 with quantitative justification
```

**Insights Agent Prompt Strategy:**
- Cross-domain synthesis with interdependency analysis
- Strategic market positioning assessment
- Comprehensive risk/opportunity evaluation
- Detailed implementation strategy with specific actions
- Evidence-based go/no-go recommendation
- Emphasis on detailed, actionable content (3-5 sentences per point)
- Quality requirements: clear English, no abbreviations, complete sentences

**Orchestrator Prompt Strategy:**
- Intent classification rules (location | database | conversation)
- Automatic database checking for existing reports
- Smart routing with auto-execution (no permission asking)
- Escalation handling for missing data
- Expert knowledge fallback for general queries

### 4.2 JSON Parsing & Retry Logic

**Robust JSON Parsing Pipeline:**
1. Clean response: remove markdown wrappers (` ```json ` ` `)
2. Direct parse attempt
3. On failure: detect error type (control_character | syntax_error | unterminated_string | missing_quotes | trailing_comma)
4. Apply targeted repair: remove control chars, fix quotes, remove trailing commas
5. Retry with enhanced prompt instructions (error-specific guidance)
6. Fallback to extraction (regex search for JSON object)
7. Final fallback: create default AgentOutput with error message

**Retry Mechanism:**
- **Max retries**: 2 (total 3 attempts)
- **Exponential backoff**: 1s, 2s, 4s
- **Error-specific prompt enhancement** per attempt
- Preserves original instruction, adds critical formatting requirements
- JSON validation with Pydantic models (PowerInfrastructureOutput, NetworkConnectivityOutput, etc.)

**Error Type Handling:**
- `control_character` → Remove non-ASCII, enforce UTF-8 encoding
- `syntax_error` → Validate brackets/braces, comma placement
- `unterminated_string` → Ensure quote closure, escape internal quotes
- `missing_quotes` → Enforce double quotes on keys and values
- `trailing_comma` → Strip commas before closing delimiters
- `empty_response` → Request complete JSON with all required fields

### 4.3 Parallel Execution Architecture

**Async Task Orchestration:**
- All 7 domain agents execute simultaneously via `asyncio.gather()`
- Each agent wrapped in `call_agent_with_retry()` for fault tolerance
- Shared context dictionary passed to all agents (optional coordination)
- Results collected as dict with agent-specific keys (power_result, network_result, etc.)
- Exception handling per agent (no cascading failures)
- Fallback AgentOutput created for any failed agent

**Execution Flow:**
1. User requests report for location
2. Location agent resolves coordinates
3. Create 7 agent wrapper instances (PowerInfrastructureAgentWrapper, etc.)
4. Submit 7 parallel tasks with `asyncio.gather(return_exceptions=True)`
5. Wait for all completions (fastest agent doesn't block others)
6. Process results: convert to AgentOutput if needed, handle exceptions
7. Calculate composite score from valid results
8. Call insights agent with aggregated data
9. Build ReportSchema with all domain outputs + insights
10. Save to database (PostgreSQL JSONB)
11. Generate executive summary response
12. Return to user

**Performance Characteristics:**
- **Typical execution**: 30-45 seconds for 7 agents + insights + database save
- **Bottleneck**: LLM API calls (gemini-2.5-flash latency)
- **Cache optimization**: top_scores_cache for frequent queries
- **Database connection pooling**: retry logic with progressive delays (0.5s, 1s, 2s)

---

## 5. Authentication & Security

### 5.1 Authentication Layer

**Implementation:**
- **Username**: Admin
- **Password**: professional_granite_123!
- Session-based auth using Streamlit session_state
- Login form displayed on all pages if not authenticated
- Logout button in sidebar clears auth state
- Protection applied to: Assistant page, Reports page

**Security Considerations:**
- Credentials currently stored in `config/settings.py` (plaintext)
- **Recommended production improvements**:
  - Move credentials to environment variables (.env file)
  - Hash passwords with bcrypt or Argon2
  - Implement rate limiting to prevent brute force
  - Add HTTPS enforcement (handled by Streamlit Cloud deployment)
  - Consider JWT tokens for API authentication
  - Add session timeout and re-authentication

### 5.2 Data Security

**API Key Management:**
- `GOOGLE_MAPS_API_KEY`: stored in .env file
- `GEMINI_API_KEY`: stored in .env file
- `DATABASE_URL`: PostgreSQL connection string with SSL
- All keys loaded via python-dotenv
- .env file excluded from git via .gitignore

**Database Security:**
- PostgreSQL prepared statements (prevents SQL injection)
- Parameterized queries with `%s` placeholders
- SSL/TLS connection to Neon database
- Connection string includes: `sslmode=require&channel_binding=require`
- No user input directly concatenated into SQL

**Session Security:**
- Session IDs managed by ADK DatabaseSessionService
- User sessions isolated by session_id
- No cross-session data leakage
- Session timeout based on last_activity timestamp

---

## 6. Pydantic Data Models

### 6.1 Domain-Specific Models

**Base Structures:**
```python
class MetricsData(BaseModel):
    numerical_values: Dict[str, Union[float, int]]  # MW, Tbps, USD/MWh
    percentages: Dict[str, float]                    # Efficiency, uptime
    ranges: Dict[str, Dict[str, float]]             # Min/max ranges
    units: Dict[str, str]                            # Units for each metric

class RichSection(BaseModel):
    name: str
    content: str                                     # Detailed analysis
    sub_score: float = Field(ge=1.0, le=5.0)        # Section scoring
    metrics: MetricsData
    key_points: List[str]
    tables: List[Dict[str, Any]]
```

**Domain Output Models** (all inherit base fields):
- `PowerInfrastructureOutput`: 7 sections (grid_reliability, power_capacity, generation_mix, etc.)
- `NetworkConnectivityOutput`: 7 sections (fiber_infrastructure, subsea_cables, etc.)
- `ClimateAnalysisOutput`: 7 sections (temperature_humidity, cooling_strategy, etc.)
- `OperationalRiskOutput`: sections for geopolitical, physical security, etc.
- `ESGSustainabilityOutput`: carbon analysis, environmental compliance, etc.
- `RegulatoryComplianceOutput`: data protection, permitting, tax structures
- `HyperscalerAttractivenessOutput`: labor market, real estate, incentives

**Common Fields** (all domain models):
```python
overall_score: float                              # 1.0-5.0
assumptions: List[str]
key_insights: List[str]
executive_summary: str
data_gaps: List[str]
third_party_verification: List[str]
phase_1_recommendations: Optional[Dict[str, str]]
```

### 6.2 Report Schema Model

**ReportSchema** (complete report structure):
```python
class ReportSchema(BaseModel):
    location: str                                  # Formatted address
    coordinates: Dict[str, float]                  # lat, lng
    country: str
    analysis_date: str                             # YYYY-MM-DD
    overall_suitability: OverallSuitability        # composite_score, rating, recommendation
    domain_analysis: Dict[str, DomainAnalysis]     # Scores and summaries per domain
    detailed_analysis: Dict[str, str]              # Backward compatibility
    structured_analysis: Dict[str, Any]            # Full domain model objects
    executive_summary: ExecutiveSummary            # location_overview, strengths, challenges
    phase_1_deployment: Phase1Deployment           # capacity, timeline, investment
    strategic_opportunities: List[str]
    strategic_recommendation: str
    conclusion: str                                # Go/no-go decision
    next_steps: List[str]
    insights_result: Optional[Any]                 # Full insights agent output
    data_gap_analysis: Optional[DataGapAnalysis]   # Data sources, gaps, verification
```

**from_location_and_agents() Class Method:**
- Accepts LocationContext + 7 domain agent outputs + insights output
- Extracts properties from agent results (handles both domain-specific and generic AgentOutput)
- Calculates composite score (average of valid domain scores)
- Determines rating (Excellent/Good/Moderate/Poor)
- Builds DomainAnalysis entries for each domain
- Uses intelligent insights if available, otherwise generates fallback
- Creates comprehensive data gap analysis from all agent outputs
- Returns complete ReportSchema instance ready for database storage

---

## 7. Streamlit UI Architecture

### 7.1 Application Structure

**Multi-Page Setup:**
- `Assistant.py` (main chat interface)
- `pages/Reports.py` (report viewer page)
- Shared components via `ui/` module

**Main Components:**
- `ui/auth.py`: authentication functions (check, login form, logout)
- `ui/sidebar.py`: session management, report list, navigation
- `ui/chat_display.py`: message rendering with role-based styling
- `ui/chat_input.py`: input handling, agent invocation, response streaming
- `ui/report_viewer.py`: detailed report display with section expansion

**Session Management:**
- `services/session_service.py`: session CRUD operations
- `services/agent_service.py`: ADK runner initialization
- Persistent sessions via DatabaseSessionService
- Session switching in sidebar
- Delete confirmation for sessions and reports

### 7.2 User Workflows

**Chat Interface (Assistant page):**
1. User authenticates (Admin / professional_granite_123!)
2. Session loaded or created
3. Chat history rendered from session messages
4. User enters query in chat input
5. Query sent to agent runner
6. Response status tracked (processing indicator with elapsed time)
7. Agent response streamed back
8. Message added to session history
9. Session auto-saved to database

**Report Viewing (Reports page):**
1. User navigates to Reports page
2. Sidebar displays list of all reports (cached for 30s)
3. User selects report by location
4. Full report loaded from database by ID
5. Report displayed with expandable sections by domain
6. Each domain shows: score, executive summary, subsections with metrics
7. Data gaps and third-party verification listed
8. Phase 1 deployment plan shown
9. Delete confirmation flow for reports

**Comparative Queries (via chat):**
1. User asks: "Compare all reports" or "Top 5 locations"
2. Orchestrator routes to database agent
3. Database agent uses optimized SQL queries
4. Results formatted with scores and key metrics
5. Response includes rankings and comparative insights

---

## 8. External API Integrations

### 8.1 Google Maps API

**Usage:**
- **Geocoding**: location name → coordinates (lat, lng)
- **Reverse geocoding**: coordinates → formatted address + country
- Location resolution for ambiguous queries
- Coordinate format parsing (handles degrees, N/S/E/W directional indicators)
- Validation: lat (-90 to 90), lng (-180 to 180)

**Implementation (maps_tool function):**
```python
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

# Geocoding
result = gmaps.geocode(location_query)
lat = result[0]['geometry']['location']['lat']
lng = result[0]['geometry']['location']['lng']

# Reverse geocoding
reverse_result = gmaps.reverse_geocode((lat, lng))
formatted_address = reverse_result[0]['formatted_address']

# Returns LocationContext(lat, lng, country, location, justification)
```

### 8.2 Google Generative AI API

**Agent Wrappers:**

Each domain agent wrapper calls Google Generative AI directly:
```python
import google.generativeai as genai

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')
response = await asyncio.to_thread(model.generate_content, prompt)
```

**Models Used:**
- `gemini-2.5-flash`: primary model for all agents
- `gemini-2.0-flash-exp`: alternative/experimental model
- Model selection via `GEMINI_MODEL` environment variable

**Prompt Structure:**
- System instruction from agent definition
- User query: "Analyze {domain} for data center at {lat}, {lng} in {country}"
- Language enforcement: "Provide all analysis in clear, professional English only"
- JSON output requirement: structured schema expected

**Error Handling:**
- API quota exhaustion → circuit breaker
- Timeout → retry with exponential backoff
- Invalid JSON → repair pipeline
- Model unavailable → fallback to AgentOutput with error message

---

## 9. Performance Optimization & Scalability

### 9.1 Current Performance Characteristics

**Query Response Times:**
- Database queries (list reports, compare): 50-200ms
- Single domain agent call: 5-10 seconds
- Full report generation (7 agents + insights): 30-45 seconds
- Report retrieval from database: <100ms
- Session load: <50ms

**Caching Strategy:**
- Streamlit `@st.cache_data` on `load_reports_list()` (30s TTL)
- PostgreSQL `top_scores_cache` table for rankings
- Session state for current conversation
- No caching on agent responses (always fresh analysis)

**Database Connection Handling:**
- Connection retry with progressive delays (0.5s, 1s, 2s)
- Max retries: 3 attempts
- Auto-reconnect on OperationalError or DatabaseError
- No connection pooling (single-user MVP)

### 9.2 Scalability Roadmap

**Immediate Improvements (Production Phase 1):**
- Implement connection pooling (`psycopg2.pool.ThreadedConnectionPool`)
- Add Redis cache layer for frequent queries
- Optimize JSONB queries with additional indexes
- Implement API rate limiting and quota management

**Short-Term Scaling (Multi-User Phase):**
- Containerize application (Docker)
- Deploy to cloud platform (Google Cloud Run, AWS ECS)
- Add load balancer for multiple instances
- Implement session affinity (sticky sessions)
- Database read replicas for query load distribution

**Long-Term Scaling (Enterprise Phase):**
- Kubernetes orchestration for auto-scaling
- Separate agent execution layer (worker queue)
- Implement distributed caching (Redis Cluster)
- Add CDN for static assets
- Microservices architecture: API gateway + domain agent services
- Database sharding by geographic region
- Implement GraphQL API for flexible client queries

---

## 10. Deployment Options

### 10.1 Development Environment

**Local Setup:**
```bash
# 1. Clone repository
git clone https://github.com/snaeemm/chirisa-ai.git
cd chirisa-ai

# 2. Install dependencies using uv
uv pip install -r requirements.txt

# Alternative: Create and activate virtual environment with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# 3. Configure .env file
cat > .env <<EOF
GOOGLE_MAPS_API_KEY=your_maps_key
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.5-flash
DATABASE_URL=postgresql://user:pass@host/dbname?sslmode=require
EOF

# 4. Initialize database
python -m agent.agent  # Runs init_database()

# 5. Run Streamlit
streamlit run Assistant.py

# 6. Access at http://localhost:8501
```

**Environment Variables Required:**
- `GOOGLE_MAPS_API_KEY`: Google Maps geocoding API
- `GEMINI_API_KEY`: Google AI API key
- `GEMINI_MODEL`: Model name (default: gemini-2.5-flash)
- `DATABASE_URL`: PostgreSQL connection string (Neon cloud)

### 10.2 Cloud Deployment (Streamlit Cloud)

**Recommended for MVP:**
1. Push code to GitHub
2. Connect Streamlit Cloud to repository
3. Configure secrets in Streamlit Cloud dashboard:
   - `GOOGLE_MAPS_API_KEY`
   - `GEMINI_API_KEY`
   - `DATABASE_URL`
4. Deploy from branch: `chirisa-ai-streamlit`
5. Access at: `https://your-app.streamlit.app`

**Advantages:**
- Automatic HTTPS
- Zero server management
- Automatic restarts on code push
- Built-in secret management
- Free tier available for testing

### 10.3 Production Deployment (Docker + Cloud Run)

**For Enterprise Scale:**

```dockerfile
# Dockerfile
FROM python:3.10-slim

# Install uv for faster package installation
RUN pip install uv

COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

COPY . /app
WORKDIR /app
EXPOSE 8501
CMD ["streamlit", "run", "Assistant.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

```bash
# Build and deploy
docker build -t chirisa-ai .
docker push gcr.io/project/chirisa-ai

gcloud run deploy chirisa-ai \
  --image gcr.io/project/chirisa-ai \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 0 \
  --max-instances 10
```

**Configuration:**
- Set environment variables in Cloud Run console
- Configure min/max instances (0-10 for cost optimization)
- Set memory limit (2GB recommended)
- Enable concurrency (max 80 concurrent requests)
- Configure VPC connector for database access

---

## 11. Monitoring, Logging & Error Handling

### 11.1 Current Logging

**Console Logging:**
- Agent execution: "🚀 Calling {agent_name} (attempt {n})"
- JSON parsing: "🔍 Parsing {description}...", "✅ JSON parsed successfully"
- Database operations: "✅ PostgreSQL database initialized", "📊 Report saved: {file_path}"
- Errors: "❌ {agent_name} failed: {error}", "⚠️ Database save failed: {error}"
- Performance: "⏱️ Waiting {delay}s before retry..."

**Error Handling:**
- Try-catch blocks around all agent calls
- Database connection retry logic
- JSON parsing repair pipeline
- Fallback AgentOutput for failed analyses
- User-friendly error messages in UI

### 11.2 Production Monitoring Recommendations

**Implement Structured Logging:**
- Use Python `logging` module with JSON formatter
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Include: timestamp, session_id, user_id, agent_name, execution_time
- Ship logs to: Google Cloud Logging, Datadog, or ELK stack

**Key Metrics to Track:**
- Agent execution time per domain
- Overall report generation time
- Database query latency
- API call success/failure rates
- User session duration
- Report generation requests per hour
- Cache hit/miss ratios
- Error rates by agent type

**Alerting:**
- Set up alerts for error rate > 5%
- Database connection failures
- API quota exhaustion
- Response time > 60 seconds
- Failed authentication attempts > 10 per minute

---

## 12. Testing Strategy

### 12.1 Current Testing Status

**MVP Status:**
- No automated test suite currently implemented
- Manual testing via Streamlit UI
- Agent output validation via Pydantic models
- Database schema validated on `init_database()`

**Manual Test Cases:**
- Location resolution for various formats (address, coordinates, city names)
- Report generation for known good locations
- Comparative queries ("Compare all reports", "Top 5 locations")
- Database persistence (session reload after restart)
- Authentication flow (login, logout, unauthorized access)
- Report deletion with confirmation

### 12.2 Recommended Test Suite

**Unit Tests (pytest):**
```python
# Test agent wrappers
def test_power_agent_json_parsing():
    response = mock_power_agent_response()
    result = PowerInfrastructureAgentWrapper.parse_response(response)
    assert isinstance(result, PowerInfrastructureOutput)
    assert 1.0 <= result.overall_score <= 5.0

# Test database operations
def test_save_and_retrieve_report():
    report = create_test_report()
    save_report_to_database(report)
    retrieved = get_report_by_id(report.id)
    assert retrieved['location'] == report.location

# Test JSON repair
def test_json_repair_trailing_comma():
    broken_json = '{"key": "value",}'
    repaired = repair_json_response(broken_json)
    parsed = json.loads(repaired)
    assert parsed['key'] == 'value'

# Test authentication
def test_login_with_valid_credentials():
    st.session_state.clear()
    # Simulate login
    assert check_authentication() == False
    # ... simulate form submission
    assert check_authentication() == True
```

**Integration Tests:**
- End-to-end report generation for test location
- Database save and retrieve workflow
- Multi-agent parallel execution
- Insights agent synthesis
- Session persistence across requests

**Load Tests:**
- Concurrent report generation requests
- Database query performance under load
- API rate limiting behavior
- Memory usage for long-running sessions

---

## 13. Future Enhancements & Roadmap

### 13.1 Short-Term (Next 3 Months)

**Additional Data Integrations:**
- Real-time energy price APIs (EIA, IEA)
- Subsea cable databases (TeleGeography, SubmarineCableMap)
- ESG scoring APIs (MSCI, Sustainalytics)
- BGP routing data (RIPE, ARIN)
- Weather data APIs (NOAA, OpenWeather)

**UI/UX Improvements:**
- Geospatial visualizations (maps with scored locations)
- Export reports to PDF
- Custom scoring model configuration
- Comparison views (side-by-side reports)
- Historical trend analysis

**Agent Enhancements:**
- New domain agents: Security, Compliance Monitoring
- Fine-tuned prompts based on user feedback
- Custom extraction fields (cooling water, decarb timelines)
- Multi-language support

### 13.2 Long-Term (6-12 Months)

**Enterprise Features:**
- Multi-tenant support with role-based access control
- Custom client branding (white-label)
- API access for programmatic queries
- Webhook notifications for report completion
- Scheduled report generation

**Advanced Analytics:**
- Machine learning for score prediction
- Anomaly detection in domain metrics
- Recommendation engine for optimal site selection
- What-if scenario modeling
- Cost optimization algorithms

**Platform Expansion:**
- Mobile app (iOS, Android)
- Slack/Teams integration
- Salesforce/CRM connectors
- Custom reporting templates
- Real-time collaboration features

---

## 14. Engineering Next Steps (Feedback Required)

**Priority Clarifications:**

1. **Prompt Refinement**: Which domain agents need more detailed analysis? Which are too verbose?
2. **API Integration Priority**: Which external data sources are most critical? (Energy prices, ESG data, subsea cables?)
3. **Extraction Fields**: What additional metrics should be extracted? (e.g., cooling water availability, decarbonization timelines)
4. **Deployment Preferences**: Cloud (Streamlit/Cloud Run), hybrid, or on-premise?
5. **User Scale**: Expected concurrent users? (1-10, 10-100, 100+?)
6. **Scoring Model**: Should domain weights be configurable? Custom scoring algorithms?
7. **Compliance Requirements**: Industry-specific regulations to address? (GDPR, SOC2, ISO27001?)
8. **Reporting Formats**: PDF export requirements? Custom template needs?

**Technical Debt to Address:**
- Implement comprehensive test suite (unit, integration, e2e)
- Move authentication to environment variables with password hashing
- Add API rate limiting and quota management
- Implement connection pooling for database
- Create proper error handling and logging framework
- Document API endpoints for programmatic access
- Set up CI/CD pipeline (GitHub Actions)
- Implement monitoring and alerting (Datadog, New Relic)

---

## 15. Appendix

### 15.1 Configuration Files

**config/settings.py:**
```python
APP_NAME = "shaz"
AUTH_USERNAME = "Admin"
AUTH_PASSWORD = "professional_granite_123!"
DEFAULT_MODEL = "gemini-2.0-flash-exp"
DATABASE_URL = "postgresql://..."  # Neon connection string
PAGE_CONFIG = {
    "page_title": "Ask Shahz",
    "page_icon": "💬",
    "layout": "wide"
}
```

**.env file (template):**
```
GOOGLE_MAPS_API_KEY=your_maps_api_key
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
DATABASE_URL=postgresql://user:pass@host/dbname?sslmode=require
```

### 15.2 Key File Locations

**Agent Definitions:**
- `agent/agent.py`: Orchestrator and location agent
- `agent/database_agent.py`: Database operations agent
- `agent/insights_agent.py`: Cross-domain synthesis agent
- `agent/power_agent.py`: Power infrastructure specialist
- `agent/network_agent.py`: Network connectivity specialist
- `agent/climate_agent.py`: Climate analysis specialist
- `agent/risk_agent.py`: Operational risk specialist
- `agent/esg_agent.py`: ESG/sustainability specialist
- `agent/regulatory_agent.py`: Regulatory compliance specialist
- `agent/hyperscaler_agent.py`: Hyperscaler attractiveness specialist

**Database & Models:**
- `agent/database.py`: PostgreSQL operations
- `agent/models.py`: Base Pydantic models
- `agent/domain_models.py`: Domain-specific Pydantic models
- `agent/synthesis_agents.py`: Report generation orchestration

**UI Components:**
- `Assistant.py`: Main chat interface
- `pages/Reports.py`: Report viewer page
- `ui/auth.py`: Authentication module
- `ui/sidebar.py`: Session and report navigation
- `ui/chat_display.py`: Message rendering
- `ui/chat_input.py`: User input handling
- `ui/report_viewer.py`: Detailed report display

**Services:**
- `services/agent_service.py`: ADK runner initialization
- `services/session_service.py`: Session management
- `services/title_generator.py`: Chat title generation

### 15.3 Dependencies

**Package Manager:**
- `uv`: Fast Python package installer (used instead of pip)
  - Install uv: `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Faster dependency resolution and installation
  - Compatible with pip requirements.txt format

**Core Dependencies (from requirements.txt):**
- `streamlit`: Web framework
- `google-generativeai`: Gemini AI API client
- `google-adk`: Agent Development Kit
- `psycopg2-binary`: PostgreSQL driver
- `pydantic`: Data validation
- `python-dotenv`: Environment variable management
- `googlemaps`: Google Maps API client

**Additional Libraries:**
- `asyncio`: Async execution (built-in)
- `json`: JSON parsing (built-in)
- `datetime`: Date/time handling (built-in)
- `pathlib`: File path operations (built-in)

### 15.4 Contact & Support

**Repository**: https://github.com/snaeemm/chirisa-ai
**Branch**: chirisa-ai-streamlit
**Documentation**: This document + inline code comments
**Issues**: GitHub Issues for bug reports and feature requests

---

**End of Technical Documentation**
