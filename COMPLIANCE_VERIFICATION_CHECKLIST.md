# Chirisa-AI Expert Specification Compliance Verification Checklist

**Document Version**: 1.0
**Date**: 2025-11-06
**Purpose**: Systematic verification that the Chirisa-AI codebase complies with the Expert Specification document for investment-grade datacenter site analysis.

---

## ✅ PHASE 1: Agent Architecture (7 Domain Agents)

### 1.1 Agent Count Verification

**Requirement**: Exactly 7 domain agents matching the expert spec weights

| Agent | File | Weight | Status |
|-------|------|--------|--------|
| Power & Energy | `agent/power_agent.py` | 35% | ✅ EXISTS |
| Network Connectivity | `agent/network_agent.py` | 15% | ✅ EXISTS |
| Site & Civil | `agent/site_civil_agent.py` | 10% | ✅ EXISTS |
| Hazards & Resilience | `agent/climate_agent.py` | 12% | ✅ EXISTS |
| Mechanical & Thermal | `agent/mechanical_thermal_agent.py` | 8% | ✅ EXISTS |
| Regulatory & ESG (MERGED) | `agent/regulatory_esg_agent.py` | 14% | ✅ EXISTS |
| Market & Competition | `agent/market_competition_agent.py` | 6% | ✅ EXISTS |

**Verification Steps**:
```bash
cd /Users/shahzeb.naeem/Desktop/Projects/shaz/shaz/agent
ls -1 *_agent.py | grep -E "(power|network|site_civil|climate|mechanical|regulatory_esg|market)" | wc -l
# Expected output: 7
```

**Status**: ✅ PASS (7 domain agents confirmed)

---

### 1.2 Obsolete Agents Removed

**Requirement**: Remove agents not in expert spec

| Removed Agent | Reason | Status |
|---------------|--------|--------|
| `risk_agent.py` | Risk feeds into other domains, not standalone | ✅ DELETED |
| `hyperscaler_agent.py` | Merged into market_competition_agent | ✅ DELETED |
| `regulatory_agent.py` | Merged with ESG into regulatory_esg_agent | ✅ DELETED |
| `esg_agent.py` | Merged with regulatory into regulatory_esg_agent | ✅ DELETED |

**Verification Steps**:
```bash
# Verify these files DO NOT exist
test ! -f agent/risk_agent.py && echo "✅ risk_agent deleted" || echo "❌ risk_agent still exists"
test ! -f agent/hyperscaler_agent.py && echo "✅ hyperscaler_agent deleted" || echo "❌ hyperscaler_agent still exists"
test ! -f agent/regulatory_agent.py && echo "✅ regulatory_agent deleted" || echo "❌ regulatory_agent still exists"
test ! -f agent/esg_agent.py && echo "✅ esg_agent deleted" || echo "❌ esg_agent still exists"
```

**Status**: ✅ PASS

---

## ✅ PHASE 2: Composite Scoring & Weights

### 2.1 Domain Weights Configuration

**File**: `agent/synthesis_agents.py` (lines 30-39)

**Requirement**: Weights must total 100% and match expert spec exactly

| Domain | Expert Spec Weight | Code Weight | Status |
|--------|-------------------|-------------|--------|
| power_energy | 35% | 0.35 | ✅ MATCH |
| network_connectivity | 15% | 0.15 | ✅ MATCH |
| site_civil | 10% | 0.10 | ✅ MATCH |
| hazards_resilience | 12% | 0.12 | ✅ MATCH |
| mechanical_thermal | 8% | 0.08 | ✅ MATCH |
| regulatory_esg | 14% | 0.14 | ✅ MATCH |
| market_competition | 6% | 0.06 | ✅ MATCH |
| **TOTAL** | **100%** | **1.00** | ✅ PASS |

**Verification Steps**:
```python
# In Python REPL or test script:
from agent.synthesis_agents import DOMAIN_WEIGHTS
assert sum(DOMAIN_WEIGHTS.values()) == 1.0, "Weights must sum to 100%"
assert DOMAIN_WEIGHTS["power_energy"] == 0.35
assert DOMAIN_WEIGHTS["network_connectivity"] == 0.15
assert DOMAIN_WEIGHTS["site_civil"] == 0.10
assert DOMAIN_WEIGHTS["hazards_resilience"] == 0.12
assert DOMAIN_WEIGHTS["mechanical_thermal"] == 0.08
assert DOMAIN_WEIGHTS["regulatory_esg"] == 0.14
assert DOMAIN_WEIGHTS["market_competition"] == 0.06
print("✅ All weights match expert spec")
```

**Status**: ✅ PASS

---

### 2.2 Weighted Scoring Logic

**File**: `agent/synthesis_agents.py` (function: `calculate_weighted_composite_score`)

**Requirement**: NO-GO gate override + weighted average + caution penalties

**Checklist**:
- [ ] **NO-GO Override**: If any NO-GO gate triggered → composite_score = 0.0 (lines 106-123)
- [ ] **Weighted Sum**: `weighted_sum = Σ(domain_score × domain_weight)` (lines 130-135)
- [ ] **Caution Penalty**: `caution_penalty = Σ(flag.severity_points)` for all caution flags (lines 138-145)
- [ ] **Final Score**: `max(1.0, weighted_sum - caution_penalty)` clamped to [1.0, 5.0] (line 147)
- [ ] **Score Range**: Output is float between 0.0 (NO-GO) or [1.0, 5.0] (valid scores)

