# models.py - Pydantic Models for Data Center Analysis System
from typing import Dict, List, Optional, Any, Union, Literal
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

# ================================================================================================
# INVESTMENT-GRADE CORE MODELS (Chirisa-AI Enhancement)
# ================================================================================================

class NoGoGate(BaseModel):
    """Hard stop gate that fails the entire site analysis"""
    gate_type: str = Field(..., description="Type of NO-GO gate (e.g., 'Power Quality', 'Flood Risk', 'Protected Area')")
    triggered: bool = Field(..., description="Whether this gate is triggered")
    reason: str = Field(..., description="Detailed reason for NO-GO status")
    standard_reference: Optional[str] = Field(None, description="Standard violated (e.g., 'IEEE 519-2014 THD >8%')")
    mitigation_possible: bool = Field(False, description="Whether mitigation is theoretically possible")
    mitigation_cost: Optional[str] = Field(None, description="Estimated cost to mitigate if possible")

class CautionFlag(BaseModel):
    """Yellow flag requiring mitigation plan but not blocking deployment"""
    category: str = Field(..., description="Category (e.g., 'Seismic', 'Water Stress', 'Grid Timeline')")
    severity: Literal["low", "medium", "high"] = Field(..., description="Severity level")
    description: str = Field(..., description="Detailed description of the caution")
    mitigation_plan: str = Field(..., description="Specific mitigation approach")
    cost_impact: str = Field(..., description="Financial impact (e.g., '+15-25% structural cost')")
    timeline_impact: Optional[str] = Field(None, description="Impact on deployment timeline")
    severity_points: float = Field(0.0, ge=0.0, le=1.0, description="Score deduction (0.0-1.0)")

    @field_validator('severity', mode='before')
    @classmethod
    def normalize_severity(cls, v):
        """Normalize severity to lowercase and map invalid values to valid ones"""
        if isinstance(v, str):
            v_lower = v.lower()
            # Map invalid severity values to valid enum values
            if v_lower in ['extreme', 'critical', 'very high', 'very_high']:
                return 'high'
            elif v_lower in ['moderate', 'medium-high', 'medium-low', 'med']:
                return 'medium'
            elif v_lower in ['very low', 'very_low', 'minimal']:
                return 'low'
            # Return lowercase version for valid values
            return v_lower
        return v

class ProvenanceBadge(BaseModel):
    """Data source provenance with vintage and confidence tracking"""
    source: str = Field(..., description="Source name (e.g., 'ENTSO-E Transparency Platform')")
    api_version: Optional[str] = Field(None, description="API version or dataset version")
    vintage: str = Field(..., description="Data vintage (e.g., '2025-01', 'Q4 2024', '<6 months')")
    refresh_frequency: Optional[str] = Field(None, description="How often data is updated (e.g., 'Monthly', 'Real-time')")
    confidence: Literal["high", "medium", "low"] = Field(..., description="Confidence level: High=<6mo site-specific, Med=official <2yr, Low=modeled")
    coverage: str = Field(..., description="Coverage notes (e.g., 'HV lines/substations', 'EU-wide grid data')")
    url: Optional[str] = Field(None, description="Source URL if available")

    @field_validator('confidence', mode='before')
    @classmethod
    def normalize_confidence(cls, v):
        """Normalize confidence to lowercase and map invalid values to valid ones"""
        if isinstance(v, str):
            v_lower = v.lower()
            # Map invalid confidence values to valid enum values
            if v_lower in ['very high', 'very_high', 'excellent']:
                return 'high'
            elif v_lower in ['moderate', 'fair']:
                return 'medium'
            elif v_lower in ['very low', 'very_low', 'poor']:
                return 'low'
            # Return lowercase version for valid values
            return v_lower
        return v

class TransactionalVerification(BaseModel):
    """Transactional artifacts that upgrade assumptions to facts"""
    verification_type: str = Field(..., description="Type (e.g., 'Utility Letter', 'Carrier Quote', 'PPA Quote', 'Land Registry')")
    provider: str = Field(..., description="Provider name (e.g., utility company, carrier, broker)")
    artifact_description: str = Field(..., description="What was verified")
    validity_period: Optional[str] = Field(None, description="How long this verification is valid")
    confidence_upgrade: str = Field(..., description="Confidence upgrade (e.g., 'preliminary → investment-grade')")
    attached: bool = Field(False, description="Whether artifact is attached to report")
    date_obtained: Optional[str] = Field(None, description="When verification was obtained")

