# Decompiled with PyLingual (https://pylingual.io)
# Internal filename: /home/shahzeb/projects/data-center-agentic/agent/agent/synthesis_agents.py
# Bytecode version: 3.12.0rc2 (3531)
# Source timestamp: 2025-09-26 12:45:14 UTC (1758890714)

import asyncio
import time
from google.adk.tools import FunctionTool
from .models import ReportSchema, LocationContext, AgentOutput
from .database import save_report_to_database
from .domain_models import PowerInfrastructureOutput, NetworkConnectivityOutput, ClimateAnalysisOutput, ESGSustainabilityOutput, OperationalRiskOutput, RegulatoryComplianceOutput
from .utility import save_report_schema, generate_pdf_report
GEMINI_MODEL = 'gemini-2.5-flash'

def clean_agent_response(response_text: str) -> str:
    """Remove markdown code block wrapper from agent response and ensure English text"""  # inserted
    import re
    cleaned = response_text.strip()
    if cleaned.lower().startswith('```json'):
        cleaned = cleaned[7:]
    else:  # inserted
        if cleaned.startswith('```'):
            cleaned = cleaned[3:]
    if cleaned.endswith('```'):
        cleaned = cleaned[:(-3)]
    cleaned = cleaned.strip()
    cleaned = re.sub('[^\\x20-\\x7E\\n\\r\\t]', '', cleaned)
    try:
        cleaned = cleaned.encode('utf-8', errors='ignore').decode('utf-8')
    except Exception:
        pass  # postinserted
    else:  # inserted
        return cleaned
        break

def repair_json_response(json_text: str) -> str:
    """Attempt to repair common JSON formatting issues"""  # inserted
    import re
    start_idx = json_text.find('{')
    if start_idx > 0:
        json_text = json_text[start_idx:]
    end_idx = json_text.rfind('}')
    if end_idx >= 0:
        json_text = json_text[:end_idx + 1]
    json_text = re.sub(',(\\s*[}\\]])', '\\1', json_text)
    json_text = re.sub('\'([^\']*)\':', '\"\\1\":', json_text)
    json_text = re.sub('\'([^\']*?)\'', '\"\\1\"', json_text)
    json_text = re.sub('\\[\'([^\']*?)\'', '[\"\\1\"', json_text)
    json_text = re.sub('\'([^\']*?)\'\\]', '\"\\1\"]', json_text)
    json_text = re.sub(':\\s*([^\",{\\[\\s][^,}\\]]*?)(?=\\s*[,}\\]])', ': \"\\1\"', json_text)
    return json_text

def detect_json_error_type(error_message: str, response_text: str) -> str:
    """Detect specific type of JSON error for targeted retry instructions"""  # inserted
    error_msg = str(error_message).lower()
    if 'control character' in error_msg:
        return 'control_character'
    if 'expecting' in error_msg and (',' in error_msg or '}' in error_msg or ']' in error_msg):
        return 'syntax_error'
    if 'unterminated string' in error_msg:
        return 'unterminated_string'
    if 'expecting property name' in error_msg:
        return 'missing_quotes'
    if 'trailing comma' in error_msg:
        return 'trailing_comma'
    if len(response_text.strip()) == 0:
        return 'empty_response'
    return 'general_formatting'

def robust_json_parse(response_text: str, description: str='response') -> dict:
    """Parse JSON with multiple repair attempts and detailed logging"""  # inserted
    import json
    print(f'🔍 Parsing {description}...')
    cleaned = clean_agent_response(response_text)
    print(f'📝 Cleaned response length: {len(cleaned)} characters')
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        error_type = detect_json_error_type(str(e), cleaned)
        print(f'⚠️ Initial JSON parse failed: {e} (Type: {error_type})')
        print(f'📄 Raw response preview: {cleaned[:500]}...')
    try:
        repaired = repair_json_response(cleaned)
        print('🔧 Attempted JSON repair...')
        return json.loads(repaired)
    except json.JSONDecodeError as e:
        print(f'❌ Repaired JSON parse failed: {e}')
        print(f'📄 Repaired preview: {repaired[:500]}...')
    try:
        import re
        control_char_cleaned = re.sub('[\\x00-\\x1F\\x7F-\\x9F]', '', cleaned)
        if control_char_cleaned!= cleaned:
            print('🧹 Attempting control character removal...')
            return json.loads(control_char_cleaned)
    except json.JSONDecodeError as e:
        print(f'❌ Control character cleaning failed: {e}')
    else:  # inserted
        pass
    try:
        import re
        json_match = re.search('\\{.*\\}', cleaned, re.DOTALL)
        if json_match:
            json_only = json_match.group()
            repaired_only = repair_json_response(json_only)
            return json.loads(repaired_only)
    except Exception as e:
        print(f'❌ JSON extraction failed: {e}')
    original_error = json.JSONDecodeError(f'Failed to parse {description} after all repair attempts', cleaned, 0)
    original_error.error_type = error_type
    raise original_error