**Verification Steps**:
```bash
# Check NO-GO logic exists
grep -n "NO-GO.*triggered" agent/synthesis_agents.py
# Expected: Lines showing "if any_no_go_triggered: return 0.0"

# Check weighted sum calculation
grep -n "weighted_sum.*weight" agent/synthesis_agents.py
# Expected: Lines showing domain_score * DOMAIN_WEIGHTS[domain]

# Check caution penalty
grep -n "severity_points" agent/synthesis_agents.py
# Expected: Lines showing caution flag severity deduction
```

**Status**: ⚠️ NEEDS VERIFICATION (manual code review required)

---

## ✅ PHASE 3: Agent Subsection Structure

### 3.1 Power & Energy Agent (35%)

**File**: `agent/power_agent.py`

**Expert Spec Requirements** (7 subsections A-G):
- [ ] **A. Grid Reliability & Quality**: SAIDI/SAIFI, frequency (±0.1 Hz), voltage (±5%), THD (<5% V, <20% I), flicker (IEC 61000-4-15), short-circuit MVA (≥250 MVA target)
- [ ] **B. Capacity & Interconnection**: Nearest HV level, distance to substation, available capacity, interconnection timeline, MV architecture
- [ ] **C. Backup Power & Fuel Logistics**: Generator topology (N+1/2N), autonomy (72-96h), UST permitting, alternative fuels (LNG/H2)
- [ ] **D. Cost & Carbon**: Tariff structure ($/kWh + demand charges), 20-yr LCOE, carbon intensity (gCO2/kWh), PPA options

**NO-GO Gates**:
- [ ] PCC short-circuit <100 MVA OR THDv >8% without mitigation → NO-GO

**Standards Referenced**:
- [ ] IEEE 519-2014 (THD limits)
- [ ] IEC 61000 (EMC)
- [ ] IEC 61936, IEEE C37 (switchgear)
- [ ] ASHRAE 90.4 (energy efficiency)

**Verification Steps**:
```bash
# Check prompt includes subsections A-G
grep -i "Grid Reliability\|Capacity.*Interconnection\|Backup Power\|Cost.*Carbon" agent/power_agent.py

# Check NO-GO gates
grep -i "NO-GO\|100 MVA\|THD.*8%" agent/power_agent.py

# Check standards
grep -E "IEEE 519|IEC 61000|ASHRAE 90\.4" agent/power_agent.py
```

**Status**: ⚠️ NEEDS VERIFICATION

---

### 3.2 Network Connectivity Agent (15%)

**File**: `agent/network_agent.py`

**Expert Spec Requirements** (6 subsections A-F):
- [ ] **A. Fiber Infrastructure**: Backbone density, MAN rings, last-mile redundancy
- [ ] **B. Site-Level Last-Mile**: Two physically diverse POPs, entrance facility diversity (no shared conduit first 500m), lateral construction estimate, IXP distance
- [ ] **C. Subsea Cables**: Nearest landing stations (names/systems), diversity count, latency to landing (SubmarineCableMap)
- [ ] **D. International Peering & Domestic IX**: Global reach (AMS-IX/DE-CIX), IXP participants/traffic
- [ ] **E. Latency & CDN Presence**: RIPE Atlas measurements to key metros, packet loss/jitter, CDN/cloud POPs
- [ ] **F. Bandwidth Costs & Scalability**: IP transit pricing (10/100/400G), dark fiber, term discounts

**NO-GO Gates**:
- [ ] Only one buildable physical fiber route within 18 months → NO-GO

**Standards Referenced**:
- [ ] PeeringDB (IXPs)
- [ ] SubmarineCableMap (landing systems)
- [ ] RIPE Atlas (measured latency)

**Verification Steps**:
```bash
grep -i "POP.*divers\|SubmarineCableMap\|RIPE Atlas\|IXP\|single.*route" agent/network_agent.py
```

**Status**: ⚠️ NEEDS VERIFICATION

---

### 3.3 Site & Civil Agent (10%)

**File**: `agent/site_civil_agent.py`

**Expert Spec Requirements** (4 subsections A-D):
- [ ] **A. Parcel Physical**: Parcel size (ha), buildable % after setbacks, topography/slope, cut/fill volumes, soil class (bearing capacity 150-250 kPa), drainage features
- [ ] **B. Access & Logistics**: Frontage classification, motorway/port/airport road-km, heavy-haul feasibility (bridge loads, turning radii), staging/laydown (~40% building footprint), concrete supply (batch plants <30 km), workforce accommodation
- [ ] **C. Land Acquisition & Development**: Title status, ownership complexity, comps (USD/acre), Phase I/II ESA triggers, site-prep cost ladder
- [ ] **D. Stormwater & Drainage**: Impervious area uplift, detention/retention volumes, BMPs (bioswales/LID), regulatory triggers (NPDES), 100-yr storm impacts

**NO-GO Gates**:
- [ ] Protected land (WDPA/Natura 2000 strict categories) → NO-GO
- [ ] Zoning incompatibility (prohibited use) → NO-GO
- [ ] Title cloud (unresolvable ownership dispute) → NO-GO
- [ ] Severe groundwater contamination without remediation plan → NO-GO

**Standards Referenced**:
- [ ] Uptime Institute Tier Standards (2-5 hectares for 50 MW)
- [ ] ASCE 7-22 (bearing capacity 150-250 kPa)
- [ ] WRI Aqueduct (water stress)

**Verification Steps**:
```bash
grep -i "parcel\|staging\|laydown\|stormwater\|detention\|WDPA\|protected.*land\|title" agent/site_civil_agent.py
```

**Status**: ⚠️ NEEDS VERIFICATION

---

### 3.4 Hazards & Resilience Agent (12%)

**File**: `agent/climate_agent.py`

