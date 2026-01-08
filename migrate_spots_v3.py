import sqlite3
import os

DB_PATH = '/Users/catalin/Antigravity/rapoartedooh/src/data/rapoartedooh.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Checking columns in campaign_spots...")
    cursor.execute("PRAGMA table_info(campaign_spots)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'target_cities' not in columns:
        print("Adding 'target_cities' column...")
        cursor.execute("ALTER TABLE campaign_spots ADD COLUMN target_cities TEXT")
    
    if 'start_date' not in columns:
        print("Adding 'start_date' column...")
        cursor.execute("ALTER TABLE campaign_spots ADD COLUMN start_date DATE")
    
    if 'end_date' not in columns:
        print("Adding 'end_date' column...")
        cursor.execute("ALTER TABLE campaign_spots ADD COLUMN end_date DATE")
    
    if 'hourly_schedule' not in columns:
        print("Adding 'hourly_schedule' column...")
        cursor.execute("ALTER TABLE campaign_spots ADD COLUMN hourly_schedule TEXT")

    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