async def call_agent_with_retry(agent_wrapper, method_name: str, lat: float, lng: float, country: str, context=None, max_retries: int=2):
    """Intelligent retry wrapper for agent calls that handles JSON parsing failures"""  # inserted
    import json
    for attempt in range(max_retries + 1):
        try:
            print(f'🚀 Calling {agent_wrapper.name} (attempt {attempt + 1}/{max_retries + 1})')
            method = getattr(agent_wrapper, method_name)
            result = await method(lat, lng, country, context)
        except json.JSONDecodeError as json_error:
                print(f'✅ {agent_wrapper.name} completed successfully on attempt {attempt + 1}')
                return result
    else:  # inserted
        return create_fallback_response(agent_wrapper.name, lat, lng, country, 'Maximum retries exceeded')
        error_type = getattr(json_error, 'error_type', 'unknown')
        print(f'❌ {agent_wrapper.name} JSON parsing failed on attempt {attempt + 1}: {json_error}')
        print(f'🔍 Error type detected: {error_type}')
        if attempt >= max_retries:
            print(f'🛑 Max retries ({max_retries}) reached for {agent_wrapper.name}, using fallback response')
            return create_fallback_response(agent_wrapper.name, lat, lng, country, str(json_error))
        print(f'🔄 Preparing retry {attempt + 2} for {agent_wrapper.name} with enhanced JSON instructions...')
        original_instruction = agent_wrapper.adk_agent.instruction
        enhanced_instruction = create_enhanced_json_instruction(original_instruction, error_type, attempt + 1)
        agent_wrapper.adk_agent.instruction = enhanced_instruction
        retry_delay = 2 ** attempt
        print(f'⏱️ Waiting {retry_delay}s before retry...')
        await asyncio.sleep(retry_delay)
        pass
    except Exception as general_error:
        print(f'❌ {agent_wrapper.name} failed with non-JSON error on attempt {attempt + 1}: {general_error}')
        return create_fallback_response(agent_wrapper.name, lat, lng, country, str(general_error))

def create_enhanced_json_instruction(original_instruction: str, error_type: str, attempt: int) -> str:
    """Create enhanced instruction with specific JSON formatting guidance based on error type"""  # inserted
    error_specific_guidance = {'control_character': '\nCRITICAL JSON FORMATTING REQUIREMENTS (Retry #{attempt}):\n- Remove ALL control characters, special symbols, and non-printable characters\n- Use only standard ASCII characters (letters, numbers, basic punctuation)\n- No smart quotes, em-dashes, or special Unicode characters\n- Ensure all text is clean, readable English without formatting artifacts', 'syntax_error': '\nCRITICAL JSON FORMATTING REQUIREMENTS (Retry #{attempt}):\n- Double-check all JSON syntax: proper commas, brackets, braces\n- Ensure every opening brace {{ has a closing brace }}\n- Ensure every opening bracket [ has a closing bracket ]\n- No trailing commas before closing braces or brackets', 'unterminated_string': '\nCRITICAL JSON FORMATTING REQUIREMENTS (Retry #{attempt}):\n- Ensure ALL string values are properly quoted with double quotes\n- Escape any internal quotes with backslashes: \"He said \\\"Hello\\\"\"\n- Close all string values properly - no missing closing quotes', 'missing_quotes': '\nCRITICAL JSON FORMATTING REQUIREMENTS (Retry #{attempt}):\n- ALL property names must be in double quotes: \"property_name\"\n- ALL string values must be in double quotes: \"string_value\"\n- Use only double quotes, never single quotes in JSON', 'trailing_comma': '\nCRITICAL JSON FORMATTING REQUIREMENTS (Retry #{attempt}):\n- Remove ALL trailing commas before closing braces or brackets\n- Last item in objects or arrays should NOT have a comma after it', 'empty_response': '\nCRITICAL RESPONSE REQUIREMENTS (Retry #{attempt}):\n- Provide a complete JSON response - do not return empty content\n- Include all required fields according to the schema\n- Ensure the response contains actual analysis data', 'general_formatting': '\nCRITICAL JSON FORMATTING REQUIREMENTS (Retry #{attempt}):\n- Response must be valid JSON format with proper structure\n- Use proper JSON syntax with double quotes for strings\n- Remove any markdown formatting (```json, ```)\n- Ensure clean, parseable JSON structure'}
    guidance = error_specific_guidance.get(error_type, error_specific_guidance['general_formatting'])
    guidance = guidance.replace('{attempt}', str(attempt))
    enhanced_instruction = f'{original_instruction}\n\n{guidance}\n\nIMPORTANT: Your previous response had a JSON formatting error ({error_type}). Please provide the same high-quality analysis but ensure perfect JSON formatting. Focus on providing the same valuable insights with corrected formatting.'
    return enhanced_instruction

