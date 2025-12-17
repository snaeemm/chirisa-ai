"""
Shared APIs: Climate + Site Civil + Regulatory ESG Agents

This folder contains APIs that are used by multiple agents:
- Climate (Hazards) Agent
- Site Civil Agent
- Regulatory ESG Agent

APIs in this folder:
- protected_area_query: WDPA Protected Areas (via Google Earth Engine)
  - Climate: Section D - Protected Areas & Environmental Constraints
  - Site Civil: NO-GO Gate #1 - Protected Land / Zoning Incompatibility
  - Regulatory ESG: Section C - Biodiversity and protected area constraints
"""
from .protected_area_query import query_protected_area

__all__ = ["query_protected_area"]
