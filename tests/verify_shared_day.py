
import datetime
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.reporting.campaign_report_generator import CampaignReportGenerator

# Mock data manager
class MockDataManager:
    def get_city_data_for_period(self, city, date):
        return {}
    def get_event_multipliers(self, city, date):
        return 1.0, 1.0, None

def test_shared_day_calculation():
    generator = CampaignReportGenerator(MockDataManager())
    
    # Setup test data: 3 cities, 5 days (Jan 1 - Jan 5)
    start_date = datetime.date(2025, 1, 1)
    end_date = datetime.date(2025, 1, 5)
    
    campaign_data = {
        'start_date': start_date,
        'end_date': end_date,
        'daily_hours': '09:00-17:00',
        'cities': ['City A', 'City B', 'City C'],
        'city_periods': {
            '__meta__': {'shared_mode': True},
            'City A': {'start': start_date, 'end': end_date},
            'City B': {'start': start_date, 'end': end_date},
            'City C': {'start': start_date, 'end': end_date}
        },
        'city_schedules': {}
    }
    
    # Calculate metrics
    metrics = generator._calculate_multi_city_metrics(campaign_data)
    
    print(f"Total Days: {metrics['total_days']}")
    print(f"Total Campaign Hours: {metrics['total_campaign_hours']}")
    
    # Expected: 5 days, 8 hours/day * 5 days = 40 hours total (averaged across cities)
    expected_days = 5
    expected_hours = 40.0
    
    if metrics['total_days'] == expected_days:
        print("PASS: Total days calculation is correct.")
    else:
        print(f"FAIL: Expected {expected_days} days, got {metrics['total_days']}")
        
    if metrics['total_campaign_hours'] == expected_hours:
        print("PASS: Total hours calculation is correct.")
    else:
        print(f"FAIL: Expected {expected_hours} hours, got {metrics['total_campaign_hours']}")

if __name__ == "__main__":
    test_shared_day_calculation()