def create_fallback_response(agent_name: str, lat: float, lng: float, country: str, error_message: str):
    """Create a fallback AgentOutput when all retry attempts fail"""  # inserted
    from .models import AgentOutput
    return AgentOutput(overall_score=2.5, sections={}, assumptions=[f'Analysis generated using fallback due to technical issue: {error_message[:100]}...'], key_insights=[f'Data center analysis for {country} requires further investigation due to processing error'], executive_summary=f'Technical analysis for {lat}, {lng} in {country} encountered processing issues. Manual review recommended for comprehensive assessment.')

class PowerInfrastructureAgentWrapper:
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = 'Power Infrastructure Agent'

    async def analyze_power_infrastructure(self, lat, lng, country, context=None):
        """Match old agent signature exactly"""  # inserted
        start_time = time.time()
        print(f'🚀 DOMAIN AGENT: Power agent called for {country} at {lat}, {lng}')
        try:
            context_instruction = ''
            if context and 'report' in str(context).lower():
                context_instruction = '\n\nIMPORTANT: DETAILED REPORT MODE - Provide comprehensive, thorough analysis with full details.'
            prompt = f'{self.adk_agent.instruction}\n\nAnalyze power infrastructure for data center at {lat}, {lng} in {country}.{context_instruction}\n\nIMPORTANT: Provide all analysis and insights in clear, professional English only. Ensure all text is properly formatted and readable.'
            import google.generativeai as genai
            import os
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception('GEMINI_API_KEY not found')
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(self.adk_agent.model)
            response = await asyncio.to_thread(model.generate_content, prompt)
        except json.JSONDecodeError:
                print(f'🔍 DEBUG Power Agent Response (first 500 chars): {response.text[:500]}...')
            else:  # inserted
                try:
                    import json
                    cleaned_response = clean_agent_response(response.text)
                    print(f'🔧 DEBUG Cleaned Response (first 100 chars): {cleaned_response[:100]}...')
                    response_data = json.loads(cleaned_response)
                    print('✅ Power Agent JSON parsed successfully')
                except json.JSONDecodeError as json_error:
                    pass  # postinserted
                else:  # inserted
                    try:
                        return PowerInfrastructureOutput(**response_data)
                    except Exception as pydantic_error:
                        pass  # postinserted
                    else:  # inserted
                        elapsed_time = (time.time() - start_time) * 1000
                        print(f'⏱️ DOMAIN AGENT: Power agent completed in {elapsed_time:.1f}ms')
                print(f'⚠️ PowerInfrastructureOutput validation failed: {pydantic_error}')
                return AgentOutput(**response_data)
                print(f'❌ Power Agent JSON parsing failed: {json_error}')
                print(f'🔍 Cleaned response: {cleaned_response[:200]}...')
                raise json_error
            except Exception as other_error:
                elapsed_time = (time.time() - start_time) * 1000
                print(f'❌ Power Agent failed with non-JSON error after {elapsed_time:.1f}ms: {other_error}')
                return AgentOutput(overall_score=(-1.0), sections={}, assumptions=[], key_insights=[f'Power analysis for {country}'], executive_summary='')
                raise
            except Exception as e:
                elapsed_time = (time.time() - start_time) * 1000
                print(f'❌ Power agent failed after {elapsed_time:.1f}ms: {e}')
                return AgentOutput(overall_score=(-1.0), sections={}, assumptions=[], key_insights=[f'Power analysis failed: {str(e)}'], executive_summary='Power analysis unavailable')

