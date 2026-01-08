"""
Fix corrupted JSON data in campaign_spots table after migration.
The migration preserved empty strings in JSON columns, which causes JSONDecodeError.
"""

import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'src', 'data', 'rapoartedooh.db')

def fix_json_columns():
    print("Fixing JSON columns in campaign_spots...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all spots
        cursor.execute("SELECT id, target_cities, target_vehicles, spot_periods, spot_schedules FROM campaign_spots")
        spots = cursor.fetchall()
        
        print(f"Found {len(spots)} spots to check")
        fixed_count = 0
        
        for spot_id, target_cities, target_vehicles, spot_periods, spot_schedules in spots:
            updates = []
            params = []
            
            # Check and fix each JSON column
            if target_cities == '':
                updates.append("target_cities = ?")
                params.append(None)
                fixed_count += 1
            
            if target_vehicles == '':
                updates.append("target_vehicles = ?")
                params.append(None)
                fixed_count += 1
            
            if spot_periods == '':
                updates.append("spot_periods = ?")
                params.append(None)
                fixed_count += 1
            
            if spot_schedules == '':
                updates.append("spot_schedules = ?")
                params.append(None)
                fixed_count += 1
            
            # Update if needed
            if updates:
                params.append(spot_id)
                sql = f"UPDATE campaign_spots SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(sql, params)
        
        conn.commit()
        print(f"✅ Fixed {fixed_count} corrupted JSON fields")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    fix_json_columns()
