from src.data.db_config import engine, Base
from src.data.models import DriverSchedule

def init_db():
    print("Creating driver_schedules table...")
    # Create specifically the new table
    DriverSchedule.__table__.create(bind=engine, checkfirst=True)
    print("Done.")

if __name__ == "__main__":
    init_db()
