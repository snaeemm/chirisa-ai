# domain_models.py - Domain-Specific Pydantic Models for Data Center Analysis
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime

# ================================================================================================
# BASE MODELS FOR SHARED STRUCTURES
# ================================================================================================

class MetricsData(BaseModel):
    """Base model for storing quantitative metrics with proper typing"""
    numerical_values: Dict[str, Union[float, int]] = Field(default_factory=dict, description="Numerical metrics like MW, Tbps, USD/MWh")
    percentages: Dict[str, float] = Field(default_factory=dict, description="Percentage values like efficiency, uptime")
    ranges: Dict[str, Dict[str, float]] = Field(default_factory=dict, description="Min/max ranges for values")
    units: Dict[str, str] = Field(default_factory=dict, description="Units for each metric")

class RichSection(BaseModel):
    """Enhanced section model that preserves structured data"""
    name: str = Field("", description="Section display name")
    content: str = Field("", description="Detailed textual analysis")
    sub_score: float = Field(1.0, ge=1.0, le=5.0, description="Section scoring")
    metrics: MetricsData = Field(default_factory=MetricsData, description="Structured quantitative data")
    key_points: List[str] = Field(default_factory=list, description="Key findings for this section")
    tables: List[Dict[str, Any]] = Field(default_factory=list, description="Structured table data")

# ================================================================================================
# POWER INFRASTRUCTURE DOMAIN MODEL
# ================================================================================================

class PowerInfrastructureOutput(BaseModel):
    """Domain-specific model for Power Infrastructure Analysis"""
    overall_score: float = Field(..., ge=1.0, le=5.0, description="Overall power infrastructure score")

    # Core Power Infrastructure Sections
    grid_reliability: Optional[RichSection] = Field(None, description="Grid reliability statistics, SAIDI/SAIFI metrics, outage data")
    power_capacity: Optional[RichSection] = Field(None, description="Available capacity (MW), transmission lines, scalability to 100MW+")
    generation_mix: Optional[RichSection] = Field(None, description="Power generation mix percentages, baseload stability, PPA options")
    connection_process: Optional[RichSection] = Field(None, description="Grid interconnection timelines, regulatory approvals, utility support")
    electricity_costs: Optional[RichSection] = Field(None, description="Industrial rates (USD/kWh), pricing structure, market competitiveness")
    cost_model: Optional[RichSection] = Field(None, description="20-year cost projections, escalation rates, market forecasts")
    industrial_heritage: Optional[RichSection] = Field(None, description="Proximity to industrial facilities, existing infrastructure, zoning")

    # Analysis Metadata
    assumptions: List[str] = Field(default_factory=list, description="Analysis assumptions")
    key_insights: List[str] = Field(default_factory=list, description="Key insights from analysis")
    executive_summary: str = Field("", description="Executive summary")
    data_gaps: List[str] = Field(default_factory=list, description="Identified data gaps requiring verification")
    third_party_verification: List[str] = Field(default_factory=list, description="Third-party services needed")
    phase_1_recommendations: Optional[Dict[str, str]] = Field(None, description="Domain-specific Phase 1 recommendations")

# ================================================================================================
# NETWORK CONNECTIVITY DOMAIN MODEL
# ================================================================================================

class NetworkConnectivityOutput(BaseModel):
    """Domain-specific model for Network Connectivity Analysis"""
    overall_score: float = Field(..., ge=1.0, le=5.0, description="Overall network connectivity score")

    # Core Network Infrastructure Sections
    fiber_infrastructure: Optional[RichSection] = Field(None, description="Fiber density (km), coverage %, MAN infrastructure")
    subsea_cables: Optional[RichSection] = Field(None, description="Cable landing points, specific systems, capacities (Tbps)")
    international_connectivity: Optional[RichSection] = Field(None, description="Global bandwidth (Tbps), peering relationships, IXP connections")
    domestic_peering: Optional[RichSection] = Field(None, description="Carrier diversity, IXP participants, traffic volumes")
    latency_performance: Optional[RichSection] = Field(None, description="RTT measurements (ms), CDN presence, network quality")
    bandwidth_costs: Optional[RichSection] = Field(None, description="Pricing (USD/Mbps/month), cost competitiveness, scalability")
    future_proofing: Optional[RichSection] = Field(None, description="AI/ML readiness, capacity expansion plans, investments")

    # Analysis Metadata
    assumptions: List[str] = Field(default_factory=list, description="Analysis assumptions")
    key_insights: List[str] = Field(default_factory=list, description="Key insights from analysis")
    executive_summary: str = Field("", description="Executive summary")
    data_gaps: List[str] = Field(default_factory=list, description="Identified data gaps requiring verification")
    third_party_verification: List[str] = Field(default_factory=list, description="Third-party services needed")
    phase_1_recommendations: Optional[Dict[str, str]] = Field(None, description="Domain-specific Phase 1 recommendations")

# ================================================================================================
# CLIMATE ANALYSIS DOMAIN MODEL
# ================================================================================================

