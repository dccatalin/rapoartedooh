from src.data.db_config import engine, Base
from sqlalchemy import text

def migrate():
    print("Migrating database schema for Vehicle Documents and Events...")
    with engine.connect() as conn:
        # Add Vehicle Columns
        print("Adding columns to 'vehicles' table...")
        columns = [
            ("rca_expiry", "DATE"),
            ("itp_expiry", "DATE"),
            ("casco_expiry", "DATE"),
            ("rovinieta_expiry", "DATE")
        ]
        
        for col, type_ in columns:
            try:
                conn.execute(text(f"ALTER TABLE vehicles ADD COLUMN {col} {type_}"))
                print(f"  Added {col}")
            except Exception as e:
                print(f"  Skipping {col} (might exist): {e}")

        # Add VehicleSchedule Columns
        print("Adding columns to 'vehicle_schedules' table...")
        sched_columns = [
            ("origin_city", "VARCHAR(100)"),
            ("destination_city", "VARCHAR(100)")
        ]
        
        for col, type_ in sched_columns:
            try:
                conn.execute(text(f"ALTER TABLE vehicle_schedules ADD COLUMN {col} {type_}"))
                print(f"  Added {col}")
            except Exception as e:
                print(f"  Skipping {col} (might exist): {e}")
                
        conn.commit()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