class DistanceMeasurement(BaseModel):
    """Structured distance measurement with method tracking"""
    target: str = Field(..., description="Target (e.g., 'Nearest 220kV substation', 'Primary fiber POP')")
    distance_km: float = Field(..., description="Distance in kilometers")
    distance_mi: Optional[float] = Field(None, description="Distance in miles (auto-calculated)")
    method: Literal["road", "aerial", "rail", "fiber_route"] = Field("road", description="Measurement method")
    routing_buffer: Optional[float] = Field(None, description="Routing buffer percentage if aerial (typically +30%)")
    source: str = Field("Google Maps", description="Source of measurement (e.g., 'OSRM', 'OpenRouteService', 'Google Maps')")

    @field_validator('method', mode='before')
    @classmethod
    def normalize_method(cls, v):
        """Normalize distance measurement method to valid enum values"""
        if isinstance(v, str):
            v_lower = v.lower()
            # Map variations to valid enum values
            if 'road' in v_lower or 'approximate' in v_lower or 'driving' in v_lower or 'ground' in v_lower:
                return 'road'
            elif 'aerial' in v_lower or 'direct' in v_lower or 'proximity' in v_lower or 'air' in v_lower or 'straight' in v_lower or 'line' in v_lower:
                return 'aerial'
            elif 'rail' in v_lower or 'train' in v_lower:
                return 'rail'
            elif 'fiber' in v_lower or 'cable' in v_lower:
                return 'fiber_route'
            # Default fallback
            return 'road'
        return v

class LocationContext(BaseModel):
    """Structured location data model with investment-grade enhancements"""
    lat: float = Field(..., description="Latitude coordinate")
    lng: float = Field(..., description="Longitude coordinate")
    country: str = Field(..., description="Country name")
    location: str = Field(..., description="Formatted address or location name")
    justification: Optional[str] = Field(None, description="Why this location was selected for datacenter")
    site_notes: Optional[str] = Field(None, description="Optional site-specific notes from user")
    analysis_scale: Optional[str] = Field("parcel", description="Analysis scale: parcel/1km/5km/10km/regional/national")

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
    """Overall suitability assessment with investment-grade enhancements"""
    composite_score: float = Field(..., ge=-1.0, le=5.0, description="Weighted composite score or 0.0 if NO-GO")
    rating: str = Field(..., pattern="^(Excellent|Good|Moderate|Poor|NO-GO)$", description="Rating classification")
    recommendation: str = Field(..., description="Overall recommendation")
    no_go_triggered: bool = Field(False, description="Whether any NO-GO gate was triggered")
    failed_gates: List[str] = Field(default_factory=list, description="List of failed NO-GO gates")
    caution_count: int = Field(0, description="Number of caution flags raised")
    confidence_level: Optional[Literal["high", "medium", "low"]] = Field(None, description="Overall confidence in analysis")
    verification_percentage: Optional[float] = Field(None, description="Percentage of metrics verified vs assumed (0-100)")

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
    """Input for insights agent containing essential cross-domain data (7 domain agents per Expert Spec)"""
    location_context: Union[LocationContext, Dict[str, Any]]
    composite_score: float = Field(..., description="Overall composite score")
    power_analysis: DomainSummary
    network_analysis: DomainSummary
    climate_analysis: DomainSummary
    regulatory_esg_analysis: Optional[DomainSummary] = None  # MERGED regulatory + ESG domain (14% weight)
    # Remaining 3 domain agents per Expert Spec
    site_civil_analysis: Optional[DomainSummary] = None
    mechanical_thermal_analysis: Optional[DomainSummary] = None
    market_competition_analysis: Optional[DomainSummary] = None

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

