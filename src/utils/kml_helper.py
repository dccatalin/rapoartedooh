import xml.etree.ElementTree as ET
import json
from typing import List, Dict, Any, Optional

class KMLHelper:
    """Helper for converting between KML and GeoJSON for routing"""

    @staticmethod
    def kml_to_geojson(kml_content: str) -> Optional[Dict[str, Any]]:
        """
        Parses KML content and extracts the first LineString as GeoJSON.
        Handles both <LineString> and <gx:Track> if present.
        """
        try:
            # Handle potential namespaces
            namespaces = {
                'kml': 'http://www.opengis.net/kml/2.2',
                'gx': 'http://www.google.com/kml/ext/2.2'
            }
            
            root = ET.fromstring(kml_content)
            
            # Find coordinates in <LineString>
            # Use greedy search since KML structure can vary (Folders, Placemarks, etc)
            coords = []
            
            # 1. Try LineString/coordinates
            for coords_elem in root.iter():
                if coords_elem.tag.endswith('coordinates'):
                    text = coords_elem.text.strip()
                    if not text: continue
                    # KML coords are "lon,lat,alt lon,lat,alt"
                    points = text.split()
                    for p in points:
                        parts = p.split(',')
                        if len(parts) >= 2:
                            coords.append([float(parts[0]), float(parts[1])])
                    if coords: break # Take first found line
            
            # 2. Try gx:coord (google tracks) if empty
            if not coords:
                for coord_elem in root.iter():
                    if coord_elem.tag.endswith('coord'):
                        parts = coord_elem.text.strip().split()
                        if len(parts) >= 2:
                            coords.append([float(parts[0]), float(parts[1])])

            if not coords:
                return None

            return {
                "type": "Feature",
                "properties": {"source": "KML Import"},
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords
                }
            }
        except Exception as e:
            print(f"KML Parsing Error: {e}")
            return None

    @staticmethod
    def geojson_to_kml(geojson: Dict[str, Any], name: str = "Route Export") -> str:
        """
        Converts GeoJSON LineString to KML format.
        """
        try:
            if geojson.get('geometry', {}).get('type') != 'LineString':
                return ""
            
            coords = geojson['geometry']['coordinates']
            coords_str = " ".join([f"{c[0]},{c[1]},0" for c in coords])
            
            kml = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{name}</name>
    <Placemark>
      <name>{name}</name>
      <LineString>
        <tessellate>1</tessellate>
        <coordinates>
          {coords_str}
        </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>'''
            return kml
        except Exception as e:
            print(f"KML Export Error: {e}")
            return ""