class ClimateAnalysisOutput(BaseModel):
    """Domain-specific model for Climate Suitability Analysis"""
    overall_score: float = Field(..., ge=1.0, le=5.0, description="Overall climate suitability score")

    # Core Climate Analysis Sections
    temperature_humidity: Optional[RichSection] = Field(None, description="Temperature ranges (°C/°F), humidity levels, free cooling hours")
    cooling_strategy: Optional[RichSection] = Field(None, description="PUE calculations, HVAC requirements, energy consumption estimates")
    free_cooling: Optional[RichSection] = Field(None, description="Annual free cooling hours, cost savings, PUE improvements")
    seismic_geological: Optional[RichSection] = Field(None, description="Seismic activity, geological stability, building requirements")
    hydrological_flood: Optional[RichSection] = Field(None, description="Precipitation patterns, flood risk, elevation, drainage")
    wind_storm: Optional[RichSection] = Field(None, description="Wind patterns/speeds, storm frequency, design requirements")
    climate_extremes: Optional[RichSection] = Field(None, description="Heat waves, cold snaps, wildfire risk, climate projections")

    # Analysis Metadata
    assumptions: List[str] = Field(default_factory=list, description="Analysis assumptions")
    key_insights: List[str] = Field(default_factory=list, description="Key insights from analysis")
    executive_summary: str = Field("", description="Executive summary")
    data_gaps: List[str] = Field(default_factory=list, description="Identified data gaps requiring verification")
    third_party_verification: List[str] = Field(default_factory=list, description="Third-party services needed")
    phase_1_recommendations: Optional[Dict[str, str]] = Field(None, description="Domain-specific Phase 1 recommendations")

# ================================================================================================
# ESG SUSTAINABILITY DOMAIN MODEL
# ================================================================================================

class ESGSustainabilityOutput(BaseModel):
    """Domain-specific model for ESG & Sustainability Analysis"""
    overall_score: float = Field(..., ge=1.0, le=5.0, description="Overall ESG sustainability score")

    # Core ESG Analysis Sections
    renewable_energy: Optional[RichSection] = Field(None, description="Grid renewable %, PPA market maturity, carbon intensity (CO2/MWh)")
    carbon_climate_policy: Optional[RichSection] = Field(None, description="Carbon pricing ($/tonne), reporting requirements, offset markets")
    environmental_regulations: Optional[RichSection] = Field(None, description="EIA requirements, water regulations, GHG reporting, e-waste")
    social_community_impact: Optional[RichSection] = Field(None, description="Community engagement, labor laws, public perception, safety")
    corporate_governance: Optional[RichSection] = Field(None, description="ESG reporting frameworks, emissions tracking, certifications")

    # Analysis Metadata
    assumptions: List[str] = Field(default_factory=list, description="Analysis assumptions")
    key_insights: List[str] = Field(default_factory=list, description="Key insights from analysis")
    executive_summary: str = Field("", description="Executive summary")
    data_gaps: List[str] = Field(default_factory=list, description="Identified data gaps requiring verification")
    third_party_verification: List[str] = Field(default_factory=list, description="Third-party services needed")
    phase_1_recommendations: Optional[Dict[str, str]] = Field(None, description="Domain-specific Phase 1 recommendations")

# ================================================================================================
# OPERATIONAL RISK DOMAIN MODEL
# ================================================================================================

class OperationalRiskOutput(BaseModel):
    """Domain-specific model for Operational Risk Analysis"""
    overall_score: float = Field(..., ge=1.0, le=5.0, description="Overall operational risk score")

    # Core Risk Analysis Sections
    geopolitical_stability: Optional[RichSection] = Field(None, description="Political stability index, security threats, data access policies")
    physical_security: Optional[RichSection] = Field(None, description="Military proximity, crime rates, security regulations")
    emergency_response: Optional[RichSection] = Field(None, description="Response times (minutes), specialized services, partnerships")
    infrastructure_resilience: Optional[RichSection] = Field(None, description="Power/water/fiber resilience, historical outages, redundancy")
    economic_social_stability: Optional[RichSection] = Field(None, description="Currency stability, labor market, social perception")

    # Analysis Metadata
    assumptions: List[str] = Field(default_factory=list, description="Analysis assumptions")
    key_insights: List[str] = Field(default_factory=list, description="Key insights from analysis")
    executive_summary: str = Field("", description="Executive summary")
    data_gaps: List[str] = Field(default_factory=list, description="Identified data gaps requiring verification")
    third_party_verification: List[str] = Field(default_factory=list, description="Third-party services needed")
    phase_1_recommendations: Optional[Dict[str, str]] = Field(None, description="Domain-specific Phase 1 recommendations")

# ================================================================================================
# REGULATORY COMPLIANCE DOMAIN MODEL
# ================================================================================================

