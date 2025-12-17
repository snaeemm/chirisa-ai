# domain_models.py - Domain-Specific Pydantic Models for Data Center Analysis
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from datetime import datetime
# Import investment-grade models
from .models import NoGoGate, CautionFlag, ProvenanceBadge, DistanceMeasurement, VerificationLevel

# ================================================================================================
# BASE MODELS FOR SHARED STRUCTURES
# ================================================================================================

class MetricsData(BaseModel):
    """Base model for storing quantitative metrics with proper typing"""
    numerical_values: Dict[str, Union[float, int, str]] = Field(default_factory=dict, description="Numerical metrics like MW, Tbps, USD/MWh")
    percentages: Dict[str, Union[float, int]] = Field(default_factory=dict, description="Percentage values like efficiency, uptime")
    ranges: Dict[str, Union[Dict[str, float], str, Any]] = Field(default_factory=dict, description="Min/max ranges for values (can be dict or string for data gaps)")
    units: Dict[str, str] = Field(default_factory=dict, description="Units for each metric")

class RichSection(BaseModel):
    """Enhanced section model that preserves structured data"""
    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)

    name: str = Field("", description="Section display name")
    content: str = Field("", description="Detailed textual analysis")
    sub_score: float = Field(1.0, ge=-1.0, le=5.0, description="Section scoring (-1 for not found/failed, 1.0-5.0 for scored)")
    metrics: MetricsData = Field(default_factory=MetricsData, description="Structured quantitative data")
    key_points: List[str] = Field(default_factory=list, description="Key findings for this section")
    tables: List[Dict[str, Any]] = Field(default_factory=list, description="Structured table data")
    verification_metadata: Dict[str, Union[str, Dict[str, Any]]] = Field(
        default_factory=dict,
        description="Maps statement keys to verification levels. Can be string ('verified_by_public_source') or dict with level, source, data_confidence, data_quality_flag (list)"
    )

    @field_validator('verification_metadata', mode='before')
    @classmethod
    def validate_verification_metadata(cls, v):
        """Ensure verification_metadata accepts both string and dict formats"""
        if not isinstance(v, dict):
            return {}

        validated = {}
        for key, value in v.items():
            # Accept strings directly
            if isinstance(value, str):
                validated[key] = value
            # Accept dicts with 'level' and optionally 'source', 'data_confidence', 'data_quality_flag', 'comparable_across_regions'
            elif isinstance(value, dict):
                if 'level' not in value:
                    raise ValueError(f"Dict format for verification_metadata must have 'level' key. Got: {value}")
                # Ensure only allowed keys exist (expanded to support API metadata)
                allowed_keys = {'level', 'source', 'data_confidence', 'data_quality_flag', 'comparable_across_regions'}
                if not set(value.keys()).issubset(allowed_keys):
                    extra_keys = set(value.keys()) - allowed_keys
                    raise ValueError(f"verification_metadata dict can only have {allowed_keys} keys. Extra keys found: {extra_keys}")
                validated[key] = value
            else:
                raise ValueError(f"verification_metadata values must be string or dict, got {type(value)}: {value}")

        return validated

    @field_validator('sub_score')
    @classmethod
    def validate_sub_score(cls, v):
        """Validate sub_score: allow -1.0 for failures, or clamp to 1.0-5.0 range"""
        if v == -1.0:
            # Allow -1.0 to indicate "not found" or "failed"
            return v
        # Clamp to valid scoring range
        if v < 1.0:
            return 1.0
        if v > 5.0:
            return 5.0
        return v

# ================================================================================================
# POWER INFRASTRUCTURE DOMAIN MODEL
# ================================================================================================

