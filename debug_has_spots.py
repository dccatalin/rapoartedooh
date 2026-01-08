
import sys
import os
sys.path.append(os.getcwd())
from src.data.campaign_storage import CampaignStorage

s = CampaignStorage()
campaigns = s.get_all_campaigns()

if campaigns:
    print(f"Total campaigns: {len(campaigns)}")
    for c in campaigns[:5]: # Check first 5
        print(f"ID: {c['id']}, Name: {c['campaign_name']}, Has Spots: {c.get('has_spots')} (Type: {type(c.get('has_spots'))})")
else:
    print("No campaigns found.")
