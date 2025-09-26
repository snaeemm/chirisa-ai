# models.py - Pydantic Models for Data Center Analysis System
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class LocationContext(BaseModel):
    """Structured location data model"""
    lat: float = Field(..., description="Latitude coordinate")
    lng: float = Field(..., description="Longitude coordinate")
    country: str = Field(..., description="Country name")
    location: str = Field(..., description="Formatted address or location name")
    justification: Optional[str] = Field(None, description="Why this location was selected for datacenter")

class AgentInput(BaseModel):
    """Standardized input structure for all domain agents"""
    location_context: LocationContext
    additional_params: Dict[str, Any] = {}

class AgentSection(BaseModel):
    """Individual analysis section within an agent response"""
    name: str = Field(..., description="Section name (e.g., 'Grid Reliability & Resiliency')")
    content: str = Field(..., description="Section content without markdown formatting")
    sub_score: float = Field(-1.0, description="Sub-score for this section, -1 if not found")

class StructuredAgentOutput(BaseModel):
    """Enhanced agent output with structured sections"""
    overall_score: float = Field(-1.0, description="Overall score from 1.0 to 5.0, -1 if failed")
    sections: Dict[str, AgentSection] = Field(default_factory=dict, description="Structured analysis sections")
    assumptions: List[str] = Field(default_factory=list, description="Analysis assumptions")
    key_insights: List[str] = Field(default_factory=list, description="Key insights from analysis")
    executive_summary: str = Field("", description="Executive summary")
    raw_response: str = Field("", description="Original AI response for fallback")

class AgentOutput(BaseModel):
    """Standardized output structure for all domain agents"""
    overall_score: float = Field(-1.0, description="Overall score 1.0-5.0, -1 if failed")
    sections: Dict[str, AgentSection] = Field(default_factory=dict, description="Structured analysis sections")
    assumptions: List[str] = Field(default_factory=list, description="Analysis assumptions")
    key_insights: List[str] = Field(default_factory=list, description="Key insights from analysis")
    executive_summary: str = Field("", description="Executive summary")
    data_gaps: List[str] = Field(default_factory=list, description="Identified data gaps requiring verification")
    third_party_verification: List[str] = Field(default_factory=list, description="Third-party services needed")
    phase_1_recommendations: Optional[Dict[str, str]] = Field(None, description="Domain-specific Phase 1 recommendations")

class DomainAnalysis(BaseModel):
    """Individual domain analysis structure"""
    score: float = Field(..., ge=1.0, le=5.0)
    key_findings: List[str] = Field(..., max_items=5)
    summary: str

class OverallSuitability(BaseModel):
    """Overall suitability assessment"""
    composite_score: float = Field(..., ge=-1.0, le=5.0)
    rating: str = Field(..., pattern="^(Excellent|Good|Moderate|Poor)$")
    recommendation: str

class ExecutiveSummary(BaseModel):
    """Executive summary structure"""
    location_overview: str
    key_strengths: List[str] = Field(..., max_items=5)
    key_challenges: List[str] = Field(..., max_items=5)
    critical_success_factors: List[str] = Field(..., max_items=5)

class Phase1Deployment(BaseModel):
    """Phase 1 deployment details"""
    recommended_capacity: str
    timeline: str
    priority_actions: List[str] = Field(..., max_items=5)
    estimated_investment: str
    risk_mitigation: List[str] = Field(..., max_items=5)

# Insights Agent Models - Cross-Domain Intelligence
class DomainSummary(BaseModel):
    """Essential data from each domain analysis"""
    overall_score: float = Field(..., description="Domain score 1.0-5.0")
    key_insights: List[str] = Field(..., description="Top 2-3 insights from domain")
    executive_summary: str = Field(..., description="Domain executive summary")

class InsightsInput(BaseModel):
    """Input for insights agent containing essential cross-domain data"""
    location_context: LocationContext
    composite_score: float = Field(..., description="Overall composite score")
    power_analysis: DomainSummary
    network_analysis: DomainSummary
    climate_analysis: DomainSummary
    risk_analysis: DomainSummary
    esg_analysis: DomainSummary
    regulatory_analysis: DomainSummary

