"""
Migration script to add CASCADE delete to campaign_spots.campaign_id foreign key.
This allows campaigns to be deleted even if they have associated spots.
"""

import sqlite3
import os

# Path to database
db_path = os.path.join(os.path.dirname(__file__), 'src', 'data', 'rapoartedooh.db')

def migrate():
    print("Starting migration: Add CASCADE delete to campaign_spots...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # SQLite doesn't support ALTER COLUMN for foreign keys
        # We need to recreate the table
        
        # 1. Create new table with CASCADE
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS campaign_spots_new (
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
        
        # 2. Copy data from old table
        cursor.execute("""
            INSERT INTO campaign_spots_new 
            SELECT * FROM campaign_spots
        """)
        
        # 3. Drop old table
        cursor.execute("DROP TABLE campaign_spots")
        
        # 4. Rename new table
        cursor.execute("ALTER TABLE campaign_spots_new RENAME TO campaign_spots")
        
        conn.commit()
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
