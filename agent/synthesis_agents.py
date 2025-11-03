# synthesis_agents.py - Synthesis and Report Orchestration

import os
import asyncio
from dotenv import load_dotenv
from google.adk.tools import FunctionTool
from .models import ReportSchema, LocationContext, AgentOutput
from .database import save_report_to_database
from .domain_models import (
    PowerInfrastructureOutput, NetworkConnectivityOutput, ClimateAnalysisOutput,
    ESGSustainabilityOutput, OperationalRiskOutput, RegulatoryComplianceOutput
)
from .utility import save_report_schema

# Load environment variables from .env file
load_dotenv(override=True)

# Configuration
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

# --------------------------------------------------------------------------------
# Simplified Response Handling - Agents now output structured JSON directly
# --------------------------------------------------------------------------------

def clean_agent_response(response_text: str) -> str:
    """Remove markdown code block wrapper from agent response and ensure English text"""
    import re

    cleaned = response_text.strip()

    # Remove ```json from start (case insensitive)
    if cleaned.lower().startswith('```json'):
        cleaned = cleaned[7:]  # Remove '```json'
    elif cleaned.startswith('```'):
        cleaned = cleaned[3:]   # Remove '```' only

    # Remove ``` from end
    if cleaned.endswith('```'):
        cleaned = cleaned[:-3]

    # Clean and ensure proper encoding
    cleaned = cleaned.strip()

    # Remove any non-printable characters that could cause black boxes
    cleaned = re.sub(r'[^\x20-\x7E\n\r\t]', '', cleaned)

    # Ensure proper UTF-8 encoding
    try:
        cleaned = cleaned.encode('utf-8', errors='ignore').decode('utf-8')
    except Exception:
        pass

    return cleaned

def repair_json_response(json_text: str) -> str:
    """Attempt to repair common JSON formatting issues"""
    import re

    # Remove any text before the first {
    start_idx = json_text.find('{')
    if start_idx > 0:
        json_text = json_text[start_idx:]

    # Remove any text after the last }
    end_idx = json_text.rfind('}')
    if end_idx >= 0:
        json_text = json_text[:end_idx + 1]

    # Fix invalid escape sequences (e.g., \$ -> \\$)
    json_text = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', json_text)

    # Fix common issues
    # Remove trailing commas before } or ]
    json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)

    # Fix missing commas between fields - look for patterns like }" or ]" followed by "
    # This handles cases where closing brace/bracket of nested object/array is immediately followed by a new field
    json_text = re.sub(r'(\}|\])\s*(")', r'\1,\2', json_text)

    # Fix missing commas between string values and next property
    # Pattern: "value" followed by whitespace and then "key":
    json_text = re.sub(r'("\s*)\s+("[\w_]+"\s*:)', r'\1,\2', json_text)

    # Fix single quotes to double quotes (comprehensive)
    # Replace single quotes with double quotes for keys
    json_text = re.sub(r"'([^']*)':", r'"\1":', json_text)

    # Replace single quotes with double quotes for string values
    json_text = re.sub(r"'([^']*?)'", r'"\1"', json_text)

    # Fix arrays with single quoted strings
    json_text = re.sub(r"\['([^']*?)'", r'["\1"', json_text)
    json_text = re.sub(r"'([^']*?)'\]", r'"\1"]', json_text)

    # Ensure strings are properly quoted
    json_text = re.sub(r':\s*([^",{\[\s][^,}\]]*?)(?=\s*[,}\]])', r': "\1"', json_text)

    return json_text

def extract_grounding_sources(response) -> list:
    """Extract grounding sources (web search results) from Gemini API response"""
    grounding_sources = []
    try:
        print(f"🔍 DEBUG: Extracting grounding sources...")
        print(f"🔍 DEBUG: Response type: {type(response)}")
        print(f"🔍 DEBUG: Has candidates: {hasattr(response, 'candidates')}")

        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            print(f"🔍 DEBUG: Has grounding_metadata: {hasattr(candidate, 'grounding_metadata')}")

            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                grounding_metadata = candidate.grounding_metadata
                print(f"🔍 DEBUG: Grounding metadata type: {type(grounding_metadata)}")
                print(f"🔍 DEBUG: Has grounding_chunks: {hasattr(grounding_metadata, 'grounding_chunks')}")
                print(f"🔍 DEBUG: Grounding metadata attributes: {dir(grounding_metadata)}")

                # Check if grounding_chunks exists and has items
                chunks = getattr(grounding_metadata, 'grounding_chunks', None)
                print(f"🔍 DEBUG: grounding_chunks value: {chunks}")
                print(f"🔍 DEBUG: grounding_chunks type: {type(chunks) if chunks is not None else 'None'}")
                print(f"🔍 DEBUG: grounding_chunks length: {len(chunks) if chunks else 0}")

                if hasattr(grounding_metadata, 'grounding_chunks') and grounding_metadata.grounding_chunks:
                    print(f"🔍 DEBUG: Number of grounding chunks: {len(grounding_metadata.grounding_chunks)}")
                    for i, chunk in enumerate(grounding_metadata.grounding_chunks):
                        print(f"🔍 DEBUG: Chunk {i}: has web attr = {hasattr(chunk, 'web')}")
                        if hasattr(chunk, 'web') and chunk.web:
                            # Ensure all fields are strings, never None
                            url = chunk.web.uri if hasattr(chunk.web, 'uri') and chunk.web.uri else ""
                            title = chunk.web.title if hasattr(chunk.web, 'title') and chunk.web.title else "Web Source"

                            source = {
                                "url": str(url) if url else "",
                                "title": str(title) if title else "Web Source",
                                "date": "",  # Not typically provided by search grounding
                                "snippet": ""  # Not typically provided directly
                            }
                            if source["url"]:  # Only add if we have a URL
                                grounding_sources.append(source)
                                print(f"✅ Added source: {source['title'][:50]}...")
                else:
                    print(f"⚠️ No grounding_chunks in metadata (empty or None)")

                    # Check for alternative grounding fields
                    if hasattr(grounding_metadata, 'search_entry_point'):
                        print(f"🔍 DEBUG: Found search_entry_point: {grounding_metadata.search_entry_point}")
                    if hasattr(grounding_metadata, 'grounding_supports'):
                        print(f"🔍 DEBUG: Found grounding_supports: {grounding_metadata.grounding_supports}")
                    if hasattr(grounding_metadata, 'web_search_queries'):
                        print(f"🔍 DEBUG: Found web_search_queries: {grounding_metadata.web_search_queries}")
            else:
                print(f"⚠️ No grounding_metadata in candidate")
        else:
            print(f"⚠️ No candidates in response")

    except Exception as e:
        print(f"❌ ERROR extracting grounding metadata: {e}")
        import traceback
        print(f"📄 Traceback: {traceback.format_exc()}")

    print(f"✅ Extracted {len(grounding_sources)} grounding sources total")
    return grounding_sources

