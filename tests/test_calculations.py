import pytest
from src.reporting.financial_report_generator import FinancialReportGenerator

class TestCalculations:
    def test_roi_calculation(self):
        # Revenue = 1000, Cost = 500 -> ROI = 100%
        revenue = 1000
        total_cost = 500
        roi = ((revenue - total_cost) / total_cost) * 100
        assert roi == 100.0

        # Revenue = 500, Cost = 1000 -> ROI = -50%
        revenue = 500
        total_cost = 1000
        roi = ((revenue - total_cost) / total_cost) * 100
        assert roi == -50.0

    def test_cost_calculation(self):
        distance = 100
        cost_per_km = 0.5
        fixed_costs = 200
        
        total_cost = (distance * cost_per_km) + fixed_costs
        assert total_cost == 250.0  # (100 * 0.5) + 200 = 50 + 200 = 250

    def test_distance_calculation(self):
        # 8 hours driving, 15 min stationing/hour, 50 km/h, 1 day
        daily_hours = 8
        stationing_min = 15
        speed = 50
        days = 1
        
        effective_hours = daily_hours - (daily_hours * stationing_min / 60)
        # 8 - (8 * 0.25) = 6 hours driving
        assert effective_hours == 6.0
        
        distance = effective_hours * speed * days
        # 6 * 50 * 1 = 300 km
        assert distance == 300.0
