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

    if 'status' not in columns:
        print("Adding 'status' column to campaign_spots...")
        cursor.execute("ALTER TABLE campaign_spots ADD COLUMN status TEXT DEFAULT 'OK'")
    
    if 'order_index' not in columns:
        print("Adding 'order_index' column to campaign_spots...")
        cursor.execute("ALTER TABLE campaign_spots ADD COLUMN order_index INTEGER DEFAULT 0")

    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