class WeightedDomainScore(BaseModel):
    """Domain score with weight and contribution to composite"""
    domain_name: str = Field(..., description="Domain name")
    raw_score: float = Field(..., ge=1.0, le=5.0, description="Raw domain score (1.0-5.0)")
    weight: float = Field(..., ge=0.0, le=1.0, description="Weight in composite (0.0-1.0)")
    weighted_contribution: float = Field(..., description="Contribution to composite score (raw_score * weight)")
    no_go_gates_triggered: int = Field(0, description="Number of NO-GO gates triggered in this domain")
    caution_flags_count: int = Field(0, description="Number of caution flags in this domain")

class ReportSchema(BaseModel):
    """Complete report structure with investment-grade enhancements"""
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

    # INVESTMENT-GRADE ENHANCEMENTS (Chirisa-AI)
    weighted_domain_scores: Optional[List[WeightedDomainScore]] = Field(None, description="Domain scores with weights and contributions")
    all_no_go_gates: List[NoGoGate] = Field(default_factory=list, description="All NO-GO gates across domains")
    all_caution_flags: List[CautionFlag] = Field(default_factory=list, description="All caution flags across domains")
    provenance_summary: List[ProvenanceBadge] = Field(default_factory=list, description="Summary of data sources used")
    transactional_verifications: List[TransactionalVerification] = Field(default_factory=list, description="Transactional artifacts attached")
    distance_measurements: List[DistanceMeasurement] = Field(default_factory=list, description="Key distance measurements")

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
        regulatory_esg_result: Any = None,  # MERGED regulatory + ESG domain (14% weight)
        site_civil_result: Any = None,
        mechanical_thermal_result: Any = None,
        market_competition_result: Any = None
    ) -> DataGapAnalysis:
        """Create comprehensive data gap analysis from all 7 domain agent results"""
        all_data_gaps = []
        all_third_party = []
        all_assumptions = []

        # Collect from all 7 domain agents per Expert Spec
        agents = [power_result, network_result, climate_result]
        if regulatory_esg_result:
            agents.append(regulatory_esg_result)
        if site_civil_result:
            agents.append(site_civil_result)
        if mechanical_thermal_result:
            agents.append(mechanical_thermal_result)
        if market_competition_result:
            agents.append(market_competition_result)

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
        power_result: Any,  # PowerInfrastructureOutput (35% weight)
        network_result: Any,  # NetworkConnectivityOutput (15% weight)
        climate_result: Any,  # ClimateAnalysisOutput (12% weight)
        regulatory_esg_result: Any = None,  # MERGED RegulatoryESGOutput (14% weight)
        site_civil_result: Any = None,  # SiteCivilInfrastructureOutput (10% weight)
        mechanical_thermal_result: Any = None,  # MechanicalThermalOutput (8% weight)
        market_competition_result: Any = None,  # MarketCompetitionOutput (6% weight)
        insights_result: Any = None,  # Optional intelligent insights from insights_agent
        # INVESTMENT-GRADE ENHANCEMENTS (Chirisa-AI)
        weighted_domain_scores: Optional[List[WeightedDomainScore]] = None,
        all_no_go_gates: Optional[List[NoGoGate]] = None,
        all_caution_flags: Optional[List[CautionFlag]] = None,
        composite_score_override: Optional[float] = None  # Use weighted score instead of calculating
    ) -> "ReportSchema":
        """Create report from location context and 7 domain agent outputs per Expert Specification"""

        # Extract properties from all 7 domain agent results
        power_props = cls._extract_agent_properties(power_result)
        network_props = cls._extract_agent_properties(network_result)
        climate_props = cls._extract_agent_properties(climate_result)
        regulatory_esg_props = cls._extract_agent_properties(regulatory_esg_result) if regulatory_esg_result else None
        site_civil_props = cls._extract_agent_properties(site_civil_result) if site_civil_result else None
        mechanical_thermal_props = cls._extract_agent_properties(mechanical_thermal_result) if mechanical_thermal_result else None
        market_competition_props = cls._extract_agent_properties(market_competition_result) if market_competition_result else None

        # INVESTMENT-GRADE: Use weighted composite score if provided, otherwise fallback to simple average
        if composite_score_override is not None:
            composite_score = composite_score_override
            print(f"📊 Using weighted composite score: {composite_score:.2f}/5.0")
        else:
            # Fallback: Calculate simple average composite score from 7 domain agents
            scores = [
                power_props['overall_score'],
                network_props['overall_score'],
                climate_props['overall_score']
            ]

            # Add remaining 4 domain agents if available
            if regulatory_esg_props:
                scores.append(regulatory_esg_props['overall_score'])
            if site_civil_props:
                scores.append(site_civil_props['overall_score'])
            if mechanical_thermal_props:
                scores.append(mechanical_thermal_props['overall_score'])
            if market_competition_props:
                scores.append(market_competition_props['overall_score'])

            # Filter out failed scores (-1) and calculate average
            valid_scores = [s for s in scores if s > 0]
            composite_score = sum(valid_scores) / len(valid_scores) if valid_scores else -1.0
            print(f"⚠️ Using fallback simple average score: {composite_score:.2f}/5.0")

        # Determine rating with NO-GO support
        no_go_triggered = False
        failed_gate_names = []

        if all_no_go_gates:
            triggered_gates = [g for g in all_no_go_gates if g.triggered]
            if triggered_gates:
                no_go_triggered = True
                failed_gate_names = [g.gate_type for g in triggered_gates]
                composite_score = 0.0  # Override to 0.0 for NO-GO
                rating = "NO-GO"
                print(f"🚫 NO-GO TRIGGERED: {len(triggered_gates)} gate(s) - Score set to 0.0")

        if not no_go_triggered:
            if composite_score >= 4.5:
                rating = "Excellent"
            elif composite_score >= 3.5:
                rating = "Good"
            elif composite_score >= 2.5:
                rating = "Moderate"
            elif composite_score >= 1.0:
                rating = "Poor"
            else:
                rating = "Poor"  # For -1.0 or invalid scores

        # Build domain analysis using 7 domain agents per Expert Spec
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
            "regulatory_esg": DomainAnalysis(
                score=regulatory_esg_props['overall_score'] if regulatory_esg_props and regulatory_esg_props['overall_score'] > 0 else 1.0,
                key_findings=regulatory_esg_props['key_insights'][:3] if regulatory_esg_props else [],
                summary=regulatory_esg_props['executive_summary'] if regulatory_esg_props else ""
            ),
            "site_civil": DomainAnalysis(
                score=site_civil_props['overall_score'] if site_civil_props and site_civil_props['overall_score'] > 0 else 1.0,
                key_findings=site_civil_props['key_insights'][:3] if site_civil_props else [],
                summary=site_civil_props['executive_summary'] if site_civil_props else ""
            ),
            "mechanical_thermal": DomainAnalysis(
                score=mechanical_thermal_props['overall_score'] if mechanical_thermal_props and mechanical_thermal_props['overall_score'] > 0 else 1.0,
                key_findings=mechanical_thermal_props['key_insights'][:3] if mechanical_thermal_props else [],
                summary=mechanical_thermal_props['executive_summary'] if mechanical_thermal_props else ""
            ),
            "market_competition": DomainAnalysis(
                score=market_competition_props['overall_score'] if market_competition_props and market_competition_props['overall_score'] > 0 else 1.0,
                key_findings=market_competition_props['key_insights'][:3] if market_competition_props else [],
                summary=market_competition_props['executive_summary'] if market_competition_props else ""
            )
        }

        # Aggregate insights for executive summary from all 7 domain agents
        all_insights = (
            power_props['key_insights'] + network_props['key_insights'] +
            climate_props['key_insights']
        )

        # Add remaining domain agent insights if available
        if regulatory_esg_props:
            all_insights.extend(regulatory_esg_props['key_insights'])
        if site_civil_props:
            all_insights.extend(site_civil_props['key_insights'])
        if mechanical_thermal_props:
            all_insights.extend(mechanical_thermal_props['key_insights'])
        if market_competition_props:
            all_insights.extend(market_competition_props['key_insights'])

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

            # Fallback Phase 1 plan (simple capacity determination based on composite score)
            try:
                # Simple capacity determination based on composite score
                if composite_score >= 4.0:
                    capacity = "100-150 MW initial deployment with campus expansion potential"
                    investment = "$400-600 million USD Phase 1"
                    timeline = "18-24 months for Phase 1"
                elif composite_score >= 3.0:
                    capacity = "50-100 MW initial deployment with scalability planning"
                    investment = "$200-400 million USD Phase 1"
                    timeline = "24-30 months for Phase 1"
                else:
                    capacity = "25-50 MW pilot deployment with assessment period"
                    investment = "$100-200 million USD pilot phase"
                    timeline = "30-36 months for Phase 1"

                dynamic_phase1 = Phase1Deployment(
                    recommended_capacity=capacity,
                    timeline=timeline,
                    priority_actions=["Site acquisition", "Grid interconnection planning", "Regulatory approvals", "Infrastructure development", "Equipment procurement"],
                    estimated_investment=investment,
                    risk_mitigation=["Diversified power sources", "Redundant connectivity", "Local partnerships", "Phased rollout", "Continuous monitoring"]
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

        # Calculate verification percentage and confidence level
        verification_pct = None
        confidence_level = None
        if all_no_go_gates or all_caution_flags:
            # TODO: Implement actual verification tracking when agents provide provenance data
            # For now, estimate based on whether we have caution flags (indicates some verification)
            if all_caution_flags and len(all_caution_flags) > 0:
                verification_pct = 40.0  # Placeholder
                confidence_level = "medium"
            else:
                verification_pct = 30.0  # Placeholder
                confidence_level = "low"

        return cls(
            location=location_context.location,
            coordinates={"lat": location_context.lat, "lng": location_context.lng},
            country=location_context.country,
            analysis_date=datetime.now().strftime("%Y-%m-%d"),
            overall_suitability=OverallSuitability(
                composite_score=composite_score,
                rating=rating,
                recommendation=f"Location rated as {rating} for datacenter deployment" if not no_go_triggered else f"NO-GO: {', '.join(failed_gate_names[:3])}",
                no_go_triggered=no_go_triggered,
                failed_gates=failed_gate_names,
                caution_count=len(all_caution_flags) if all_caution_flags else 0,
                confidence_level=confidence_level,
                verification_percentage=verification_pct
            ),
            domain_analysis=domain_analysis,
            detailed_analysis={
                "power_infrastructure": power_props['executive_summary'],
                "network_connectivity": network_props['executive_summary'],
                "climate_environmental": climate_props['executive_summary'],
                **({"regulatory_esg": regulatory_esg_props['executive_summary']} if regulatory_esg_props else {}),
                **({"site_civil": site_civil_props['executive_summary']} if site_civil_props else {}),
                **({"mechanical_thermal": mechanical_thermal_props['executive_summary']} if mechanical_thermal_props else {}),
                **({"market_competition": market_competition_props['executive_summary']} if market_competition_props else {})
            },
            structured_analysis={
                "power_infrastructure": power_result,  # Store original domain agent objects (7 total per Expert Spec)
                "network_connectivity": network_result,
                "climate_environmental": climate_result,
                **({"regulatory_esg": regulatory_esg_result} if regulatory_esg_result else {}),
                **({"site_civil": site_civil_result} if site_civil_result else {}),
                **({"mechanical_thermal": mechanical_thermal_result} if mechanical_thermal_result else {}),
                **({"market_competition": market_competition_result} if market_competition_result else {})
            },
            executive_summary=executive_summary,
            phase_1_deployment=dynamic_phase1,
            strategic_opportunities=strategic_opportunities,
            strategic_recommendation=strategic_recommendation,
            conclusion=conclusion,
            next_steps=next_steps,
            insights_result=full_insights_result,
            data_gap_analysis=cls._create_data_gap_analysis(
                power_result, network_result, climate_result,
                regulatory_esg_result, site_civil_result,
                mechanical_thermal_result, market_competition_result
            ),
            # INVESTMENT-GRADE ENHANCEMENTS
            weighted_domain_scores=weighted_domain_scores if weighted_domain_scores else [],
            all_no_go_gates=[g.model_dump() if hasattr(g, 'model_dump') else g for g in (all_no_go_gates or [])],
            all_caution_flags=[f.model_dump() if hasattr(f, 'model_dump') else f for f in (all_caution_flags or [])],
            provenance_summary=[],  # TODO: Collect from agents when they provide provenance
            transactional_verifications=[],  # TODO: Add transactional verification support
            distance_measurements=[]  # TODO: Collect distance measurements from agents
        )