"""
Infrastructure Registry APIs - External infrastructure databases

This module contains APIs that query external infrastructure registries:
- PeeringDB (network_query.py): Facilities, IXPs, carriers
- OpenStreetMap/OpenInfraMap (power_infra_query.py): Substations, transmission lines
"""

from .network_query import query_peeringdb
from .power_infra_query import find_power_assets

__all__ = ['query_peeringdb', 'find_power_assets']
