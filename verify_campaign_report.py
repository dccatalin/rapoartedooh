import sys
import os
import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'Numarare', 'src'))

from reporting.campaign_report_generator import CampaignReportGenerator

class MockDataManager:
    def get_setting(self, key, default):
        return default

def verify_campaign_report():
    # Mock DataManager
    data_manager = MockDataManager()
    
    # Instantiate Generator
    generator = CampaignReportGenerator(data_manager)
    
    # Sample Data (Dr. Max Example)
    # Note: Removed explicit stats to test auto-fill from CityDataManager
    campaign_data = {
        'client_name': 'Dr. Max',
        'campaign_name': 'Campanie DOOH Mobila',
        'city': 'Cluj-Napoca',
        'start_date': datetime.date(2025, 11, 21),
        'end_date': datetime.date(2025, 11, 27),
        'daily_hours': '9:00-17:00',
        'total_hours': 40,
        'vehicle_speed_kmh': 20.0,
        'stationing_min_per_hour': 10
        # Stats below should be auto-filled
        # 'population': 308000,
        # 'active_population_pct': 60,
        # 'daily_traffic_total': 200000,
        # 'daily_pedestrian_total': 255000
    }
    
    # Generate Report
    output_path = os.path.join(os.path.dirname(__file__), 'test_campaign_report_v2.pdf')
    print(f"Generating report to: {output_path}")
    
    try:
        generated_path = generator.generate_campaign_report(campaign_data, output_path)
        print(f"Success! Report generated at: {generated_path}")
    except Exception as e:
        print(f"Error generating report: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_campaign_report()
