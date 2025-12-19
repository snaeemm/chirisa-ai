"""
Resource Stress APIs - Resource availability metrics

This module contains APIs that query resource stress/availability data:
- WRI Aqueduct (water_stress_query.py): Water stress scores (0-5)
"""

from .water_stress_query import query_water_stress

__all__ = ['query_water_stress']
