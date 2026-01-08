import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'rapoartedooh.db')

def migrate():
    print(f"Migrating database at {DB_PATH}...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Create vehicle_schedules table
        print("Creating vehicle_schedules table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vehicle_schedules (
                id VARCHAR(36) PRIMARY KEY,
                vehicle_id VARCHAR(36) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                event_type VARCHAR(50) NOT NULL,
                details VARCHAR(200),
                created_at DATETIME,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
            )
        """)
        
        conn.commit()
        print("Migration successful!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