class PowerInfrastructureOutput(BaseModel):
    """Domain-specific model for Power Infrastructure Analysis - INVESTMENT-GRADE (Chirisa-AI)"""
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
    sources: List[Dict[str, str]] = Field(default_factory=list, description="Web sources: [{'url': '...', 'title': '...', 'date': '...', 'snippet': '...'}]")

    # INVESTMENT-GRADE ENHANCEMENTS (Chirisa-AI)
    no_go_gates: List[NoGoGate] = Field(default_factory=list, description="NO-GO gates for power domain")
    caution_flags: List[CautionFlag] = Field(default_factory=list, description="Caution flags requiring mitigation")
    provenance_badges: List[ProvenanceBadge] = Field(default_factory=list, description="Data source provenance")
    distance_measurements: List[DistanceMeasurement] = Field(default_factory=list, description="Distance to substations, transmission lines")

# ================================================================================================
# NETWORK CONNECTIVITY DOMAIN MODEL
# ================================================================================================

class NetworkConnectivityOutput(BaseModel):
    """Domain-specific model for Network Connectivity Analysis - INVESTMENT-GRADE (Chirisa-AI)"""
    overall_score: float = Field(..., ge=1.0, le=5.0, description="Overall network connectivity score")

    # Core Network Infrastructure Sections (8 subsections - expanded from 7)
    fiber_infrastructure: Optional[RichSection] = Field(None, description="Fiber density (km), coverage %, MAN infrastructure")
    last_mile_diversity: Optional[RichSection] = Field(None, description="CRITICAL: Physical route diversity, entrance facility diversity, carrier hotel proximity (NEW)")
    subsea_cables: Optional[RichSection] = Field(None, description="Cable landing points, specific systems, capacities (Tbps)")
    ixp_peering: Optional[RichSection] = Field(None, description="IXP presence, peering ecosystem, regional traffic exchange")
    carrier_diversity: Optional[RichSection] = Field(None, description="Carrier diversity, Tier-1 presence, market concentration")
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
    sources: List[Dict[str, str]] = Field(default_factory=list, description="Web sources: [{'url': '...', 'title': '...', 'date': '...', 'snippet': '...'}]")

    # INVESTMENT-GRADE ENHANCEMENTS (Chirisa-AI)
    no_go_gates: List[NoGoGate] = Field(default_factory=list, description="NO-GO gates for network domain (e.g., single fiber route)")
    caution_flags: List[CautionFlag] = Field(default_factory=list, description="Caution flags requiring mitigation")
    provenance_badges: List[ProvenanceBadge] = Field(default_factory=list, description="Data source provenance")
    distance_measurements: List[DistanceMeasurement] = Field(default_factory=list, description="Distance to POPs, IXPs, landing stations")

    @field_validator('executive_summary')
    @classmethod
    def validate_executive_summary_if_scored(cls, v, info):
        """If overall_score > 1.0, executive_summary should not be empty"""
        if hasattr(info.data, 'overall_score') and info.data.get('overall_score', 0) > 1.0:
            if not v or not v.strip():
                raise ValueError("executive_summary cannot be empty when overall_score > 1.0")
        return v

    @model_validator(mode='after')
    def validate_subsection_completeness(self):
        """Ensure at least 3 of 8 subsections are populated if overall_score > 1.0"""
        if self.overall_score > 1.0:
            subsection_fields = [
                self.fiber_infrastructure, self.last_mile_diversity, self.subsea_cables,
                self.ixp_peering, self.carrier_diversity, self.latency_performance,
                self.bandwidth_costs, self.future_proofing
            ]
            populated_count = sum(1 for field in subsection_fields if field is not None)

            if populated_count < 3:
                raise ValueError(
                    f"At least 3 of 8 subsections must be populated when overall_score > 1.0. "
                    f"Found only {populated_count} populated subsections."
                )
        return self

# ================================================================================================
# CLIMATE ANALYSIS DOMAIN MODEL
# ================================================================================================

