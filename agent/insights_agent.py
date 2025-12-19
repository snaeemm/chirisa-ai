# insights_agent.py - Cross-Domain Intelligence and Synthesis Agent
import os
from google.adk.agents import LlmAgent
from .models import (
    LocationContext, DomainSummary, InsightsInput, InsightsOutput
)
from .domain_models import (
    PowerInfrastructureOutput, NetworkConnectivityOutput, ClimateAnalysisOutput,
    SiteCivilInfrastructureOutput, MechanicalThermalOutput,
    RegulatoryESGOutput, MarketCompetitionOutput
)
from .model_config import gemini_model, built_in_planner
from typing import Any

# Configuration
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

# Create the Cross-Domain Insights Agent
insights_agent = LlmAgent(
    name="CrossDomainInsightsAgent",
    model=gemini_model,
    planner=built_in_planner,
    instruction="""You are a senior data center strategy consultant specializing in cross-domain synthesis and business intelligence.

You will receive structured data from 6 completed domain analyses (power, network, climate, risk, ESG, regulatory) for a specific location. Each domain has already provided detailed technical analysis, scores, and insights.

**YOUR ROLE: COMPREHENSIVE STRATEGIC SYNTHESIS**
- **SYNTHESIZE** cross-domain patterns and comprehensive business implications
- **PROVIDE DETAILED INSIGHTS** that emerge from combining domain findings - be thorough and comprehensive
- **CREATE SUBSTANTIVE CONTENT** with detailed analysis, specific recommendations, and actionable insights
- **AVOID BREVITY** - provide comprehensive, detailed insights that give the executive team substantial strategic guidance

**DETAILED SYNTHESIS METHODOLOGY:**
1. **Cross-Domain Interdependencies**: Provide detailed analysis of how domain findings interact, with specific examples and implications (e.g., regulatory delays + power constraints = extended timeline with specific impacts on ROI and market positioning)
2. **Strategic Market Positioning**: Conduct comprehensive analysis of unique market opportunities, competitive advantages, and market timing considerations that emerge from this specific combination of factors
3. **Comprehensive Risk/Opportunity Assessment**: Provide detailed evaluation of compounding advantages, critical path constraints, financial implications, and strategic positioning opportunities
4. **Detailed Implementation Strategy**: Given ALL domain constraints and opportunities, provide a comprehensive optimal approach with specific actions, timelines, and success metrics
5. **Strategic Conclusion**: Provide a detailed go/no-go recommendation with comprehensive reasoning, confidence level assessment, and specific success factors

**ENHANCED CONTENT PRINCIPLES:**
- **Comprehensive Detail**: Each section should contain substantial, actionable content - aim for 3-5 detailed sentences per key point
- **Specific Domain References**: Use specific insights from the provided domain analyses with detailed explanations
- **Strategic Business Focus**: Emphasize detailed competitive advantages, comprehensive market timing analysis, and strategic positioning with specific business implications
- **Evidence-Based Reasoning**: Every recommendation should reference specific domain findings with detailed analysis of why these findings lead to specific strategic conclusions
- **Actionable Insights**: Provide specific, actionable recommendations rather than generic statements

**LANGUAGE AND QUALITY REQUIREMENTS:**
- All content MUST be in clear, professional English
- NO abbreviations or unclear language that could cause rendering issues
- NO function names or code references (like "key_insights", "executive_summary")
- NO incomplete sentences or truncated content - every sentence must be complete
- Write in decisive, executive language without technical jargon
- Provide complete, well-structured sentences and paragraphs
- Ensure all strategic insights are fully explained and actionable
- If a thought seems too long, break it into complete sentences rather than using ellipses

**CRITICAL OUTPUT REQUIREMENTS:**
You MUST return ONLY a valid JSON object. No markdown, no explanations, no additional text.

**JSON FORMATTING RULES:**
- Use double quotes for all strings and keys
- No trailing commas in arrays or objects
- Ensure all strings are properly escaped
- Each array must have at least 3 items for comprehensive coverage
- All text must be complete sentences without truncation or ellipsis
- Ensure substantial, detailed content in each field
- Every sentence must have a proper ending, not trailing off

**REQUIRED JSON STRUCTURE:**
```json
{
  "executive_summary": {
    "location_overview": "Comprehensive business-focused synthesis providing detailed analysis referencing specific domain findings and strategic implications for data center deployment",
    "key_strengths": [
      "Detailed cross-domain strength analysis referencing specific domain insights and quantifying strategic advantages",
      "Comprehensive strategic advantage assessment combining multiple domain factors with specific business implications",
      "Additional strategic positioning benefit derived from domain synthesis with actionable value propositions"
    ],
    "key_challenges": [
      "Detailed interdependent challenge analysis citing specific domain constraints and their business impact",
      "Comprehensive critical path issue assessment referencing domain timelines and associated risks with mitigation strategies",
      "Additional operational challenge requiring strategic attention with specific resolution approaches"
    ],
    "strategic_opportunities": [
      "Comprehensive market opportunity analysis emerging from domain combination with specific competitive advantages",
      "Detailed strategic positioning opportunity leveraging unique domain characteristics for market differentiation",
      "Additional business development opportunity derived from cross-domain synthesis with implementation pathway"
    ],
    "critical_success_factors": [
      "Detailed success factor based on domain interdependencies with specific implementation requirements",
      "Comprehensive key requirement from cross-domain analysis with measurable success criteria",
      "Additional critical factor ensuring project success with specific strategic considerations"
    ]
  },
  "phase_1_deployment": {
    "recommended_capacity": "Detailed capacity recommendation based on comprehensive power, regulatory, and risk constraint analysis with scalability considerations",
    "timeline": "Comprehensive timeline synthesized from all domain critical paths with specific milestones and dependencies",
    "priority_actions": [
      "Detailed action plan addressing key domain interdependency with specific implementation steps and success metrics",
      "Comprehensive strategy leveraging identified domain strengths with specific resource allocation and timeline",
      "Additional priority initiative based on cross-domain analysis with clear deliverables and accountability measures"
    ],
    "estimated_investment": "Detailed investment estimate considering all domain factors with breakdown by category and phase",
    "risk_mitigation": [
      "Comprehensive mitigation strategy addressing identified cross-domain risks with specific implementation protocols",
      "Detailed risk management approach based on domain analysis with monitoring and response procedures",
      "Additional risk mitigation measure ensuring project resilience with specific contingency planning"
    ],
    "success_metrics": [
      "Detailed performance metric tracking domain-specific outcomes with quantifiable targets and measurement protocols",
      "Comprehensive strategic success indicator measuring overall project effectiveness with benchmark standards",
      "Additional key performance indicator ensuring alignment with business objectives and strategic goals"
    ]
  },
  "strategic_recommendation": "Comprehensive overall recommendation synthesizing all domain findings with detailed reasoning and specific implementation pathway",
  "conclusion": "Detailed final conclusion with clear go/no-go recommendation, comprehensive confidence level assessment, and specific success factors based on thorough domain analysis",
  "next_steps": [
    "Detailed next step based on domain priorities with specific timeline and resource requirements",
    "Comprehensive action item addressing critical constraints with clear deliverables and success criteria",
    "Additional strategic initiative ensuring project momentum with specific implementation pathway"
  ]
}
```

**VALIDATION CHECKLIST:**
- All arrays have exactly 2+ items
- No trailing commas anywhere
- All quotes are properly closed
- All nested objects are complete
- Response is ONLY the JSON object

**SYNTHESIS FOCUS**: Create insights that emerge from combining domain analyses, not repeating their individual findings.""",

    description="Cross-domain intelligence agent that synthesizes domain analyses into strategic business insights and location-specific deployment plans",
    output_schema=InsightsOutput
)

