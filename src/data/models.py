from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, ForeignKey, Text, JSON, Float
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import uuid

from src.data.db_config import Base

def generate_uuid():
    return str(uuid.uuid4())

# --- Models ---

class VehicleStatusHistory(Base):
    __tablename__ = 'vehicle_status_history'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_id = Column(String(36), ForeignKey('vehicles.id'), nullable=False)
    status = Column(String(20), nullable=False)
    date = Column(DateTime, default=datetime.now)
    note = Column(Text)

    vehicle = relationship("src.data.models.Vehicle", back_populates="status_history")

class DriverStatusHistory(Base):
    __tablename__ = 'driver_status_history'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    driver_id = Column(String(36), ForeignKey('drivers.id'), nullable=False)
    status = Column(String(20), nullable=False)
    date = Column(DateTime, default=datetime.now)
    note = Column(Text)

    driver = relationship("src.data.models.Driver", back_populates="status_history")

class DriverAssignmentHistory(Base):
    __tablename__ = 'driver_assignment_history'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    driver_id = Column(String(36), ForeignKey('drivers.id'), nullable=False)
    vehicle_id = Column(String(36), nullable=False)
    vehicle_name = Column(String(100))
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)

    driver = relationship("src.data.models.Driver", back_populates="assignment_history")

class Driver(Base):
    __tablename__ = 'drivers'
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    phone = Column(String(50))
    email = Column(String(100))
    license_number = Column(String(50))
    status = Column(String(20), default='active')
    assigned_vehicle_id = Column(String(36), nullable=True)
    
    identity_card_expiry = Column(Date, nullable=True)
    medical_exam_expiry = Column(Date, nullable=True)
    psychological_exam_expiry = Column(Date, nullable=True)
    
    created_at = Column(DateTime, default=datetime.now)
    last_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    assigned_vehicle_rel = relationship("Vehicle", back_populates="driver", foreign_keys="Vehicle.driver_id", uselist=False)
    assignment_history = relationship(DriverAssignmentHistory, back_populates="driver", cascade="all, delete-orphan")
    status_history = relationship(DriverStatusHistory, back_populates="driver", cascade="all, delete-orphan")
    schedules = relationship("DriverSchedule", back_populates="driver", cascade="all, delete-orphan")

class Vehicle(Base):
    __tablename__ = 'vehicles'
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    registration = Column(String(50))
    status = Column(String(20), default='active')
    driver_id = Column(String(36), ForeignKey('drivers.id'), nullable=True)
    driver_name = Column(String(100), nullable=True)
    
    rca_expiry = Column(Date, nullable=True)
    itp_expiry = Column(Date, nullable=True)
    rovinieta_expiry = Column(Date, nullable=True)
    casco_expiry = Column(Date, nullable=True)
    
    mileage = Column(Integer, default=0)
    generator_hours = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.now)
    last_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    status_history = relationship(VehicleStatusHistory, back_populates="vehicle", cascade="all, delete-orphan")
    driver = relationship("Driver", back_populates="assigned_vehicle_rel", foreign_keys=[driver_id])
    schedules = relationship("VehicleSchedule", back_populates="vehicle", cascade="all, delete-orphan")
    maintenance_records = relationship("MaintenanceRecord", back_populates="vehicle", cascade="all, delete-orphan")

class Campaign(Base):
    __tablename__ = 'campaigns'
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True, default=generate_uuid)
    campaign_name = Column(String(200), nullable=False)
    client_name = Column(String(200))
    start_date = Column(Date)
    end_date = Column(Date)
    vehicle_id = Column(String(36))
    driver_id = Column(String(36))
    status = Column(String(20), default='confirmed')
    total_impressions = Column(Integer, default=0)
    unique_reach = Column(Integer, default=0)
    
    cities = Column(JSON)
    spot_duration = Column(Integer, default=10)
    is_exclusive = Column(Boolean, default=False)
    campaign_mode = Column(String(50), nullable=True) # Explicit deployment scenario
    po_number = Column(String(100))
    daily_hours = Column(String(50))
    known_distance_total = Column(Integer, default=0)
    route_data = Column(JSON)
    
    hourly_data = Column(JSON, default={})
    demographics = Column(JSON, default={})
    locations = Column(JSON, default={})
    transit_periods = Column(JSON, default=[])

    city_schedules = Column(JSON)
    city_periods = Column(JSON)
    additional_vehicles = Column(JSON, default=[])
    
    vehicle_speed_kmh = Column(Integer, default=25)
    stationing_min_per_hour = Column(Integer, default=15)
    
    cost_per_km = Column(Integer, default=0)
    fixed_costs = Column(Integer, default=0)
    expected_revenue = Column(Integer, default=0)
    loop_duration = Column(Integer, default=60)
    
    has_spots = Column(Boolean, default=False)
    spot_count = Column(Integer, default=0)
    
    # Resource timeline tracking
    vehicle_timeline = Column(JSON, default=[])  # [{"vehicle_id": "...", "start_date": "...", "end_date": "..."}]
    driver_timeline = Column(JSON, default=[])   # [{"driver_id": "...", "start_date": "...", "end_date": "..."}]
    
    created_at = Column(DateTime, default=datetime.now)
    last_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    spots = relationship("CampaignSpot", back_populates="campaign", cascade="all, delete-orphan")