**Expert Spec Requirements** (5 subsections A-E):
- [ ] **A. Seismic & Geological**: PGA (Peak Ground Acceleration), soils, foundation class
- [ ] **B. Hydrological & Flood**: FEMA zones (V/VE/A), BFE (Base Flood Elevation) vs FF (Finished Floor), 100/500-yr flood, historical events
- [ ] **C. Wind, Storm & Wildfire**: Design wind speeds (ASCE 7), wildfire severity (NIFC/CAMS), mitigation feasibility
- [ ] **D. Climate Extremes & 2050 Projections**: NEX-GDDP projections, temperature/humidity deltas affecting PUE, equipment derating trends
- [ ] **E. Protected Areas**: WDPA/Natura 2000 constraints, buffer zones

**NO-GO Gates**:
- [ ] FEMA V/VE flood zones OR Zone A where BFE > design FF and raising impractical → NO-GO
- [ ] Wildfire "Very High" severity at parcel center with no feasible mitigations → NO-GO
- [ ] PGA beyond policy limits (e.g., >0.5g) with no capex headroom → NO-GO
- [ ] Inside WDPA/Natura 2000 strict categories or policy buffers → NO-GO

**Standards Referenced**:
- [ ] ASHRAE TC 9.9 (climate standards)
- [ ] FEMA flood maps
- [ ] USGS/GEM seismic hazard maps
- [ ] NIFC/CAMS wildfire severity
- [ ] NFPA 75/76/2001 (fire/life safety)

**Verification Steps**:
```bash
grep -i "FEMA\|PGA\|wildfire\|seismic\|flood.*zone\|WDPA\|protected" agent/climate_agent.py
```

**Status**: ⚠️ NEEDS VERIFICATION

---

### 3.5 Mechanical & Thermal Agent (8%)

**File**: `agent/mechanical_thermal_agent.py`

**Expert Spec Requirements** (3 subsections A-C):
- [ ] **A. Cooling Topology & Redundancy**: Air-cooled vs evap vs adiabatic vs hybrid; N+1 vs 2N cost deltas; liquid-cooling readiness (rear-door/DTCh/immersion) for 30-50 kW/rack
- [ ] **B. Free-Cooling & PUE Envelope**: ERA5/EPW-based economiser hours (≤18°C DB target), monthly profile, feasible PUE bands (≤1.25 / ≤1.40 / ≥1.60)
- [ ] **C. Water Treatment & Chemistry**: Make-up & blowdown volumes, TDS/biological load, treatment capex/opex, Legionella controls

**Standards Referenced**:
- [ ] ASHRAE TC 9.9 (climate classes)
- [ ] ASHRAE 90.4 (energy efficiency)
- [ ] EN 50600-2-3 (cooling)

**Verification Steps**:
```bash
grep -i "PUE\|economiser\|free.*cooling\|liquid.*cooling\|water.*treatment\|Legionella" agent/mechanical_thermal_agent.py
```

**Status**: ⚠️ NEEDS VERIFICATION

---

### 3.6 Regulatory & ESG Agent (14% - MERGED)

**File**: `agent/regulatory_esg_agent.py`

**Expert Spec Requirements** (5 subsections A-E):
- [ ] **A. Data Sovereignty & Privacy**: GDPR/CCPA/PDPA, localization requirements, cross-border transfer mechanisms (BCR/SCC/adequacy), government access risk, breach penalties, cybersecurity frameworks (ISO 27001, SOC 2, NERC CIP)
- [ ] **B. Government Incentives & Investment Climate**: SEZ/FTZ, tax holidays (% & years), import duty exemptions, foreign ownership caps, investment protection treaties (BIT/ICSID), currency repatriation
- [ ] **C. Operational & Environmental Compliance**: Building codes (IBC/Eurocode), fire safety (NFPA 75/76), EIA requirements (scope, timeline), water permits, air emissions (generator NOx/PM limits), noise limits (dBA at property line), e-waste (WEEE Directive), water stress (WRI Aqueduct)
- [ ] **D. Permitting & Zoning Framework**: Zoning status (use-by-right vs CUP vs rezone), number of permits required, permitting timeline (min/likely/max), permit fees (USD), public hearing requirements, fast-track programs, historical approval rates
- [ ] **E. ESG Trajectory (Policy & Carbon)**: Grid renewable % and carbon intensity (gCO2/kWh per ElectricityMaps/WattTime), PPA market maturity, CFE accounting availability (hourly matching), carbon pricing (USD/tonne via ETS/carbon tax), GHG reporting requirements (GHG Protocol Scope 1/2/3, TCFD, CDP, ISSB), net-zero targets (national & grid operator), ESG reporting frameworks (GRI, SASB, ISSB), sustainability certifications (LEED, BREEAM), community engagement, NIMBY risk

**NO-GO Gates**:
- [ ] Prohibited cross-border data transfers with no legal mechanism (SCC/BCR/adequacy) AND business requires international data flows → NO-GO

**CAUTION FLAGS**:
- [ ] **Restrictive Data Localization**: Mandatory for specific sectors OR strict government access → 0.4-0.7 deduction, +$5-15M
- [ ] **Foreign Ownership Restrictions**: Cap <50% OR critical infrastructure approval required → 0.4-0.6 deduction, +$3-10M
- [ ] **Complex Environmental Compliance**: EIA >12 months OR strict emissions/noise limits → 0.3-0.5 deduction, +$2-8M, +6-18 months
- [ ] **Permitting Complexity**: >10 permits OR >24 months timeline OR rezoning OR public hearings → 0.5-0.8 deduction, +$5-15M, +12-24 months
- [ ] **High Grid Carbon Intensity**: >400 gCO2/kWh OR renewable <20% OR no PPA market → 0.4-0.7 deduction, +$10-30M

