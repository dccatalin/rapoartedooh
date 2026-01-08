# v1.1 - Added State History
import logging
import datetime
from typing import Dict, Any, Optional, List
from src.data.db_config import SessionLocal
from src.data.models import Vehicle, VehicleStatusHistory

logger = logging.getLogger(__name__)

class VehicleManager:
    """Manage vehicle data and status tracking using Database"""
    
    # Vehicle status options
    STATUS_ACTIVE = "active"
    STATUS_MAINTENANCE = "maintenance"
    STATUS_DEFECTIVE = "defective"
    STATUS_INACTIVE = "inactive"
    
    VALID_STATUSES = [STATUS_ACTIVE, STATUS_MAINTENANCE, STATUS_DEFECTIVE, STATUS_INACTIVE]
    
    def __init__(self):
        pass # No file path needed anymore
    
    def _to_dict(self, vehicle: Vehicle) -> Dict[str, Any]:
        """Convert SQLAlchemy object to dictionary for compatibility"""
        if not vehicle:
            return {}
        
        # Get status history
        history = []
        for h in vehicle.status_history:
            history.append({
                'status': h.status,
                'date': h.date.isoformat() if h.date else None,
                'note': h.note
            })
            
        return {
            'id': vehicle.id,
            'name': vehicle.name,
            'registration': vehicle.registration,
            'driver_id': vehicle.driver_id,
            'driver_name': vehicle.driver_name,
            'status': vehicle.status,
            'status_history': history,
            'created': vehicle.created_at.isoformat() if vehicle.created_at else None,
            'last_modified': vehicle.last_modified.isoformat() if vehicle.last_modified else None,
            # Documents
            'rca_expiry': vehicle.rca_expiry.isoformat() if vehicle.rca_expiry else None,
            'itp_expiry': vehicle.itp_expiry.isoformat() if vehicle.itp_expiry else None,
            'rovinieta_expiry': vehicle.rovinieta_expiry.isoformat() if vehicle.rovinieta_expiry else None,
            'casco_expiry': vehicle.casco_expiry.isoformat() if vehicle.casco_expiry else None,
            'mileage': vehicle.mileage,
            'generator_hours': vehicle.generator_hours
        }
    
    def add_vehicle(
        self, 
        name: str, 
        registration: str = "",
        status: str = STATUS_ACTIVE,
        rca_expiry: datetime.date = None,
        itp_expiry: datetime.date = None,
        rovinieta_expiry: datetime.date = None,
        casco_expiry: datetime.date = None,
        mileage: int = 0,
        generator_hours: float = 0.0
    ) -> str:
        """Add a new vehicle"""
        session = SessionLocal()
        try:
            if status not in self.VALID_STATUSES:
                status = self.STATUS_ACTIVE
            
            vehicle = Vehicle(
                name=name,
                registration=registration,
                status=status,
                rca_expiry=rca_expiry,
                itp_expiry=itp_expiry,
                rovinieta_expiry=rovinieta_expiry,
                casco_expiry=casco_expiry,
                mileage=mileage,
                generator_hours=generator_hours
            )
            session.add(vehicle)
            session.flush() # Get ID
            
            # Add initial status history
            history = VehicleStatusHistory(
                vehicle_id=vehicle.id,
                status=status,
                note='Vehicle created'
            )
            session.add(history)
            
            session.commit()
            logger.info(f"Added vehicle: {name} (ID: {vehicle.id})")
            return vehicle.id
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding vehicle: {e}")
            return ""
        finally:
            session.close()
    
    def get_vehicle(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific vehicle by ID"""
        session = SessionLocal()
        try:
            vehicle = session.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
            return self._to_dict(vehicle) if vehicle else None
        finally:
            session.close()
    
    def get_all_vehicles(self) -> List[Dict[str, Any]]:
        """Get all vehicles"""
        session = SessionLocal()
        try:
            vehicles = session.query(Vehicle).all()
            return [self._to_dict(v) for v in vehicles]
        finally:
            session.close()
    
    def get_active_vehicles(self) -> List[Dict[str, Any]]:
        """Get only active vehicles"""
        session = SessionLocal()
        try:
            vehicles = session.query(Vehicle).filter(Vehicle.status == self.STATUS_ACTIVE).all()
            return [self._to_dict(v) for v in vehicles]
        finally:
            session.close()
    
    def get_vehicles_with_drivers(self) -> List[Dict[str, Any]]:
        """Get vehicles that have assigned drivers"""
        session = SessionLocal()
        try:
            vehicles = session.query(Vehicle).filter(Vehicle.driver_id.isnot(None)).all()
            return [self._to_dict(v) for v in vehicles]
        finally:
            session.close()
    
    def update_vehicle(
        self, 
        vehicle_id: str, 
        name: Optional[str] = None,
        registration: Optional[str] = None,
        status: Optional[str] = None,
        status_note: Optional[str] = None,
        rca_expiry: Optional[datetime.date] = None,
        itp_expiry: Optional[datetime.date] = None,
        rovinieta_expiry: Optional[datetime.date] = None,
        casco_expiry: Optional[datetime.date] = None,
        status_date: Optional[datetime.datetime] = None,
        mileage: Optional[int] = None,
        generator_hours: Optional[float] = None
    ) -> bool:
        """Update vehicle information"""
        session = SessionLocal()
        try:
            vehicle = session.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
            if not vehicle:
                logger.error(f"Vehicle not found: {vehicle_id}")
                return False
            
            if name is not None:
                vehicle.name = name
            if registration is not None:
                vehicle.registration = registration
                
            # Update Documents
            if rca_expiry is not None: vehicle.rca_expiry = rca_expiry
            if itp_expiry is not None: vehicle.itp_expiry = itp_expiry
            if rovinieta_expiry is not None: vehicle.rovinieta_expiry = rovinieta_expiry
            if casco_expiry is not None: vehicle.casco_expiry = casco_expiry
            if mileage is not None: vehicle.mileage = mileage
            if generator_hours is not None: vehicle.generator_hours = generator_hours
            
            # Track status changes
            if status is not None and status in self.VALID_STATUSES:
                if status != vehicle.status:
                    # Add to status history
                    history = VehicleStatusHistory(
                        vehicle_id=vehicle.id,
                        status=status,
                        date=status_date or datetime.datetime.now(),
                        note=status_note or f'Status changed to {status}'
                    )
                    session.add(history)
                    
                    # --- SYNC WITH VehicleSchedule ---
                    from src.data.models import VehicleSchedule
                    
                    old_status = vehicle.status
                    new_status = status
                    eff_date = (status_date or datetime.datetime.now()).date()
                    
                    # Close/Delete old events if it was defective/maintenance
                    if old_status in ['defective', 'maintenance']:
                        # Find ALL unclosed or recent schedules of this type for this vehicle
                        to_delete = session.query(VehicleSchedule).filter(
                            VehicleSchedule.vehicle_id == vehicle.id,
                            VehicleSchedule.event_type == old_status
                        ).all()
                        
                        for sch in to_delete:
                            session.delete(sch)
                            logger.info(f"Deleted {old_status} schedule {sch.id} for vehicle {vehicle.registration}")
                    
                    # Open new event if it is defective/maintenance
                    if new_status in ['defective', 'maintenance']:
                        new_sch = VehicleSchedule(
                            vehicle_id=vehicle.id,
                            start_date=eff_date,
                            end_date=eff_date + datetime.timedelta(days=365), # Far future default
                            event_type=new_status,
                            details=status_note or f"Auto-created from status change to {new_status}"
                        )
                        session.add(new_sch)
                        logger.info(f"Opened {new_status} schedule for vehicle {vehicle.registration}")
                    
                    vehicle.status = status
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating vehicle: {e}")
            return False
        finally:
            session.close()
    
    def assign_driver(
        self, 
        vehicle_id: str, 
        driver_id: Optional[str],
        driver_name: Optional[str] = None
    ) -> bool:
        """Assign driver to vehicle"""
        session = SessionLocal()
        try:
            vehicle = session.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
            if not vehicle:
                logger.error(f"Vehicle not found: {vehicle_id}")
                return False
            
            vehicle.driver_id = driver_id
            vehicle.driver_name = driver_name
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error assigning driver: {e}")
            return False
        finally:
            session.close()
    
    def get_status_history(self, vehicle_id: str) -> List[Dict[str, Any]]:
        """Get status change history for a vehicle"""
        session = SessionLocal()
        try:
            vehicle = session.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
            if vehicle:
                return [
                    {
                        'id': h.id,  # Add ID for CRUD operations
                        'status': h.status,
                        'date': h.date.isoformat() if h.date else None,
                        'note': h.note
                    }
                    for h in vehicle.status_history
                ]
            return []
        finally:
            session.close()
    
    def delete_vehicle(self, vehicle_id: str, force: bool = False) -> bool:
        """Delete a vehicle"""
        session = SessionLocal()
        try:
            vehicle = session.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
            if not vehicle:
                return False
            
            if not force and vehicle.driver_id:
                logger.warning(f"Vehicle has assigned driver: {vehicle.driver_name}")
                # Allow deletion but log warning (matching previous behavior)
                
            session.delete(vehicle)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting vehicle: {e}")
            return False
        finally:
            session.close()
    
    
    def has_driver(self, vehicle_id: str) -> bool:
        """Check if vehicle has an assigned driver"""
        session = SessionLocal()
        try:
            vehicle = session.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
            return bool(vehicle and vehicle.driver_id)
        finally:
            session.close()

    # --- Schedule / Manual Event Management ---
    
    def add_schedule(
        self,
        vehicle_id: str,
        start_date: datetime.date,
        end_date: datetime.date,
        event_type: str,
        origin_city: str = None,
        destination_city: str = None,
        details: str = ""
    ) -> bool:
        """Add a manual schedule/event (maintenance, etc)"""
        session = SessionLocal()
        try:
            from src.data.models import VehicleSchedule
            
            # Simple validation
            if start_date > end_date:
                return False
                
            schedule = VehicleSchedule(
                vehicle_id=vehicle_id,
                start_date=start_date,
                end_date=end_date,
                event_type=event_type,
                origin_city=origin_city,
                destination_city=destination_city,
                details=details
            )
            session.add(schedule)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding schedule: {e}")
            return False
        finally:
            session.close()
            
    def get_vehicle_schedules(self, vehicle_id: str = None) -> List[Dict[str, Any]]:
        """Get schedules for a vehicle or all if ID is None"""
        session = SessionLocal()
        try:
            from src.data.models import VehicleSchedule
            
            query = session.query(VehicleSchedule)
            if vehicle_id:
                query = query.filter(VehicleSchedule.vehicle_id == vehicle_id)
            
            schedules = query.all()
            return [
                {
                    'id': s.id,
                    'vehicle_id': s.vehicle_id,
                    'start': s.start_date,
                    'end': s.end_date,
                    'type': s.event_type,
                    'origin': s.origin_city,
                    'destination': s.destination_city,
                    'details': s.details
                }
                for s in schedules
            ]
        finally:
            session.close()
            
    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule event"""
        session = SessionLocal()
        try:
            from src.data.models import VehicleSchedule
            session.query(VehicleSchedule).filter(VehicleSchedule.id == schedule_id).delete()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting schedule: {e}")
            return False
        finally:
            session.close()
