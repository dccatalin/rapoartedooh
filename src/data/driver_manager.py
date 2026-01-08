# v1.1 - Added State History
import logging
import datetime
from typing import Dict, Any, Optional, List
from src.data.db_config import SessionLocal
from src.data.models import Driver, DriverAssignmentHistory, DriverStatusHistory

logger = logging.getLogger(__name__)

class DriverManager:
    """Manage driver data and vehicle assignments using Database"""
    
    def __init__(self):
        pass
    
    def _to_dict(self, driver: Driver) -> Dict[str, Any]:
        """Convert SQLAlchemy object to dictionary for compatibility"""
        if not driver:
            return {}
            
        # Get assignment history
        history = []
        for h in driver.assignment_history:
            history.append({
                'vehicle_id': h.vehicle_id,
                'vehicle_name': h.vehicle_name,
                'start_date': h.start_date.isoformat() if h.start_date else None,
                'end_date': h.end_date.isoformat() if h.end_date else None
            })
            
        # Get assigned vehicle from relationship
        assigned_vehicle_id = None
        if driver.assigned_vehicle_rel:
            assigned_vehicle_id = driver.assigned_vehicle_rel.id
        
        # Get status history
        s_history = []
        for sh in driver.status_history:
            s_history.append({
                'status': sh.status,
                'date': sh.date.isoformat() if sh.date else None,
                'note': sh.note
            })
        
        return {
            'id': driver.id,
            'name': driver.name,
            'phone': driver.phone,
            'license_number': driver.license_number,
            'status': driver.status,
            'status_history': s_history,
            'assigned_vehicle': assigned_vehicle_id,
            'assignment_history': history,
            
            'identity_card_expiry': driver.identity_card_expiry.isoformat() if driver.identity_card_expiry else None,
            'medical_exam_expiry': driver.medical_exam_expiry.isoformat() if driver.medical_exam_expiry else None,
            'psychological_exam_expiry': driver.psychological_exam_expiry.isoformat() if driver.psychological_exam_expiry else None,
            
            'created': driver.created_at.isoformat() if driver.created_at else None,
            'last_modified': driver.last_modified.isoformat() if driver.last_modified else None
        }
    
    def add_driver(
        self, 
        name: str, 
        phone: str = "", 
        license_number: str = "",
        status: str = "active"
    ) -> str:
        """Add a new driver"""
        session = SessionLocal()
        try:
            driver = Driver(
                name=name,
                phone=phone,
                license_number=license_number,
                status=status
            )
            session.add(driver)
            session.flush() # Get ID
            
            # Initial status history
            sh = DriverStatusHistory(
                driver_id=driver.id,
                status=status,
                note='Driver created'
            )
            session.add(sh)
            
            session.commit()
            logger.info(f"Added driver: {name} (ID: {driver.id})")
            return driver.id
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding driver: {e}")
            return ""
        finally:
            session.close()
    
    def get_driver(self, driver_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific driver by ID"""
        session = SessionLocal()
        try:
            driver = session.query(Driver).filter(Driver.id == driver_id).first()
            return self._to_dict(driver) if driver else None
        finally:
            session.close()
    
    def get_all_drivers(self) -> List[Dict[str, Any]]:
        """Get all drivers"""
        session = SessionLocal()
        try:
            drivers = session.query(Driver).all()
            return [self._to_dict(d) for d in drivers]
        finally:
            session.close()
    
    def get_active_drivers(self) -> List[Dict[str, Any]]:
        """Get only active drivers"""
        session = SessionLocal()
        try:
            drivers = session.query(Driver).filter(Driver.status == 'active').all()
            return [self._to_dict(d) for d in drivers]
        finally:
            session.close()
    
    def update_driver(
        self, 
        driver_id: str, 
        name: Optional[str] = None,
        phone: Optional[str] = None,
        license_number: Optional[str] = None,
        status: Optional[str] = None,
        status_note: Optional[str] = None,
        status_date: Optional[datetime.datetime] = None,
        identity_card_expiry: Optional[datetime.date] = None,
        medical_exam_expiry: Optional[datetime.date] = None,
        psychological_exam_expiry: Optional[datetime.date] = None
    ) -> bool:
        """Update driver information"""
        session = SessionLocal()
        try:
            driver = session.query(Driver).filter(Driver.id == driver_id).first()
            if not driver:
                logger.error(f"Driver not found: {driver_id}")
                return False
            
            if name is not None:
                driver.name = name
            if phone is not None:
                driver.phone = phone
            if license_number is not None:
                driver.license_number = license_number
            if identity_card_expiry is not None:
                driver.identity_card_expiry = identity_card_expiry
            if medical_exam_expiry is not None:
                driver.medical_exam_expiry = medical_exam_expiry
            if psychological_exam_expiry is not None:
                driver.psychological_exam_expiry = psychological_exam_expiry

            if status is not None:
                old_status = driver.status
                if status != old_status:
                    sh = DriverStatusHistory(
                        driver_id=driver_id,
                        status=status,
                        date=status_date or datetime.datetime.now(),
                        note=status_note or f"Status changed to {status}"
                    )
                    session.add(sh)
                    
                    # Automated Schedule Management
                    from src.data.models import DriverSchedule
                    
                    # 1. Delete future/unclosed events of the OLD status if we are moving to active
                    if status == 'active':
                        # Deleting overlapping future events of specific types (vacation, medical, inactive)
                        session.query(DriverSchedule).filter(
                            DriverSchedule.driver_id == driver_id,
                            DriverSchedule.event_type.in_(['vacation', 'medical', 'inactive'])
                        ).delete(synchronize_session=False)
                    
                    # 2. Add unclosed event for the NEW status if not active
                    if status in ['vacation', 'medical', 'inactive']:
                        event_date = (status_date or datetime.datetime.now()).date()
                        # If moving to a non-active state, create a "Driver Event"
                        schedule = DriverSchedule(
                            driver_id=driver_id,
                            start_date=event_date,
                            end_date=datetime.date(2099, 12, 31), # "Unclosed"
                            event_type=status,
                            details=status_note or f"Status change: {status}"
                        )
                        session.add(schedule)

                driver.status = status
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating driver: {e}")
            return False
        finally:
            session.close()
    
    def assign_to_vehicle(
        self, 
        driver_id: str, 
        vehicle_id: Optional[str],
        vehicle_name: Optional[str] = None
    ) -> bool:
        """
        Assign driver to vehicle and track history.
        Pass vehicle_id=None to unassign.
        """
        session = SessionLocal()
        try:
            driver = session.query(Driver).filter(Driver.id == driver_id).first()
            if not driver:
                logger.error(f"Driver not found: {driver_id}")
                return False
            
            # If unassigning
            if vehicle_id is None and driver.assigned_vehicle_id:
                # Close last assignment
                last_assignment = session.query(DriverAssignmentHistory).filter(
                    DriverAssignmentHistory.driver_id == driver_id,
                    DriverAssignmentHistory.end_date.is_(None)
                ).order_by(DriverAssignmentHistory.start_date.desc()).first()
                
                if last_assignment:
                    last_assignment.end_date = datetime.datetime.now()
                
                driver.assigned_vehicle_id = None
            
            # If assigning to new vehicle
            elif vehicle_id:
                # Close previous assignment if exists
                if driver.assigned_vehicle_id:
                    last_assignment = session.query(DriverAssignmentHistory).filter(
                        DriverAssignmentHistory.driver_id == driver_id,
                        DriverAssignmentHistory.end_date.is_(None)
                    ).order_by(DriverAssignmentHistory.start_date.desc()).first()
                    
                    if last_assignment:
                        last_assignment.end_date = datetime.datetime.now()
                
                # Add new assignment to history
                assignment = DriverAssignmentHistory(
                    driver_id=driver_id,
                    vehicle_id=vehicle_id,
                    vehicle_name=vehicle_name or vehicle_id,
                    start_date=datetime.datetime.now()
                )
                session.add(assignment)
                driver.assigned_vehicle_id = vehicle_id
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error assigning driver: {e}")
            return False
        finally:
            session.close()
    
    def get_status_history(self, driver_id: str) -> List[Dict[str, Any]]:
        """Get status change history for a driver"""
        session = SessionLocal()
        try:
            driver = session.query(Driver).filter(Driver.id == driver_id).first()
            if driver:
                return [
                    {
                        'id': h.id,  # Add ID for CRUD operations
                        'status': h.status,
                        'date': h.date.isoformat() if h.date else None,
                        'note': h.note
                    }
                    for h in driver.status_history
                ]
            return []
        finally:
            session.close()

    def get_driver_history(self, driver_id: str) -> List[Dict[str, Any]]:
        """Get assignment history for a driver"""
        session = SessionLocal()
        try:
            driver = session.query(Driver).filter(Driver.id == driver_id).first()
            if driver:
                # Sort by start date desc
                hists = session.query(DriverAssignmentHistory).filter(
                    DriverAssignmentHistory.driver_id == driver_id
                ).order_by(DriverAssignmentHistory.start_date.desc()).all()
                
                return [
                    {
                        'id': h.id,
                        'vehicle_id': h.vehicle_id,
                        'vehicle_name': h.vehicle_name,
                        'start_date': h.start_date.isoformat() if h.start_date else None,
                        'end_date': h.end_date.isoformat() if h.end_date else None
                    }
                    for h in hists
                ]
            return []
        finally:
            session.close()

    def add_assignment_history(self, driver_id: str, vehicle_id: str, vehicle_name: str, 
                               start_date: datetime.datetime, end_date: Optional[datetime.datetime] = None) -> bool:
        """Manually add an assignment history record"""
        session = SessionLocal()
        try:
            assignment = DriverAssignmentHistory(
                driver_id=driver_id,
                vehicle_id=vehicle_id,
                vehicle_name=vehicle_name,
                start_date=start_date,
                end_date=end_date
            )
            session.add(assignment)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding assignment history: {e}")
            return False
        finally:
            session.close()

    def update_assignment_history(self, history_id: int, vehicle_id: Optional[str] = None, 
                                  vehicle_name: Optional[str] = None,
                                  start_date: Optional[datetime.datetime] = None, 
                                  end_date: Optional[datetime.datetime] = None) -> bool:
        """Update an existing assignment history record"""
        session = SessionLocal()
        try:
            h = session.query(DriverAssignmentHistory).filter(DriverAssignmentHistory.id == history_id).first()
            if h:
                if vehicle_id is not None: h.vehicle_id = vehicle_id
                if vehicle_name is not None: h.vehicle_name = vehicle_name
                if start_date is not None: h.start_date = start_date
                if end_date is not None: h.end_date = end_date
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating assignment history: {e}")
            return False
        finally:
            session.close()

    def delete_assignment_history(self, history_id: int) -> bool:
        """Delete an assignment history record"""
        session = SessionLocal()
        try:
            session.query(DriverAssignmentHistory).filter(DriverAssignmentHistory.id == history_id).delete()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting assignment history: {e}")
            return False
        finally:
            session.close()
    
    def delete_driver(self, driver_id: str) -> bool:
        """Delete a driver (only if not assigned to vehicle)"""
        session = SessionLocal()
        try:
            driver = session.query(Driver).filter(Driver.id == driver_id).first()
            if not driver:
                return False
            
            if driver.assigned_vehicle_id:
                logger.error(f"Cannot delete driver: assigned to vehicle {driver.assigned_vehicle_id}")
                return False
            
            session.delete(driver)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting driver: {e}")
            return False
        finally:
            session.close()
    
    def get_unassigned_drivers(self) -> List[Dict[str, Any]]:
        """Get drivers not assigned to any vehicle"""
        session = SessionLocal()
        try:
            drivers = session.query(Driver).filter(
                Driver.status == 'active',
                Driver.assigned_vehicle_id.is_(None)
            ).all()
            return [self._to_dict(d) for d in drivers]
        finally:
            session.close()

    # --- Driver Schedule / Events ---

    def add_driver_schedule(
        self,
        driver_id: str,
        start_date: datetime.date,
        end_date: datetime.date,
        event_type: str,
        details: str = ""
    ) -> bool:
        """Add a manual schedule/event (vacation, medical, etc)"""
        session = SessionLocal()
        try:
            from src.data.models import DriverSchedule
            
            if start_date > end_date:
                return False
                
            schedule = DriverSchedule(
                driver_id=driver_id,
                start_date=start_date,
                end_date=end_date,
                event_type=event_type,
                details=details
            )
            session.add(schedule)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding driver schedule: {e}")
            return False
        finally:
            session.close()

    def get_driver_schedules(self, driver_id: str) -> List[Dict[str, Any]]:
        """Get schedules for a driver"""
        session = SessionLocal()
        try:
            from src.data.models import DriverSchedule
            
            schedules = session.query(DriverSchedule).filter(
                DriverSchedule.driver_id == driver_id
            ).order_by(DriverSchedule.start_date.desc()).all()
            
            return [
                {
                    'id': s.id,
                    'driver_id': s.driver_id,
                    'start_date': s.start_date.isoformat() if s.start_date else None,
                    'end_date': s.end_date.isoformat() if s.end_date else None,
                    'event_type': s.event_type,
                    'details': s.details
                }
                for s in schedules
            ]
        finally:
            session.close()
            
    def delete_driver_schedule(self, schedule_id: str) -> bool:
        """Delete a driver schedule event"""
        session = SessionLocal()
        try:
            from src.data.models import DriverSchedule
            session.query(DriverSchedule).filter(DriverSchedule.id == schedule_id).delete()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting driver schedule: {e}")
            return False
        finally:
            session.close()