**Standards Referenced**:
- [ ] GDPR Article 44-50, CCPA/CPRA, PDPA, ISO 27001/27017/27018, SOC 2, NERC CIP
- [ ] OECD Guidelines, World Bank Ease of Doing Business
- [ ] IBC, NFPA 75/76, ISO 14001, NEPA, EU WEEE Directive, WRI Aqueduct, ISO 50001
- [ ] World Bank Dealing with Construction Permits
- [ ] ElectricityMaps, WattTime MOER, RE100, TCFD, CDP, ISSB, GHG Protocol, GRI, SASB, LEED, BREEAM, ILO, ISO 45001

**Verification Steps**:
```bash
# Check all 5 subsections present
grep -i "Data Sovereignty\|Government Incentives\|Operational.*Environmental\|Permitting.*Zoning\|ESG Trajectory" agent/regulatory_esg_agent.py

# Check MERGED prompt mentions both regulatory AND ESG
grep -i "regulatory.*ESG\|ESG.*regulatory" agent/regulatory_esg_agent.py

# Check standards
grep -E "GDPR|ISO 27001|ElectricityMaps|WattTime|TCFD|GHG Protocol" agent/regulatory_esg_agent.py
```

**Status**: ⚠️ NEEDS VERIFICATION

---

### 3.7 Market & Competition Agent (6%)

**File**: `agent/market_competition_agent.py`

**Expert Spec Requirements** (4 subsections A-D):
- [ ] **A. Competitive Landscape**: Existing DC capacity (MW), occupancy %, pipeline/absorption, pricing comps (USD/kW-mo; USD/acre), notable competitors within 100 km (distance, MW)
- [ ] **B. Cloud Ecosystem & Demand**: Hyperscaler presence/region lists (AWS/Azure/GCP), enterprise/regulated sector demand anchors
- [ ] **C. Peering Opportunities & Network Ecosystem**: IXPs, carrier-neutral hubs, CDN presence, subsea proximity
- [ ] **D. Strategic Positioning**: Regional access, incentives, time-zone coverage

**Standards Referenced**:
- [ ] Data Centre Map, Cloudscene (if licensed)
- [ ] CBRE/JLL/C&W market reports (if licensed)
- [ ] LoopNet (listings/comps)

**Verification Steps**:
```bash
grep -i "competitive\|hyperscaler\|cloud.*ecosystem\|peering\|strategic.*position" agent/market_competition_agent.py
```

**Status**: ⚠️ NEEDS VERIFICATION

---

## ✅ PHASE 4: NO-GO Gates Implementation

### 4.1 Power NO-GO Gates

**File**: `agent/power_agent.py`

| NO-GO Gate | Trigger Condition | Standard Reference | Status |
|------------|-------------------|-------------------|--------|
| Low Short-Circuit Capacity | PCC <100 MVA for ≥50MW campus | IEEE 519 | ⚠️ CHECK |
| High THD | THDv >8% without funded mitigation | IEEE 519-2014 | ⚠️ CHECK |
| No Credible Grid Path | No credible grid path <5 years (queue, private-wire, binding PPA) | Utility policy | ⚠️ CHECK |

**Verification**: Check agent prompt includes these NO-GO triggers and standard references.

---

### 4.2 Network NO-GO Gates

**File**: `agent/network_agent.py`

| NO-GO Gate | Trigger Condition | Standard Reference | Status |
|------------|-------------------|-------------------|--------|
| Single Fiber Route | Only one viable physical route within 18 months | Redundancy best practice | ⚠️ CHECK |

---

### 4.3 Site & Civil NO-GO Gates

**File**: `agent/site_civil_agent.py`

| NO-GO Gate | Trigger Condition | Standard Reference | Status |
|------------|-------------------|-------------------|--------|
| Protected Land | Inside WDPA/Natura 2000 strict categories or policy buffers | WDPA/Natura 2000 | ⚠️ CHECK |
| Title Cloud | Unresolvable ownership dispute, liens, easements blocking development | Legal due diligence | ⚠️ CHECK |
| Severe Contamination | Brownfield CERCLA-level contamination without remediation plan/budget | CERCLA (US) / equivalent | ⚠️ CHECK |

---

### 4.4 Hazards NO-GO Gates

**File**: `agent/climate_agent.py`

| NO-GO Gate | Trigger Condition | Standard Reference | Status |
|------------|-------------------|-------------------|--------|
| FEMA Flood Zones | FEMA V/VE or Zone A where BFE > design FF and raising impractical | FEMA flood maps | ⚠️ CHECK |
| Extreme Wildfire | "Very High" severity at parcel center with no feasible mitigations | NIFC/CAMS | ⚠️ CHECK |
| Extreme Seismic | PGA beyond policy limits with no capex headroom | USGS/GEM seismic maps | ⚠️ CHECK |
| Protected Areas | Inside WDPA/Natura 2000 strict categories | WDPA protected areas database | ⚠️ CHECK |

---

### 4.5 Regulatory & ESG NO-GO Gates

**File**: `agent/regulatory_esg_agent.py`

| NO-GO Gate | Trigger Condition | Standard Reference | Status |
|------------|-------------------|-------------------|--------|
| Prohibited Data Transfers | Absolute prohibition on cross-border data transfer with no legal mechanism (SCC, BCR, adequacy) AND business requires international data flows | GDPR Article 44-50; China Cybersecurity Law Article 37 | ⚠️ CHECK |

---

### 4.6 Other NO-GO Gates (Per Expert Spec)

| NO-GO Gate | Trigger Condition | Which Agent Should Check | Status |
|------------|-------------------|--------------------------|--------|
| Airport/Military Airspace | Prohibited airspace or critical safety buffer that precludes permitted height or RF compliance | ❓ site_civil OR hazards? | ⚠️ ASSIGN |
| UST Fuel Storage | UST >50,000 gallons not permitted for required generator autonomy (or no alternative fuel plan) | ❓ power OR site_civil? | ⚠️ ASSIGN |

