import requests
import json

class RoutingHelper:
    """
    Helper to interact with OSRM (Open Source Routing Machine) API.
    Used for generating optimized routes between waypoints.
    """
    
    OSRM_BASE_URL = "http://router.project-osrm.org/route/v1/driving/"
    
    @classmethod
    def get_route_osrm(cls, waypoints):
        """
        waypoints: List of [lat, lon] coordinates.
        Returns: Dict representing GeoJSON LineString of the route.
        """
        if not waypoints or len(waypoints) < 2:
            return None
            
        # OSRM expects lon,lat separated by semicolon
        coords_str = ";".join([f"{wp[1]},{wp[0]}" for wp in waypoints])
        
        url = f"{cls.OSRM_BASE_URL}{coords_str}?overview=full&geometries=geojson"
        
        try:
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                print(f"OSRM Error: {response.text}")
                return {"error": f"OSRM API error: {response.status_code}"}
                
            data = response.json()
            
            if data.get('code') == 'Ok' and data.get('routes'):
                # Return the geometry of the first route
                return {
                    "type": "Feature",
                    "geometry": data['routes'][0]['geometry'],
                    "properties": {
                        "distance_meters": data['routes'][0]['distance'],
                        "duration_seconds": data['routes'][0]['duration']
                    }
                }
            else:
                return {"error": f"OSRM No Route: {data.get('code', 'Unknown code')}"}
        except Exception as e:
            return {"error": f"Routing Exception: {str(e)}"}
            
        return None
