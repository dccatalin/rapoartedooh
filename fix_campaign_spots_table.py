"""
Complete fix for campaign_spots table corruption.
The migration script misaligned all columns. This script will:
1. Backup existing data
2. Drop corrupted table
3. Recreate with correct schema
4. Restore valid data only
"""

import sqlite3
import os
import json

db_path = os.path.join(os.path.dirname(__file__), 'src', 'data', 'rapoartedooh.db')

def fix_campaign_spots_table():
    print("Fixing campaign_spots table corruption...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Backup old table
        print("\n1. Creating backup...")
        cursor.execute("DROP TABLE IF EXISTS campaign_spots_backup")
        cursor.execute("CREATE TABLE campaign_spots_backup AS SELECT * FROM campaign_spots")
        backup_count = cursor.execute("SELECT COUNT(*) FROM campaign_spots_backup").fetchone()[0]
        print(f"   Backed up {backup_count} spots")
        
        # 2. Drop corrupted table
        print("\n2. Dropping corrupted table...")
        cursor.execute("DROP TABLE campaign_spots")
        
        # 3. Recreate with correct schema (matching the model exactly)
        print("\n3. Recreating table with correct schema...")
        cursor.execute("""
            CREATE TABLE campaign_spots (
                id TEXT PRIMARY KEY,
                campaign_id TEXT NOT NULL,
                name TEXT NOT NULL,
                file_path TEXT,
                file_name TEXT,
                duration INTEGER DEFAULT 10,
                status TEXT DEFAULT 'OK',
                order_index INTEGER DEFAULT 0,
                target_cities TEXT,
                target_vehicles TEXT,
                spot_shared_mode INTEGER DEFAULT 1,
                spot_periods TEXT,
                spot_schedules TEXT,
                start_date TEXT,
                end_date TEXT,
                hourly_schedule TEXT,
                is_active INTEGER DEFAULT 1,
                uploaded_at TEXT,
                notes TEXT,
                created_at TEXT,
                last_modified TEXT,
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
            )
        """)
        
        # 4. Restore ONLY the basic, non-corrupted data
        print("\n4. Restoring valid data...")
        cursor.execute("""
            INSERT INTO campaign_spots 
            (id, campaign_id, name, file_path, file_name, duration, status, order_index, is_active, created_at)
            SELECT id, campaign_id, name, file_path, file_name, duration, status, order_index, is_active, created_at
            FROM campaign_spots_backup
        """)
        
        restored_count = cursor.execute("SELECT COUNT(*) FROM campaign_spots").fetchone()[0]
        print(f"   Restored {restored_count} spots with basic data")
        print("   Note: Complex scheduling data (target_cities, spot_periods, etc.) was corrupted and set to NULL")
        
        conn.commit()
        print("\n✅ Table successfully recreated!")
        print("\nℹ️  Users will need to reconfigure spot targeting and scheduling for existing spots.")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    fix_campaign_spots_table()