class ClimateAnalysisOutput(BaseModel):
    """Domain-specific model for Climate Suitability Analysis - INVESTMENT-GRADE (Chirisa-AI)"""
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
    sources: List[Dict[str, str]] = Field(default_factory=list, description="Web sources: [{'url': '...', 'title': '...', 'date': '...', 'snippet': '...'}]")

    # INVESTMENT-GRADE ENHANCEMENTS (Chirisa-AI)
    no_go_gates: List[NoGoGate] = Field(default_factory=list, description="NO-GO gates for hazards/climate (e.g., FEMA V/VE zone, wildfire, PGA)")
    caution_flags: List[CautionFlag] = Field(default_factory=list, description="Caution flags requiring mitigation")
    provenance_badges: List[ProvenanceBadge] = Field(default_factory=list, description="Data source provenance (FEMA, NOAA, GEM, ERA5)")
    distance_measurements: List[DistanceMeasurement] = Field(default_factory=list, description="Distance measurements for hazard assessment")

# ================================================================================================
# SITE & CIVIL INFRASTRUCTURE DOMAIN MODEL
# ================================================================================================

class SiteCivilInfrastructureOutput(BaseModel):
    """Domain-specific model for Site & Civil Infrastructure Analysis - INVESTMENT-GRADE (Chirisa-AI)"""
    overall_score: float = Field(..., ge=1.0, le=5.0, description="Overall site & civil infrastructure score")

    # Core Site & Civil Sections (6 sections)
    land_availability: Optional[RichSection] = Field(None, description="Land availability (hectares), zoning, ownership, costs, expansion potential")
    geotechnical_conditions: Optional[RichSection] = Field(None, description="Soil bearing capacity (kPa), foundation requirements, groundwater, contamination")
    water_wastewater: Optional[RichSection] = Field(None, description="Water capacity (m³/day), WRI Aqueduct stress, wastewater, costs")
    transportation_access: Optional[RichSection] = Field(None, description="Road/airport/seaport distance, equipment delivery, weight limits")
    permitting_timeline: Optional[RichSection] = Field(None, description="Permitting timeline (months), EIA requirements, community engagement")
    civil_grading: Optional[RichSection] = Field(None, description="Topography, grading/earthwork, stormwater management")

    # Analysis Metadata
    assumptions: List[str] = Field(default_factory=list, description="Analysis assumptions")
    key_insights: List[str] = Field(default_factory=list, description="Key insights from analysis")
    executive_summary: str = Field("", description="Executive summary")
    data_gaps: List[str] = Field(default_factory=list, description="Identified data gaps requiring verification")
    third_party_verification: List[str] = Field(default_factory=list, description="Third-party services needed")
    phase_1_recommendations: Optional[Dict[str, str]] = Field(None, description="Domain-specific Phase 1 recommendations")
    sources: List[Dict[str, str]] = Field(default_factory=list, description="Web sources: [{'url': '...', 'title': '...', 'date': '...', 'snippet': '...'}]")

    # INVESTMENT-GRADE ENHANCEMENTS (Chirisa-AI)
    no_go_gates: List[NoGoGate] = Field(default_factory=list, description="NO-GO gates for site/civil (protected land, geotechnical, water)")
    caution_flags: List[CautionFlag] = Field(default_factory=list, description="Caution flags requiring mitigation")
    provenance_badges: List[ProvenanceBadge] = Field(default_factory=list, description="Data source provenance (WRI, USGS, local utilities)")
    distance_measurements: List[DistanceMeasurement] = Field(default_factory=list, description="Distance to airport, seaport, highways")

# ================================================================================================
# MECHANICAL & THERMAL SYSTEMS DOMAIN MODEL
# ================================================================================================