def sanitize_sources(sources: list) -> list:
    """Sanitize sources list to ensure all fields are valid strings"""
    if not isinstance(sources, list):
        return []

    sanitized = []
    for source in sources:
        if isinstance(source, dict):
            # Ensure all required fields are present and are strings (not None)
            sanitized_source = {
                "url": str(source.get("url", "")) if source.get("url") is not None else "",
                "title": str(source.get("title", "Unknown Source")) if source.get("title") is not None else "Unknown Source",
                "date": str(source.get("date", "")) if source.get("date") is not None else "",
                "snippet": str(source.get("snippet", "")) if source.get("snippet") is not None else ""
            }
            # Only add if we have at least a URL
            if sanitized_source["url"]:
                sanitized.append(sanitized_source)
        elif isinstance(source, str):
            # If source is just a string, create a minimal source object
            sanitized.append({
                "url": "",
                "title": str(source),
                "date": "",
                "snippet": ""
            })

    return sanitized

def sanitize_metrics_data(data: dict) -> dict:
    """Sanitize metrics data to ensure all percentages and numerical values are valid numbers"""
    import re

    def clean_number_string(value):
        """Convert string representations to numbers, handling special cases"""
        if isinstance(value, (int, float)):
            return value

        if isinstance(value, str):
            # Remove any non-numeric characters except decimal point, minus sign, and digits
            cleaned = re.sub(r'[^\d.\-]', '', value.strip())

            # If we have an empty string after cleaning, return 0
            if not cleaned or cleaned == '-':
                return 0

            try:
                # Try to parse as float first, then convert to int if it's a whole number
                num = float(cleaned)
                if num == int(num):
                    return int(num)
                return num
            except ValueError:
                return 0

        return 0

    # Recursively process the data structure
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if key in ['percentages', 'numerical_values']:
                # These should contain numeric values
                if isinstance(value, dict):
                    sanitized[key] = {k: clean_number_string(v) for k, v in value.items()}
                else:
                    sanitized[key] = value
            elif key == 'metrics' and isinstance(value, dict):
                # Recursively sanitize metrics
                sanitized[key] = sanitize_metrics_data(value)
            elif isinstance(value, dict):
                # Recursively process nested dicts
                sanitized[key] = sanitize_metrics_data(value)
            elif isinstance(value, list):
                # Process lists
                sanitized[key] = [sanitize_metrics_data(item) if isinstance(item, dict) else item for item in value]
            else:
                sanitized[key] = value
        return sanitized

    return data

def detect_json_error_type(error_message: str, response_text: str) -> str:
    """Detect specific type of JSON error for targeted retry instructions"""
    error_msg = str(error_message).lower()

    if "control character" in error_msg:
        return "control_character"
    elif "expecting" in error_msg and ("," in error_msg or "}" in error_msg or "]" in error_msg):
        return "syntax_error"
    elif "unterminated string" in error_msg:
        return "unterminated_string"
    elif "expecting property name" in error_msg:
        return "missing_quotes"
    elif "trailing comma" in error_msg:
        return "trailing_comma"
    elif len(response_text.strip()) == 0:
        return "empty_response"
    else:
        return "general_formatting"

def robust_json_parse(response_text: str, description: str = "response") -> dict:
    """Parse JSON with multiple repair attempts and detailed logging"""
    import json

    print(f"🔍 Parsing {description}...")

    # Step 1: Basic cleaning
    cleaned = clean_agent_response(response_text)
    print(f"📝 Cleaned response length: {len(cleaned)} characters")

    # Step 2: Try direct parsing
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        error_type = detect_json_error_type(str(e), cleaned)
        print(f"⚠️ Initial JSON parse failed: {e} (Type: {error_type})")
        print(f"📄 Raw response preview: {cleaned[:500]}...")

    # Step 3: Enhanced repair based on error type
    try:
        repaired = repair_json_response(cleaned)
        print(f"🔧 Attempted JSON repair...")
        return json.loads(repaired)
    except json.JSONDecodeError as e:
        print(f"❌ Repaired JSON parse failed: {e}")
        print(f"📄 Repaired preview: {repaired[:500]}...")

    # Step 4: Control character specific cleaning
    try:
        import re
        # Remove control characters more aggressively
        control_char_cleaned = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', cleaned)
        if control_char_cleaned != cleaned:
            print(f"🧹 Attempting control character removal...")
            return json.loads(control_char_cleaned)
    except json.JSONDecodeError as e:
        print(f"❌ Control character cleaning failed: {e}")

    # Step 5: Try extracting just the JSON object
    try:
        import re
        # Look for the main JSON object pattern
        json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if json_match:
            json_only = json_match.group()
            repaired_only = repair_json_response(json_only)
            return json.loads(repaired_only)
    except Exception as e:
        print(f"❌ JSON extraction failed: {e}")

    # If all else fails, raise the original error with context and error type
    original_error = json.JSONDecodeError(f"Failed to parse {description} after all repair attempts", cleaned, 0)
    original_error.error_type = error_type  # Add error type for retry logic
    raise original_error

# --------------------------------------------------------------------------------
# Agent Retry Mechanism for JSON Parsing Failures
# --------------------------------------------------------------------------------

async def call_agent_with_retry(agent_wrapper, method_name: str, lat: float, lng: float, country: str, context=None, max_retries: int = 2):
    """Intelligent retry wrapper for agent calls that handles JSON parsing failures"""
    import json

    for attempt in range(max_retries + 1):
        try:
            print(f"🚀 Calling {agent_wrapper.name} (attempt {attempt + 1}/{max_retries + 1})")

            # Call the agent method
            method = getattr(agent_wrapper, method_name)
            result = await method(lat, lng, country, context)

            # If we get here, the call was successful
            print(f"✅ {agent_wrapper.name} completed successfully on attempt {attempt + 1}")
            return result

        except json.JSONDecodeError as json_error:
            error_type = getattr(json_error, 'error_type', 'unknown')
            print(f"❌ {agent_wrapper.name} JSON parsing failed on attempt {attempt + 1}: {json_error}")
            print(f"🔍 Error type detected: {error_type}")

            # If this was the last attempt, fall back to error response
            if attempt >= max_retries:
                print(f"🛑 Max retries ({max_retries}) reached for {agent_wrapper.name}, using fallback response")
                return create_fallback_response(agent_wrapper.name, lat, lng, country, str(json_error))

            # Prepare retry with enhanced instructions based on error type
            print(f"🔄 Preparing retry {attempt + 2} for {agent_wrapper.name} with enhanced JSON instructions...")

            # Modify the agent's instruction temporarily for retry
            original_instruction = agent_wrapper.adk_agent.instruction
            enhanced_instruction = create_enhanced_json_instruction(original_instruction, error_type, attempt + 1)
            agent_wrapper.adk_agent.instruction = enhanced_instruction

            # Wait a bit before retrying (exponential backoff)
            retry_delay = 2 ** attempt  # 1s, 2s, 4s...
            print(f"⏱️ Waiting {retry_delay}s before retry...")
            await asyncio.sleep(retry_delay)

        except Exception as general_error:
            print(f"❌ {agent_wrapper.name} failed with non-JSON error on attempt {attempt + 1}: {general_error}")

            # For non-JSON errors, don't retry - return fallback immediately
            return create_fallback_response(agent_wrapper.name, lat, lng, country, str(general_error))

    # This shouldn't be reached, but just in case
    return create_fallback_response(agent_wrapper.name, lat, lng, country, "Maximum retries exceeded")