class NetworkConnectivityAgentWrapper:
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = 'Network Connectivity Agent'

    async def analyze_network_connectivity(self, lat, lng, country, context=None):
        """Match old agent signature exactly"""  # inserted
        start_time = time.time()
        print(f'🚀 DOMAIN AGENT: Network agent called for {country} at {lat}, {lng}')
        try:
            context_instruction = ''
            if context and 'report' in str(context).lower():
                context_instruction = '\n\nIMPORTANT: DETAILED REPORT MODE - Provide comprehensive, thorough analysis with full details.'
            prompt = f'{self.adk_agent.instruction}\n\nAnalyze network connectivity for data center at {lat}, {lng} in {country}.{context_instruction}\n\nIMPORTANT: Provide all analysis and insights in clear, professional English only. Ensure all text is properly formatted and readable.'
            import google.generativeai as genai
            import os
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception('GEMINI_API_KEY not found')
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(self.adk_agent.model)
            response = await asyncio.to_thread(model.generate_content, prompt)
        except json.JSONDecodeError:
                print(f'🔍 DEBUG Network Agent Response (first 500 chars): {response.text[:500]}...')
            else:  # inserted
                try:
                    import json
                    cleaned_response = clean_agent_response(response.text)
                    print(f'🔧 DEBUG Cleaned Response (first 100 chars): {cleaned_response[:100]}...')
                    response_data = json.loads(cleaned_response)
                    print('✅ Network Agent JSON parsed successfully')
                except json.JSONDecodeError as json_error:
                    pass  # postinserted
                else:  # inserted
                    try:
                        return NetworkConnectivityOutput(**response_data)
                    except Exception as pydantic_error:
                        pass  # postinserted
                    else:  # inserted
                        elapsed_time = (time.time() - start_time) * 1000
                        print(f'⏱️ DOMAIN AGENT: Network agent completed in {elapsed_time:.1f}ms')
                print(f'⚠️ NetworkConnectivityOutput validation failed: {pydantic_error}')
                return AgentOutput(**response_data)
                print(f'❌ Network Agent JSON parsing failed: {json_error}')
                print(f'🔍 Cleaned response: {cleaned_response[:200]}...')
                raise json_error
            except Exception as other_error:
                print(f'❌ Network Agent failed with non-JSON error: {other_error}')
                return AgentOutput(overall_score=(-1.0), sections={}, assumptions=[], key_insights=[f'Network analysis for {country}'], executive_summary='')
                raise
            except Exception as e:
                elapsed_time = (time.time() - start_time) * 1000
                print(f'❌ Network agent failed after {elapsed_time:.1f}ms: {e}')
                return AgentOutput(overall_score=(-1.0), sections={}, assumptions=[], key_insights=[f'Network analysis failed: {str(e)}'], executive_summary='Network analysis unavailable')

class ClimateSuitabilityAgentWrapper:
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = 'Climate Suitability Agent'

    async def analyze_climate_suitability(self, lat, lng, country, context=None):
        """Match old agent signature exactly"""  # inserted
        try:
            context_instruction = ''
            if context and 'report' in str(context).lower():
                context_instruction = '\n\nIMPORTANT: DETAILED REPORT MODE - Provide comprehensive, thorough analysis with full details.'
            prompt = f'{self.adk_agent.instruction}\n\nAnalyze climate suitability for data center at {lat}, {lng} in {country}.{context_instruction}\n\nIMPORTANT: Provide all analysis and insights in clear, professional English only. Ensure all text is properly formatted and readable.'
            import google.generativeai as genai
            import os
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception('GEMINI_API_KEY not found')
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(self.adk_agent.model)
            response = await asyncio.to_thread(model.generate_content, prompt)
        except json.JSONDecodeError:
            else:  # inserted
                try:
                    import json
                    cleaned_response = clean_agent_response(response.text)
                    response_data = json.loads(cleaned_response)
                    print('✅ Climate Agent JSON parsed successfully')
                except json.JSONDecodeError as json_error:
                    pass  # postinserted
                else:  # inserted
                    try:
                        return ClimateAnalysisOutput(**response_data)
                    except Exception as pydantic_error:
                        pass  # postinserted
                print(f'⚠️ ClimateAnalysisOutput validation failed: {pydantic_error}')
                return AgentOutput(**response_data)
                print(f'❌ Climate Agent JSON parsing failed: {json_error}')
                raise json_error
            except Exception as other_error:
                print(f'❌ Climate Agent failed with non-JSON error: {other_error}')
                return AgentOutput(overall_score=(-1.0), sections={}, assumptions=[], key_insights=[f'Climate analysis for {country}'], executive_summary='')
                raise
            except Exception as e:
                print(f'❌ Climate agent failed: {e}')
                return AgentOutput(overall_score=(-1.0), sections={}, assumptions=[], key_insights=[f'Climate analysis failed: {str(e)}'], executive_summary='Climate analysis unavailable')

class OperationalRiskAgentWrapper:
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = 'Operational Risk Agent'

    async def analyze_operational_risk(self, lat, lng, country, context=None):
        """Match old agent signature exactly"""  # inserted
        try:
            context_instruction = ''
            if context and 'report' in str(context).lower():
                context_instruction = '\n\nIMPORTANT: DETAILED REPORT MODE - Provide comprehensive, thorough analysis with full details.'
            prompt = f'{self.adk_agent.instruction}\n\nAnalyze operational risk for data center at {lat}, {lng} in {country}.{context_instruction}\n\nIMPORTANT: Provide all analysis and insights in clear, professional English only. Ensure all text is properly formatted and readable.'
            import google.generativeai as genai
            import os
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception('GEMINI_API_KEY not found')
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(self.adk_agent.model)
            response = await asyncio.to_thread(model.generate_content, prompt)
        except json.JSONDecodeError:
            else:  # inserted
                try:
                    import json
                    cleaned_response = clean_agent_response(response.text)
                    response_data = json.loads(cleaned_response)
                    print('✅ Risk Agent JSON parsed successfully')
                except json.JSONDecodeError as json_error:
                    pass  # postinserted
                else:  # inserted
                    try:
                        return OperationalRiskOutput(**response_data)
                    except Exception as pydantic_error:
                        pass  # postinserted
                print(f'⚠️ OperationalRiskOutput validation failed: {pydantic_error}')
                return AgentOutput(**response_data)
                print(f'❌ Risk Agent JSON parsing failed: {json_error}')
                raise json_error
            except Exception as other_error:
                print(f'❌ Risk Agent failed with non-JSON error: {other_error}')
                return AgentOutput(overall_score=(-1.0), sections={}, assumptions=[], key_insights=[f'Risk analysis for {country}'], executive_summary='')
                raise
            except Exception as e:
                print(f'❌ Risk agent failed: {e}')
                return AgentOutput(overall_score=(-1.0), sections={}, assumptions=[], key_insights=[f'Risk analysis failed: {str(e)}'], executive_summary='Risk analysis unavailable')