class MechanicalThermalOutput(BaseModel):
    """Domain-specific model for Mechanical & Thermal Systems Analysis - INVESTMENT-GRADE (Chirisa-AI)"""
    overall_score: float = Field(..., ge=1.0, le=5.0, description="Overall mechanical & thermal score")

    # Core Mechanical & Thermal Sections (7 sections)
    cooling_strategy: Optional[RichSection] = Field(None, description="Cooling strategy selection, PUE target, free cooling hours, CAPEX/OPEX")
    hvac_design: Optional[RichSection] = Field(None, description="HVAC redundancy (N+1, 2N), chiller/cooling tower capacity, air handling")
    thermal_resilience: Optional[RichSection] = Field(None, description="Ride-through time, failure modes, thermal mass, backup cooling")
    free_cooling_efficiency: Optional[RichSection] = Field(None, description="Free cooling hours, economizer type, energy savings, PUE improvement")
    water_consumption: Optional[RichSection] = Field(None, description="WUE (L/kWh), water consumption (m³/year), recycling, sustainability")
    mechanical_infrastructure: Optional[RichSection] = Field(None, description="Mechanical room space, equipment procurement, installation complexity")
    fire_suppression: Optional[RichSection] = Field(None, description="Fire suppression type (clean agent, water mist), life safety compliance")

    # Analysis Metadata
    assumptions: List[str] = Field(default_factory=list, description="Analysis assumptions")
    key_insights: List[str] = Field(default_factory=list, description="Key insights from analysis")
    executive_summary: str = Field("", description="Executive summary")
    data_gaps: List[str] = Field(default_factory=list, description="Identified data gaps requiring verification")
    third_party_verification: List[str] = Field(default_factory=list, description="Third-party services needed")
    phase_1_recommendations: Optional[Dict[str, str]] = Field(None, description="Domain-specific Phase 1 recommendations")
    sources: List[Dict[str, str]] = Field(default_factory=list, description="Web sources: [{'url': '...', 'title': '...', 'date': '...', 'snippet': '...'}]")

    # INVESTMENT-GRADE ENHANCEMENTS (Chirisa-AI)
    no_go_gates: List[NoGoGate] = Field(default_factory=list, description="NO-GO gates for mechanical/thermal (inadequate thermal resilience)")
    caution_flags: List[CautionFlag] = Field(default_factory=list, description="Caution flags requiring mitigation")
    provenance_badges: List[ProvenanceBadge] = Field(default_factory=list, description="Data source provenance (ASHRAE, Uptime Institute)")
    distance_measurements: List[DistanceMeasurement] = Field(default_factory=list, description="Mechanical-related distance measurements")

# ================================================================================================
# ESG SUSTAINABILITY DOMAIN MODEL
# ================================================================================================

class ESGSustainabilityOutput(BaseModel):
    """Domain-specific model for ESG & Sustainability Analysis - INVESTMENT-GRADE (Chirisa-AI)"""
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
    sources: List[Dict[str, str]] = Field(default_factory=list, description="Web sources: [{'url': '...', 'title': '...', 'date': '...', 'snippet': '...'}]")

    # INVESTMENT-GRADE ENHANCEMENTS (Chirisa-AI)
    no_go_gates: List[NoGoGate] = Field(default_factory=list, description="NO-GO gates for ESG domain")
    caution_flags: List[CautionFlag] = Field(default_factory=list, description="Caution flags requiring mitigation")
    provenance_badges: List[ProvenanceBadge] = Field(default_factory=list, description="Data source provenance (ElectricityMaps, WattTime)")
    distance_measurements: List[DistanceMeasurement] = Field(default_factory=list, description="ESG-related distance measurements")

# ================================================================================================
# OPERATIONAL RISK DOMAIN MODEL - DEPRECATED (per expert spec: risk feeds into other domains, not standalone)
# ================================================================================================
# NOTE: This model is kept for backward compatibility but is no longer used in the 7-agent architecture.
# Risk content has been integrated into: site_civil_agent (physical security), climate_agent (emergency response),
# regulatory_esg_agent (geopolitical/cyber), power_agent (infrastructure resilience), network_agent (connectivity resilience)