def create_enhanced_json_instruction(original_instruction: str, error_type: str, attempt: int) -> str:
    """Create enhanced instruction with specific JSON formatting guidance based on error type"""

    error_specific_guidance = {
        "control_character": """
CRITICAL JSON FORMATTING REQUIREMENTS (Retry #{attempt}):
- Remove ALL control characters, special symbols, and non-printable characters
- Use only standard ASCII characters (letters, numbers, basic punctuation)
- No smart quotes, em-dashes, or special Unicode characters
- Ensure all text is clean, readable English without formatting artifacts""",

        "syntax_error": """
CRITICAL JSON FORMATTING REQUIREMENTS (Retry #{attempt}):
- Double-check all JSON syntax: proper commas, brackets, braces
- Ensure every opening brace {{ has a closing brace }}
- Ensure every opening bracket [ has a closing bracket ]
- No trailing commas before closing braces or brackets""",

        "unterminated_string": """
CRITICAL JSON FORMATTING REQUIREMENTS (Retry #{attempt}):
- Ensure ALL string values are properly quoted with double quotes
- Escape any internal quotes with backslashes: "He said \\"Hello\\""
- Close all string values properly - no missing closing quotes""",

        "missing_quotes": """
CRITICAL JSON FORMATTING REQUIREMENTS (Retry #{attempt}):
- ALL property names must be in double quotes: "property_name"
- ALL string values must be in double quotes: "string_value"
- Use only double quotes, never single quotes in JSON""",

        "trailing_comma": """
CRITICAL JSON FORMATTING REQUIREMENTS (Retry #{attempt}):
- Remove ALL trailing commas before closing braces or brackets
- Last item in objects or arrays should NOT have a comma after it""",

        "empty_response": """
CRITICAL RESPONSE REQUIREMENTS (Retry #{attempt}):
- Provide a complete JSON response - do not return empty content
- Include all required fields according to the schema
- Ensure the response contains actual analysis data""",

        "general_formatting": """
CRITICAL JSON FORMATTING REQUIREMENTS (Retry #{attempt}):
- Response must be valid JSON format with proper structure
- Use proper JSON syntax with double quotes for strings
- Remove any markdown formatting (```json, ```)
- Ensure clean, parseable JSON structure"""
    }

    guidance = error_specific_guidance.get(error_type, error_specific_guidance["general_formatting"])
    guidance = guidance.replace("{attempt}", str(attempt))

    enhanced_instruction = f"""{original_instruction}

{guidance}

IMPORTANT: Your previous response had a JSON formatting error ({error_type}). Please provide the same high-quality analysis but ensure perfect JSON formatting. Focus on providing the same valuable insights with corrected formatting."""

    return enhanced_instruction

def create_fallback_response(agent_name: str, lat: float, lng: float, country: str, error_message: str):
    """Create a fallback AgentOutput when all retry attempts fail"""
    from .models import AgentOutput

    return AgentOutput(
        overall_score=2.5,  # Neutral score since we couldn't get real analysis
        sections={},
        assumptions=[f"Analysis generated using fallback due to technical issue: {error_message[:100]}..."],
        key_insights=[f"Data center analysis for {country} requires further investigation due to processing error"],
        executive_summary=f"Technical analysis for {lat}, {lng} in {country} encountered processing issues. Manual review recommended for comprehensive assessment."
    )

# --------------------------------------------------------------------------------
# Old-Style Agent Wrappers - Match Original Pattern Exactly
# --------------------------------------------------------------------------------

class PowerInfrastructureAgentWrapper:
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = "Power Infrastructure Agent"
        self.model = os.getenv('GEMINI_MODEL')
    async def analyze_power_infrastructure(self, lat, lng, country, context=None):
        """Match old agent signature exactly"""
        try:
            # Note: context parameter kept for compatibility but not used

            # Use the ADK agent's instruction as the prompt base (like old code)
            prompt = f"{self.adk_agent.instruction}\n\nAnalyze power infrastructure for data center at {lat}, {lng} in {country}.\n\nIMPORTANT: Provide all analysis and insights in clear, professional English only. Ensure all text is properly formatted and readable."

            # Use Google GenAI client with Search grounding
            try:
                from google.genai import Client, types
                from google.genai.types import Tool, GoogleSearch
            except ImportError as import_error:
                print(f"❌ CRITICAL: google-genai package not installed!")
                print(f"❌ Error: {import_error}")
                print(f"❌ Install with: uv add google-genai or pip install google-genai")
                raise Exception("google-genai package required for Google Search grounding. Please install: google-genai>=0.3.0") from import_error
            import os

            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception("GEMINI_API_KEY not found")

            # Create client and grounding tool
            client = Client(api_key=api_key)
            grounding_tool = Tool(google_search=GoogleSearch())

            print(f"🔍 {self.name} calling with Google Search grounding enabled")

            # Call with grounding
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[grounding_tool],
                    response_modalities=["TEXT"],
                )
            )

            # Parse JSON response from agent into PowerInfrastructureOutput
            print(f"🔍 DEBUG Power Agent Response (first 500 chars): {response.text[:500]}...")

            # Extract grounding sources from Google Search
            grounding_sources = extract_grounding_sources(response)
            if grounding_sources:
                print(f"📚 Extracted {len(grounding_sources)} grounding sources from Power Agent")

            try:
                import json
                # Clean the response to remove markdown wrapper
                cleaned_response = clean_agent_response(response.text)
                print(f"🔧 DEBUG Cleaned Response (first 100 chars): {cleaned_response[:100]}...")

                # Try to parse JSON, with repair if needed
                try:
                    response_data = json.loads(cleaned_response)
                except json.JSONDecodeError as first_error:
                    print(f"⚠️ Initial JSON parse failed, attempting repair...")
                    repaired_response = repair_json_response(cleaned_response)
                    response_data = json.loads(repaired_response)
                print(f"✅ Power Agent JSON parsed successfully")

                # Sanitize metrics data to ensure all percentages and numerical values are valid numbers
                response_data = sanitize_metrics_data(response_data)

                # Inject grounding sources and sanitize
                if grounding_sources:
                    existing_sources = response_data.get("sources", [])
                    combined_sources = (existing_sources if isinstance(existing_sources, list) else []) + grounding_sources
                    response_data["sources"] = sanitize_sources(combined_sources)
                    print(f"✅ Injected and sanitized {len(response_data['sources'])} total sources into Power Agent response")
                else:
                    # Still sanitize existing sources even if no grounding sources
                    if "sources" in response_data:
                        response_data["sources"] = sanitize_sources(response_data.get("sources", []))

                # Try to create PowerInfrastructureOutput first (new format)
                try:
                    return PowerInfrastructureOutput(**response_data)
                except Exception as pydantic_error:
                    print(f"⚠️ PowerInfrastructureOutput validation failed: {pydantic_error}")
                    # Fallback to generic AgentOutput for backward compatibility
                    return AgentOutput(**response_data)

            except json.JSONDecodeError as json_error:
                print(f"❌ Power Agent JSON parsing failed: {json_error}")
                print(f"🔍 Cleaned response: {cleaned_response[:200]}...")
                # Re-raise JSON errors for retry mechanism
                raise json_error
            except Exception as other_error:
                print(f"❌ Power Agent failed with non-JSON error: {other_error}")
                # Final fallback for non-JSON errors
                return AgentOutput(
                    overall_score=-1.0,
                    sections={},
                    assumptions=[],
                    key_insights=[f"Power analysis for {country}"],
                    executive_summary=""
                )
        except Exception as e:
            print(f"❌ Power agent failed: {e}")
            # Return AgentOutput fallback for backward compatibility
            return AgentOutput(
                overall_score=-1.0,
                sections={},
                assumptions=[],
                key_insights=[f"Power analysis failed: {str(e)}"],
                executive_summary="Power analysis unavailable"
            )

