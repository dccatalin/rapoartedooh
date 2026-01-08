
import sqlite3
import os

DB_PATH = 'src/data/rapoartedooh.db'

def add_column():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(campaigns)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'transit_periods' not in columns:
            print("Adding transit_periods column...")
            cursor.execute("ALTER TABLE campaigns ADD COLUMN transit_periods JSON")
            print("Column added successfully.")
        else:
            print("Column 'transit_periods' already exists.")
            
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    add_column()
