"""
Final fix: Delete all corrupted spots and start fresh.
The backup itself contains corrupted data, so we need to start clean.
"""

import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'src', 'data', 'rapoartedooh.db')

def clean_start():
    print("Performing clean start for campaign_spots...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Drop both tables
        print("\n1. Dropping all spot tables...")
        cursor.execute("DROP TABLE IF EXISTS campaign_spots")
        cursor.execute("DROP TABLE IF EXISTS campaign_spots_backup")
        cursor.execute("DROP TABLE IF EXISTS campaign_spots_new")
        
        # Recreate fresh table
        print("\n2. Creating fresh campaign_spots table...")
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
        
        conn.commit()
        print("\n✅ Fresh table created successfully!")
        print("\nℹ️  All previous spots have been removed.")
        print("   Users can now upload spots without corruption issues.")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    clean_start()
