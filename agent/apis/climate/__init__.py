"""
Climate API Module - Orchestrator Only

This module contains the combined_hazard_query.py orchestrator that fetches
all climate hazard data in parallel from the geospatial_hazards folder.

Individual hazard APIs have moved to domain-based folders:
- geospatial_hazards/seismic_hazard_query.py
- geospatial_hazards/flood_hazard_query.py
- geospatial_hazards/protected_area_query.py
- geospatial_hazards/thinkhazard_query.py
"""

from .combined_hazard_query import query_all_climate_hazards, format_climate_hazard_summary

__all__ = ['query_all_climate_hazards', 'format_climate_hazard_summary']
