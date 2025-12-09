#!/usr/bin/env python3
"""
ULTIMATE OSM POWER INFRASTRUCTURE QUERY SCRIPT
==============================================

This script works around network restrictions by providing multiple methods.
The Overpass API is 100% FREE - no authentication or API key needed!

Run this on YOUR LOCAL MACHINE where there are no network restrictions.
"""

import requests
import json
from math import radians, cos, sin, asin, sqrt
from datetime import datetime

def haversine_distance(lon1, lat1, lon2, lat2):
    """Calculate distance in km between two coordinates."""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return 6371 * c

class PowerInfraQuery:
    """Query OSM for power infrastructure - Works on your local machine!"""
    
    def __init__(self):
        # Try multiple Overpass servers
        self.servers = [
            "https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.openstreetmap.ru/api/interpreter",
            "https://overpass.openstreetmap.fr/api/interpreter"
        ]
        self.working_server = None
    
    def test_connection(self):
        """Test which Overpass server works."""
        print("Testing Overpass API servers...")
        for server in self.servers:
            try:
                print(f"  Trying {server}...")
                response = requests.get(f"{server.replace('/interpreter', '/status')}", timeout=5)
                if response.status_code == 200:
                    print(f"  ✅ {server} is working!")
                    self.working_server = server
                    return True
            except Exception as e:
                print(f"  ❌ {server} failed: {e}")
        
        print("\n⚠️  Could not connect to any Overpass server.")
        print("This script needs to run on a machine with internet access.")
        print("Try using Overpass Turbo web interface: https://overpass-turbo.eu/")
        return False
    
    def query_power_infrastructure(self, lat, lon, radius_km=10, voltage_filter=None):
        """
        Query power infrastructure near a location.
        
        Args:
            lat: Site latitude
            lon: Site longitude
            radius_km: Search radius in kilometers
            voltage_filter: Optional voltage filter (e.g., "132000|400000")
        
        Returns:
            Dictionary with substations and power lines data
        """
        if not self.working_server:
            if not self.test_connection():
                return None
        
        radius_m = radius_km * 1000
        
        voltage_part = ""
        if voltage_filter:
            voltage_part = f'["voltage"~"^({voltage_filter}).*"]'
        
        query = f"""[out:json][timeout:120];
(
  node["power"="substation"]{voltage_part}(around:{radius_m},{lat},{lon});
  way["power"="substation"]{voltage_part}(around:{radius_m},{lat},{lon});
  relation["power"="substation"]{voltage_part}(around:{radius_m},{lat},{lon});
  way["power"="line"](around:{radius_m},{lat},{lon});
  relation["power"="line"](around:{radius_m},{lat},{lon});
);
out body;
>;
out skel qt;
"""
        
        print(f"\nQuerying power infrastructure within {radius_km}km of ({lat}, {lon})...")
        print(f"Using server: {self.working_server}")
        
        try:
            response = requests.post(
                self.working_server,
                data={'data': query},
                timeout=120
            )
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ Query successful! Received {len(data.get('elements', []))} elements")
            return self.process_data(data, lat, lon)
            
        except Exception as e:
            print(f"❌ Query failed: {e}")
            return None
    
    def process_data(self, data, site_lat, site_lon):
        """Process OSM data into structured format."""
        substations = []
        power_lines = []
        nodes = {}  # Store node coordinates for ways
        
        # First pass: collect all nodes
        for element in data.get('elements', []):
            if element['type'] == 'node':
                nodes[element['id']] = {
                    'lat': element['lat'],
                    'lon': element['lon']
                }
        
        # Second pass: process substations and lines
        for element in data.get('elements', []):
            tags = element.get('tags', {})
            
            if tags.get('power') == 'substation':
                sub = {
                    'id': element['id'],
                    'type': element['type'],
                    'name': tags.get('name', 'Unnamed'),
                    'voltage': tags.get('voltage', 'Unknown'),
                    'substation_type': tags.get('substation', 'Unknown'),
                    'operator': tags.get('operator', 'Unknown'),
                    'frequency': tags.get('frequency', 'Unknown'),
                    'tags': tags
                }
                
                if element['type'] == 'node':
                    sub['lat'] = element['lat']
                    sub['lon'] = element['lon']
                    sub['distance_km'] = haversine_distance(
                        site_lon, site_lat,
                        element['lon'], element['lat']
                    )
                elif element['type'] == 'way' and 'nodes' in element and element['nodes']:
                    # Calculate center point of way
                    way_nodes = [nodes.get(n) for n in element['nodes'] if n in nodes]
                    if way_nodes:
                        avg_lat = sum(n['lat'] for n in way_nodes) / len(way_nodes)
                        avg_lon = sum(n['lon'] for n in way_nodes) / len(way_nodes)
                        sub['lat'] = avg_lat
                        sub['lon'] = avg_lon
                        sub['distance_km'] = haversine_distance(
                            site_lon, site_lat, avg_lon, avg_lat
                        )
                
                substations.append(sub)
            
            elif tags.get('power') == 'line':
                line = {
                    'id': element['id'],
                    'type': element['type'],
                    'voltage': tags.get('voltage', 'Unknown'),
                    'cables': tags.get('cables', 'Unknown'),
                    'operator': tags.get('operator', 'Unknown'),
                    'line_type': tags.get('line', 'Unknown'),
                    'frequency': tags.get('frequency', 'Unknown'),
                    'tags': tags
                }
                power_lines.append(line)
        
        # Sort substations by distance
        substations.sort(key=lambda x: x.get('distance_km', float('inf')))
        
        return {
            'substations': substations,
            'power_lines': power_lines,
            'query_info': {
                'site_lat': site_lat,
                'site_lon': site_lon,
                'timestamp': datetime.now().isoformat(),
                'total_elements': len(data.get('elements', []))
            }
        }
    
    def generate_report(self, results, output_file='power_infrastructure_report.json'):
        """Generate and save a comprehensive report."""
        if not results:
            print("No results to report.")
            return
        
        # Save JSON
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✅ Report saved to: {output_file}")
        
        # Print summary
        print("\n" + "="*80)
        print("POWER INFRASTRUCTURE SUMMARY")
        print("="*80)
        print(f"Site Location: {results['query_info']['site_lat']}, {results['query_info']['site_lon']}")
        print(f"Query Time: {results['query_info']['timestamp']}")
        print(f"Total Substations: {len(results['substations'])}")
        print(f"Total Power Lines: {len(results['power_lines'])}")
        
        if results['substations']:
            nearest = results['substations'][0]
            print(f"\nNearest Substation:")
            print(f"  Name: {nearest['name']}")
            print(f"  Distance: {nearest.get('distance_km', 'N/A'):.2f} km")
            print(f"  Voltage: {nearest['voltage']}")
            print(f"  Type: {nearest['substation_type']}")
            print(f"  Operator: {nearest['operator']}")
            
            print(f"\nTop 5 Nearest Substations:")
            for i, sub in enumerate(results['substations'][:5], 1):
                dist = sub.get('distance_km', float('inf'))
                print(f"  {i}. {sub['name']} - {dist:.2f} km - {sub['voltage']} V")
        
        # Voltage analysis
        voltage_counts = {}
        for sub in results['substations']:
            voltages = sub['voltage'].split(';')
            for v in voltages:
                v = v.strip()
                if v and v != 'Unknown':
                    voltage_counts[v] = voltage_counts.get(v, 0) + 1
        
        if voltage_counts:
            print(f"\nVoltage Levels Available:")
            for voltage in sorted(voltage_counts.keys(), key=lambda x: int(x) if x.isdigit() else 0, reverse=True):
                kv = int(voltage) / 1000 if voltage.isdigit() else voltage
                print(f"  {kv} kV: {voltage_counts[voltage]} substation(s)")
        
        print("="*80)