class IntelligentExecutiveSummary(BaseModel):
    """Intelligent executive summary with cross-domain insights"""
    location_overview: str = Field(..., description="Location context and business rationale")
    key_strengths: List[str] = Field(default_factory=list, description="Primary competitive advantages")
    key_challenges: List[str] = Field(default_factory=list, description="Critical challenges to address")
    strategic_opportunities: List[str] = Field(default_factory=list, description="Strategic business opportunities")
    critical_success_factors: List[str] = Field(default_factory=list, description="Must-have factors for success")

class IntelligentPhase1Plan(BaseModel):
    """Intelligent Phase 1 deployment plan based on cross-domain analysis"""
    recommended_capacity: str = Field(..., description="Technical capacity with business justification")
    timeline: str = Field(..., description="Realistic timeline considering domain constraints")
    priority_actions: List[str] = Field(default_factory=list, description="Location-specific priority actions")
    estimated_investment: str = Field(..., description="Investment estimate with breakdown")
    risk_mitigation: List[str] = Field(default_factory=list, description="Critical risk mitigation strategies")
    success_metrics: List[str] = Field(default_factory=list, description="Key success metrics to track")

class InsightsOutput(BaseModel):
    """Complete insights agent output"""
    executive_summary: IntelligentExecutiveSummary
    phase_1_deployment: IntelligentPhase1Plan
    strategic_recommendation: str = Field(..., description="Overall strategic recommendation")
    conclusion: str = Field(..., description="Final conclusion summarizing location viability and go/no-go recommendation")
    next_steps: List[str] = Field(default_factory=list, description="Immediate next steps")

# Data Gaps and Assumptions Tracking Models
class DataSource(BaseModel):
    """Information about data sources used in analysis"""
    name: str = Field(..., description="Name of the data source")
    type: str = Field(..., description="Type: public, commercial, proprietary, estimated")
    reliability: str = Field(..., description="Reliability level: high, medium, low")
    last_updated: Optional[str] = Field(None, description="When the data was last updated")
    url: Optional[str] = Field(None, description="Source URL if available")

class DataGap(BaseModel):
    """Information about missing or insufficient data"""
    category: str = Field(..., description="Analysis category affected")
    description: str = Field(..., description="Description of the data gap")
    impact: str = Field(..., description="Impact on analysis: high, medium, low")
    recommended_source: str = Field(..., description="Recommended source for this data")
    estimated_cost: Optional[str] = Field(None, description="Estimated cost to obtain the data")

class ThirdPartyDueDiligence(BaseModel):
    """Third-party services needed for complete analysis"""
    service_type: str = Field(..., description="Type of service: legal, environmental, financial, technical")
    provider_type: str = Field(..., description="Type of provider needed")
    description: str = Field(..., description="Description of what is needed")
    estimated_timeline: str = Field(..., description="Estimated time to complete")
    estimated_cost: Optional[str] = Field(None, description="Estimated cost range")
    criticality: str = Field(..., description="Criticality: critical, important, nice-to-have")

class AssumptionTracking(BaseModel):
    """Enhanced assumption tracking with confidence levels"""
    category: str = Field(..., description="Analysis category")
    assumption: str = Field(..., description="The assumption made")
    confidence_level: str = Field(..., description="Confidence level: high, medium, low")
    impact_if_wrong: str = Field(..., description="Impact if assumption is incorrect")
    validation_method: str = Field(..., description="How this assumption could be validated")

class DataGapAnalysis(BaseModel):
    """Complete data gap and assumptions analysis"""
    data_sources_used: List[DataSource] = Field(default_factory=list, description="Data sources used in analysis")
    data_gaps_identified: List[str] = Field(default_factory=list, description="Identified data gaps")
    third_party_requirements: List[str] = Field(default_factory=list, description="Third-party due diligence needed")
    assumptions_made: List[AssumptionTracking] = Field(default_factory=list, description="Assumptions with confidence tracking")
    overall_confidence: str = Field(..., description="Overall confidence in analysis: high, medium, low")
    next_steps_priority: List[str] = Field(default_factory=list, description="Priority next steps to address gaps")