class NetworkConnectivityAgentWrapper:
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = "Network Connectivity Agent"
        self.model = os.getenv('GEMINI_MODEL')
    async def analyze_network_connectivity(self, lat, lng, country, context=None):
        """Match old agent signature exactly"""
        try:
            prompt = f"{self.adk_agent.instruction}\n\nAnalyze network connectivity for data center at {lat}, {lng} in {country}.\n\nIMPORTANT: Provide all analysis and insights in clear, professional English only. Ensure all text is properly formatted and readable."
            # Use Google GenAI client with Search grounding
            try:
                from google.genai import Client, types
                from google.genai.types import Tool, GoogleSearch
            except ImportError as import_error:
                print(f"❌ CRITICAL: google-genai package not installed!")
                print(f"❌ Error: {import_error}")
                print(f"❌ Install with: uv add google-genai or pip install google-genai")
                raise Exception("google-genai package required for Google Search grounding. Please install: google-genai>=0.3.0") from import_error
            import os

            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception("GEMINI_API_KEY not found")

            # Create client and grounding tool
            client = Client(api_key=api_key)
            grounding_tool = Tool(google_search=GoogleSearch())

            print(f"🔍 {self.name} calling with Google Search grounding enabled")

            # Call with grounding
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[grounding_tool],
                    response_modalities=["TEXT"],
                )
            )

            # Parse JSON response from agent into NetworkConnectivityOutput
            print(f"🔍 DEBUG Network Agent Response (first 500 chars): {response.text[:500]}...")

            # Extract grounding sources from Google Search
            grounding_sources = extract_grounding_sources(response)
            if grounding_sources:
                print(f"📚 Extracted {len(grounding_sources)} grounding sources from Network Agent")

            try:
                import json
                # Clean the response to remove markdown wrapper
                cleaned_response = clean_agent_response(response.text)
                print(f"🔧 DEBUG Cleaned Response (first 100 chars): {cleaned_response[:100]}...")

                # Try to parse JSON, with repair if needed
                try:
                    response_data = json.loads(cleaned_response)
                except json.JSONDecodeError as first_error:
                    print(f"⚠️ Initial JSON parse failed, attempting repair...")
                    repaired_response = repair_json_response(cleaned_response)
                    response_data = json.loads(repaired_response)
                print(f"✅ Network Agent JSON parsed successfully")

                # Sanitize metrics data to ensure all percentages and numerical values are valid numbers
                response_data = sanitize_metrics_data(response_data)

                # Inject grounding sources and sanitize
                if grounding_sources:
                    existing_sources = response_data.get("sources", [])
                    combined_sources = (existing_sources if isinstance(existing_sources, list) else []) + grounding_sources
                    response_data["sources"] = sanitize_sources(combined_sources)
                    print(f"✅ Injected and sanitized {len(response_data['sources'])} total sources into Network Agent response")
                else:
                    # Still sanitize existing sources even if no grounding sources
                    if "sources" in response_data:
                        response_data["sources"] = sanitize_sources(response_data.get("sources", []))

                # Try to create NetworkConnectivityOutput first (new format)
                try:
                    return NetworkConnectivityOutput(**response_data)
                except Exception as pydantic_error:
                    print(f"⚠️ NetworkConnectivityOutput validation failed: {pydantic_error}")
                    # Fallback to generic AgentOutput for backward compatibility
                    return AgentOutput(**response_data)

            except json.JSONDecodeError as json_error:
                print(f"❌ Network Agent JSON parsing failed: {json_error}")
                print(f"🔍 Cleaned response: {cleaned_response[:200]}...")
                # Re-raise JSON errors for retry mechanism
                raise json_error
            except Exception as other_error:
                print(f"❌ Network Agent failed with non-JSON error: {other_error}")
                # Final fallback for non-JSON errors
                return AgentOutput(
                    overall_score=-1.0,
                    sections={},
                    assumptions=[],
                    key_insights=[f"Network analysis for {country}"],
                    executive_summary=""
                )
        except Exception as e:
            print(f"❌ Network agent failed: {e}")
            return AgentOutput(
                overall_score=-1.0,
                sections={},
                assumptions=[],
                key_insights=[f"Network analysis failed: {str(e)}"],
                executive_summary="Network analysis unavailable"
            )

class ClimateSuitabilityAgentWrapper:
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = "Climate Suitability Agent"
        self.model = os.getenv('GEMINI_MODEL')

    async def analyze_climate_suitability(self, lat, lng, country, context=None):
        """Match old agent signature exactly"""
        try:
            prompt = f"{self.adk_agent.instruction}\n\nAnalyze climate suitability for data center at {lat}, {lng} in {country}.\n\nIMPORTANT: Provide all analysis and insights in clear, professional English only. Ensure all text is properly formatted and readable."
            # Use Google GenAI client with Search grounding
            try:
                from google.genai import Client, types
                from google.genai.types import Tool, GoogleSearch
            except ImportError as import_error:
                print(f"❌ CRITICAL: google-genai package not installed!")
                print(f"❌ Error: {import_error}")
                print(f"❌ Install with: uv add google-genai or pip install google-genai")
                raise Exception("google-genai package required for Google Search grounding. Please install: google-genai>=0.3.0") from import_error
            import os

            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception("GEMINI_API_KEY not found")

            # Create client and grounding tool
            client = Client(api_key=api_key)
            grounding_tool = Tool(google_search=GoogleSearch())

            print(f"🔍 {self.name} calling with Google Search grounding enabled")

            # Call with grounding
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[grounding_tool],
                    response_modalities=["TEXT"],
                )
            )

            # Parse JSON response from agent into ClimateAnalysisOutput

            # Extract grounding sources from Google Search
            grounding_sources = extract_grounding_sources(response)
            if grounding_sources:
                print(f"📚 Extracted {len(grounding_sources)} grounding sources from Climate Suitability Agent")

            try:
                import json
                # Clean the response to remove markdown wrapper
                cleaned_response = clean_agent_response(response.text)
                response_data = json.loads(cleaned_response)
                print(f"✅ Climate Agent JSON parsed successfully")

                # Sanitize metrics data to ensure all percentages and numerical values are valid numbers
                response_data = sanitize_metrics_data(response_data)

                # Inject grounding sources and sanitize
                if grounding_sources:
                    existing_sources = response_data.get("sources", [])
                    combined_sources = (existing_sources if isinstance(existing_sources, list) else []) + grounding_sources
                    response_data["sources"] = sanitize_sources(combined_sources)
                    print(f"✅ Injected and sanitized {len(response_data['sources'])} total sources into Climate Suitability Agent response")
                else:
                    # Still sanitize existing sources even if no grounding sources
                    if "sources" in response_data:
                        response_data["sources"] = sanitize_sources(response_data.get("sources", []))

                # Try to create ClimateAnalysisOutput first (new format)
                try:
                    return ClimateAnalysisOutput(**response_data)
                except Exception as pydantic_error:
                    print(f"⚠️ ClimateAnalysisOutput validation failed: {pydantic_error}")
                    # Fallback to generic AgentOutput for backward compatibility
                    return AgentOutput(**response_data)

            except json.JSONDecodeError as json_error:
                print(f"❌ Climate Agent JSON parsing failed: {json_error}")
                # Re-raise JSON errors for retry mechanism
                raise json_error
            except Exception as other_error:
                print(f"❌ Climate Agent failed with non-JSON error: {other_error}")
                # Final fallback for non-JSON errors
                return AgentOutput(
                    overall_score=-1.0,
                    sections={},
                    assumptions=[],
                    key_insights=[f"Climate analysis for {country}"],
                    executive_summary=""
                )
        except Exception as e:
            print(f"❌ Climate agent failed: {e}")
            # Return AgentOutput fallback for backward compatibility
            return AgentOutput(
                overall_score=-1.0,
                sections={},
                assumptions=[],
                key_insights=[f"Climate analysis failed: {str(e)}"],
                executive_summary="Climate analysis unavailable"
            )