def main():
    """Main function demonstrating the usage."""
    
    print("="*80)
    print("OSM POWER INFRASTRUCTURE QUERY")
    print("="*80)
    print("\nThis script queries OpenStreetMap for power infrastructure.")
    print("The Overpass API is 100% FREE - no authentication needed!\n")
    
    # Initialize query object
    piq = PowerInfraQuery()
    
    # Example: Query for power infrastructure in Dubai
    # CHANGE THESE VALUES TO YOUR ACTUAL SITE COORDINATES
    site_lat = 25.2048  # Your site latitude
    site_lon = 55.2708  # Your site longitude
    site_name = "Dubai Test Site"
    radius_km = 15      # Search radius in km
    
    print(f"Site: {site_name}")
    print(f"Coordinates: {site_lat}, {site_lon}")
    print(f"Search Radius: {radius_km} km\n")
    
    # Query the data
    results = piq.query_power_infrastructure(site_lat, site_lon, radius_km)
    
    if results:
        # Generate report
        piq.generate_report(results, 'power_infrastructure_report.json')
        
        print("\n✅ SUCCESS! Power infrastructure data retrieved.")
        print("\nYou can now:")
        print("  1. View power_infrastructure_report.json")
        print("  2. Analyze the data in Python/Excel/GIS software")
        print("  3. Calculate connection costs")
        print("  4. Plan your project accordingly")
    else:
        print("\n❌ Could not retrieve data.")
        print("\nAlternative methods:")
        print("  1. Use Overpass Turbo: https://overpass-turbo.eu/")
        print("  2. Run this script on a different network")
        print("  3. Use a VPN to bypass network restrictions")

if __name__ == "__main__":
    main()

# ============================================================================
# ADDITIONAL EXAMPLES
# ============================================================================

def example_queries():
    """Additional example queries for different scenarios."""
    
    piq = PowerInfraQuery()
    
    # Example 1: Query high-voltage substations only (132kV and above)
    print("\n" + "="*80)
    print("EXAMPLE 1: High-Voltage Substations Only")
    print("="*80)
    results_hv = piq.query_power_infrastructure(
        lat=25.2048,
        lon=55.2708,
        radius_km=20,
        voltage_filter="132000|220000|400000"
    )
    if results_hv:
        piq.generate_report(results_hv, 'high_voltage_substations.json')
    
    # Example 2: Larger search area
    print("\n" + "="*80)
    print("EXAMPLE 2: Wider Search Area (30km radius)")
    print("="*80)
    results_wide = piq.query_power_infrastructure(
        lat=25.2048,
        lon=55.2708,
        radius_km=30
    )
    if results_wide:
        piq.generate_report(results_wide, 'wide_area_search.json')

# Uncomment to run examples:
# example_queries()