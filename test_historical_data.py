import sys
import os
import datetime
import json

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data.city_data_manager import CityDataManager

def test_historical_data():
    print("Testing CityDataManager with Historical Data...")
    manager = CityDataManager()
    
    # 1. Test loading
    cities = manager.get_all_cities()
    print(f"Loaded {len(cities)} cities.")
    if "Bucuresti" not in cities:
        print("FAIL: Bucuresti not found")
        return
        
    # 2. Test get_city_profile (current)
    profile = manager.get_city_profile("Bucuresti")
    if not profile:
        print("FAIL: Could not get current profile for Bucuresti")
        return
    print(f"Current Bucuresti population: {profile.get('population')}")
    
    # 3. Test get_city_data_for_period
    # Test exact match
    date_q4 = datetime.date(2024, 11, 15) # Q4 2024
    data_q4 = manager.get_city_data_for_period("Bucuresti", date_q4)
    if not data_q4:
        print("FAIL: Could not get data for Q4 2024")
    else:
        print(f"Data for Q4 2024 found: {data_q4.get('population')}")
        
    # Test fallback (future date)
    date_future = datetime.date(2025, 5, 1)
    data_future = manager.get_city_data_for_period("Bucuresti", date_future)
    if not data_future:
        print("FAIL: Could not get data for future date (fallback)")
    else:
        print(f"Data for Future (fallback) found: {data_future.get('population')}")
        
    # 4. Test add_city (historical)
    new_city_data = {
        "population": 10000,
        "active_population_pct": 50,
        "daily_traffic_total": 5000,
        "daily_pedestrian_total": 5000,
        "modal_split": {},
        "avg_commute_distance_km": 5,
        "description": "Test City"
    }
    manager.add_city("TestCity", new_city_data)
    
    # Verify it was added with correct period
    now = datetime.datetime.now()
    quarter = (now.month - 1) // 3 + 1
    period_key = f"{now.year}-Q{quarter}"
    
    # Reload to verify persistence
    manager2 = CityDataManager()
    history = manager2.profiles.get("TestCity")
    if not history:
        print("FAIL: TestCity not saved")
        return
        
    if period_key not in history:
        print(f"FAIL: TestCity does not have key {period_key}")
        print(f"Keys found: {history.keys()}")
    else:
        print(f"PASS: TestCity saved correctly with period {period_key}")

if __name__ == "__main__":
    test_historical_data()