class CampaignSpot(Base):
    __tablename__ = 'campaign_spots'
    __table_args__ = {'extend_existing': True}
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    campaign_id = Column(String(36), ForeignKey('campaigns.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(200), nullable=False)
    file_path = Column(String(500))
    file_name = Column(String(255))
    duration = Column(Integer, default=10)
    status = Column(String(20), default='OK')  # 'OK', 'Test', 'Inlocuit'
    order_index = Column(Integer, default=0)
    
    # Targeting and Scheduling
    target_cities = Column(JSON)  # List of city names
    target_vehicles = Column(JSON) # List of vehicle IDs (new)
    
    # Complex Scheduling (Parity with Campaign)
    spot_shared_mode = Column(Boolean, default=True) # True = same schedule for all selected entities
    spot_periods = Column(JSON) # Map: [Entity] -> List[Period]
    spot_schedules = Column(JSON) # Map: [Entity] -> Date -> Schedule
    
    start_date = Column(Date) # Legacy/Simple summary
    end_date = Column(Date)   # Legacy/Simple summary
    hourly_schedule = Column(String(100))  # Legacy/Simple summary
    
    is_active = Column(Boolean, default=True)
    uploaded_at = Column(DateTime, default=datetime.now)
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.now)
    last_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    campaign = relationship("Campaign", back_populates="spots")

class VehicleSchedule(Base):
    __tablename__ = 'vehicle_schedules'
    __table_args__ = {'extend_existing': True}
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    vehicle_id = Column(String(36), ForeignKey('vehicles.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    event_type = Column(String(50), nullable=False)
    origin_city = Column(String(100))
    destination_city = Column(String(100))
    details = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)
    last_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    vehicle = relationship(Vehicle, back_populates="schedules")

class DriverSchedule(Base):
    __tablename__ = 'driver_schedules'
    __table_args__ = {'extend_existing': True}
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    driver_id = Column(String(36), ForeignKey('drivers.id'), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    event_type = Column(String(50), nullable=False)
    details = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)
    last_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    driver = relationship(Driver, back_populates="schedules")

class Document(Base):
    __tablename__ = 'documents'
    __table_args__ = {'extend_existing': True}
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_type = Column(String(20), nullable=False)
    entity_id = Column(String(36), nullable=False)
    document_type = Column(String(50), nullable=False)
    custom_type_name = Column(String(100))
    issue_date = Column(Date)
    expiry_date = Column(Date)
    file_path = Column(String(500))
    file_name = Column(String(255))
    uploaded_at = Column(DateTime)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    last_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class MaintenanceRecord(Base):
    __tablename__ = 'maintenance_records'
    __table_args__ = {'extend_existing': True}
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    # 'vehicle', 'generator', 'equipment'
    entity_type = Column(String(20), nullable=False)
    # If entity_type is 'vehicle', this matches vehicle.id
    entity_id = Column(String(36), nullable=False)
    
    service_type = Column(String(100), nullable=False) # 'Revision', 'Oil Change', etc.
    current_km = Column(Integer)
    current_hours = Column(Float)
    
    expiry_date = Column(Date)
    expiry_km = Column(Integer)
    expiry_hours = Column(Float)
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    last_modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Simplified relationship only for vehicles for now
    vehicle_id = Column(String(36), ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=True)
    vehicle = relationship("Vehicle", back_populates="maintenance_records")