class OperationalRiskOutput(BaseModel):
    """Domain-specific model for Operational Risk Analysis - INVESTMENT-GRADE (Chirisa-AI)"""
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
    sources: List[Dict[str, str]] = Field(default_factory=list, description="Web sources: [{'url': '...', 'title': '...', 'date': '...', 'snippet': '...'}]")

    # INVESTMENT-GRADE ENHANCEMENTS (Chirisa-AI)
    no_go_gates: List[NoGoGate] = Field(default_factory=list, description="NO-GO gates for risk domain")
    caution_flags: List[CautionFlag] = Field(default_factory=list, description="Caution flags requiring mitigation")
    provenance_badges: List[ProvenanceBadge] = Field(default_factory=list, description="Data source provenance")
    distance_measurements: List[DistanceMeasurement] = Field(default_factory=list, description="Distance to military bases, borders, emergency services")

# ================================================================================================
# REGULATORY COMPLIANCE DOMAIN MODEL
# ================================================================================================

class RegulatoryComplianceOutput(BaseModel):
    """Domain-specific model for Regulatory Compliance Analysis - INVESTMENT-GRADE (Chirisa-AI)"""
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
    sources: List[Dict[str, str]] = Field(default_factory=list, description="Web sources: [{'url': '...', 'title': '...', 'date': '...', 'snippet': '...'}]")

    # INVESTMENT-GRADE ENHANCEMENTS (Chirisa-AI)
    no_go_gates: List[NoGoGate] = Field(default_factory=list, description="NO-GO gates for regulatory domain")
    caution_flags: List[CautionFlag] = Field(default_factory=list, description="Caution flags requiring mitigation")
    provenance_badges: List[ProvenanceBadge] = Field(default_factory=list, description="Data source provenance")
    distance_measurements: List[DistanceMeasurement] = Field(default_factory=list, description="Regulatory-related distance measurements")

# ================================================================================================
# MERGED REGULATORY & ESG DOMAIN MODEL (14% Composite Weight)
# ================================================================================================

class RegulatoryESGOutput(BaseModel):
    """MERGED domain model for Regulatory & ESG Compliance Analysis - INVESTMENT-GRADE (Chirisa-AI)

    This model merges regulatory compliance and ESG sustainability into ONE domain (14% weight per expert spec).
    Covers 5 subsections: A) Data Sovereignty, B) Government Incentives, C) Operational/Environmental Compliance,
    D) Permitting & Zoning, E) ESG Trajectory (carbon, renewable energy, climate policy).
    """
    overall_score: float = Field(..., ge=1.0, le=5.0, description="Overall regulatory & ESG compliance score (merged domain)")

    # 5 Core Subsections per Expert Specification
    data_sovereignty_privacy: Optional[RichSection] = Field(None, description="Data protection laws (GDPR/CCPA), localization requirements, cross-border transfers, cybersecurity frameworks (ISO 27001, SOC 2)")
    government_incentives: Optional[RichSection] = Field(None, description="Tax incentives, SEZ/FTZ benefits, import duty exemptions, foreign ownership restrictions, investment protection treaties")
    operational_environmental_compliance: Optional[RichSection] = Field(None, description="Building codes (IBC), fire safety (NFPA 75/76), EIA requirements, water permits, air emissions, noise limits, e-waste regulations, water stress (WRI Aqueduct)")
    permitting_zoning: Optional[RichSection] = Field(None, description="Zoning classification, use-by-right vs CUP, number of permits, permitting timeline (months), public hearings, fast-track programs")
    esg_trajectory: Optional[RichSection] = Field(None, description="Grid renewable % and carbon intensity (gCO₂/kWh), PPA market maturity, CFE accounting, carbon pricing ($/tonne), GHG reporting (TCFD/CDP/ISSB), net-zero targets, ESG reporting frameworks (GRI/SASB), LEED/BREEAM certifications, community engagement, NIMBY risk")

    # Analysis Metadata
    assumptions: List[str] = Field(default_factory=list, description="Analysis assumptions")
    key_insights: List[str] = Field(default_factory=list, description="Key insights from analysis")
    executive_summary: str = Field("", description="Executive summary covering regulatory and ESG readiness")
    data_gaps: List[str] = Field(default_factory=list, description="Identified data gaps requiring verification")
    third_party_verification: List[str] = Field(default_factory=list, description="Third-party services needed (legal counsel, PPA advisors, grid audit)")
    phase_1_recommendations: Optional[Dict[str, str]] = Field(None, description="Domain-specific Phase 1 recommendations")
    sources: List[Dict[str, str]] = Field(default_factory=list, description="Web sources: [{'url': '...', 'title': '...', 'date': '...', 'snippet': '...'}]")

    # INVESTMENT-GRADE ENHANCEMENTS (Chirisa-AI)
    no_go_gates: List[NoGoGate] = Field(default_factory=list, description="NO-GO gates for regulatory & ESG domain (e.g., prohibited cross-border data transfers)")
    caution_flags: List[CautionFlag] = Field(default_factory=list, description="Caution flags requiring mitigation (e.g., foreign ownership restrictions, high grid carbon intensity)")
    provenance_badges: List[ProvenanceBadge] = Field(default_factory=list, description="Data source provenance (DLA Piper, ElectricityMaps, WattTime, Investment Authority)")
    distance_measurements: List[DistanceMeasurement] = Field(default_factory=list, description="Regulatory & ESG-related distance measurements")

