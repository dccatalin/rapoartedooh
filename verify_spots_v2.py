import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append('/Users/catalin/Antigravity/rapoartedooh')

from src.data.campaign_storage import CampaignStorage
from src.data.db_config import init_db

def test_enhancements():
    storage = CampaignStorage()
    
    # 1. Create a test campaign or use existing
    campaign_id = "test_enhancement_cid"
    
    # 2. Add multiple spots
    print("Adding spots...")
    s1_id = storage.save_spot({
        'campaign_id': campaign_id,
        'name': 'Spot 1',
        'duration': 10,
        'status': 'OK'
    })
    s2_id = storage.save_spot({
        'campaign_id': campaign_id,
        'name': 'Spot 2',
        'duration': 15,
        'status': 'Test'
    })
    s3_id = storage.save_spot({
        'campaign_id': campaign_id,
        'name': 'Spot 3',
        'duration': 20,
        'status': 'OK'
    })

    # 3. Check order and status
    spots = storage.get_campaign_spots(campaign_id)
    print(f"Initial spots: {[s['name'] for s in spots]}")
    
    # 4. Test reordering
    print("Reordering: Spot 2 Up...")
    storage.reorder_spots(campaign_id, s2_id, 'up')
    spots = storage.get_campaign_spots(campaign_id)
    print(f"Post-reorder: {[s['name'] for s in spots]}")
    
    # 5. Test editing
    print("Editing Spot 3 status to Replace...")
    storage.save_spot({
        'id': s3_id,
        'campaign_id': campaign_id,
        'status': 'Inlocuit'
    })
    spots = storage.get_campaign_spots(campaign_id)
    for s in spots:
        if s['id'] == s3_id:
            print(f"Spot 3 status: {s['status']}")

    # 6. Verify filtering logic (simulation of UI logic)
    ok_spots = [s for s in spots if s['status'] == 'OK']
    total_dur = sum(s['duration'] for s in ok_spots)
    print(f"OK Spots Count: {len(ok_spots)} (Expected 1)")
    print(f"OK Spots Total Duration: {total_dur} (Expected 10)")

    # Cleanup
    storage.delete_spot(s1_id)
    storage.delete_spot(s2_id)
    storage.delete_spot(s3_id)
    print("Verification complete!")

if __name__ == "__main__":
    test_enhancements()
