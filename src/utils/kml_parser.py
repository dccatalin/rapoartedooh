import xml.etree.ElementTree as ET
import math

def parse_kml(file_path):
    """
    Parse KML file to extract coordinates and calculate total distance.
    Returns:
        dict: {
            'distance_km': float,
            'points': list of (lat, lon),
            'name': str (optional)
        }
    """
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Namespace handling
        ns = {'kml': 'http://www.opengis.net/kml/2.2'}
        
        # Try to find LineString coordinates
        # Note: This is a simplified parser looking for the first LineString
        # A more robust one would handle MultiGeometry, Placemarks, etc.
        
        coords_text = None
        name = "Route"
        
        # Search for Placemark with LineString
        for placemark in root.findall('.//kml:Placemark', ns):
            name_elem = placemark.find('kml:name', ns)
            if name_elem is not None:
                name = name_elem.text
                
            line_string = placemark.find('.//kml:LineString', ns)
            if line_string is not None:
                coords_elem = line_string.find('kml:coordinates', ns)
                if coords_elem is not None:
                    coords_text = coords_elem.text
                    break
        
        # Fallback: search anywhere for coordinates if no Placemark structure found
        if not coords_text:
            coords_elem = root.find('.//kml:coordinates', ns)
            if coords_elem is not None:
                coords_text = coords_elem.text
                
        if not coords_text:
            return {'distance_km': 0, 'points': [], 'error': 'No coordinates found'}
            
        # Parse coordinates
        points = []
        for coord in coords_text.strip().split():
            parts = coord.split(',')
            if len(parts) >= 2:
                try:
                    lon = float(parts[0])
                    lat = float(parts[1])
                    points.append((lat, lon))
                except ValueError:
                    continue
                    
        if len(points) < 2:
            return {'distance_km': 0, 'points': points, 'name': name}
            
        # Calculate total distance
        total_distance = 0
        for i in range(len(points) - 1):
            total_distance += haversine_distance(points[i], points[i+1])
            
        return {
            'distance_km': round(total_distance, 2),
            'points': points,
            'name': name
        }
        
    except Exception as e:
        return {'distance_km': 0, 'points': [], 'error': str(e)}

def haversine_distance(point1, point2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    lat1, lon1 = point1
    lat2, lon2 = point2
    
    # Convert decimal degrees to radians 
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r
