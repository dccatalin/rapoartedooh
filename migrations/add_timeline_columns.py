"""
Migration script to add vehicle_timeline and driver_timeline columns to campaigns table
"""
import sqlite3
import os
import json

# Path to database
db_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'data', 'rapoartedooh.db')

def migrate():
    """Add timeline columns to campaigns table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(campaigns)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Add vehicle_timeline if not exists
        if 'vehicle_timeline' not in columns:
            print("Adding vehicle_timeline column...")
            cursor.execute("""
                ALTER TABLE campaigns 
                ADD COLUMN vehicle_timeline TEXT DEFAULT '[]'
            """)
            print("✓ vehicle_timeline column added")
        else:
            print("✓ vehicle_timeline column already exists")
        
        # Add driver_timeline if not exists
        if 'driver_timeline' not in columns:
            print("Adding driver_timeline column...")
            cursor.execute("""
                ALTER TABLE campaigns 
                ADD COLUMN driver_timeline TEXT DEFAULT '[]'
            """)
            print("✓ driver_timeline column added")
        else:
            print("✓ driver_timeline column already exists")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    print("Starting database migration...")
    print(f"Database: {db_path}\n")
    migrate()
