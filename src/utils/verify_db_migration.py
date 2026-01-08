import sys
import os
import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.data.db_config import init_db
from src.data.vehicle_manager import VehicleManager
from src.data.driver_manager import DriverManager
from src.data.campaign_storage import CampaignStorage

def verify():
    print("Initializing DB...")
    init_db()
    
    vm = VehicleManager()
    dm = DriverManager()
    cs = CampaignStorage()
    
    print("\n--- Testing Vehicle Manager ---")
    v_id = vm.add_vehicle("Test Vehicle", "B-99-TST")
    print(f"Created Vehicle ID: {v_id}")
    
    vehicle = vm.get_vehicle(v_id)
    assert vehicle['name'] == "Test Vehicle"
    assert vehicle['registration'] == "B-99-TST"
    print("Vehicle retrieval: OK")
    
    print("\n--- Testing Driver Manager ---")
    d_id = dm.add_driver("Test Driver", "0700000000")
    print(f"Created Driver ID: {d_id}")
    
    driver = dm.get_driver(d_id)
    assert driver['name'] == "Test Driver"
    print("Driver retrieval: OK")
    
    print("\n--- Testing Assignment ---")
    success = dm.assign_to_vehicle(d_id, v_id, "Test Vehicle")
    # Also update vehicle side (usually handled by UI logic, but let's check manager)
    vm.assign_driver(v_id, d_id, "Test Driver")
    
    driver = dm.get_driver(d_id)
    vehicle = vm.get_vehicle(v_id)
    
    assert driver['assigned_vehicle'] == v_id
    assert vehicle['driver_id'] == d_id
    print("Assignment: OK")
    
    print("\n--- Testing Campaign Storage ---")
    c_data = {
        'campaign_name': 'Test Campaign',
        'client_name': 'Test Client',
        'start_date': datetime.date.today(),
        'end_date': datetime.date.today(),
        'vehicle_id': v_id,
        'driver_id': d_id,
        'status': 'active',
        'cities': ['Bucuresti', 'Ploiesti'],
        'spot_duration': 15,
        'is_exclusive': True,
        'po_number': 'PO-12345',
        'daily_hours': '09:00-18:00',
        'known_distance_total': 150.5,
        'route_data': {'distance_km': 150.5, 'points': []},
        'hourly_data': {'12': 100},
        'demographics': {'male': 50},
        'locations': {'loc1': 'test'}
    }
    
    c_id = cs.save_campaign(c_data)
    print(f"Created Campaign ID: {c_id}")
    
    campaign = cs.get_campaign(c_id)
    assert campaign['campaign_name'] == 'Test Campaign'
    assert campaign['hourly_data']['12'] == 100
    assert 'Bucuresti' in campaign['cities']
    assert campaign['spot_duration'] == 15
    assert campaign['is_exclusive'] is True
    assert campaign['po_number'] == 'PO-12345'
    assert campaign['daily_hours'] == '09:00-18:00'
    assert campaign['known_distance_total'] == 150.5
    assert campaign['route_data']['distance_km'] == 150.5
    print("Campaign retrieval: OK")
    
    print("\n--- Cleanup ---")
    cs.delete_campaign(c_id)
    # Note: Delete vehicle/driver might fail if constraints are enforced, but let's try
    vm.delete_vehicle(v_id, force=True) 
    dm.delete_driver(d_id)
    
    print("Verification Completed Successfully!")

if __name__ == "__main__":
    verify()
