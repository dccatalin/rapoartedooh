import os
import sys
from datetime import datetime, date, timedelta
import json

# Add project root to path
sys.path.append('/Users/catalin/Antigravity/rapoartedooh')

from src.data.campaign_storage import CampaignStorage

def test_spot_targeting():
    storage = CampaignStorage()
    
    # Test campaign ID
    campaign_id = "test_complex_targeting_cid_v2"
    
    print("Testing complex spot data persistence...")
    
    # Data Structures
    target_cities = ['București', 'Cluj-Napoca']
    target_vehicles = ['V001', 'V002']
    
    spot_periods = {
        'București': [{'start': '2025-01-01', 'end': '2025-01-10'}],
        'V001': {'Cluj-Napoca': [{'start': '2025-02-01', 'end': '2025-02-10'}]} # Nested
    }
    
    spot_schedules = {
        'București': {'2025-01-01': {'active': True, 'hours': '10:00-12:00'}}
    }
    
    # 1. Create a spot with complex targeting
    spot_id = storage.save_spot({
        'campaign_id': campaign_id,
        'name': 'Complex Spot Test',
        'duration': 15,
        'status': 'OK',
        
        'target_cities': target_cities,
        'target_vehicles': target_vehicles,
        'spot_shared_mode': False,
        'spot_periods': spot_periods,
        'spot_schedules': spot_schedules,
        
        # Legacy fallback
        'start_date': date(2025, 1, 1),
        'end_date': date(2025, 2, 10),
        'hourly_schedule': 'Mixed'
    })
    
    print(f"Created spot with ID: {spot_id}")
    
    # 2. Retrieve and verify
    spots = storage.get_campaign_spots(campaign_id)
    if spots:
        s = [spot for spot in spots if spot['id'] == spot_id][0]
        print(f"\nRetrieved spot:")
        print(f"  Name: {s['name']}")
        print(f"  Target Vehicles: {s.get('target_vehicles')}")
        print(f"  Spot Periods Keys: {list(s.get('spot_periods', {}).keys())}")
        
        # Verify data
        assert s.get('target_vehicles') == target_vehicles, "Vehicles mismatch"
        # Check deep structure
        assert s['spot_periods']['București'][0]['start'] == '2025-01-01', "Period mismatch"
        assert s['spot_schedules']['București']['2025-01-01']['hours'] == '10:00-12:00', "Schedule mismatch"
        
        print("\n✅ All complex targeting fields verified successfully!")
    
    # 3. Test Export Logic Simulation
    print("\nSimulating Media Plan Export Logic...")
    # Using the spot created above
    s = storage.get_campaign_spots(campaign_id)[0]
    
    # We expect 2 segments:
    # 1. București: 2025-01-01 to 2025-01-10 @ 10:00-12:00
    # 2. V001 (Cluj): 2025-02-01 to 2025-02-10 @ 09:00-18:00 (default)
    
    # Let's verify our assumptions about the stored data first
    sp = s.get('spot_periods')
    ss = s.get('spot_schedules')
    
    daily_map = {}
    
    def process(entity_periods, entity_schedules, c_name, v_name):
        if not entity_periods: return
        if isinstance(entity_periods, list):
            for p in entity_periods:
                try:
                    p_start = datetime.strptime(str(p.get('start'))[:10], "%Y-%m-%d").date()
                    p_end = datetime.strptime(str(p.get('end'))[:10], "%Y-%m-%d").date()
                    curr = p_start
                    while curr <= p_end:
                        d_str = curr.isoformat()
                        d_hours = "09:00-18:00"
                        if entity_schedules and isinstance(entity_schedules, dict):
                             if d_str in entity_schedules:
                                d_hours = entity_schedules[d_str].get('hours', d_hours)
                        
                        if d_str not in daily_map: daily_map[d_str] = {}
                        if d_hours not in daily_map[d_str]: daily_map[d_str][d_hours] = {'c': set(), 'v': set()}
                        
                        if c_name: daily_map[d_str][d_hours]['c'].add(c_name)
                        if v_name: daily_map[d_str][d_hours]['v'].add(v_name)
                        
                        curr += timedelta(days=1)
                except Exception as e:
                    print(f"Error: {e}")

    for k1, v1 in sp.items():
        if isinstance(v1, dict): # Vehicle -> City
            vid = k1
            for city, per in v1.items():
                sched = ss.get(vid, {}).get(city, {}) if ss.get(vid) else {}
                process(per, sched, city, vid)
        else: # City (Shared)
            city = k1
            sched = ss.get(city, {})
            process(v1, sched, city, "All")
            
    # Verify Daily Map Counts
    # 1. București: 10 days
    # 2. Cluj: 10 days
    total_days = len(daily_map)
    print(f"  Total Active Days: {total_days}")
    assert total_days == 20, f"Expected 20 active days, got {total_days}"
    
    # Verify Content
    d1 = daily_map.get('2025-01-01')
    assert d1 is not None, "Missing Jan 1st"
    assert '10:00-12:00' in d1, "Missing custom hours for Jan 1st"
    
    d2 = daily_map.get('2025-02-01')
    assert d2 is not None, "Missing Feb 1st"
    assert '09:00-18:00' in d2, "Missing default hours for Feb 1st"
    
    print("✅ Export logic simulation passed!")

    # Cleanup
    storage.delete_spot(spot_id)
    print("\nVerification complete!")

if __name__ == "__main__":
    test_spot_targeting()