**Action Required**: Determine which agent should implement these NO-GO checks.

---

## ✅ PHASE 5: Caution Flags & Thresholds

### 5.1 Caution Flag Model Validation

**File**: `agent/models.py`

**Requirements**:
- [ ] `CautionFlag` model includes: `category`, `severity` (low/medium/high), `description`, `mitigation_plan`, `cost_impact`, `timeline_impact`, `severity_points` (0.0-1.0)
- [ ] Severity mapping: low (0.2-0.3), medium (0.3-0.5), high (0.5-0.8)

**Verification Steps**:
```python
from agent.models import CautionFlag
flag = CautionFlag(
    category="Test",
    severity="high",
    description="Test",
    mitigation_plan="Test",
    cost_impact="+$5M",
    timeline_impact="+6 months",
    severity_points=0.7
)
assert flag.severity in ["low", "medium", "high"]
assert 0.0 <= flag.severity_points <= 1.0
```

**Status**: ⚠️ CHECK

---

### 5.2 Caution Flag Thresholds (Per Expert Spec)

| Caution Flag | Trigger Condition | Severity | Cost Impact | Timeline Impact | Score Deduction | Agent | Status |
|--------------|-------------------|----------|-------------|-----------------|-----------------|-------|--------|
| PGA 0.3-0.5g | Moderate seismic risk | Medium | +15-25% structural | N/A | 0.3-0.5 | climate | ⚠️ CHECK |
| Water Stress High | WRI Aqueduct "High" but TSE feasible | Medium | +$5-15M treatment | N/A | 0.3-0.5 | climate OR mechanical | ⚠️ CHECK |
| Grid Interconnection Delay | >36 months or long-lead transformer constraints | Medium-High | Carrying costs | +12-36 months | 0.4-0.6 | power | ⚠️ CHECK |
| Single POP Only | One carrier-neutral POP, second lateral pending | Medium | +$0.5-2M lateral + MMR | +6-12 months | 0.3-0.5 | network | ⚠️ CHECK |
| NIMBY Risk | Community opposition risk | Medium | +$2-5M engagement | +6-18 months | 0.3-0.5 | regulatory_esg OR site_civil | ⚠️ CHECK |
| Restrictive Data Localization | Sector-specific OR government access | Medium-High | +$5-15M multi-region | N/A | 0.4-0.7 | regulatory_esg | ⚠️ CHECK |
| Foreign Ownership <50% | JV or local partner required | Medium-High | +$3-10M structuring | N/A | 0.4-0.6 | regulatory_esg | ⚠️ CHECK |
| Complex EIA | >12 months OR strict limits | Medium | +$2-8M | +6-18 months | 0.3-0.5 | regulatory_esg | ⚠️ CHECK |
| Permitting Complexity | >10 permits OR >24 months OR rezoning | High | +$5-15M | +12-24 months | 0.5-0.8 | regulatory_esg | ⚠️ CHECK |
| High Grid Carbon | >400 gCO2/kWh OR <20% renewable | Medium-High | +$10-30M PPAs/offsets | +6-12 months | 0.4-0.7 | regulatory_esg | ⚠️ CHECK |

**Action Required**: Verify each agent's prompt includes these caution flag triggers and severity mappings.

---

## ✅ PHASE 6: Domain Models (Pydantic Schemas)

### 6.1 Active Domain Models

**File**: `agent/domain_models.py`

| Domain Model | Agent | Required Subsections | Status |
|--------------|-------|---------------------|--------|
| `PowerInfrastructureOutput` | power_agent | 7 subsections (grid_reliability, power_capacity, generation_mix, connection_process, electricity_costs, cost_model, industrial_heritage) | ⚠️ CHECK |
| `NetworkConnectivityOutput` | network_agent | 6-8 subsections (fiber_infrastructure, last_mile_diversity, subsea_cables, ixp_peering, carrier_diversity, latency_performance, bandwidth_costs, future_proofing) | ⚠️ CHECK |
| `ClimateAnalysisOutput` | climate_agent | 5-7 subsections (temperature_humidity, cooling_strategy, free_cooling, seismic_geological, hydrological_flood, wind_storm, climate_extremes) | ⚠️ CHECK |
| `SiteCivilInfrastructureOutput` | site_civil_agent | 4-6 subsections (land_availability, geotechnical_conditions, water_wastewater, transportation_access, permitting_timeline, civil_grading) | ⚠️ CHECK |
| `MechanicalThermalOutput` | mechanical_thermal_agent | 3-7 subsections (cooling_strategy, hvac_design, thermal_resilience, free_cooling_efficiency, water_consumption, mechanical_infrastructure, fire_suppression) | ⚠️ CHECK |
| `RegulatoryESGOutput` | regulatory_esg_agent | 5 subsections (data_sovereignty_privacy, government_incentives, operational_environmental_compliance, permitting_zoning, esg_trajectory) | ✅ CREATED |
| `MarketCompetitionOutput` | market_competition_agent | 4 subsections (competitive_landscape, cloud_ecosystem, peering_opportunities, strategic_positioning) | ⚠️ CHECK |

**Verification Steps**:
```python
# Check model exists and has required fields
from agent.domain_models import RegulatoryESGOutput
import inspect
fields = RegulatoryESGOutput.__fields__.keys()
required = ["data_sovereignty_privacy", "government_incentives", "operational_environmental_compliance", "permitting_zoning", "esg_trajectory"]
for field in required:
    assert field in fields, f"Missing field: {field}"
print("✅ RegulatoryESGOutput has all 5 required subsections")
```

**Status**: ⚠️ NEEDS VERIFICATION

