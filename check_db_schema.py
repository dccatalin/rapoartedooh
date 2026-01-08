"""
Script to check the current database schema and test campaign deletion
"""

import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'src', 'data', 'rapoartedooh.db')

def check_schema():
    print("Checking database schema...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get campaign_spots table schema
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='campaign_spots'")
        result = cursor.fetchone()
        if result:
            print("\n=== campaign_spots table schema ===")
            print(result[0])
        else:
            print("❌ campaign_spots table not found!")
        
        # Check for campaigns with name containing "COPIE"
        cursor.execute("SELECT id, campaign_name FROM campaigns WHERE campaign_name LIKE '%COPIE%'")
        campaigns = cursor.fetchall()
        print(f"\n=== Found {len(campaigns)} campaigns with 'COPIE' in name ===")
        for cid, name in campaigns:
            print(f"  - {name} (ID: {cid})")
            
            # Check spots for this campaign
            cursor.execute("SELECT COUNT(*) FROM campaign_spots WHERE campaign_id = ?", (cid,))
            spot_count = cursor.fetchone()[0]
            print(f"    → Has {spot_count} spots")
        
        # Try to delete one campaign manually to see the error
        if campaigns:
            test_id = campaigns[0][0]
            test_name = campaigns[0][1]
            print(f"\n=== Attempting to delete '{test_name}' ===")
            try:
                cursor.execute("DELETE FROM campaigns WHERE id = ?", (test_id,))
                conn.commit()
                print("✅ Deletion successful!")
            except Exception as e:
                print(f"❌ Deletion failed: {e}")
                conn.rollback()
        
    finally:
        conn.close()

if __name__ == "__main__":
    check_schema()