class OperationalRiskAgentWrapper:
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = "Operational Risk Agent"
        self.model = os.getenv('GEMINI_MODEL')

    async def analyze_operational_risk(self, lat, lng, country, context=None):
        """Match old agent signature exactly"""
        try:
            prompt = f"{self.adk_agent.instruction}\n\nAnalyze operational risk for data center at {lat}, {lng} in {country}.\n\nIMPORTANT: Provide all analysis and insights in clear, professional English only. Ensure all text is properly formatted and readable."
            # Use Google GenAI client with Search grounding
            try:
                from google.genai import Client, types
                from google.genai.types import Tool, GoogleSearch
            except ImportError as import_error:
                print(f"❌ CRITICAL: google-genai package not installed!")
                print(f"❌ Error: {import_error}")
                print(f"❌ Install with: uv add google-genai or pip install google-genai")
                raise Exception("google-genai package required for Google Search grounding. Please install: google-genai>=0.3.0") from import_error
            import os

            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception("GEMINI_API_KEY not found")

            # Create client and grounding tool
            client = Client(api_key=api_key)
            grounding_tool = Tool(google_search=GoogleSearch())

            print(f"🔍 {self.name} calling with Google Search grounding enabled")

            # Call with grounding
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[grounding_tool],
                    response_modalities=["TEXT"],
                )
            )

            # Parse JSON response from agent into OperationalRiskOutput

            # Extract grounding sources from Google Search
            grounding_sources = extract_grounding_sources(response)
            if grounding_sources:
                print(f"📚 Extracted {len(grounding_sources)} grounding sources from Operational Risk Agent")

            try:
                import json
                # Clean the response to remove markdown wrapper
                cleaned_response = clean_agent_response(response.text)
                response_data = json.loads(cleaned_response)
                print(f"✅ Risk Agent JSON parsed successfully")

                # Sanitize metrics data to ensure all percentages and numerical values are valid numbers
                response_data = sanitize_metrics_data(response_data)

                # Inject grounding sources and sanitize
                if grounding_sources:
                    existing_sources = response_data.get("sources", [])
                    combined_sources = (existing_sources if isinstance(existing_sources, list) else []) + grounding_sources
                    response_data["sources"] = sanitize_sources(combined_sources)
                    print(f"✅ Injected and sanitized {len(response_data['sources'])} total sources into Operational Risk Agent response")
                else:
                    # Still sanitize existing sources even if no grounding sources
                    if "sources" in response_data:
                        response_data["sources"] = sanitize_sources(response_data.get("sources", []))

                # Try to create OperationalRiskOutput first (new format)
                try:
                    return OperationalRiskOutput(**response_data)
                except Exception as pydantic_error:
                    print(f"⚠️ OperationalRiskOutput validation failed: {pydantic_error}")
                    # Fallback to generic AgentOutput for backward compatibility
                    return AgentOutput(**response_data)

            except json.JSONDecodeError as json_error:
                print(f"❌ Risk Agent JSON parsing failed: {json_error}")
                # Re-raise JSON errors for retry mechanism
                raise json_error
            except Exception as other_error:
                print(f"❌ Risk Agent failed with non-JSON error: {other_error}")
                # Final fallback for non-JSON errors
                return AgentOutput(
                    overall_score=-1.0,
                    sections={},
                    assumptions=[],
                    key_insights=[f"Risk analysis for {country}"],
                    executive_summary=""
                )
        except Exception as e:
            print(f"❌ Risk agent failed: {e}")
            return AgentOutput(
                overall_score=-1.0,
                sections={},
                assumptions=[],
                key_insights=[f"Risk analysis failed: {str(e)}"],
                executive_summary="Risk analysis unavailable"
            )

class SustainabilityESGAgentWrapper:
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = "Sustainability ESG Agent"
        self.model = os.getenv('GEMINI_MODEL')

    async def analyze_sustainability_esg(self, lat, lng, country, context=None):
        """Match old agent signature exactly"""
        try:
            prompt = f"{self.adk_agent.instruction}\n\nAnalyze sustainability ESG for data center at {lat}, {lng} in {country}.\n\nIMPORTANT: Provide all analysis and insights in clear, professional English only. Ensure all text is properly formatted and readable."
            # Use Google GenAI client with Search grounding
            try:
                from google.genai import Client, types
                from google.genai.types import Tool, GoogleSearch
            except ImportError as import_error:
                print(f"❌ CRITICAL: google-genai package not installed!")
                print(f"❌ Error: {import_error}")
                print(f"❌ Install with: uv add google-genai or pip install google-genai")
                raise Exception("google-genai package required for Google Search grounding. Please install: google-genai>=0.3.0") from import_error
            import os

            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception("GEMINI_API_KEY not found")

            # Create client and grounding tool
            client = Client(api_key=api_key)
            grounding_tool = Tool(google_search=GoogleSearch())

            print(f"🔍 {self.name} calling with Google Search grounding enabled")

            # Call with grounding
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[grounding_tool],
                    response_modalities=["TEXT"],
                )
            )

            # Parse JSON response from agent into ESGSustainabilityOutput

            # Extract grounding sources from Google Search
            grounding_sources = extract_grounding_sources(response)
            if grounding_sources:
                print(f"📚 Extracted {len(grounding_sources)} grounding sources from Sustainability ESG Agent")

            try:
                import json
                # Clean the response to remove markdown wrapper
                cleaned_response = clean_agent_response(response.text)
                response_data = json.loads(cleaned_response)
                print(f"✅ ESG Agent JSON parsed successfully")

                # Sanitize metrics data to ensure all percentages and numerical values are valid numbers
                response_data = sanitize_metrics_data(response_data)

                # Inject grounding sources and sanitize
                if grounding_sources:
                    existing_sources = response_data.get("sources", [])
                    combined_sources = (existing_sources if isinstance(existing_sources, list) else []) + grounding_sources
                    response_data["sources"] = sanitize_sources(combined_sources)
                    print(f"✅ Injected and sanitized {len(response_data['sources'])} total sources into Sustainability ESG Agent response")
                else:
                    # Still sanitize existing sources even if no grounding sources
                    if "sources" in response_data:
                        response_data["sources"] = sanitize_sources(response_data.get("sources", []))

                # Try to create ESGSustainabilityOutput first (new format)
                try:
                    return ESGSustainabilityOutput(**response_data)
                except Exception as pydantic_error:
                    print(f"⚠️ ESGSustainabilityOutput validation failed: {pydantic_error}")
                    # Fallback to generic AgentOutput for backward compatibility
                    return AgentOutput(**response_data)

            except json.JSONDecodeError as json_error:
                print(f"❌ ESG Agent JSON parsing failed: {json_error}")
                # Re-raise JSON errors for retry mechanism
                raise json_error
            except Exception as other_error:
                print(f"❌ ESG Agent failed with non-JSON error: {other_error}")
                # Final fallback for non-JSON errors
                return AgentOutput(
                    overall_score=-1.0,
                    sections={},
                    assumptions=[],
                    key_insights=[f"ESG analysis for {country}"],
                    executive_summary=""
                )
        except Exception as e:
            print(f"❌ ESG agent failed: {e}")
            return AgentOutput(
                overall_score=-1.0,
                sections={},
                assumptions=[],
                key_insights=[f"ESG analysis failed: {str(e)}"],
                executive_summary="ESG analysis unavailable"
            )

