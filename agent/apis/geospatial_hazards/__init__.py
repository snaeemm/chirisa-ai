"""
Geospatial Hazards APIs - Location-based risk data

This module contains APIs that query geospatial hazard data:
- USGS/GEM Seismic (seismic_hazard_query.py): PGA, seismic risk
- GloFAS (flood_hazard_query.py): Flood risk categories
- WDPA (protected_area_query.py): Protected areas, IUCN categories
- World Bank ThinkHazard (thinkhazard_query.py): Multi-hazard assessment
"""

from .seismic_hazard_query import query_seismic_hazard
from .flood_hazard_query import query_flood_hazard
from .protected_area_query import query_protected_area
from .thinkhazard_query import query_thinkhazard

__all__ = [
    'query_seismic_hazard',
    'query_flood_hazard',
    'query_protected_area',
    'query_thinkhazard'
]
