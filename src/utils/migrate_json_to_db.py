import json
import os
import sys
import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.data.db_config import init_db, SessionLocal
from src.data.models import Vehicle, Driver, Campaign, VehicleStatusHistory, DriverAssignmentHistory

def load_json(filename):
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', filename)
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.datetime.fromisoformat(str(date_str))
    except ValueError:
        return None

def parse_date_only(date_str):
    if not date_str:
        return None
    try:
        if isinstance(date_str, str):
            return datetime.date.fromisoformat(date_str)
        return date_str
    except ValueError:
        return None

def migrate():
    print("Initializing database...")
    init_db()
    session = SessionLocal()
    
    try:
        # 1. Migrate Drivers
        print("Migrating Drivers...")
        drivers_data = load_json('drivers.json')
        driver_map = {} # Old ID -> New Object
        
        for d_id, d_data in drivers_data.items():
            driver = Driver(
                id=d_id,
                name=d_data.get('name'),
                phone=d_data.get('phone'),
                license_number=d_data.get('license_number'),
                status=d_data.get('status', 'active'),
                assigned_vehicle_id=d_data.get('assigned_vehicle'),
                created_at=parse_date(d_data.get('created')),
                last_modified=parse_date(d_data.get('last_modified'))
            )
            session.add(driver)
            driver_map[d_id] = driver
            
            # Migrate assignment history
            for hist in d_data.get('assignment_history', []):
                assignment = DriverAssignmentHistory(
                    driver_id=d_id,
                    vehicle_id=hist.get('vehicle_id'),
                    vehicle_name=hist.get('vehicle_name'),
                    start_date=parse_date(hist.get('start_date')),
                    end_date=parse_date(hist.get('end_date'))
                )
                session.add(assignment)

        # 2. Migrate Vehicles
        print("Migrating Vehicles...")
        vehicles_data = load_json('vehicles.json')
        
        for v_id, v_data in vehicles_data.items():
            vehicle = Vehicle(
                id=v_id,
                name=v_data.get('name'),
                registration=v_data.get('registration'),
                status=v_data.get('status', 'active'),
                driver_id=v_data.get('driver_id'),
                driver_name=v_data.get('driver_name'),
                created_at=parse_date(v_data.get('created')),
                last_modified=parse_date(v_data.get('last_modified'))
            )
            session.add(vehicle)
            
            # Migrate status history
            for hist in v_data.get('status_history', []):
                status_hist = VehicleStatusHistory(
                    vehicle_id=v_id,
                    status=hist.get('status'),
                    date=parse_date(hist.get('date')),
                    note=hist.get('note')
                )
                session.add(status_hist)

        # 3. Migrate Campaigns
        print("Migrating Campaigns...")
        campaigns_data = load_json('campaign_history.json')
        
        for c_id, c_data in campaigns_data.items():
            # Handle complex fields
            hourly = c_data.get('hourly_data', {})
            demos = c_data.get('demographics', {})
            locs = c_data.get('locations', {})
            cities = c_data.get('cities', [])
            city_sched = c_data.get('city_schedules', {})
            city_periods = c_data.get('city_periods', {})
            
            # Handle spot duration (could be sec or string)
            spot_dur = c_data.get('spot_duration_sec') or c_data.get('spot_duration')
            if isinstance(spot_dur, str) and spot_dur.isdigit():
                spot_dur = int(spot_dur)
            
            campaign = Campaign(
                id=c_id,
                campaign_name=c_data.get('campaign_name'),
                client_name=c_data.get('client_name'),
                start_date=parse_date_only(c_data.get('start_date')),
                end_date=parse_date_only(c_data.get('end_date')),
                vehicle_id=c_data.get('vehicle_id'),
                driver_id=c_data.get('driver_id'),
                status=c_data.get('status'),
                total_impressions=c_data.get('total_impressions', 0),
                unique_reach=c_data.get('unique_reach', 0),
                
                # New fields
                cities=cities,
                spot_duration=spot_dur,
                is_exclusive=c_data.get('is_exclusive', False),
                po_number=c_data.get('po_number'),
                daily_hours=c_data.get('daily_hours'),
                known_distance_total=c_data.get('known_distance_total', 0),
                route_data=c_data.get('route_data', {}),
                city_schedules=city_sched,
                city_periods=city_periods,
                
                hourly_data=hourly,
                demographics=demos,
                locations=locs,
                created_at=parse_date(c_data.get('created_at')) or datetime.datetime.now(),
                last_modified=parse_date(c_data.get('last_modified'))
            )
            session.add(campaign)
            
        session.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        session.rollback()
        print(f"Error during migration: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    migrate()
