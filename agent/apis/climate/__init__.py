"""
Climate/Hazards API Module - Climate Agent Only

APIs:
- seismic_hazard_query: USGS/GEM seismic hazard
- flood_hazard_query: GloFAS flood monitoring
- thinkhazard_query: World Bank multi-hazard
- combined_hazard_query: Parallel fetcher for all climate APIs

Note: protected_area_query is in climate_site_civil_regulatory_esg/
since it's shared by Climate, Site Civil, and Regulatory ESG agents.
"""