class RegulatoryComplianceAgentWrapper:
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = "Regulatory Compliance Agent"
        self.model = os.getenv('GEMINI_MODEL')

    async def analyze_regulatory_compliance(self, lat, lng, country, context=None):
        """Match old agent signature exactly"""
        try:
            prompt = f"{self.adk_agent.instruction}\n\nAnalyze regulatory compliance for data center at {lat}, {lng} in {country}.\n\nIMPORTANT: Provide all analysis and insights in clear, professional English only. Ensure all text is properly formatted and readable."
            # Use Google GenAI client with Search grounding
            try:
                from google.genai import Client, types
                from google.genai.types import Tool, GoogleSearch
            except ImportError as import_error:
                print(f"❌ CRITICAL: google-genai package not installed!")
                print(f"❌ Error: {import_error}")
                print(f"❌ Install with: uv add google-genai or pip install google-genai")
                raise Exception("google-genai package required for Google Search grounding. Please install: google-genai>=0.3.0") from import_error
            import os

            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception("GEMINI_API_KEY not found")

            # Create client and grounding tool
            client = Client(api_key=api_key)
            grounding_tool = Tool(google_search=GoogleSearch())

            print(f"🔍 {self.name} calling with Google Search grounding enabled")

            # Call with grounding
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[grounding_tool],
                    response_modalities=["TEXT"],
                )
            )

            # Parse JSON response from agent into RegulatoryComplianceOutput
            print(f"🔍 DEBUG Regulatory Agent Response (first 500 chars): {response.text[:500]}...")

            # Extract grounding sources from Google Search
            grounding_sources = extract_grounding_sources(response)
            if grounding_sources:
                print(f"📚 Extracted {len(grounding_sources)} grounding sources from Regulatory Agent")

            try:
                import json
                # Clean the response to remove markdown wrapper
                cleaned_response = clean_agent_response(response.text)
                print(f"🔧 DEBUG Cleaned Response (first 100 chars): {cleaned_response[:100]}...")

                # Try to parse JSON, with repair if needed
                try:
                    response_data = json.loads(cleaned_response)
                except json.JSONDecodeError as first_error:
                    print(f"⚠️ Initial JSON parse failed, attempting repair...")
                    repaired_response = repair_json_response(cleaned_response)
                    response_data = json.loads(repaired_response)
                print(f"✅ Regulatory Agent JSON parsed successfully")

                # Sanitize metrics data to ensure all percentages and numerical values are valid numbers
                response_data = sanitize_metrics_data(response_data)

                # Inject grounding sources and sanitize
                if grounding_sources:
                    existing_sources = response_data.get("sources", [])
                    combined_sources = (existing_sources if isinstance(existing_sources, list) else []) + grounding_sources
                    response_data["sources"] = sanitize_sources(combined_sources)
                    print(f"✅ Injected and sanitized {len(response_data['sources'])} total sources into Regulatory Agent response")
                else:
                    # Still sanitize existing sources even if no grounding sources
                    if "sources" in response_data:
                        response_data["sources"] = sanitize_sources(response_data.get("sources", []))

                # Try to create RegulatoryComplianceOutput first (new format)
                try:
                    return RegulatoryComplianceOutput(**response_data)
                except Exception as pydantic_error:
                    print(f"⚠️ RegulatoryComplianceOutput validation failed: {pydantic_error}")
                    # Fallback to generic AgentOutput for backward compatibility
                    return AgentOutput(**response_data)

            except json.JSONDecodeError as json_error:
                print(f"❌ Regulatory Agent JSON parsing failed: {json_error}")
                # Re-raise JSON errors for retry mechanism
                raise json_error
            except Exception as other_error:
                print(f"❌ Regulatory Agent failed with non-JSON error: {other_error}")
                # Final fallback for non-JSON errors
                return AgentOutput(
                    overall_score=-1.0,
                    sections={},
                    assumptions=[],
                    key_insights=[f"Regulatory analysis for {country}"],
                    executive_summary=""
                )
        except Exception as e:
            print(f"❌ Regulatory agent failed: {e}")
            return AgentOutput(
                overall_score=-1.0,
                sections={},
                assumptions=[],
                key_insights=[f"Regulatory analysis failed: {str(e)}"],
                executive_summary="Regulatory analysis unavailable"
            )

