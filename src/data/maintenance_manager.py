import logging
import datetime
from typing import Dict, Any, Optional, List
from src.data.db_config import SessionLocal
from src.data.models import MaintenanceRecord, Vehicle

logger = logging.getLogger(__name__)

class MaintenanceManager:
    """Manages maintenance records for vehicles and equipment"""
    
    def add_record(self, entity_type: str, entity_id: str, service_type: str,
                  current_km: Optional[int] = None, current_hours: Optional[float] = None,
                  expiry_date: Optional[datetime.date] = None, 
                  expiry_km: Optional[int] = None, 
                  expiry_hours: Optional[float] = None,
                  notes: Optional[str] = None) -> Optional[str]:
        """Add a new maintenance record"""
        session = SessionLocal()
        try:
            record = MaintenanceRecord(
                entity_type=entity_type,
                entity_id=entity_id,
                service_type=service_type,
                current_km=current_km,
                current_hours=current_hours,
                expiry_date=expiry_date,
                expiry_km=expiry_km,
                expiry_hours=expiry_hours,
                notes=notes
            )
            
            # If it's a vehicle, link it for relationship convenience
            if entity_type == 'vehicle':
                record.vehicle_id = entity_id
                
                # Proactively update vehicle stats if provided
                vehicle = session.query(Vehicle).filter(Vehicle.id == entity_id).first()
                if vehicle:
                    if current_km is not None and (vehicle.mileage or 0) < current_km:
                        vehicle.mileage = current_km
                    if current_hours is not None and (vehicle.generator_hours or 0.0) < current_hours:
                        vehicle.generator_hours = current_hours
            
            session.add(record)
            session.commit()
            return record.id
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding maintenance record: {e}")
            return None
        finally:
            session.close()

    def get_records(self, entity_type: str, entity_id: str) -> List[Dict[str, Any]]:
        """Get maintenance history for an entity"""
        session = SessionLocal()
        try:
            records = session.query(MaintenanceRecord).filter(
                MaintenanceRecord.entity_type == entity_type,
                MaintenanceRecord.entity_id == entity_id
            ).order_by(MaintenanceRecord.created_at.desc()).all()
            
            return [self._to_dict(r) for r in records]
        finally:
            session.close()

    def _to_dict(self, record: MaintenanceRecord) -> Dict[str, Any]:
        return {
            'id': record.id,
            'entity_type': record.entity_type,
            'entity_id': record.entity_id,
            'service_type': record.service_type,
            'current_km': record.current_km,
            'current_hours': record.current_hours,
            'expiry_date': record.expiry_date.isoformat() if record.expiry_date else None,
            'expiry_km': record.expiry_km,
            'expiry_hours': record.expiry_hours,
            'notes': record.notes,
            'created_at': record.created_at.isoformat() if record.created_at else None
        }
