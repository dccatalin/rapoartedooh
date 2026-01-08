from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from src.data.db_config import Base

def generate_uuid():
    return str(uuid.uuid4())

class Vehicle(Base):
    __tablename__ = 'vehicles'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    registration = Column(String(50))
    status = Column(String(20), default='active')
    driver_id = Column(String(36), ForeignKey('drivers.id'), nullable=True)
    driver_name = Column(String(100), nullable=True) # Denormalized for convenience, or remove if strictly normalized
    created_at = Column(DateTime, default=datetime.now)
    last_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    status_history = relationship("VehicleStatusHistory", back_populates="vehicle", cascade="all, delete-orphan")
    driver = relationship("Driver", back_populates="assigned_vehicle_rel", foreign_keys=[driver_id])

class VehicleStatusHistory(Base):
    __tablename__ = 'vehicle_status_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_id = Column(String(36), ForeignKey('vehicles.id'), nullable=False)
    status = Column(String(20), nullable=False)
    date = Column(DateTime, default=datetime.now)
    note = Column(Text)

    vehicle = relationship("Vehicle", back_populates="status_history")

class Driver(Base):
    __tablename__ = 'drivers'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    phone = Column(String(50))
    license_number = Column(String(50))
    status = Column(String(20), default='active')
    assigned_vehicle_id = Column(String(36), ForeignKey('vehicles.id'), nullable=True) # Redundant if 1:1, but keeps bidirectional logic clear
    created_at = Column(DateTime, default=datetime.now)
    last_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    assignment_history = relationship("DriverAssignmentHistory", back_populates="driver", cascade="all, delete-orphan")
    assigned_vehicle_rel = relationship("Vehicle", back_populates="driver", foreign_keys=[Vehicle.driver_id], uselist=False)

class DriverAssignmentHistory(Base):
    __tablename__ = 'driver_assignment_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    driver_id = Column(String(36), ForeignKey('drivers.id'), nullable=False)
    vehicle_id = Column(String(36), nullable=True) # Store ID even if vehicle deleted? Or FK? Let's keep ID for history.
    vehicle_name = Column(String(100))
    start_date = Column(DateTime, default=datetime.now)
    end_date = Column(DateTime, nullable=True)

    driver = relationship("Driver", back_populates="assignment_history")

class Campaign(Base):
    __tablename__ = 'campaigns'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    campaign_name = Column(String(200), nullable=False)
    client_name = Column(String(200))
    start_date = Column(Date)
    end_date = Column(Date)
    vehicle_id = Column(String(36)) # Loose coupling for now, or FK if strict
    driver_id = Column(String(36))
    status = Column(String(20))
    
    # Metrics
    total_impressions = Column(Integer, default=0)
    unique_reach = Column(Integer, default=0)
    
    # Campaign Details
    cities = Column(JSON) # List of cities
    spot_duration = Column(Integer) # In seconds
    is_exclusive = Column(Boolean, default=False)
    po_number = Column(String(50))
    daily_hours = Column(String(50))
    known_distance_total = Column(Integer, default=0)
    route_data = Column(JSON)
    
    # Complex data stored as JSON
    hourly_data = Column(JSON)
    demographics = Column(JSON)
    locations = Column(JSON)
    city_schedules = Column(JSON) # Schedule per city
    city_periods = Column(JSON) # Dates per city
    
    # Vehicle Performance
    vehicle_speed_kmh = Column(Integer, default=25)
    stationing_min_per_hour = Column(Integer, default=15)
    
    created_at = Column(DateTime, default=datetime.now)
    last_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class VehicleSchedule(Base):
    __tablename__ = 'vehicle_schedules'

    id = Column(String(36), primary_key=True, default=generate_uuid)
    vehicle_id = Column(String(36), ForeignKey('vehicles.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    event_type = Column(String(50), nullable=False) # 'maintenance', 'no_docs', 'transit', 'manual_transit'
    details = Column(String(200)) # Note/Reason
    created_at = Column(DateTime, default=datetime.now)

    vehicle = relationship("Vehicle", backref="schedules")
    
    created_at = Column(DateTime, default=datetime.now)
    last_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)
