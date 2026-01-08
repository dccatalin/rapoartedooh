import pytest
from src.utils.route_optimizer import RouteOptimizer

class TestRouteOptimizer:
    def setup_method(self):
        self.optimizer = RouteOptimizer()
        self.cities = [
            {'name': 'Bucuresti', 'population': 1800000, 'traffic_estimate': 100},
            {'name': 'Cluj-Napoca', 'population': 300000, 'traffic_estimate': 80},
            {'name': 'Timisoara', 'population': 250000, 'traffic_estimate': 70}
        ]

    def test_traffic_score_calculation(self):
        score = self.optimizer._calculate_city_traffic_score(self.cities[0])
        assert score > 0
        
        # Bucharest should have higher score than Cluj
        score_buc = self.optimizer._calculate_city_traffic_score(self.cities[0])
        score_cluj = self.optimizer._calculate_city_traffic_score(self.cities[1])
        assert score_buc > score_cluj

    def test_suggest_optimal_route_basic(self):
        route, score = self.optimizer.suggest_optimal_route(self.cities)
        
        assert len(route) == 3
        assert "Bucuresti" in route
        assert "Cluj-Napoca" in route
        assert score > 0

    def test_suggest_city_route(self):
        city = "Bucuresti"
        pois = ["Mall Vitan", "Piata Romana"]
        
        route, score = self.optimizer.suggest_city_route(city, pois)
        
        assert len(route) >= 3  # Hub + 2 POIs
        assert "Mall Vitan" in route
        assert "Piata Romana" in route
        # Should include a hotspot like Piata Victoriei
        assert any(h in route for h in self.optimizer.CITY_HOTSPOTS["Bucuresti"])

    def test_spatial_logic(self):
        # Test if nearest neighbor logic works reasonably
        # Bucharest is closer to Ploiesti than to Timisoara
        cities = [
            {'name': 'Bucuresti'},
            {'name': 'Timisoara'},
            {'name': 'Ploiesti'}
        ]
        
        # Force start at Bucharest
        route, _ = self.optimizer.suggest_optimal_route(cities, start_city='Bucuresti')
        
        # Should be Bucuresti -> Ploiesti -> Timisoara
        assert route[0] == 'Bucuresti'
        assert route[1] == 'Ploiesti'
        assert route[2] == 'Timisoara'