---

### 6.2 Deprecated Domain Models (Backward Compatibility)

**File**: `agent/domain_models.py`

| Deprecated Model | Reason | Keep for Compatibility? | Status |
|------------------|--------|-------------------------|--------|
| `OperationalRiskOutput` | Risk feeds into other domains, not standalone | ✅ YES (marked deprecated) | ✅ DEPRECATED |
| `HyperscalerAttractivenessOutput` | Merged into market_competition_agent | ✅ YES (marked deprecated) | ✅ DEPRECATED |
| `ESGSustainabilityOutput` | Merged into regulatory_esg_agent | ⚠️ DECIDE | ⚠️ CHECK |
| `RegulatoryComplianceOutput` | Merged into regulatory_esg_agent | ⚠️ DECIDE | ⚠️ CHECK |

**Action Required**: Decide whether to keep deprecated ESG/Regulatory models for backward compatibility or remove entirely.

---

### 6.3 Shared Models

**File**: `agent/models.py`

| Model | Purpose | Required Fields | Status |
|-------|---------|----------------|--------|
| `NoGoGate` | Hard stop gates | gate_type, triggered (bool), reason, standard_reference, mitigation_possible, mitigation_cost | ⚠️ CHECK |
| `CautionFlag` | Yellow flags | category, severity (low/medium/high), description, mitigation_plan, cost_impact, timeline_impact, severity_points (0.0-1.0) | ⚠️ CHECK |
| `ProvenanceBadge` | Data source tracking | source, api_version, vintage, refresh_frequency, confidence (high/medium/low), coverage, url | ⚠️ CHECK |
| `DistanceMeasurement` | Distance tracking | target, distance_km, method (road/aerial/rail/fiber_route), source | ⚠️ CHECK |
| `WeightedDomainScore` | Domain scoring | domain_name, raw_score, weight, weighted_contribution, no_go_gates_triggered, caution_flags_count | ⚠️ CHECK |
| `LocationContext` | Location input | lat, lng, country, location, justification, site_notes | ⚠️ CHECK |

**Verification Steps**:
```python
from agent.models import NoGoGate, CautionFlag, ProvenanceBadge
# Test instantiation
gate = NoGoGate(gate_type="Test", triggered=False, reason="N/A", standard_reference="N/A", mitigation_possible=False, mitigation_cost="N/A")
flag = CautionFlag(category="Test", severity="low", description="Test", mitigation_plan="Test", cost_impact="N/A", timeline_impact="N/A", severity_points=0.2)
badge = ProvenanceBadge(source="Test", api_version="1.0", vintage="2024", refresh_frequency="Annual", confidence="high", coverage="Global", url="https://example.com")
print("✅ All shared models instantiate correctly")
```

**Status**: ⚠️ NEEDS VERIFICATION

---

## ✅ PHASE 7: Data Sources & Provenance

### 7.1 ProvenanceBadge Implementation

**Requirement**: Every agent must output `provenance_badges` array with source tracking

| Agent | Required Data Sources (Per Expert Spec) | Status |
|-------|------------------------------------------|--------|
| power_agent | OpenInfraMap (HV lines/substations), ENTSO-E Transparency (EU), EIA (US), national regulators, queue portals (ERCOT/PJM/CAISO) | ⚠️ CHECK |
| network_agent | PeeringDB (IXPs), SubmarineCableMap.com (landing systems), TeleGeography (if licensed), RIPE Atlas (measured latency), carrier quotes (PacketFabric/Megaport) | ⚠️ CHECK |
| climate_agent | ERA5 (climate), ThinkHazard/GEM/USGS/FEMA/NOAA/USFS (hazards), WRI Aqueduct (water stress) | ⚠️ CHECK |
| site_civil_agent | Google Earth/Maps, OSM/Overpass, NASA SRTM (DEM), ISRIC SoilGrids, SSURGO (US), Regrid/INSPIRE, LoopNet | ⚠️ CHECK |
| mechanical_thermal_agent | ERA5/EPW climate files, ASHRAE TC 9.9 / 90.4 | ⚠️ CHECK |
| regulatory_esg_agent | DLA Piper (privacy), ElectricityMaps (avg grid), WattTime MOER (marginal), national EIAs, MISA/MODON (KSA), EU taxonomy, CDP/ISSB guidance | ⚠️ CHECK |
| market_competition_agent | Data Centre Map, Cloudscene, CBRE/JLL/C&W reports (if licensed), company filings | ⚠️ CHECK |

**Verification Steps**:
```bash
# Check each agent prompt mentions required data sources
grep -i "OpenInfraMap\|ENTSO-E\|EIA\|ERCOT\|PJM\|CAISO" agent/power_agent.py
grep -i "PeeringDB\|SubmarineCableMap\|RIPE Atlas\|TeleGeography" agent/network_agent.py
grep -i "ERA5\|FEMA\|USGS\|GEM\|WRI Aqueduct" agent/climate_agent.py
grep -i "Google Earth\|OSM\|SRTM\|SoilGrids" agent/site_civil_agent.py
grep -i "ERA5\|EPW\|ASHRAE" agent/mechanical_thermal_agent.py
grep -i "DLA Piper\|ElectricityMaps\|WattTime" agent/regulatory_esg_agent.py
grep -i "Data Centre Map\|Cloudscene\|CBRE\|JLL" agent/market_competition_agent.py
```

**Status**: ⚠️ NEEDS VERIFICATION

---

### 7.2 Confidence Levels

**Requirement**: ProvenanceBadge must include confidence level

| Confidence Level | Criteria | Status |
|------------------|----------|--------|
| High | Site-specific measured data <6 months old OR legal text <12 months | ⚠️ CHECK |
| Medium | Official guidance <2 years old OR regional data | ⚠️ CHECK |
| Low | Modelled/estimated data OR >2 years old | ⚠️ CHECK |