# ================================================================================================
# MARKET & COMPETITION DOMAIN MODEL (6% Composite Weight)
# ================================================================================================

class MarketCompetitionOutput(BaseModel):
    """Domain-specific model for Market & Competition Analysis - INVESTMENT-GRADE (Chirisa-AI)

    Per expert spec, covers 4 subsections: A) Competitive Landscape, B) Cloud Ecosystem & Demand,
    C) Peering Opportunities & Network Ecosystem, D) Strategic Positioning.
    """
    overall_score: float = Field(..., ge=1.0, le=5.0, description="Overall market & competition score")

    # 4 Core Subsections per Expert Specification
    competitive_landscape: Optional[RichSection] = Field(None, description="Existing DC capacity (MW), occupancy %, pipeline/absorption, pricing comps (USD/kW-mo; USD/acre), competitors within 100 km")
    cloud_ecosystem_demand: Optional[RichSection] = Field(None, description="Hyperscaler presence/regions (AWS/Azure/GCP), enterprise/regulated sector demand anchors")
    peering_network_ecosystem: Optional[RichSection] = Field(None, description="IXPs, carrier-neutral hubs, CDN presence, subsea proximity")
    strategic_positioning: Optional[RichSection] = Field(None, description="Regional access, incentives, time-zone coverage, geopolitical advantages")

    # Analysis Metadata
    assumptions: List[str] = Field(default_factory=list, description="Analysis assumptions")
    key_insights: List[str] = Field(default_factory=list, description="Key insights from analysis")
    executive_summary: str = Field("", description="Executive summary")
    data_gaps: List[str] = Field(default_factory=list, description="Identified data gaps requiring verification")
    third_party_verification: List[str] = Field(default_factory=list, description="Third-party services needed (CBRE, JLL, CoStar)")
    phase_1_recommendations: Optional[Dict[str, str]] = Field(None, description="Domain-specific Phase 1 recommendations")
    sources: List[Dict[str, str]] = Field(default_factory=list, description="Web sources: [{'url': '...', 'title': '...', 'date': '...', 'snippet': '...'}]")

    # INVESTMENT-GRADE ENHANCEMENTS (Chirisa-AI)
    no_go_gates: List[NoGoGate] = Field(default_factory=list, description="NO-GO gates for market/competition domain")
    caution_flags: List[CautionFlag] = Field(default_factory=list, description="Caution flags requiring mitigation")
    provenance_badges: List[ProvenanceBadge] = Field(default_factory=list, description="Data source provenance (CBRE, JLL, CoStar, Data Centre Map)")
    distance_measurements: List[DistanceMeasurement] = Field(default_factory=list, description="Distance to competitors, anchor customers, IXPs")

