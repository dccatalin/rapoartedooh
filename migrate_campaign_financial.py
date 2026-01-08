"""
Migration script to add missing financial columns to campaigns table
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
        cursor.execute("PRAGMA table_info(campaigns)")
        existing_columns = {info[1] for info in cursor.fetchall()}
        
        # Columns to add
        new_columns = {
            'cost_per_km': 'INTEGER DEFAULT 0',
            'fixed_costs': 'INTEGER DEFAULT 0',
            'expected_revenue': 'INTEGER DEFAULT 0',
            'loop_duration': 'INTEGER DEFAULT 60'
        }
        
        added = 0
        for col_name, col_def in new_columns.items():
            if col_name not in existing_columns:
                print(f"Adding column: {col_name}")
                cursor.execute(f"ALTER TABLE campaigns ADD COLUMN {col_name} {col_def}")
                added += 1
            else:
                print(f"Column {col_name} already exists")
        
        conn.commit()
        print(f"\nMigration completed! Added {added} columns.")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
