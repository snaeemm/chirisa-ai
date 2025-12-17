"""
Shared APIs: Site Civil + Regulatory ESG Agents

This folder contains APIs that are used by multiple agents:
- Site Civil Agent
- Regulatory ESG Agent

APIs in this folder:
- water_stress_query: WRI Aqueduct Water Stress (via Google Earth Engine)
  - Site Civil: Section C - Water & Wastewater Infrastructure (>4.0 = NO-GO)
  - Regulatory ESG: Section C - Water stress levels (WRI Aqueduct baseline/future)
"""
from .water_stress_query import query_water_stress

__all__ = ["query_water_stress"]