class SustainabilityESGAgentWrapper:
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = 'Sustainability ESG Agent'

    async def analyze_sustainability_esg(self, lat, lng, country, context=None):
        """Match old agent signature exactly"""  # inserted
        try:
            context_instruction = ''
            if context and 'report' in str(context).lower():
                context_instruction = '\n\nIMPORTANT: DETAILED REPORT MODE - Provide comprehensive, thorough analysis with full details.'
            prompt = f'{self.adk_agent.instruction}\n\nAnalyze sustainability ESG for data center at {lat}, {lng} in {country}.{context_instruction}\n\nIMPORTANT: Provide all analysis and insights in clear, professional English only. Ensure all text is properly formatted and readable.'
            import google.generativeai as genai
            import os
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception('GEMINI_API_KEY not found')
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(self.adk_agent.model)
            response = await asyncio.to_thread(model.generate_content, prompt)
        except json.JSONDecodeError:
            else:  # inserted
                try:
                    import json
                    cleaned_response = clean_agent_response(response.text)
                    response_data = json.loads(cleaned_response)
                    print('✅ ESG Agent JSON parsed successfully')
                except json.JSONDecodeError as json_error:
                    pass  # postinserted
                else:  # inserted
                    try:
                        return ESGSustainabilityOutput(**response_data)
                    except Exception as pydantic_error:
                        pass  # postinserted
                print(f'⚠️ ESGSustainabilityOutput validation failed: {pydantic_error}')
                return AgentOutput(**response_data)
                print(f'❌ ESG Agent JSON parsing failed: {json_error}')
                raise json_error
            except Exception as other_error:
                print(f'❌ ESG Agent failed with non-JSON error: {other_error}')
                return AgentOutput(overall_score=(-1.0), sections={}, assumptions=[], key_insights=[f'ESG analysis for {country}'], executive_summary='')
                raise
            except Exception as e:
                print(f'❌ ESG agent failed: {e}')
                return AgentOutput(overall_score=(-1.0), sections={}, assumptions=[], key_insights=[f'ESG analysis failed: {str(e)}'], executive_summary='ESG analysis unavailable')

class RegulatoryComplianceAgentWrapper:
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = 'Regulatory Compliance Agent'

    async def analyze_regulatory_compliance(self, lat, lng, country, context=None):
        """Match old agent signature exactly"""  # inserted
        try:
            context_instruction = ''
            if context and 'report' in str(context).lower():
                context_instruction = '\n\nIMPORTANT: DETAILED REPORT MODE - Provide comprehensive, thorough analysis with full details.'
            prompt = f'{self.adk_agent.instruction}\n\nAnalyze regulatory compliance for data center at {lat}, {lng} in {country}.{context_instruction}\n\nIMPORTANT: Provide all analysis and insights in clear, professional English only. Ensure all text is properly formatted and readable.'
            import google.generativeai as genai
            import os
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception('GEMINI_API_KEY not found')
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(self.adk_agent.model)
            response = await asyncio.to_thread(model.generate_content, prompt)
        except json.JSONDecodeError:
            else:  # inserted
                try:
                    import json
                    cleaned_response = clean_agent_response(response.text)
                    response_data = json.loads(cleaned_response)
                    print('✅ Regulatory Agent JSON parsed successfully')
                except json.JSONDecodeError as json_error:
                    pass  # postinserted
                else:  # inserted
                    try:
                        return RegulatoryComplianceOutput(**response_data)
                    except Exception as pydantic_error:
                        pass  # postinserted
                print(f'⚠️ RegulatoryComplianceOutput validation failed: {pydantic_error}')
                return AgentOutput(**response_data)
                print(f'❌ Regulatory Agent JSON parsing failed: {json_error}')
                raise json_error
            except Exception as other_error:
                print(f'❌ Regulatory Agent failed with non-JSON error: {other_error}')
                return AgentOutput(overall_score=(-1.0), sections={}, assumptions=[], key_insights=[f'Regulatory analysis for {country}'], executive_summary='')
                raise
            except Exception as e:
                print(f'❌ Regulatory agent failed: {e}')
                return AgentOutput(overall_score=(-1.0), sections={}, assumptions=[], key_insights=[f'Regulatory analysis failed: {str(e)}'], executive_summary='Regulatory analysis unavailable')

