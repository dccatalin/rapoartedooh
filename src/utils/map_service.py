import requests
import logging
from typing import List, Optional
import os

logger = logging.getLogger(__name__)

class MapService:
    GOOGLE_BASE_URL = "https://maps.googleapis.com/maps/api/staticmap"
    MAPBOX_BASE_URL = "https://api.mapbox.com/styles/v1/mapbox/streets-v11/static"
    
class MapService:
    GOOGLE_BASE_URL = "https://maps.googleapis.com/maps/api/staticmap"
    MAPBOX_BASE_URL = "https://api.mapbox.com/styles/v1/mapbox/streets-v11/static"
    
    def __init__(self, google_key: str = None, mapbox_key: str = None):
        self.google_key = google_key
        self.mapbox_key = mapbox_key
        
    def download_map_image(self, cities: List[str], output_path: str, coordinates: Optional[List[tuple]] = None) -> bool:
        """
        Download static map image using available providers with fallback.
        Priority: Google -> Mapbox
        """
        # 1. Try Google Maps
        if self.google_key:
            logger.info("Attempting map generation with Google Maps...")
            if self._download_google(cities, output_path):
                return True
            logger.warning("Google Maps generation failed.")
            
        # 2. Try Mapbox
        if self.mapbox_key and coordinates:
            logger.info("Attempting map generation with Mapbox...")
            if self._download_mapbox(coordinates, output_path):
                return True
            logger.warning("Mapbox generation failed.")
            
        logger.error("All map providers failed or no keys available.")
        return False

    def _download_google(self, cities, output_path):
        try:
            url = self._generate_google_url(cities, 600, 400)
            if not url: return False
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return True
            return False
        except Exception as e:
            logger.error(f"Google Maps error: {e}")
            return False

    def _download_mapbox(self, coordinates, output_path):
        try:
            url = self._generate_mapbox_url_with_coords(coordinates, 600, 400)
            if not url: return False
            
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return True
            return False
        except Exception as e:
            logger.error(f"Mapbox error: {e}")
            return False

    def _generate_google_url(self, cities, width, height):
        markers = ""
        for city in cities:
            markers += f"&markers=label:{city[0]}|{city}"
        path = f"&path=color:0x0000ff|weight:5|{'|'.join(cities)}"
        return f"{self.GOOGLE_BASE_URL}?size={width}x{height}&maptype=roadmap{markers}{path}&key={self.google_key}"

    def _generate_mapbox_url_with_coords(self, coords: List[tuple], width, height):
        overlays = []
        for i, (lat, lon) in enumerate(coords):
            overlays.append(f"pin-s-label+{i+1}({lon},{lat})")
        
        overlay_str = ",".join(overlays)
        return f"{self.MAPBOX_BASE_URL}/{overlay_str}/auto/{width}x{height}?access_token={self.mapbox_key}"
