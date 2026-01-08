import os
import sys
from datetime import datetime, date, timedelta
import pandas as pd

def test_campaign_export_simulation():
    print("Simulating Campaign Schedule Export Logic (Persistent / Saved Data)...")
    
    # Mock 'existing_data' structure
    existing_data = {
        'vehicle_id': 'V1',
        'additional_vehicles': [{'vehicle_id': 'V2'}],
        'city_periods': {
            'București': [{'start': '2025-01-01', 'end': '2025-01-05'}],
            'Cluj': [{'start': '2025-02-01', 'end': '2025-02-02'}],
            '__meta__': {'shared_mode': True}
        },
        'city_schedules': {
            'București': {'2025-01-01': {'active': True, 'hours': '10-12'}}
        },
        'transit_periods': [
            {'vehicle_id': 'V1', 'origin': 'A', 'destination': 'B', 'start': '2025-01-06', 'end': '2025-01-06', 'hours': '06-08', 'km': 100, 'duration': 2}
        ],
        'daily_hours': "09:00-18:00"
    }
    
    vehicle_options = {'V1': 'Ford (V1)', 'V2': 'Toyota (V2)'}

    # --- LOGIC START (Copied from 1_Campaigns.py) ---
    csv_ready = None
    full_export_data = []

    if existing_data and existing_data.get('vehicle_id'):
        # 1. Gather all vehicles from SAVED data
        saved_vids = [existing_data.get('vehicle_id')]
        for av in existing_data.get('additional_vehicles', []):
            if av.get('vehicle_id'): saved_vids.append(av.get('vehicle_id'))
        
        # 2. Gather Configuration
        s_shared_mode = existing_data.get('city_periods', {}).get('__meta__', {}).get('shared_mode', True)
        s_city_periods = existing_data.get('city_periods', {})
        s_city_schedules = existing_data.get('city_schedules', {})
        s_transit = existing_data.get('transit_periods', [])
        s_daily_h = existing_data.get('daily_hours') or "09:00-18:00"

        # 3. Pre-calculate Shared Segments
        s_shared_map_segments = []
        if s_shared_mode:
            for city, periods in s_city_periods.items():
                if city == '__meta__': continue
                if isinstance(periods, dict): periods = [periods]
                daily_log = {}
                for p in periods:
                    try:
                        curr = datetime.fromisoformat(str(p['start'])[:10]).date()
                        end_p = datetime.fromisoformat(str(p['end'])[:10]).date()
                        while curr <= end_p:
                            d_str = str(curr)
                            d_hours = s_city_schedules.get(city, {}).get(d_str, {}).get('hours', s_daily_h)
                            is_active = s_city_schedules.get(city, {}).get(d_str, {}).get('active', True)
                            if is_active: daily_log[d_str] = d_hours
                            curr += timedelta(days=1)
                    except: pass
                sorted_dl = sorted(daily_log.keys())
                if sorted_dl:
                    cur_s = sorted_dl[0]
                    cur_e = sorted_dl[0]
                    cur_h = daily_log[cur_s]
                    for day in sorted_dl[1:]:
                        h = daily_log[day]
                        d_obj = datetime.fromisoformat(day).date()
                        prev_obj = datetime.fromisoformat(cur_e).date()
                        if h == cur_h and (d_obj - prev_obj).days == 1:
                            cur_e = day
                        else:
                            s_shared_map_segments.append({'city': city, 'start': cur_s, 'end': cur_e, 'hours': cur_h})
                            cur_s, cur_e, cur_h = day, day, h
                    s_shared_map_segments.append({'city': city, 'start': cur_s, 'end': cur_e, 'hours': cur_h})

        # 4. Build Rows
        for vid in saved_vids:
            v_str = vehicle_options.get(vid, vid)
            vehicle_timeline = []
            if s_shared_mode:
                for seg in s_shared_map_segments:
                    vehicle_timeline.append({'type':'campaign', 'city':seg['city'], 'start':seg['start'], 'end':seg['end'], 'hours':seg['hours']})
            
            for tp in s_transit:
                if tp.get('vehicle_id') == vid:
                    vehicle_timeline.append({'type': 'transit', 'city': f"TRANSIT: {tp.get('origin')} -> {tp.get('destination')}", 'start': tp.get('start'), 'end': tp.get('end'), 'hours': f"{tp.get('hours')}"})

            vehicle_timeline.sort(key=lambda x: str(x['start']))
            
            for item in vehicle_timeline:
                 full_export_data.append({
                    'Vehicle': v_str,
                    'City': item['city'],
                    'Start': item['start'],
                    'End': item['end'],
                    'Hours': item['hours']
                })

    print(full_export_data)

    # Assertions
    # Check V1 data
    v1 = [x for x in full_export_data if 'V1' in x['Vehicle']]
    assert len(v1) == 4, f"V1 should have 4 rows, got {len(v1)}"
    assert "TRANSIT" in v1[2]['City'] # The intermediate transit
    
    # Check V2 data (Inherited shared schedule)
    v2 = [x for x in full_export_data if 'V2' in x['Vehicle']]
    assert len(v2) == 3, f"V2 should have 3 rows (Campaign only), got {len(v2)}"
    
    print("✅ Persistent Export Logic verified!")

if __name__ == "__main__":
    test_campaign_export_simulation()