class HyperscalerAttractivenessAgentWrapper:
    def __init__(self, adk_agent):
        self.adk_agent = adk_agent
        self.name = 'Hyperscaler Attractiveness Agent'

    async def analyze_hyperscaler_attractiveness(self, lat, lng, country, context=None):
        """Match old agent signature exactly"""  # inserted
        try:
            context_instruction = ''
            if context and 'report' in str(context).lower():
                context_instruction = '\n\nIMPORTANT: DETAILED REPORT MODE - Provide comprehensive, thorough analysis with full details.'
            prompt = f'{self.adk_agent.instruction}\n\nAnalyze hyperscaler attractiveness for data center at {lat}, {lng} in {country}.{context_instruction}\n\nIMPORTANT: Provide all analysis and insights in clear, professional English only. Ensure all text is properly formatted and readable.'
            import google.generativeai as genai
            import os
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise Exception('GEMINI_API_KEY not found')
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(self.adk_agent.model)
            response = await asyncio.to_thread(model.generate_content, prompt)
        except json.JSONDecodeError:
            else:  # inserted
                try:
                    import json
                    cleaned_response = clean_agent_response(response.text)
                    response_data = json.loads(cleaned_response)
                    print('✅ Hyperscaler Agent JSON parsed successfully')
                except json.JSONDecodeError as json_error:
                    pass  # postinserted
                else:  # inserted
                    try:
                        from .domain_models import HyperscalerAttractivenessOutput
                        return HyperscalerAttractivenessOutput(**response_data)
                    except Exception as pydantic_error:
                        pass  # postinserted
                print(f'⚠️ HyperscalerAttractivenessOutput validation failed: {pydantic_error}')
                return AgentOutput(**response_data)
                print(f'❌ Hyperscaler Agent JSON parsing failed: {json_error}')
                raise json_error
            except Exception as other_error:
                print(f'❌ Hyperscaler Agent failed with non-JSON error: {other_error}')
                return AgentOutput(overall_score=(-1.0), sections={}, assumptions=[], key_insights=[f'Hyperscaler analysis for {country}'], executive_summary='')
                raise
            except Exception as e:
                print(f'❌ Hyperscaler agent failed: {e}')
                return AgentOutput(overall_score=(-1.0), sections={}, assumptions=[], key_insights=[f'Hyperscaler analysis failed: {str(e)}'], executive_summary='Hyperscaler analysis unavailable')