# ================================================================================================
# HYPERSCALER ATTRACTIVENESS DOMAIN MODEL - DEPRECATED (per expert spec: merged into market_competition_agent)
# ================================================================================================
# NOTE: This model is kept for backward compatibility but is no longer used in the 7-agent architecture.
# Hyperscaler content has been integrated into MarketCompetitionOutput subsections B (cloud ecosystem) and D (strategic positioning)

class HyperscalerAttractivenessOutput(BaseModel):
    """Domain-specific model for Hyperscaler Attractiveness Analysis - INVESTMENT-GRADE (Chirisa-AI)"""
    overall_score: float = Field(..., ge=1.0, le=5.0, description="Overall hyperscaler attractiveness score")

    # Core Hyperscaler Attractiveness Sections (7 sections including GTM feasibility)
    competitive_landscape: Optional[RichSection] = Field(None, description="Existing data centers, hyperscaler presence, pricing dynamics, supply-demand balance")
    cloud_ecosystem: Optional[RichSection] = Field(None, description="Cloud adoption rates, AWS/Azure/GCP presence, SaaS ecosystem, government digitization")
    peering_opportunities: Optional[RichSection] = Field(None, description="IXPs, interconnection facilities, CDN presence, submarine cables")
    proximity_to_demand: Optional[RichSection] = Field(None, description="Enterprise customers, government demand, financial services, anchor tenants")
    labor_market: Optional[RichSection] = Field(None, description="Technical workforce, salary competitiveness, educational institutions, immigration policies")
    gtm_feasibility: Optional[RichSection] = Field(None, description="Go-to-market feasibility, lease-up timeline, pre-leasing strategy, time-to-revenue analysis")
    strategic_relevance: Optional[RichSection] = Field(None, description="Geopolitical stability, market access, time zone advantages, government incentives")

    # Analysis Metadata
    assumptions: List[str] = Field(default_factory=list, description="Analysis assumptions")
    key_insights: List[str] = Field(default_factory=list, description="Key insights from analysis")
    executive_summary: str = Field("", description="Executive summary")
    data_gaps: List[str] = Field(default_factory=list, description="Identified data gaps requiring verification")
    third_party_verification: List[str] = Field(default_factory=list, description="Third-party services needed")
    phase_1_recommendations: Optional[Dict[str, str]] = Field(None, description="Domain-specific Phase 1 recommendations")
    sources: List[Dict[str, str]] = Field(default_factory=list, description="Web sources: [{'url': '...', 'title': '...', 'date': '...', 'snippet': '...'}]")

    # INVESTMENT-GRADE ENHANCEMENTS (Chirisa-AI)
    no_go_gates: List[NoGoGate] = Field(default_factory=list, description="NO-GO gates for market/competition domain")
    caution_flags: List[CautionFlag] = Field(default_factory=list, description="Caution flags requiring mitigation")
    provenance_badges: List[ProvenanceBadge] = Field(default_factory=list, description="Data source provenance (CBRE, JLL, CoStar)")
    distance_measurements: List[DistanceMeasurement] = Field(default_factory=list, description="Distance to competitors, anchor customers")

# ================================================================================================
# UTILITY FUNCTIONS FOR MODEL CONVERSION
# ================================================================================================

def convert_to_generic_agent_output(domain_output: Union[
    PowerInfrastructureOutput, NetworkConnectivityOutput, ClimateAnalysisOutput,
    SiteCivilInfrastructureOutput, MechanicalThermalOutput,
    RegulatoryESGOutput, MarketCompetitionOutput  # 7 domain models per expert spec
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