class HyperscalerAttractivenessAgentWrapper:
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = "Hyperscaler Attractiveness Agent"
        self.model = os.getenv('GEMINI_MODEL')

    async def analyze_hyperscaler_attractiveness(self, lat, lng, country, context=None):
        """Match old agent signature exactly"""
        try:
            prompt = f"{self.adk_agent.instruction}\n\nAnalyze hyperscaler attractiveness for data center at {lat}, {lng} in {country}.\n\nIMPORTANT: Provide all analysis and insights in clear, professional English only. Ensure all text is properly formatted and readable."
            # Use Google GenAI client with Search grounding
            try:
                from google.genai import Client, types
                from google.genai.types import Tool, GoogleSearch
            except ImportError as import_error:
                print(f"❌ CRITICAL: google-genai package not installed!")
                print(f"❌ Error: {import_error}")
                print(f"❌ Install with: uv add google-genai or pip install google-genai")
                raise Exception("google-genai package required for Google Search grounding. Please install: google-genai>=0.3.0") from import_error
            import os

            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception("GEMINI_API_KEY not found")

            # Create client and grounding tool
            client = Client(api_key=api_key)
            grounding_tool = Tool(google_search=GoogleSearch())

            print(f"🔍 {self.name} calling with Google Search grounding enabled")

            # Call with grounding
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[grounding_tool],
                    response_modalities=["TEXT"],
                )
            )

            # Parse JSON response from agent into HyperscalerAttractivenessOutput

            # Extract grounding sources from Google Search
            grounding_sources = extract_grounding_sources(response)
            if grounding_sources:
                print(f"📚 Extracted {len(grounding_sources)} grounding sources from Hyperscaler Attractiveness Agent")

            try:
                import json
                # Clean the response to remove markdown wrapper
                cleaned_response = clean_agent_response(response.text)
                response_data = json.loads(cleaned_response)
                print(f"✅ Hyperscaler Agent JSON parsed successfully")

                # Sanitize metrics data to ensure all percentages and numerical values are valid numbers
                response_data = sanitize_metrics_data(response_data)

                # Inject grounding sources and sanitize
                if grounding_sources:
                    existing_sources = response_data.get("sources", [])
                    combined_sources = (existing_sources if isinstance(existing_sources, list) else []) + grounding_sources
                    response_data["sources"] = sanitize_sources(combined_sources)
                    print(f"✅ Injected and sanitized {len(response_data['sources'])} total sources into Hyperscaler Attractiveness Agent response")
                else:
                    # Still sanitize existing sources even if no grounding sources
                    if "sources" in response_data:
                        response_data["sources"] = sanitize_sources(response_data.get("sources", []))

                # Try to create HyperscalerAttractivenessOutput first (new format)
                try:
                    from .domain_models import HyperscalerAttractivenessOutput
                    return HyperscalerAttractivenessOutput(**response_data)
                except Exception as pydantic_error:
                    print(f"⚠️ HyperscalerAttractivenessOutput validation failed: {pydantic_error}")
                    # Fallback to generic AgentOutput for backward compatibility
                    return AgentOutput(**response_data)

            except json.JSONDecodeError as json_error:
                print(f"❌ Hyperscaler Agent JSON parsing failed: {json_error}")
                # Re-raise JSON errors for retry mechanism
                raise json_error
            except Exception as other_error:
                print(f"❌ Hyperscaler Agent failed with non-JSON error: {other_error}")
                # Final fallback for non-JSON errors
                return AgentOutput(
                    overall_score=-1.0,
                    sections={},
                    assumptions=[],
                    key_insights=[f"Hyperscaler analysis for {country}"],
                    executive_summary=""
                )
        except Exception as e:
            print(f"❌ Hyperscaler agent failed: {e}")
            return AgentOutput(
                overall_score=-1.0,
                sections={},
                assumptions=[],
                key_insights=[f"Hyperscaler analysis failed: {str(e)}"],
                executive_summary="Hyperscaler analysis unavailable"
            )