async def generate_datacenter_report(location_context: LocationContext) -> str:
    """Generate comprehensive data center site analysis report with executive insights.\n\n    Executes parallel analysis across all domains (Power, Network, Climate, Risk, ESG, Regulatory),\n    creates structured report with executive summary, and returns business-focused insights.\n    """  # inserted
    try:
        if isinstance(location_context, dict):
            if 'lat' not in location_context or 'lng' not in location_context:
                location_context.setdefault('lat', 0.0)
                location_context.setdefault('lng', 0.0)
            location_context = LocationContext(**location_context)
        print(f'🚀 Starting parallel analysis for {location_context.location}')
        from .power_agent import power_agent
        from .network_agent import network_agent
        from .climate_agent import climate_agent
        from .risk_agent import risk_agent
        from .esg_agent import esg_agent
        from .regulatory_agent import regulatory_agent
        from .hyperscaler_agent import hyperscaler_agent
        agents = {'power': PowerInfrastructureAgentWrapper(power_agent), 'network': NetworkConnectivityAgentWrapper(network_agent), 'climate': ClimateSuitabilityAgentWrapper(climate_agent), 'risk': OperationalRiskAgentWrapper(risk_agent), 'esg': SustainabilityESGAgentWrapper(esg_agent), 'regulatory': RegulatoryComplianceAgentWrapper(regulatory_agent), 'hyperscaler': HyperscalerAttractivenessAgentWrapper(hyperscaler_agent)}
        lat, lng, country = (location_context.lat, location_context.lng, location_context.country)
        print(f'🚀 Starting parallel analysis with retry protection for {location_context.location}')
        report_context = {'mode': 'report', 'type': 'comprehensive_report'}
        agent_tasks = {'power': call_agent_with_retry(agents['power'], 'analyze_power_infrastructure', lat, lng, country, report_context), 'network': call_agent_with_retry(agents['network'], 'analyze_network_connectivity', lat, lng, country, report_context), 'climate': call_agent_with_retry(agents['climate'], 'analyze_climate_suitability', lat, lng, country, report_context), 'risk': call_agent_with_retry(agents['risk'], 'analyze_operational_risk', lat, lng, country, report_context), 'esg': call_agent_with_retry(agents['esg'], 'analyze_sustainability_esg', lat, lng, country, report_context), 'regulatory': call_agent_with_retry(agents['regulatory'], 'analyze_regulatory_compliance', lat, lng, country, report_context), 'hyperscaler': call_agent_with_retry(agents['hyperscaler'], 'analyze_hyperscaler_attractiveness', lat, lng, country, report_context)}
        results = await asyncio.gather(*agent_tasks.values(), return_exceptions=True)
    except Exception as e:
            agent_results = dict(zip(agent_tasks.keys(), results))
            processed_results = {}
            for key, result in agent_results.items():
                result_key = f'{key}_result'
            else:  # inserted
                try:
                    if isinstance(result, Exception):
                        print(f'❌ {key} failed: {str(result)}')
                        processed_results[result_key] = AgentOutput(score=1.0, insights=[f'Analysis failed: {str(result)}'], detailed_analysis=f'Agent execution failed: {str(result)}', summary=f'Could not complete {key} analysis due to error.')
                    else:  # inserted
                        if isinstance(result, dict):
                            processed_results[result_key] = AgentOutput(**result)
                        else:  # inserted
                            processed_results[result_key] = result
                        print(f'✅ {result_key} completed - Score: {processed_results[result_key].overall_score}')
                except Exception as e:
                    pass  # postinserted
            else:  # inserted
                agent_results = processed_results
                print('🔄 Parallel analysis completed. Generating intelligent insights...')
                scores = [getattr(agent_results['power_result'], 'overall_score', 1.0), getattr(agent_results['network_result'], 'overall_score', 1.0), getattr(agent_results['climate_result'], 'overall_score', 1.0), getattr(agent_results['risk_result'], 'overall_score', 1.0), getattr(agent_results['esg_result'], 'overall_score', 1.0), getattr(agent_results['regulatory_result'], 'overall_score', 1.0), getattr(agent_results.get('hyperscaler_result'), 'overall_score', 1.0) if 'hyperscaler_result' in agent_results else 1.0]
                valid_scores = [s for s in scores if s > 0]
                    composite_score = sum(valid_scores) / len(valid_scores) if valid_scores else 1.0
                    from .insights_agent import insights_agent, prepare_insights_input
                    insights_input = prepare_insights_input(location_context=location_context, composite_score=composite_score, power_result=agent_results['power_result'], network_result=agent_results['network_result'], climate_result=agent_results['climate_result'], risk_result=agent_results['risk_result'], esg_result=agent_results['esg_result'], regulatory_result=agent_results['regulatory_result'])
                    print('🧠 Calling insights agent for intelligent synthesis...')
                else:  # inserted
                    try:
                        import google.generativeai as genai
                        import os
                        import json
                        api_key = os.getenv('GEMINI_API_KEY')
                        if not api_key:
                            raise Exception('GEMINI_API_KEY not found')
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel(insights_agent.model)
                        prompt = f'{insights_agent.instruction}\n\nAnalyze the following cross-domain data and provide intelligent insights:\n\n{json.dumps(insights_input.model_dump(), indent=2)}'
                        print(f'📤 Sending prompt to insights agent (length: {len(prompt)} chars)')
                        response = await asyncio.to_thread(model.generate_content, prompt)
                    except Exception as e:
                            print(f'📥 Received response from insights agent (length: {len(response.text)} chars)')
                            insights_data = robust_json_parse(response.text, 'insights agent response')
                            from .models import InsightsOutput
                            insights_result = InsightsOutput(**insights_data)
                            print('✅ Insights agent completed successfully')
                    except Exception as e:
                        pass  # postinserted
            print(f'❌ Error processing {key} result: {str(e)}')
            processed_results[result_key] = AgentOutput(overall_score=(-1.0), sections={}, assumptions=[], key_insights=[f'Result processing failed: {str(e)}'], executive_summary=f'Failed to process {key} analysis result.')
            print(f'⚠️ Insights agent failed, using fallback: {e}')
            print(f'🔍 Error type: {type(e).__name__}')
            if hasattr(e, 'response'):
                print(f'📄 Response that failed: {e.response[:1000]}...')
            insights_result = None
            print(f'⚠️ Database save failed: {e}')
            import traceback
            error_message = f'❌ Complete analysis pipeline failed: {str(e)}\n🔍 Traceback: {traceback.format_exc()}'
            print(error_message)
            return error_message
                """Collect assumptions from all domain agent results."""  # inserted
                all_assumptions = []
                for agent_key, agent_result in agent_results.items():
                    if hasattr(agent_result, 'assumptions') and agent_result.assumptions:
                        all_assumptions.extend(agent_result.assumptions)
                return list(set(all_assumptions))
                    """Identify specific data gaps requiring third-party verification."""  # inserted
                    data_gaps = []
                    data_gaps.extend([f'On-site soil and geological survey for {location}', 'Local utility capacity confirmation and grid connection costs', 'Real estate availability and zoning verification', 'Local labor market rates and availability assessment', 'Detailed regulatory timeline and permit requirements'])
                    for agent_key, agent_result in agent_results.items():
                        score = getattr(agent_result, 'overall_score', 5.0)
                        if 'power' in agent_key and score < 4.0:
                            data_gaps.append('Detailed power grid stability testing and backup power requirements')
                        if 'network' in agent_key and score < 4.0:
                            data_gaps.append('Network latency testing and fiber infrastructure verification')
                        if 'climate' in agent_key and score < 4.0:
                            data_gaps.append('Detailed climate resilience and cooling efficiency analysis')
                        if 'risk' in agent_key and score < 4.0:
                            data_gaps.append('Comprehensive security assessment and emergency response planning')
                    return data_gaps[:8]
                        """Generate an executive-level response with key insights and due diligence requirements"""  # inserted
                        try:
                            rounded_score = round(report.overall_suitability.composite_score, 1)
                            strengths = report.executive_summary.key_strengths[:2] if report.executive_summary.key_strengths else []
                            challenges = report.executive_summary.key_challenges[:2] if report.executive_summary.key_challenges else []
                            assumptions = collect_all_assumptions(agent_results)
                            data_gaps = identify_data_gaps(agent_results, report.location)
                            response = f'🏢 **Data Center Site Analysis Complete for {report.location}**\n\n'
                            response += f'📊 **Overall Suitability**: {rounded_score}/5.0 - **{report.overall_suitability.rating}**\n'
                            response += f'📍 **Location**: {report.location}, {report.country}\n\n'
                            if strengths:
                                response += '✅ **Key Strengths**:\n'
                                for strength in strengths:
                                    clean_strength = strength.split(':')[0] if ':' in strength else strength
                                    response += f'  • {clean_strength}\n'
                                response += '\n'
                            if challenges:
                                response += '⚠️ **Key Challenges**:\n'
                                for challenge in challenges:
                                    clean_challenge = challenge.split(':')[0] if ':' in challenge else challenge
                                    response += f'  • {clean_challenge}\n'
                                response += '\n'
                            if report.overall_suitability.rating == 'Excellent':
                                response += '🎯 **Recommendation**: Highly suitable for immediate data center development with favorable conditions across all domains.\n\n'
                            else:  # inserted
                                if report.overall_suitability.rating == 'Good':
                                    response += '🎯 **Recommendation**: Well-suited for data center development with manageable challenges and strong fundamentals.\n\n'
                                else:  # inserted
                                    if report.overall_suitability.rating == 'Moderate':
                                        response += '🎯 **Recommendation**: Suitable for development with careful planning and risk mitigation strategies.\n\n'
                                    else:  # inserted
                                        response += '🎯 **Recommendation**: Consider alternative locations or extensive risk mitigation before proceeding.\n\n'
                            phase1 = report.phase_1_deployment
                            response += f'🚀 **Phase 1 Plan**: {phase1.recommended_capacity}\n'
                            response += f'⏱️ **Timeline**: {phase1.timeline}\n'
                            response += f'💰 **Investment**: {phase1.estimated_investment}\n\n'
                            response += '🔍 **Data Gaps & Due Diligence Requirements**:\n\n'
                            if assumptions:
                                response += '📋 **Key Assumptions Made**:\n'
                                for assumption in assumptions[:5]:
                                    response += f'  • {assumption}\n'
                            else:  # inserted
                                default_assumptions = ['Analysis based on publicly available data and industry standards', 'Current regulatory and economic conditions assumed to remain stable', 'Standard data center infrastructure requirements and specifications used', 'Local market conditions estimated using regional benchmarks']
                                response += '📋 **Key Assumptions Made**:\n'
                                for assumption in default_assumptions:
                                    response += f'  • {assumption}\n'
                            response += '\n'
                            response += '🎯 **Third-Party Verification Required**:\n'
                            for gap in data_gaps:
                                response += f'  • {gap}\n'
                            response += '\n'
                            response += '⚠️ **Important**: This analysis is based on publicly available information and industry standards. '
                            response += 'Critical business decisions should include on-site verification, local regulatory consultation, '
                            response += 'and detailed technical surveys.\n\n'
                            response += '📋 **Reports Generated**: Comprehensive analysis reports have been saved for detailed review\n'
                            response += '🔍 **Domains Analyzed**: Power, Network, Climate, Risk, ESG, and Regulatory assessments'
                            return response
                        except Exception as e:
                            print(f'⚠️ Error generating executive response: {e}')
                            return f'✅ Analysis complete for {report.location} - Overall Score: {rounded_score}/5.0 ({report.overall_suitability.rating})'
datacenter_report_tool = FunctionTool(func=generate_datacenter_report)