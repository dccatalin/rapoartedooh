import json
import os
import logging

logger = logging.getLogger(__name__)

class DistanceService:
    """
    Service to calculate distances and transit times between cities.
    Uses a local JSON database of pre-calculated routes.
    """
    def __init__(self):
        self.matrix_path = os.path.join(os.path.dirname(__file__), 'distance_matrix.json')
        self.matrix = self._load_matrix()

    def _load_matrix(self):
        if not os.path.exists(self.matrix_path):
            return {}
        try:
            with open(self.matrix_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading distance matrix: {e}")
            return {}

    def get_transit_info(self, city1, city2):
        """
        Get distance and duration between two cities.
        Returns (km, hours). If unknown, returns (0, 0).
        """
        if not city1 or not city2:
            return 0, 0
            
        c1 = city1.strip()
        c2 = city2.strip()
        
        if c1.lower() == c2.lower():
            return 0, 0
            
        # Try direct lookup
        key = f"{c1}-{c2}"
        if key in self.matrix:
            data = self.matrix[key]
            return data.get('km', 0), data.get('hours', 0)
            
        # Try reverse lookup
        key_rev = f"{c2}-{c1}"
        if key_rev in self.matrix:
            data = self.matrix[key_rev]
            return data.get('km', 0), data.get('hours', 0)

        # Basic fallback or unknown
        # Could add logic for 'Bucuresti Sector X' mapping to 'Bucuresti'
        if "Bucuresti" in c1 and "Bucuresti" in c2:
            return 15, 0.5
            
        return 0, 0
