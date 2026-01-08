
import sqlite3
import os

DB_PATH = '/Users/catalin/Antigravity/rapoartedooh/src/data/rapoartedooh.db'

def migrate():
    if not os.path.exists(DB_PATH):
        # Fallback for relative path if script run from root
        rel_path = 'src/data/rapoartedooh.db'
        if os.path.exists(rel_path):
            current_db_path = rel_path
        else:
            print(f"Database not found at {DB_PATH}")
            return
    else:
        current_db_path = DB_PATH
        
    print(f"Migrating database at: {current_db_path}")

    conn = sqlite3.connect(current_db_path)
    cursor = conn.cursor()

    print("Checking columns in campaign_spots...")
    cursor.execute("PRAGMA table_info(campaign_spots)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'target_vehicles' not in columns:
        print("Adding 'target_vehicles' column...")
        cursor.execute("ALTER TABLE campaign_spots ADD COLUMN target_vehicles TEXT")
        
    if 'spot_periods' not in columns:
        print("Adding 'spot_periods' column...")
        cursor.execute("ALTER TABLE campaign_spots ADD COLUMN spot_periods TEXT")
        
    if 'spot_schedules' not in columns:
        print("Adding 'spot_schedules' column...")
        cursor.execute("ALTER TABLE campaign_spots ADD COLUMN spot_schedules TEXT")
        
    if 'spot_shared_mode' not in columns:
        print("Adding 'spot_shared_mode' column...")
        cursor.execute("ALTER TABLE campaign_spots ADD COLUMN spot_shared_mode INTEGER DEFAULT 1")

    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
