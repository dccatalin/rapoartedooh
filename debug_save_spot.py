
import sys
import os
import datetime
import json
sys.path.append(os.getcwd())
from src.data.campaign_storage import CampaignStorage
from src.data.db_config import SessionLocal
from src.data.models import Campaign, CampaignSpot

# Setup
s = CampaignStorage()
session = SessionLocal()

# 1. Create a dummy campaign
camp = Campaign(campaign_name="Debug Save Spot Campaign")
session.add(camp)
session.commit()
camp_id = camp.id
print(f"Created Debug Campaign ID: {camp_id}")

# 2. Test Data
test_spot_data = {
    'campaign_id': camp_id,
    'name': "Test Spot Persistence",
    'duration': 15,
    'status': "OK",
    'target_cities': ["Bucuresti", "Cluj"],
    'start_date': datetime.date(2025, 1, 1),
    'end_date': datetime.date(2025, 1, 31),
    'hourly_schedule': "10:00-14:00",
    'is_active': True,
    'notes': "Debug note"
}

# 3. Call save_spot - mimicking the UI call (no temp file for now as we test DB persistence)
print("Saving spot...")
try:
    with open("dummy_test_file.txt", "w") as f:
        f.write("dummy content")
    
    # storage.save_spot handles file moving, so we need a dummy file
    saved_spot_id = s.save_spot(test_spot_data, "dummy_test_file.txt")
    print(f"Saved Spot ID: {saved_spot_id}")
    
    # 4. Verify Persistence
    print("Verifying persistence...")
    # New session to ensure we read from DB
    session2 = SessionLocal()
    real_id = saved_spot_id[0] if isinstance(saved_spot_id, tuple) else saved_spot_id
    spot = session2.query(CampaignSpot).filter(CampaignSpot.id == real_id).first()
    
    if spot:
        print(f"Spot Found: {spot.name}")
        print(f"Target Cities: {spot.target_cities} (Type: {type(spot.target_cities)})")
        print(f"Start Date: {spot.start_date} (Type: {type(spot.start_date)})")
        print(f"End Date: {spot.end_date} (Type: {type(spot.end_date)})")
        print(f"Hourly Schedule: {spot.hourly_schedule}")
        
        # Check integrity
        failures = []
        if spot.target_cities != ["Bucuresti", "Cluj"]:
            failures.append("target_cities mismatch")
        if spot.start_date != datetime.date(2025, 1, 1):
            failures.append("start_date mismatch")
        if spot.end_date != datetime.date(2025, 1, 31):
            failures.append("end_date mismatch")
        if spot.hourly_schedule != "10:00-14:00":
            failures.append("hourly_schedule mismatch")
            
        if failures:
            print("FAILED: " + ", ".join(failures))
        else:
            print("SUCCESS: All fields persisted correctly.")
    else:
        print("FAILED: Spot not found in DB.")
        
    session2.close()

except Exception as e:
    print(f"EXCEPTION: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Cleanup
    if os.path.exists("dummy_test_file.txt"):
        os.remove("dummy_test_file.txt")
    
    # Delete test campaign and spots
    try:
        session3 = SessionLocal()
        s_obj = session3.query(CampaignSpot).filter(CampaignSpot.campaign_id == camp_id).all()
        for sp in s_obj:
            session3.delete(sp)
        c_obj = session3.query(Campaign).filter(Campaign.id == camp_id).first()
        if c_obj:
            session3.delete(c_obj)
        session3.commit()
        session3.close()
        print("Cleanup complete.")
    except:
        pass
