"""
Comprehensive migration script to add all missing columns to database tables
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
        total_added = 0
        
        # Check and add missing columns for each table
        tables_to_check = {
            'drivers': {
                'email': 'TEXT',
                'license_number': 'TEXT'
            },
            'driver_assignment_history': {
                'created_at': 'DATETIME'
            },
            'campaigns': {
                'cost_per_km': 'INTEGER DEFAULT 0',
                'fixed_costs': 'INTEGER DEFAULT 0',
                'expected_revenue': 'INTEGER DEFAULT 0',
                'loop_duration': 'INTEGER DEFAULT 60'
            }
        }
        
        for table_name, columns_to_add in tables_to_check.items():
            # Check if table exists
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if not cursor.fetchone():
                print(f"Table {table_name} does not exist, skipping...")
                continue
            
            # Get existing columns
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = {info[1] for info in cursor.fetchall()}
            
            # Add missing columns
            for col_name, col_def in columns_to_add.items():
                if col_name not in existing_columns:
                    print(f"Adding {table_name}.{col_name}...")
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}")
                    total_added += 1
                else:
                    print(f"Column {table_name}.{col_name} already exists")
        
        conn.commit()
        print(f"\n✅ Migration completed! Added {total_added} columns total.")
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
