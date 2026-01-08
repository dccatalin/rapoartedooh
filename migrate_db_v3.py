
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join("src", "data", "rapoartedooh.db")

def migrate():
    print(f"Migrating database at {DB_PATH}...")
    
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(campaigns)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'last_modified' not in columns:
            print("Adding 'last_modified' column to 'campaigns' table...")
            cursor.execute("ALTER TABLE campaigns ADD COLUMN last_modified DATETIME")
            
            # Update existing rows with current time
            now = datetime.now()
            cursor.execute("UPDATE campaigns SET last_modified = ?", (now,))
            
            conn.commit()
            print("Migration successful: added 'last_modified'.")
        else:
            print("'last_modified' column already exists.")
            
        if 'created_at' not in columns:
            print("Adding 'created_at' column to 'campaigns' table...")
            cursor.execute("ALTER TABLE campaigns ADD COLUMN created_at DATETIME")
            now = datetime.now()
            cursor.execute("UPDATE campaigns SET created_at = ?", (now,))
            conn.commit()
            print("Migration successful: added 'created_at'.")

    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