**Action Required**: Verify agent prompts instruct LLM to assign confidence levels correctly.

---

## ✅ PHASE 8: Report Structure & Output

### 8.1 ReportSchema Structure

**File**: `agent/models.py`

**Required Fields**:
- [ ] `location_context`: LocationContext
- [ ] `composite_score`: float (0.0 for NO-GO, 1.0-5.0 for valid scores)
- [ ] `weighted_domain_scores`: List[WeightedDomainScore] (7 domains)
- [ ] `all_no_go_gates`: List[NoGoGate] (aggregated from all agents)
- [ ] `all_caution_flags`: List[CautionFlag] (aggregated from all agents)
- [ ] `agent_results`: Dict[str, AgentOutput] (7 domain results)
- [ ] `insights`: Optional[str] (from insights_agent synthesis)
- [ ] `executive_summary`: str (overall assessment)
- [ ] `generated_at`: str (ISO timestamp)

**Verification Steps**:
```python
from agent.models import ReportSchema
import inspect
fields = ReportSchema.__fields__.keys()
required = ["location_context", "composite_score", "weighted_domain_scores", "all_no_go_gates", "all_caution_flags", "agent_results"]
for field in required:
    assert field in fields, f"Missing field: {field}"
print("✅ ReportSchema has all required fields")
```

**Status**: ⚠️ NEEDS VERIFICATION

---

### 8.2 PDF/JSON Export

**File**: `agent/utility.py`

**Requirements**:
- [ ] `generate_pdf_report()` includes all subsections from 7 agents
- [ ] `save_json_report()` includes all NO-GO gates, caution flags, provenance badges
- [ ] PDF includes provenance badges per section
- [ ] JSON includes distance measurements with methodology

**Verification Steps**:
```bash
# Check PDF generation includes all agents
grep -n "power\|network\|climate\|site_civil\|mechanical\|regulatory_esg\|market_competition" agent/utility.py

# Check JSON export
grep -n "no_go_gates\|caution_flags\|provenance_badges\|distance_measurements" agent/utility.py
```

**Status**: ⚠️ NEEDS VERIFICATION

---

## ✅ PHASE 9: Agent Coordination Dependencies

### 9.1 Cross-Agent Data Flow

**Expert Spec Requirements**:

| Dependency | From Agent → To Agent | Data Needed | Status |
|------------|----------------------|-------------|--------|
| Power → Mechanical | Interconnection voltage, short-circuit MVA, UPS/generator heat rejection | Cooling plant sizing, electrical selectivity | ⚠️ CHECK |
| Power → Risk | Fuel autonomy, refueling logistics | Operational risk assessment | ⚠️ N/A (risk deprecated) |
| Network → Market | Fiber/IXP/subsea proximity | Market attractiveness, latency claims | ⚠️ CHECK |
| Site → Hazards | Finished floor elevation (FFE), cut/fill | Flood modeling, drainage sizing | ⚠️ CHECK |
| Regulatory → Power/Mechanical | Noise limits, emissions rules, renewable mandates | Generator enclosures, PPA strategy | ⚠️ CHECK |
| All → Scoring Coordinator | Domain scores, NO-GO gates, caution flags | Weighted composite score | ⚠️ CHECK |

**Action Required**: Verify `shared_context` dictionary in `synthesis_agents.py` includes cross-agent coordination data.

**Verification Steps**:
```bash
grep -n "shared_context" agent/synthesis_agents.py
# Check if shared_context is passed to all agents and includes relevant fields
```

**Status**: ⚠️ NEEDS VERIFICATION

---

## ✅ PHASE 10: Standards & References

### 10.1 Power & Electrical Standards

| Standard | Purpose | Agent | Status |
|----------|---------|-------|--------|
| IEEE 519-2014 | THD limits (<5% V, <20% I) | power | ⚠️ CHECK |
| IEC 61000 | EMC (electromagnetic compatibility) | power | ⚠️ CHECK |
| IEC 61936 | Power installations >1 kV | power | ⚠️ CHECK |
| IEEE C37 | Switchgear ratings | power | ⚠️ CHECK |
| ASHRAE 90.4 | Energy efficiency for datacenters | power, mechanical | ⚠️ CHECK |

---

### 10.2 Network & Connectivity Standards

| Standard | Purpose | Agent | Status |
|----------|---------|-------|--------|
| PeeringDB | IXP directory | network | ⚠️ CHECK |
| SubmarineCableMap | Subsea cable landing systems | network | ⚠️ CHECK |
| RIPE Atlas | Measured latency probes | network | ⚠️ CHECK |

---

### 10.3 Climate & Hazards Standards

| Standard | Purpose | Agent | Status |
|----------|---------|-------|--------|
| ASHRAE TC 9.9 | Climate classes for datacenters | climate, mechanical | ⚠️ CHECK |
| FEMA | Flood zone maps | climate | ⚠️ CHECK |
| USGS/GEM | Seismic hazard maps (PGA) | climate | ⚠️ CHECK |
| NIFC/CAMS | Wildfire severity | climate | ⚠️ CHECK |
| NFPA 75/76/2001 | Fire protection & life safety | climate, mechanical | ⚠️ CHECK |

---

### 10.4 Site & Civil Standards

| Standard | Purpose | Agent | Status |
|----------|---------|-------|--------|
| ASCE 7-22 | Bearing capacity (150-250 kPa) | site_civil | ⚠️ CHECK |
| Uptime Institute Tier Standards | Land area (2-5 hectares for 50 MW) | site_civil | ⚠️ CHECK |
| WRI Aqueduct | Water stress assessment | site_civil, climate | ⚠️ CHECK |