class RegulatoryComplianceOutput(BaseModel):
    """Domain-specific model for Regulatory Compliance Analysis"""
    overall_score: float = Field(..., ge=1.0, le=5.0, description="Overall regulatory compliance score")

    # Core Regulatory Analysis Sections
    data_sovereignty: Optional[RichSection] = Field(None, description="Data protection laws, residency requirements, transfer restrictions")
    government_incentives: Optional[RichSection] = Field(None, description="Tax incentives, SEZ benefits, import duty exemptions")
    operational_compliance: Optional[RichSection] = Field(None, description="Construction standards, environmental regulations, licensing")
    permitting_zoning: Optional[RichSection] = Field(None, description="Zoning approval, EIA requirements, permitting timelines (months)")

    # Analysis Metadata
    assumptions: List[str] = Field(default_factory=list, description="Analysis assumptions")
    key_insights: List[str] = Field(default_factory=list, description="Key insights from analysis")
    executive_summary: str = Field("", description="Executive summary")
    data_gaps: List[str] = Field(default_factory=list, description="Identified data gaps requiring verification")
    third_party_verification: List[str] = Field(default_factory=list, description="Third-party services needed")
    phase_1_recommendations: Optional[Dict[str, str]] = Field(None, description="Domain-specific Phase 1 recommendations")

# ================================================================================================
# HYPERSCALER ATTRACTIVENESS DOMAIN MODEL
# ================================================================================================

class HyperscalerAttractivenessOutput(BaseModel):
    """Domain-specific model for Hyperscaler Attractiveness Analysis"""
    overall_score: float = Field(..., ge=1.0, le=5.0, description="Overall hyperscaler attractiveness score")

    # Core Hyperscaler Attractiveness Sections (7 sections from screenshot)
    competitive_landscape: Optional[RichSection] = Field(None, description="Existing data centers, hyperscaler presence, pricing dynamics, supply-demand balance")
    cloud_ecosystem: Optional[RichSection] = Field(None, description="Cloud adoption rates, AWS/Azure/GCP presence, SaaS ecosystem, government digitization")
    peering_opportunities: Optional[RichSection] = Field(None, description="IXPs, interconnection facilities, CDN presence, submarine cables")
    proximity_to_demand: Optional[RichSection] = Field(None, description="Enterprise customers, government demand, financial services, anchor tenants")
    labor_market: Optional[RichSection] = Field(None, description="Technical workforce, salary competitiveness, educational institutions, immigration policies")
    infrastructure_scalability: Optional[RichSection] = Field(None, description="Land availability, utility scalability, transportation, long-term planning")
    strategic_relevance: Optional[RichSection] = Field(None, description="Geopolitical stability, market access, time zone advantages, government incentives")

    # Analysis Metadata
    assumptions: List[str] = Field(default_factory=list, description="Analysis assumptions")
    key_insights: List[str] = Field(default_factory=list, description="Key insights from analysis")
    executive_summary: str = Field("", description="Executive summary")
    data_gaps: List[str] = Field(default_factory=list, description="Identified data gaps requiring verification")
    third_party_verification: List[str] = Field(default_factory=list, description="Third-party services needed")
    phase_1_recommendations: Optional[Dict[str, str]] = Field(None, description="Domain-specific Phase 1 recommendations")

# ================================================================================================
# UTILITY FUNCTIONS FOR MODEL CONVERSION
# ================================================================================================

def convert_to_generic_agent_output(domain_output: Union[
    PowerInfrastructureOutput, NetworkConnectivityOutput, ClimateAnalysisOutput,
    ESGSustainabilityOutput, OperationalRiskOutput, RegulatoryComplianceOutput, HyperscalerAttractivenessOutput
]) -> "AgentOutput":
    """Convert domain-specific output back to generic AgentOutput for backward compatibility"""
    from .models import AgentOutput, AgentSection

    # Get all section attributes from the domain model
    sections = {}
    for field_name, field_value in domain_output.__dict__.items():
        if isinstance(field_value, RichSection):
            sections[field_name] = AgentSection(
                name=field_value.name,
                content=field_value.content,
                sub_score=field_value.sub_score
            )

    return AgentOutput(
        overall_score=domain_output.overall_score,
        sections=sections,
        assumptions=domain_output.assumptions,
        key_insights=domain_output.key_insights,
        executive_summary=domain_output.executive_summary,
        data_gaps=domain_output.data_gaps,
        third_party_verification=domain_output.third_party_verification,
        phase_1_recommendations=domain_output.phase_1_recommendations
    )

def extract_metrics_for_tables(rich_section: RichSection) -> Dict[str, Any]:
    """Extract structured metrics from RichSection for table generation"""
    table_data = {}

    # Add numerical values with units
    for metric, value in rich_section.metrics.numerical_values.items():
        unit = rich_section.metrics.units.get(metric, "")
        table_data[metric] = f"{value} {unit}".strip()

    # Add percentages
    for metric, value in rich_section.metrics.percentages.items():
        table_data[metric] = f"{value}%"

    # Add ranges
    for metric, range_data in rich_section.metrics.ranges.items():
        if "min" in range_data and "max" in range_data:
            unit = rich_section.metrics.units.get(metric, "")
            table_data[f"{metric}_range"] = f"{range_data['min']}-{range_data['max']} {unit}".strip()

    return table_data