class ReportSchema(BaseModel):
    """Complete report structure"""
    location: str
    coordinates: Dict[str, float]  # {"lat": float, "lng": float}
    country: str
    analysis_date: str
    overall_suitability: OverallSuitability
    domain_analysis: Dict[str, DomainAnalysis]
    detailed_analysis: Dict[str, str]  # Keep for backward compatibility
    structured_analysis: Dict[str, Any] = Field(default_factory=dict)  # Enhanced to support domain-specific models
    executive_summary: ExecutiveSummary
    phase_1_deployment: Phase1Deployment

    # Enhanced insights fields from insights agent
    strategic_opportunities: List[str] = Field(default_factory=list, description="Strategic business opportunities")
    strategic_recommendation: str = Field("", description="Overall strategic recommendation")
    conclusion: str = Field("", description="Final conclusion and go/no-go decision")
    next_steps: List[str] = Field(default_factory=list, description="Immediate next steps")
    insights_result: Optional[Any] = Field(None, description="Full insights agent result for reference")

    # Data Gaps and Assumptions Analysis
    data_gap_analysis: Optional[DataGapAnalysis] = Field(None, description="Analysis of data gaps and third-party due diligence requirements")

    @staticmethod
    def _extract_agent_properties(agent_result: Any) -> Dict[str, Any]:
        """Extract common properties from agent result (works with both domain-specific and generic models)"""
        try:
            return {
                'overall_score': getattr(agent_result, 'overall_score', -1.0),
                'key_insights': getattr(agent_result, 'key_insights', []),
                'executive_summary': getattr(agent_result, 'executive_summary', ''),
                'assumptions': getattr(agent_result, 'assumptions', [])
            }
        except Exception as e:
            print(f"⚠️ Error extracting properties from agent result: {e}")
            return {
                'overall_score': -1.0,
                'key_insights': [],
                'executive_summary': '',
                'assumptions': []
            }

    @classmethod
    def _create_data_gap_analysis(
        cls,
        power_result: Any,
        network_result: Any,
        climate_result: Any,
        risk_result: Any,
        esg_result: Any,
        regulatory_result: Any,
        hyperscaler_result: Any = None
    ) -> DataGapAnalysis:
        """Create comprehensive data gap analysis from all agent results"""
        all_data_gaps = []
        all_third_party = []
        all_assumptions = []

        # Collect from all agents
        agents = [power_result, network_result, climate_result, risk_result, esg_result, regulatory_result]
        if hyperscaler_result:
            agents.append(hyperscaler_result)

        for agent_result in agents:
            if hasattr(agent_result, 'data_gaps') and agent_result.data_gaps:
                all_data_gaps.extend(agent_result.data_gaps)
            if hasattr(agent_result, 'third_party_verification') and agent_result.third_party_verification:
                all_third_party.extend(agent_result.third_party_verification)
            if hasattr(agent_result, 'assumptions') and agent_result.assumptions:
                # Convert string assumptions to AssumptionTracking format
                for assumption in agent_result.assumptions:
                    all_assumptions.append(AssumptionTracking(
                        category="General Analysis",  # Required field that was missing
                        assumption=assumption,
                        confidence_level="medium",  # Default since not specified by agents
                        impact_if_wrong="medium",   # Default since not specified by agents
                        validation_method="Third-party verification recommended"
                    ))

        # Determine overall confidence based on number of data gaps
        if len(all_data_gaps) <= 3:
            confidence = "high"
        elif len(all_data_gaps) <= 6:
            confidence = "medium"
        else:
            confidence = "low"

        return DataGapAnalysis(
            data_sources_used=[
                DataSource(
                    name="Public data analysis",
                    type="publicly_available",
                    reliability="medium",
                    last_updated="Current analysis"
                )
            ],
            data_gaps_identified=all_data_gaps,
            third_party_requirements=all_third_party,
            assumptions_made=all_assumptions,
            overall_confidence=confidence,
            next_steps_priority=[
                "Address critical data gaps through third-party verification",
                "Validate key assumptions with local experts",
                "Conduct on-site assessments for high-impact areas"
            ]
        )

    @classmethod
    def from_location_and_agents(
        cls,
        location_context: LocationContext,
        power_result: Any,  # Can be PowerInfrastructureOutput or AgentOutput
        network_result: Any,  # Can be NetworkConnectivityOutput or AgentOutput
        climate_result: Any,  # Can be ClimateAnalysisOutput or AgentOutput
        risk_result: Any,  # Can be OperationalRiskOutput or AgentOutput
        esg_result: Any,  # Can be ESGSustainabilityOutput or AgentOutput
        regulatory_result: Any,  # Can be RegulatoryComplianceOutput or AgentOutput
        hyperscaler_result: Any = None,  # Optional HyperscalerAttractivenessOutput
        insights_result: Any = None  # Optional intelligent insights from insights_agent
    ) -> "ReportSchema":
        """Create report from location context and agent outputs (supports both domain-specific and generic models)"""

        # Extract properties from all agent results
        power_props = cls._extract_agent_properties(power_result)
        network_props = cls._extract_agent_properties(network_result)
        climate_props = cls._extract_agent_properties(climate_result)
        risk_props = cls._extract_agent_properties(risk_result)
        esg_props = cls._extract_agent_properties(esg_result)
        regulatory_props = cls._extract_agent_properties(regulatory_result)
        hyperscaler_props = cls._extract_agent_properties(hyperscaler_result) if hyperscaler_result else None

        # Calculate composite score from extracted properties
        scores = [
            power_props['overall_score'],
            network_props['overall_score'],
            climate_props['overall_score'],
            risk_props['overall_score'],
            esg_props['overall_score'],
            regulatory_props['overall_score']
        ]

        # Include hyperscaler score if available
        if hyperscaler_props and hyperscaler_props['overall_score'] > 0:
            scores.append(hyperscaler_props['overall_score'])
        # Filter out failed scores (-1) and calculate average
        valid_scores = [s for s in scores if s > 0]
        composite_score = sum(valid_scores) / len(valid_scores) if valid_scores else -1.0

        # Determine rating
        if composite_score >= 4.5:
            rating = "Excellent"
        elif composite_score >= 3.5:
            rating = "Good"
        elif composite_score >= 2.5:
            rating = "Moderate"
        else:
            rating = "Poor"

        # Build domain analysis using extracted properties
        domain_analysis = {
            "power_infrastructure": DomainAnalysis(
                score=power_props['overall_score'] if power_props['overall_score'] > 0 else 1.0,
                key_findings=power_props['key_insights'][:3],
                summary=power_props['executive_summary']
            ),
            "network_connectivity": DomainAnalysis(
                score=network_props['overall_score'] if network_props['overall_score'] > 0 else 1.0,
                key_findings=network_props['key_insights'][:3],
                summary=network_props['executive_summary']
            ),
            "climate_environmental": DomainAnalysis(
                score=climate_props['overall_score'] if climate_props['overall_score'] > 0 else 1.0,
                key_findings=climate_props['key_insights'][:3],
                summary=climate_props['executive_summary']
            ),
            "operational_risk": DomainAnalysis(
                score=risk_props['overall_score'] if risk_props['overall_score'] > 0 else 1.0,
                key_findings=risk_props['key_insights'][:3],
                summary=risk_props['executive_summary']
            ),
            "esg_sustainability": DomainAnalysis(
                score=esg_props['overall_score'] if esg_props['overall_score'] > 0 else 1.0,
                key_findings=esg_props['key_insights'][:3],
                summary=esg_props['executive_summary']
            ),
            "regulatory_compliance": DomainAnalysis(
                score=regulatory_props['overall_score'] if regulatory_props['overall_score'] > 0 else 1.0,
                key_findings=regulatory_props['key_insights'][:3],
                summary=regulatory_props['executive_summary']
            )
        }

        # Add hyperscaler analysis if available
        if hyperscaler_props:
            domain_analysis["hyperscaler_attractiveness"] = DomainAnalysis(
                score=hyperscaler_props['overall_score'] if hyperscaler_props['overall_score'] > 0 else 1.0,
                key_findings=hyperscaler_props['key_insights'][:3],
                summary=hyperscaler_props['executive_summary']
            )

        # Aggregate insights for executive summary using extracted properties
        all_insights = (
            power_props['key_insights'] + network_props['key_insights'] +
            climate_props['key_insights'] + risk_props['key_insights'] +
            esg_props['key_insights'] + regulatory_props['key_insights']
        )

        # Add hyperscaler insights if available
        if hyperscaler_props:
            all_insights.extend(hyperscaler_props['key_insights'])

        # Use intelligent insights if available, otherwise fallback to basic aggregation
        if insights_result and hasattr(insights_result, 'executive_summary'):
            print("✅ Using intelligent executive summary from insights agent")
            # Extract intelligent insights
            intelligent_exec = insights_result.executive_summary
            executive_summary = ExecutiveSummary(
                location_overview=intelligent_exec.location_overview,
                key_strengths=intelligent_exec.key_strengths,
                key_challenges=intelligent_exec.key_challenges,
                critical_success_factors=intelligent_exec.critical_success_factors
            )

            # Extract intelligent Phase 1 plan
            intelligent_phase1 = insights_result.phase_1_deployment
            dynamic_phase1 = Phase1Deployment(
                recommended_capacity=intelligent_phase1.recommended_capacity,
                timeline=intelligent_phase1.timeline,
                priority_actions=intelligent_phase1.priority_actions,
                estimated_investment=intelligent_phase1.estimated_investment,
                risk_mitigation=intelligent_phase1.risk_mitigation
            )

            # Extract additional insights fields
            strategic_opportunities = intelligent_exec.strategic_opportunities
            strategic_recommendation = getattr(insights_result, 'strategic_recommendation', '')
            conclusion = getattr(insights_result, 'conclusion', '')
            next_steps = getattr(insights_result, 'next_steps', [])
            full_insights_result = insights_result
        else:
            print("⚠️ Using fallback executive summary - insights agent not available")
            # Fallback to basic aggregation
            executive_summary = ExecutiveSummary(
                location_overview=f"Comprehensive analysis of {location_context.location} for datacenter deployment",
                key_strengths=all_insights[:3] if len(all_insights) >= 3 else all_insights,
                key_challenges=all_insights[3:6] if len(all_insights) >= 6 else [],
                critical_success_factors=all_insights[6:9] if len(all_insights) >= 9 else []
            )

            # Fallback values for additional insights fields
            strategic_opportunities = []
            strategic_recommendation = f"Location shows {rating.lower()} potential for datacenter deployment based on composite analysis"
            conclusion = f"Based on comprehensive domain analysis, this location receives a {rating} rating for datacenter viability"
            next_steps = ["Conduct detailed site survey", "Engage local authorities", "Develop implementation timeline"]
            full_insights_result = None

            # Fallback Phase 1 plan
            try:
                from .utility import generate_dynamic_phase1_plan
                dynamic_phase1 = generate_dynamic_phase1_plan(
                    location_context, power_result, network_result, climate_result,
                    risk_result, esg_result, regulatory_result, composite_score
                )
            except Exception as e:
                print(f"⚠️ Error generating fallback Phase 1 plan: {e}")
                dynamic_phase1 = Phase1Deployment(
                    recommended_capacity="50-100 MW initial deployment",
                    timeline="18-24 months for Phase 1",
                    priority_actions=["Site acquisition", "Grid connection", "Regulatory approvals", "Infrastructure development", "Equipment procurement"],
                    estimated_investment="$200-400 million USD",
                    risk_mitigation=["Diversified power sources", "Redundant connectivity", "Local partnerships", "Phased approach", "Risk monitoring"]
                )

        return cls(
            location=location_context.location,
            coordinates={"lat": location_context.lat, "lng": location_context.lng},
            country=location_context.country,
            analysis_date=datetime.now().strftime("%Y-%m-%d"),
            overall_suitability=OverallSuitability(
                composite_score=composite_score,
                rating=rating,
                recommendation=f"Location rated as {rating} for datacenter deployment"
            ),
            domain_analysis=domain_analysis,
            detailed_analysis={
                "power_infrastructure": power_props['executive_summary'],
                "network_connectivity": network_props['executive_summary'],
                "climate_environmental": climate_props['executive_summary'],
                "operational_risk": risk_props['executive_summary'],
                "esg_sustainability": esg_props['executive_summary'],
                "regulatory_compliance": regulatory_props['executive_summary'],
                **({"hyperscaler_attractiveness": hyperscaler_props['executive_summary']} if hyperscaler_props else {})
            },
            structured_analysis={
                "power_infrastructure": power_result,  # Store original objects (domain-specific or generic)
                "network_connectivity": network_result,
                "climate_environmental": climate_result,
                "operational_risk": risk_result,
                "esg_sustainability": esg_result,
                "regulatory_compliance": regulatory_result,
                **({"hyperscaler_attractiveness": hyperscaler_result} if hyperscaler_result else {})
            },
            executive_summary=executive_summary,
            phase_1_deployment=dynamic_phase1,
            strategic_opportunities=strategic_opportunities,
            strategic_recommendation=strategic_recommendation,
            conclusion=conclusion,
            next_steps=next_steps,
            insights_result=full_insights_result,
            data_gap_analysis=cls._create_data_gap_analysis(
                power_result, network_result, climate_result, risk_result,
                esg_result, regulatory_result, hyperscaler_result
            )
        )