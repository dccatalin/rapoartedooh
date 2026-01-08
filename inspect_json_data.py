"""
Inspect and fix malformed JSON data in campaign_spots table
"""

import sqlite3
import os
import json

db_path = os.path.join(os.path.dirname(__file__), 'src', 'data', 'rapoartedooh.db')

def inspect_and_fix_json():
    print("Inspecting JSON data in campaign_spots...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all spots with their JSON columns
        cursor.execute("""
            SELECT id, name, target_cities, target_vehicles, spot_periods, spot_schedules 
            FROM campaign_spots
        """)
        spots = cursor.fetchall()
        
        print(f"\nFound {len(spots)} spots")
        fixed_count = 0
        
        for spot_id, name, target_cities, target_vehicles, spot_periods, spot_schedules in spots:
            print(f"\n--- Spot: {name} (ID: {spot_id[:8]}...) ---")
            
            updates = []
            params = []
            
            # Check each JSON column
            for col_name, col_value in [
                ('target_cities', target_cities),
                ('target_vehicles', target_vehicles),
                ('spot_periods', spot_periods),
                ('spot_schedules', spot_schedules)
            ]:
                if col_value is None:
                    print(f"  {col_name}: NULL ✓")
                    continue
                
                if col_value == '':
                    print(f"  {col_name}: empty string → NULL")
                    updates.append(f"{col_name} = ?")
                    params.append(None)
                    fixed_count += 1
                    continue
                
                # Try to parse JSON
                try:
                    parsed = json.loads(col_value)
                    print(f"  {col_name}: valid JSON ✓")
                except json.JSONDecodeError as e:
                    print(f"  {col_name}: INVALID JSON - {e}")
                    print(f"    Raw value: {repr(col_value[:100])}")
                    # Set to NULL to fix
                    updates.append(f"{col_name} = ?")
                    params.append(None)
                    fixed_count += 1
            
            # Update if needed
            if updates:
                params.append(spot_id)
                sql = f"UPDATE campaign_spots SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(sql, params)
                print(f"  → Updated {len(updates)} columns")
        
        conn.commit()
        print(f"\n✅ Fixed {fixed_count} corrupted JSON fields")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    inspect_and_fix_json()