# --------------------------------------------------------------------------------
# Custom Parallel Analysis Function
# Run all domain agents in parallel with deterministic output control
# --------------------------------------------------------------------------------
async def generate_datacenter_report(location_context: LocationContext) -> str:
    """Generate comprehensive data center site analysis report with executive insights.

    Executes parallel analysis across all domains (Power, Network, Climate, Risk, ESG, Regulatory),
    creates structured report with executive summary, and returns business-focused insights.
    """

    try:
        # Handle dict input from ADK framework (convert to LocationContext)
        if isinstance(location_context, dict):
            location_context = LocationContext(**location_context)

        print(f"🚀 Starting parallel analysis for {location_context.location}")

        # Import agents locally to avoid circular imports
        from .power_agent import power_agent
        from .network_agent import network_agent
        from .climate_agent import climate_agent
        from .risk_agent import risk_agent
        from .esg_agent import esg_agent
        from .regulatory_agent import regulatory_agent
        from .hyperscaler_agent import hyperscaler_agent

        # Step 1: Create wrapped agents matching old pattern
        agents = {
            "power": PowerInfrastructureAgentWrapper(power_agent),
            "network": NetworkConnectivityAgentWrapper(network_agent),
            "climate": ClimateSuitabilityAgentWrapper(climate_agent),
            "risk": OperationalRiskAgentWrapper(risk_agent),
            "esg": SustainabilityESGAgentWrapper(esg_agent),
            "regulatory": RegulatoryComplianceAgentWrapper(regulatory_agent),
            "hyperscaler": HyperscalerAttractivenessAgentWrapper(hyperscaler_agent),
        }

        # Extract coordinates for old interface
        lat, lng, country = location_context.lat, location_context.lng, location_context.country

        # Step 2: Run all agents in parallel with intelligent retry mechanism
        print(f"🚀 Starting parallel analysis with retry protection for {location_context.location}")
        shared_context = {}  # Basic context dict like old code

        agent_tasks = {
            "power": call_agent_with_retry(agents["power"], "analyze_power_infrastructure", lat, lng, country, shared_context),
            "network": call_agent_with_retry(agents["network"], "analyze_network_connectivity", lat, lng, country, shared_context),
            "climate": call_agent_with_retry(agents["climate"], "analyze_climate_suitability", lat, lng, country, shared_context),
            "risk": call_agent_with_retry(agents["risk"], "analyze_operational_risk", lat, lng, country, shared_context),
            "esg": call_agent_with_retry(agents["esg"], "analyze_sustainability_esg", lat, lng, country, shared_context),
            "regulatory": call_agent_with_retry(agents["regulatory"], "analyze_regulatory_compliance", lat, lng, country, shared_context),
            "hyperscaler": call_agent_with_retry(agents["hyperscaler"], "analyze_hyperscaler_attractiveness", lat, lng, country, shared_context)
        }

        results = await asyncio.gather(*agent_tasks.values(), return_exceptions=True)
        agent_results = dict(zip(agent_tasks.keys(), results))

        # Process results - convert old format to AgentOutput for compatibility
        processed_results = {}
        for key, result in agent_results.items():
            result_key = f"{key}_result"  # Convert "power" to "power_result"
            try:
                if isinstance(result, Exception):
                    print(f"❌ {key} failed: {str(result)}")
                    processed_results[result_key] = AgentOutput(
                        score=1.0,
                        insights=[f"Analysis failed: {str(result)}"],
                        detailed_analysis=f"Agent execution failed: {str(result)}",
                        summary=f"Could not complete {key} analysis due to error."
                    )
                else:
                    # Convert old dict format to AgentOutput
                    if isinstance(result, dict):
                        processed_results[result_key] = AgentOutput(**result)
                    else:
                        processed_results[result_key] = result
                    print(f"✅ {result_key} completed - Score: {processed_results[result_key].overall_score}")
            except Exception as e:
                print(f"❌ Error processing {key} result: {str(e)}")
                processed_results[result_key] = AgentOutput(
                    overall_score=-1.0,
                    sections={},
                    assumptions=[],
                    key_insights=[f"Result processing failed: {str(e)}"],
                    executive_summary=f"Failed to process {key} analysis result."
                )

        agent_results = processed_results

        print(f"🔄 Parallel analysis completed. Generating intelligent insights...")

        # Step 2: Calculate composite score for insights agent
        scores = [
            getattr(agent_results['power_result'], 'overall_score', 1.0),
            getattr(agent_results['network_result'], 'overall_score', 1.0),
            getattr(agent_results['climate_result'], 'overall_score', 1.0),
            getattr(agent_results['risk_result'], 'overall_score', 1.0),
            getattr(agent_results['esg_result'], 'overall_score', 1.0),
            getattr(agent_results['regulatory_result'], 'overall_score', 1.0),
            getattr(agent_results.get('hyperscaler_result'), 'overall_score', 1.0) if 'hyperscaler_result' in agent_results else 1.0
        ]
        valid_scores = [s for s in scores if s > 0]
        composite_score = sum(valid_scores) / len(valid_scores) if valid_scores else 1.0

        # Step 3: Generate intelligent insights using cross-domain synthesis
        from .insights_agent import insights_agent, prepare_insights_input

        insights_input = prepare_insights_input(
            location_context=location_context,
            composite_score=composite_score,
            power_result=agent_results['power_result'],
            network_result=agent_results['network_result'],
            climate_result=agent_results['climate_result'],
            risk_result=agent_results['risk_result'],
            esg_result=agent_results['esg_result'],
            regulatory_result=agent_results['regulatory_result']
        )

        print(f"🧠 Calling insights agent for intelligent synthesis...")
        try:
            # Call insights agent using direct Gemini API (like other wrappers)
            import google.generativeai as genai
            import os
            import json

            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception("GEMINI_API_KEY not found")

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(insights_agent.model)

            # Create prompt with insights input data
            prompt = f"{insights_agent.instruction}\n\nAnalyze the following cross-domain data and provide intelligent insights:\n\n{json.dumps(insights_input.model_dump(), indent=2)}"

            print(f"📤 Sending prompt to insights agent (length: {len(prompt)} chars)")
            response = await asyncio.to_thread(model.generate_content, prompt)
            print(f"📥 Received response from insights agent (length: {len(response.text)} chars)")

            # Parse JSON response with robust error handling
            insights_data = robust_json_parse(response.text, "insights agent response")

            # Convert to InsightsOutput model
            from .models import InsightsOutput
            insights_result = InsightsOutput(**insights_data)
            print(f"✅ Insights agent completed successfully")

        except Exception as e:
            print(f"⚠️ Insights agent failed, using fallback: {e}")
            print(f"🔍 Error type: {type(e).__name__}")
            # Log more details for debugging
            if hasattr(e, 'response'):
                print(f"📄 Response that failed: {e.response[:1000]}...")
            insights_result = None

        # Step 4: Create ReportSchema with intelligent insights
        report_schema = ReportSchema.from_location_and_agents(
            location_context=location_context,
            power_result=agent_results['power_result'],
            network_result=agent_results['network_result'],
            climate_result=agent_results['climate_result'],
            risk_result=agent_results['risk_result'],
            esg_result=agent_results['esg_result'],
            regulatory_result=agent_results['regulatory_result'],
            hyperscaler_result=agent_results.get('hyperscaler_result'),  # Include hyperscaler analysis
            insights_result=insights_result  # Pass intelligent insights
        )
        print(f"✅ ReportSchema created with intelligent insights - Overall Score: {report_schema.overall_suitability.composite_score}")

        # Step 3: Direct JSON generation
        json_result = save_report_schema(report_schema)
        print(f"✅ JSON saved: {json_result.get('file_path', 'Unknown')}")

        # Step 3.5: Auto-save to database
        try:
            db_result = save_report_to_database(report_schema)
            print(f"✅ Database: {db_result}")
        except Exception as e:
            print(f"⚠️ Database save failed: {e}")

        # Step 4: Generate executive summary response
        def generate_executive_response(report: "ReportSchema") -> str:
            """Generate an executive-level response with key insights"""
            try:
                # Round the score for display
                rounded_score = round(report.overall_suitability.composite_score, 1)

                # Extract top strengths and challenges
                strengths = report.executive_summary.key_strengths[:2] if report.executive_summary.key_strengths else []
                challenges = report.executive_summary.key_challenges[:2] if report.executive_summary.key_challenges else []

                # Create response
                response = f"🏢 **Data Center Site Analysis Complete for {report.location}**\n\n"

                # Overall assessment
                response += f"📊 **Overall Suitability**: {rounded_score}/5.0 - **{report.overall_suitability.rating}**\n"
                response += f"📍 **Location**: {report.location}, {report.country}\n\n"

                # Key findings
                if strengths:
                    response += "✅ **Key Strengths**:\n"
                    for strength in strengths:
                        clean_strength = strength.split(':')[0] if ':' in strength else strength
                        response += f"  • {clean_strength}\n"
                    response += "\n"

                if challenges:
                    response += "⚠️ **Key Challenges**:\n"
                    for challenge in challenges:
                        clean_challenge = challenge.split(':')[0] if ':' in challenge else challenge
                        response += f"  • {clean_challenge}\n"
                    response += "\n"

                # Recommendation
                if report.overall_suitability.rating == "Excellent":
                    response += "🎯 **Recommendation**: Highly suitable for immediate data center development with favorable conditions across all domains.\n\n"
                elif report.overall_suitability.rating == "Good":
                    response += "🎯 **Recommendation**: Well-suited for data center development with manageable challenges and strong fundamentals.\n\n"
                elif report.overall_suitability.rating == "Moderate":
                    response += "🎯 **Recommendation**: Suitable for development with careful planning and risk mitigation strategies.\n\n"
                else:
                    response += "🎯 **Recommendation**: Consider alternative locations or extensive risk mitigation before proceeding.\n\n"

                # Phase 1 highlights
                phase1 = report.phase_1_deployment
                response += f"🚀 **Phase 1 Plan**: {phase1.recommended_capacity}\n"
                response += f"⏱️ **Timeline**: {phase1.timeline}\n"
                response += f"💰 **Investment**: {phase1.estimated_investment}\n\n"

                # Collect dynamic data gaps from all agent results
                all_data_gaps = []
                all_third_party = []
                for agent_key, agent_result in agent_results.items():
                    if hasattr(agent_result, 'data_gaps') and agent_result.data_gaps:
                        all_data_gaps.extend(agent_result.data_gaps)  # Now just strings
                    if hasattr(agent_result, 'third_party_verification') and agent_result.third_party_verification:
                        all_third_party.extend(agent_result.third_party_verification)  # Now just strings

                # Display dynamic data gaps and third-party verification
                if all_data_gaps or all_third_party:
                    response += "🔍 **Data Gaps & Third-Party Verification Required**:\n\n"

                    if all_data_gaps:
                        response += "📋 **Data Gaps Identified**:\n"
                        for gap in list(set(all_data_gaps))[:6]:  # Remove duplicates and limit
                            response += f"  • {gap}\n"
                        response += "\n"

                    if all_third_party:
                        response += "🎯 **Third-Party Services Needed**:\n"
                        for verification in list(set(all_third_party))[:6]:  # Remove duplicates and limit
                            response += f"  • {verification}\n"
                        response += "\n"

                    response += "⚠️ **Important**: This analysis is based on publicly available information. "
                    response += "Critical business decisions should include verification of the identified data gaps.\n\n"

                # Reports generated (brief mention)
                response += f"📋 **Reports Generated**: Comprehensive analysis reports have been saved for detailed review\n"
                response += f"🔍 **Domains Analyzed**: Power, Network, Climate, Risk, ESG, and Regulatory assessments"

                return response

            except Exception as e:
                print(f"⚠️ Error generating executive response: {e}")
                return f"✅ Analysis complete for {report.location} - Overall Score: {rounded_score}/5.0 ({report.overall_suitability.rating})"

        final_message = generate_executive_response(report_schema)
        return final_message

    except Exception as e:
        import traceback
        error_message = (
            f"❌ Complete analysis pipeline failed: {str(e)}\n"
            f"🔍 Traceback: {traceback.format_exc()}"
        )
        print(error_message)
        return error_message

# Use the async function directly - FunctionTool should handle async functions
datacenter_report_tool = FunctionTool(func=generate_datacenter_report)

# All wrapper functions removed - logic moved into generate_datacenter_report


