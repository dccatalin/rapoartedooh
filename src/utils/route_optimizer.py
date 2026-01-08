"""
Route Optimizer
Suggests optimal routes based on traffic data and city populations.
"""
from typing import List, Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class RouteOptimizer:
    """Optimize campaign routes based on traffic exposure"""
    
    def __init__(self):
        pass
    
    def suggest_optimal_route(
        self, 
        cities: List[Dict[str, Any]], 
        start_city: Optional[str] = None
    ) -> Tuple[List[str], float]:
        """
        Suggest optimal route through cities to maximize traffic exposure.
        
        Args:
            cities: List of city data dictionaries with traffic info
            start_city: Optional starting city name
            
        Returns:
            Tuple of (ordered_city_names, total_traffic_score)
        """
        if not cities:
            return [], 0.0
        
        # Calculate traffic score for each city
        city_scores = []
        for city in cities:
            score = self._calculate_city_traffic_score(city)
            city_scores.append({
                'name': city.get('name', ''),
                'score': score,
                'data': city
            })
        
        # Sort by traffic score (highest first)
        city_scores.sort(key=lambda x: x['score'], reverse=True)
        
        # If start city specified, move it to front
        if start_city:
            for i, city in enumerate(city_scores):
                if city['name'] == start_city:
                    city_scores.insert(0, city_scores.pop(i))
                    break
        
        # Extract ordered names and calculate total score
        ordered_names = [city['name'] for city in city_scores]
        total_score = sum(city['score'] for city in city_scores)
        
        logger.info(f"Optimized route: {' → '.join(ordered_names)} (Score: {total_score:.1f})")
        
        return ordered_names, total_score
    
    def _calculate_city_traffic_score(self, city_data: Dict[str, Any]) -> float:
        """
        Calculate traffic score for a city based on available data.
        
        Score factors:
        - Population (weight: 0.4)
        - Traffic estimate (weight: 0.3)
        - POI density (weight: 0.2)
        - Road density (weight: 0.1)
        """
        score = 0.0
        
        # Population score (normalized to 0-100)
        population = city_data.get('population', 0)
        if population > 0:
            # Log scale for population (cities from 1k to 2M)
            import math
            pop_score = min(100, (math.log10(population) - 3) * 25)  # 10k = 25, 100k = 50, 1M = 75
            score += pop_score * 0.4
        
        # Traffic estimate score
        traffic = city_data.get('traffic_estimate', 0)
        if traffic > 0:
            traffic_score = min(100, traffic / 1000)  # Normalize to 0-100
            score += traffic_score * 0.3
        
        # POI density score
        poi_density = city_data.get('poi_density', 0)
        if poi_density > 0:
            poi_score = min(100, poi_density * 10)  # Normalize
            score += poi_score * 0.2
        
        # Road density score
        road_density = city_data.get('road_density', 0)
        if road_density > 0:
            road_score = min(100, road_density * 20)  # Normalize
            score += road_score * 0.1
        
        return score
    
    def calculate_route_score(
        self, 
        cities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate detailed score breakdown for a route.
        
        Returns:
            Dictionary with total score and per-city breakdown
        """
        breakdown = []
        total_score = 0.0
        
        for city in cities:
            city_score = self._calculate_city_traffic_score(city)
            total_score += city_score
            
            breakdown.append({
                'city': city.get('name', 'Unknown'),
                'score': city_score,
                'population': city.get('population', 0),
                'traffic': city.get('traffic_estimate', 0)
            })
        
        return {
            'total_score': total_score,
            'average_score': total_score / len(cities) if cities else 0,
            'breakdown': breakdown
        }
    
    
    
    # Known high-traffic zones for major cities
    CITY_HOTSPOTS = {
        "Bucuresti": [
            "Piata Victoriei", "Piata Unirii", "Piata Universitatii", 
            "Bd. Magheru", "Calea Victoriei", "Sos. Nordului", 
            "Mall Baneasa", "AFI Cotroceni"
        ],
        "Cluj-Napoca": [
            "Piata Unirii", "Piata Avram Iancu", "Str. Memorandumului",
            "Calea Manastur", "Iulius Mall", "Vivo Mall"
        ],
        "Timisoara": [
            "Piata Victoriei", "Piata Unirii", "Iulius Town",
            "Calea Sagului", "Complex Studentesc"
        ],
        "Iasi": [
            "Palas Mall", "Piata Unirii", "Bd. Copou",
            "Tudor Vladimirescu", "Podu Ros"
        ],
        "Constanta": [
            "Bd. Mamaia", "City Park Mall", "Zona Peninsulara",
            "Portul Tomis", "Vivo Mall"
        ],
        "Brasov": [
            "Piata Sfatului", "Str. Republicii", "Calea Bucuresti",
            "Coresi Mall", "Livada Postei"
        ]
    }

    # Approximate coordinates for major cities (Latitude, Longitude)
    CITY_COORDINATES = {
        "Bucuresti": (44.4268, 26.1025),
        "Cluj-Napoca": (46.7712, 23.6236),
        "Timisoara": (45.7489, 21.2087),
        "Iasi": (47.1585, 27.6014),
        "Constanta": (44.1792, 28.6123),
        "Brasov": (45.6579, 25.6012),
        "Craiova": (44.3302, 23.7949),
        "Galati": (45.4353, 28.0080),
        "Ploiesti": (44.9367, 26.0129),
        "Oradea": (47.0465, 21.9189),
        "Braila": (45.2692, 27.9575),
        "Arad": (46.1866, 21.3123),
        "Pitesti": (44.8565, 24.8692),
        "Sibiu": (45.7983, 24.1256),
        "Bacau": (46.5674, 26.9138),
        "Targu Mures": (46.5456, 24.5625),
        "Baia Mare": (47.6533, 23.5795),
        "Buzau": (45.1502, 26.8177),
        "Botosani": (47.7412, 26.6664),
        "Satu Mare": (47.7900, 22.8857)
    }

    def suggest_optimal_route(
        self, 
        cities: List[Dict[str, Any]], 
        start_city: Optional[str] = None
    ) -> Tuple[List[str], float]:
        """
        Suggest optimal route through cities to maximize traffic exposure AND minimize travel distance.
        Uses a 'Best-Start Nearest Neighbor' approach:
        1. Tries starting from EACH city (unless start_city is fixed).
        2. For each start, runs Nearest Neighbor to visit all others.
        3. Picks the route with the minimum total travel distance.
        """
        if not cities:
            return [], 0.0
        
        # 1. Calculate scores and prepare data
        city_scores = []
        for city in cities:
            score = self._calculate_city_traffic_score(city)
            city_scores.append({
                'name': city.get('name', ''),
                'score': score,
                'data': city
            })
            
        # If only 1 city, return it
        if len(city_scores) == 1:
            return [city_scores[0]['name']], city_scores[0]['score']

        # 2. Define helper for distance
        def get_dist(c1_name, c2_name):
            coords1 = self.CITY_COORDINATES.get(c1_name)
            coords2 = self.CITY_COORDINATES.get(c2_name)
            if coords1 and coords2:
                # Euclidean distance approximation
                return ((coords1[0] - coords2[0])**2 + (coords1[1] - coords2[1])**2)**0.5
            return float('inf') # Penalize missing coordinates

        # 3. Try all possible start nodes (or just the fixed one)
        possible_starts = [c['name'] for c in city_scores]
        if start_city:
            possible_starts = [start_city]
            
        best_route = []
        min_total_dist = float('inf')
        
        for start_node in possible_starts:
            unvisited = city_scores.copy()
            
            # Find and remove start node
            current_city = None
            for i, c in enumerate(unvisited):
                if c['name'] == start_node:
                    current_city = unvisited.pop(i)
                    break
            
            if not current_city:
                continue
                
            current_route = [current_city]
            current_dist = 0.0
            
            # Nearest Neighbor loop
            while unvisited:
                nearest = None
                nearest_dist = float('inf')
                nearest_idx = -1
                
                for i, candidate in enumerate(unvisited):
                    d = get_dist(current_city['name'], candidate['name'])
                    if d < nearest_dist:
                        nearest_dist = d
                        nearest = candidate
                        nearest_idx = i
                
                if nearest and nearest_dist != float('inf'):
                    current_city = unvisited.pop(nearest_idx)
                    current_route.append(current_city)
                    current_dist += nearest_dist
                else:
                    # If we can't find a nearest neighbor (e.g. missing coords), break
                    # Fallback: just append the rest by score
                    unvisited.sort(key=lambda x: x['score'], reverse=True)
                    current_route.extend(unvisited)
                    current_dist += 1000 * len(unvisited) # Heavy penalty
                    unvisited = []
            
            # Check if this path is better
            if current_dist < min_total_dist:
                min_total_dist = current_dist
                best_route = current_route

        # 4. Extract ordered names and calculate total score
        ordered_names = [city['name'] for city in best_route]
        total_score = sum(city['score'] for city in best_route)
        
        logger.info(f"Optimized spatial route: {' → '.join(ordered_names)} (Score: {total_score:.1f}, Dist: {min_total_dist:.2f})")
        
        return ordered_names, total_score

    def suggest_city_route(
        self,
        city_name: str,
        user_pois: List[str]
    ) -> Tuple[List[str], float]:
        """
        Suggest optimal route within a city combining user POIs and hotspots.
        Tries to create a logical flow (e.g. Center -> Outwards or North -> South)
        """
        # Normalize city name for lookup
        normalized_name = None
        for key in self.CITY_HOTSPOTS:
            if key.lower() in city_name.lower():
                normalized_name = key
                break
        
        hotspots = self.CITY_HOTSPOTS.get(normalized_name, [])
        
        # Combine unique locations
        route = []
        score = 0.0
        
        # Simple logic: Start with Hub (Hotspot 1), then User POIs, then other Hotspots
        # But let's try to be smarter: Interleave them to suggest a tour
        
        # 1. Start with main Hub
        if hotspots:
            route.append(hotspots[0])
            score += 25.0
        
        # 2. Add User POIs (assuming they are specific destinations)
        for poi in user_pois:
            clean_poi = poi.strip().strip(',.-')
            if clean_poi and clean_poi not in route:
                route.append(clean_poi)
                score += 10.0
        
        # 3. Add secondary hotspots if route is short
        for spot in hotspots[1:]:
            if spot not in route and len(route) < 6: # Limit to avoid overwhelming
                route.append(spot)
                score += 15.0
                
        return route, score

    def compare_routes(
        self,
        route_a: List[Dict[str, Any]],
        route_b: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compare two routes and return which is better.
        
        Returns:
            Comparison results with scores and recommendation
        """
        score_a = self.calculate_route_score(route_a)
        score_b = self.calculate_route_score(route_b)
        
        better = 'A' if score_a['total_score'] > score_b['total_score'] else 'B'
        difference = abs(score_a['total_score'] - score_b['total_score'])
        
        return {
            'route_a_score': score_a['total_score'],
            'route_b_score': score_b['total_score'],
            'better_route': better,
            'score_difference': difference,
            'improvement_percent': (difference / min(score_a['total_score'], score_b['total_score'])) * 100 if min(score_a['total_score'], score_b['total_score']) > 0 else 0
        }