---

### 10.5 Mechanical & Thermal Standards

| Standard | Purpose | Agent | Status |
|----------|---------|-------|--------|
| ASHRAE TC 9.9 | Climate classes | mechanical | ⚠️ CHECK |
| ASHRAE 90.4 | Energy efficiency | mechanical | ⚠️ CHECK |
| EN 50600-2-3 | Cooling for datacenters | mechanical | ⚠️ CHECK |

---

### 10.6 Regulatory & ESG Standards

| Standard | Purpose | Agent | Status |
|----------|---------|-------|--------|
| GDPR Article 44-50 | Cross-border data transfers | regulatory_esg | ⚠️ CHECK |
| CCPA/CPRA | California privacy | regulatory_esg | ⚠️ CHECK |
| ISO 27001/27017/27018 | Information security, cloud privacy | regulatory_esg | ⚠️ CHECK |
| SOC 2 Type II | Security controls audit | regulatory_esg | ⚠️ CHECK |
| NERC CIP | Critical infrastructure protection | regulatory_esg | ⚠️ CHECK |
| IBC / Eurocode | Building codes | regulatory_esg | ⚠️ CHECK |
| NFPA 75/76 | Fire protection | regulatory_esg | ⚠️ CHECK |
| ISO 14001 | Environmental management | regulatory_esg | ⚠️ CHECK |
| NEPA / equivalent | Environmental impact assessment | regulatory_esg | ⚠️ CHECK |
| EU WEEE Directive | E-waste | regulatory_esg | ⚠️ CHECK |
| ElectricityMaps | Grid carbon intensity (avg) | regulatory_esg | ⚠️ CHECK |
| WattTime MOER | Marginal Operating Emissions Rate (CFE accounting) | regulatory_esg | ⚠️ CHECK |
| TCFD / ISSB | Climate disclosure | regulatory_esg | ⚠️ CHECK |
| CDP | Carbon Disclosure Project | regulatory_esg | ⚠️ CHECK |
| GHG Protocol Scope 1/2/3 | Emissions accounting | regulatory_esg | ⚠️ CHECK |
| GRI / SASB | ESG reporting frameworks | regulatory_esg | ⚠️ CHECK |
| LEED / BREEAM | Green building certifications | regulatory_esg | ⚠️ CHECK |
| ILO / ISO 45001 | Labor & occupational health | regulatory_esg | ⚠️ CHECK |

---

## Summary Status

| Phase | Total Items | ✅ Pass | ⚠️ Needs Verification | ❌ Fail | Completion % |
|-------|-------------|---------|----------------------|---------|--------------|
| 1. Agent Architecture | 11 | 11 | 0 | 0 | 100% |
| 2. Composite Scoring | 5 | 1 | 4 | 0 | 20% |
| 3. Subsection Structure | 7 agents × ~5 checks = 35 | 0 | 35 | 0 | 0% |
| 4. NO-GO Gates | ~15 gates | 0 | 15 | 0 | 0% |
| 5. Caution Flags | ~10 flags | 0 | 10 | 0 | 0% |
| 6. Domain Models | 12 models | 1 | 11 | 0 | 8% |
| 7. Data Sources | 7 agents × provenance | 0 | 7 | 0 | 0% |
| 8. Report Structure | 6 checks | 0 | 6 | 0 | 0% |
| 9. Agent Coordination | 6 dependencies | 0 | 6 | 0 | 0% |
| 10. Standards | ~40 standards | 0 | 40 | 0 | 0% |
| **TOTAL** | **~165 items** | **13** | **134** | **0** | **~8%** |

---

## Next Steps

### Priority 1: Critical Verifications (Required for Correctness)
1. ✅ **Agent Architecture** - COMPLETE (7 agents confirmed, obsolete agents removed)
2. ⚠️ **Composite Scoring Logic** - Verify NO-GO override, weighted sum, caution penalties in `synthesis_agents.py`
3. ⚠️ **NO-GO Gates** - Verify all 15+ NO-GO gates are implemented in agent prompts with correct triggers

### Priority 2: Subsection Content (Required for Completeness)
4. ⚠️ **Agent Subsections** - Verify each of 7 agents has all required subsections A, B, C, etc. matching expert spec
5. ⚠️ **Caution Flags** - Verify caution flag triggers, severity levels, and cost/timeline impacts
6. ⚠️ **Standards References** - Verify all 40+ standards are mentioned in agent prompts

### Priority 3: Data Quality (Required for Investment-Grade)
7. ⚠️ **ProvenanceBadge** - Verify all agents output provenance badges with source, vintage, confidence
8. ⚠️ **Domain Models** - Verify Pydantic schemas match expert spec subsections
9. ⚠️ **Report Structure** - Verify ReportSchema includes all required fields

### Priority 4: Integration (Required for Orchestration)
10. ⚠️ **Agent Coordination** - Verify cross-agent data dependencies in shared_context
11. ⚠️ **PDF/JSON Export** - Verify reports include all subsections, NO-GO gates, caution flags, provenance

---

## How to Use This Checklist

1. **Manual Code Review**: For each ⚠️ item, use the "Verification Steps" commands to check implementation.
2. **Automated Testing**: Write pytest tests for critical logic (scoring, NO-GO gates, caution penalties).
3. **Agent Prompt Audits**: Review each agent's `INVESTMENT_GRADE_PROMPT` to ensure subsections A-G, NO-GO gates, caution flags, and standards are covered.
4. **Integration Testing**: Run end-to-end analysis for a test location and verify report completeness.
5. **Update Status**: Change ⚠️ to ✅ (pass) or ❌ (fail) as you verify each item.

---

**End of Checklist**
