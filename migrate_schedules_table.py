
import os
import sys

# Add src to python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.append(src_dir)

from src.data.db_config import engine, Base
from src.data.models import VehicleSchedule

def migrate_tables():
    print("Migrating database tables...")
    try:
        # inspect existing tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'vehicle_schedules' not in tables:
            print("Creating 'vehicle_schedules' table...")
            # Create specific table
            VehicleSchedule.__table__.create(bind=engine)
            print("Table 'vehicle_schedules' created successfully.")
        else:
            print("Table 'vehicle_schedules' already exists.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate_tables()
