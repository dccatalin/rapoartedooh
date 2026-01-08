"""
Migration script to add missing email column to drivers table
"""
import sqlite3
import os

DB_PATH = 'src/data/rapoartedooh.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check existing columns
        cursor.execute("PRAGMA table_info(drivers)")
        existing_columns = {info[1] for info in cursor.fetchall()}
        
        if 'email' not in existing_columns:
            print("Adding email column to drivers table...")
            cursor.execute("ALTER TABLE drivers ADD COLUMN email TEXT")
            conn.commit()
            print("Email column added successfully!")
        else:
            print("Email column already exists")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