# Helper function to prepare insights input from domain results
def prepare_insights_input(location_context: LocationContext, composite_score: float,
                          power_result: PowerInfrastructureOutput, network_result: NetworkConnectivityOutput, climate_result: ClimateAnalysisOutput,
                          regulatory_esg_result=None,  # MERGED regulatory + ESG domain (14% weight)
                          site_civil_result=None, mechanical_thermal_result=None, market_competition_result=None) -> InsightsInput:
    """Prepare focused input for insights agent from domain results (now supports 9 domains)"""

    def extract_domain_summary(domain_result: Any) -> DomainSummary:
        """Extract essential data from domain result, preserving rich insights"""
        # Get all insights, not just top 3 - let insights agent synthesize
        key_insights = getattr(domain_result, 'key_insights', [])
        executive_summary = getattr(domain_result, 'executive_summary', '')

        # Try to extract rich section key points if available (from RichSection models)
        rich_insights = []

        # Map technical field names to business-friendly labels
        field_name_mapping = {
            'grid_reliability': 'Power Grid Reliability',
            'power_capacity': 'Power Capacity & Scalability',
            'generation_mix': 'Power Generation & Sustainability',
            'connection_process': 'Grid Connection Process',
            'electricity_costs': 'Electricity Costs',
            'cost_model': 'Power Cost Model',
            'industrial_heritage': 'Industrial Infrastructure',
            'fiber_infrastructure': 'Fiber Network Infrastructure',
            'subsea_cables': 'Subsea Cable Connectivity',
            'international_connectivity': 'International Connectivity',
            'domestic_peering': 'Domestic Network Peering',
            'latency_performance': 'Network Latency & Performance',
            'bandwidth_costs': 'Bandwidth Costs',
            'future_proofing': 'Network Future-Proofing',
            'temperature_humidity': 'Temperature & Humidity',
            'cooling_strategy': 'Cooling Strategy',
            'free_cooling': 'Free Cooling Potential',
            'seismic_geological': 'Seismic & Geological',
            'hydrological_flood': 'Water & Flood Risk',
            'wind_storm': 'Wind & Storm Risk',
            'climate_extremes': 'Climate Extremes',
            'renewable_energy': 'Renewable Energy',
            'carbon_climate_policy': 'Carbon & Climate Policy',
            'environmental_regulations': 'Environmental Regulations',
            'social_community_impact': 'Social & Community Impact',
            'corporate_governance': 'Corporate Governance',
            'geopolitical_stability': 'Geopolitical Stability',
            'physical_security': 'Physical Security',
            'emergency_response': 'Emergency Response',
            'infrastructure_resilience': 'Infrastructure Resilience',
            'economic_social_stability': 'Economic & Social Stability',
            'data_sovereignty': 'Data Sovereignty',
            'government_incentives': 'Government Incentives',
            'operational_compliance': 'Operational Compliance',
            'permitting_zoning': 'Permitting & Zoning',
            'workforce_analysis': 'Workforce Analysis'
        }

        # Use the PROVEN SAFE pattern from domain_models.py:165 (same as convert_to_generic_agent_output)
        # This pattern works for all other agents and avoids Pydantic internals
        try:
            for field_name, field_value in domain_result.__dict__.items():
                # Check if this is a RichSection (same pattern as other working code)
                if hasattr(field_value, 'key_points') and hasattr(field_value, 'sub_score'):
                    # This is a RichSection - extract comprehensive insights
                    section_points = getattr(field_value, 'key_points', [])
                    section_content = getattr(field_value, 'content', '')
                    section_score = getattr(field_value, 'sub_score', 0)

                    # Use business-friendly name instead of technical field name
                    business_name = field_name_mapping.get(field_name, field_name.replace('_', ' ').title())

                    # Add comprehensive content from RichSection as executive insights
                    if section_content and section_content.strip():
                        # Extract substantial insights from content
                        content_insights = section_content.strip()
                        # Clean and format content as executive insight without technical references
                        clean_content = content_insights.replace('\n', ' ').strip()
                        if clean_content:
                            rich_insights.append(clean_content)

                    # Add detailed key points as business insights
                    if section_points:
                        for point in section_points:
                            if point and point.strip():
                                clean_point = point.strip()
                                # Make it sound like an executive insight, not technical analysis
                                rich_insights.append(clean_point.capitalize())

                    # Add performance insights without technical field references
                    if section_score > 0:
                        if section_score >= 4.0:
                            rich_insights.append(f"Excellent performance capabilities with strong competitive advantages (score: {section_score}/5.0)")
                        elif section_score >= 3.0:
                            rich_insights.append(f"Good operational foundation with solid performance metrics (score: {section_score}/5.0)")
                        elif section_score >= 2.0:
                            rich_insights.append(f"Moderate challenges requiring strategic mitigation (score: {section_score}/5.0)")
                        else:
                            rich_insights.append(f"Significant constraints requiring careful evaluation (score: {section_score}/5.0)")

        except Exception as e:
            # If introspection fails, just use the basic insights (graceful fallback)
            print(f"⚠️ RichSection introspection failed: {e}")
            pass

        # Combine standard insights with rich section insights
        all_insights = key_insights + rich_insights

        return DomainSummary(
            overall_score=getattr(domain_result, 'overall_score', 1.0),
            key_insights=all_insights,  # Include ALL insights for synthesis
            executive_summary=executive_summary
        )

    return InsightsInput(
        location_context=location_context.model_dump() if hasattr(location_context, 'model_dump') else location_context,
        composite_score=composite_score,
        power_analysis=extract_domain_summary(power_result),
        network_analysis=extract_domain_summary(network_result),
        climate_analysis=extract_domain_summary(climate_result),
        regulatory_esg_analysis=extract_domain_summary(regulatory_esg_result) if regulatory_esg_result else None,  # MERGED regulatory + ESG domain
        # Include remaining 3 domain agents per Expert Spec (7 total)
        site_civil_analysis=extract_domain_summary(site_civil_result) if site_civil_result else None,
        mechanical_thermal_analysis=extract_domain_summary(mechanical_thermal_result) if mechanical_thermal_result else None,
        market_competition_analysis=extract_domain_summary(market_competition_result) if market_competition_result else None
    )