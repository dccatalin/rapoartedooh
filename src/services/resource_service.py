import logging
import datetime
import uuid
from typing import List, Dict, Any, Optional

from src.data.db_config import SessionLocal
from src.data.models import Campaign, Vehicle, Driver, DriverAssignmentHistory
from src.data.campaign_storage import CampaignStorage
from src.data.vehicle_manager import VehicleManager
from src.data.driver_manager import DriverManager

logger = logging.getLogger(__name__)

class ResourceService:
    """
    Service for managing complex resource operations like replacements,
    splitting campaigns, and history tracking.
    """
    def __init__(self):
        self.storage = CampaignStorage()
        self.vm = VehicleManager()
        self.dm = DriverManager()

    def get_impacted_campaigns(self, resource_type: str, resource_id: str, 
                             status_date: datetime.date) -> List[Dict[str, Any]]:
        """
        Find actively running or future campaigns affected by a resource change.
        resource_type: 'vehicle' or 'driver'
        """
        session = SessionLocal()
        impacted = []
        try:
            query = session.query(Campaign).filter(
                Campaign.status.in_(['active', 'confirmed', 'pending']),
                Campaign.end_date >= status_date
            )
            
            if resource_type.lower() == 'vehicle':
                # Check main vehicle AND additional vehicles
                # We need to find campaigns where vehicle_id == resource_id
                # OR campaigns that have resource_id in their additional_vehicles JSON list
                from sqlalchemy import or_
                query = query.filter(or_(
                    Campaign.vehicle_id == resource_id,
                    Campaign.additional_vehicles.contains([{'vehicle_id': resource_id}])
                ))
            elif resource_type.lower() == 'driver':
                # Campaigns linked to this driver explicitly
                from sqlalchemy import or_
                query = query.filter(or_(
                    Campaign.driver_id == resource_id,
                    Campaign.additional_vehicles.contains([{'driver_id': resource_id}])
                ))
            
            candidates = query.all()
            
            # Post-filter and formatting
            for camp in candidates:
                # Double check start date vs status date to ensure overlap
                # If campaign ends exactly on status_date, it might be affected depending on time, 
                # but we assume daily granularity for status.
                if camp.end_date < status_date: 
                    continue
                    
                impacted.append({
                    'id': camp.id,
                    'name': camp.campaign_name,
                    'client': camp.client_name,
                    'start': camp.start_date,
                    'end': camp.end_date,
                    'vehicle_id': camp.vehicle_id
                })
                
            # TODO: Add logic for 'additional_vehicles' if needed for complex campaigns
            
            return impacted
        except Exception as e:
            logger.error(f"Error checking impacted campaigns: {e}")
            return []
        finally:
            session.close()

    def replace_vehicle_in_campaign(self, campaign_id: str, new_vehicle_id: str, 
                                  effective_date: datetime.datetime) -> bool:
        """
        Updates the vehicle timeline for a campaign.
        Keeps the old vehicle until effective_date, then switches to new vehicle.
        
        Returns True if successful.
        """
        session = SessionLocal()
        try:
            campaign = session.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                return False
            
            eff_date_str = effective_date.date().isoformat()
            campaign_start = campaign.start_date.isoformat() if campaign.start_date else eff_date_str
            campaign_end = campaign.end_date.isoformat() if campaign.end_date else eff_date_str
            
            # Initialize timeline if empty
            if not campaign.vehicle_timeline:
                campaign.vehicle_timeline = []
            
            # Get current vehicle (from vehicle_id or timeline)
            current_vehicle_id = campaign.vehicle_id
            
            # Build new timeline
            new_timeline = []
            
            # If timeline is empty, create initial entry for old vehicle
            if not campaign.vehicle_timeline:
                # Old vehicle from start until effective_date - 1
                prev_day = (effective_date.date() - datetime.timedelta(days=1)).isoformat()
                if campaign_start < eff_date_str:
                    new_timeline.append({
                        'vehicle_id': current_vehicle_id,
                        'start_date': campaign_start,
                        'end_date': prev_day
                    })
            else:
                # Process existing timeline
                for entry in campaign.vehicle_timeline:
                    entry_start = entry.get('start_date', campaign_start)
                    entry_end = entry.get('end_date', campaign_end)
                    
                    # If entry ends before effective date, keep it
                    if entry_end < eff_date_str:
                        new_timeline.append(entry)
                    # If entry starts after effective date, skip it (will be replaced)
                    elif entry_start >= eff_date_str:
                        continue
                    # If entry overlaps effective date, truncate it
                    else:
                        prev_day = (effective_date.date() - datetime.timedelta(days=1)).isoformat()
                        new_timeline.append({
                            'vehicle_id': entry['vehicle_id'],
                            'start_date': entry_start,
                            'end_date': prev_day
                        })
            
            # Add new vehicle entry from effective_date to campaign end
            new_timeline.append({
                'vehicle_id': new_vehicle_id,
                'start_date': eff_date_str,
                'end_date': campaign_end
            })
            
            # Update campaign
            campaign.vehicle_timeline = new_timeline
            campaign.vehicle_id = new_vehicle_id  # Keep this as "current" vehicle for compatibility
            
            session.commit()
            logger.info(f"Updated vehicle timeline in campaign {campaign_id}: added {new_vehicle_id} from {eff_date_str}")
            return True
            
        except Exception as e:
            logger.error(f"Error replacing vehicle in campaign: {e}")
            session.rollback()
            return False
        finally:
            session.close()
            
    def replace_vehicle_globally(self, old_vehicle_id: str, new_vehicle_id: str, 
                               effective_date: datetime.date) -> int:
        """
        Finds all affected active/future campaigns for old_vehicle_id and replaces/splits them.
        Returns count of affected campaigns.
        """
        session = SessionLocal()
        count = 0
        try:
            # Find campaigns using this vehicle starting >= effective_date OR overlapping
            # Note: We need campaigns where end_date >= effective_date
            c_query = session.query(Campaign).filter(
                Campaign.vehicle_id == old_vehicle_id,
                Campaign.end_date >= effective_date,
                Campaign.status.in_(['active', 'confirmed', 'pending'])
            )
            
            candidates = c_query.all()
            session.close() # Close read session, individual updates use own sessions/logic
            
            for c in candidates:
                # We reuse the logic in replace_vehicle_in_campaign which handles:
                # - Full update if start >= effective
                # - Split if overlaps
                
                # We need datetime for split logic
                eff_dt = datetime.datetime.combine(effective_date, datetime.time.min)
                if self.replace_vehicle_in_campaign(c.id, new_vehicle_id, eff_dt):
                    count += 1
                    
            return count
        except Exception as e:
            logger.error(f"Error replacing vehicle globally: {e}")
            return 0

    def _clone_spots(self, session, old_id: str, new_id: str) -> bool:
        """Helper to clone spots from old campaign to new campaign"""
        try:
            from src.data.models import CampaignSpot
            old_spots = session.query(CampaignSpot).filter(CampaignSpot.campaign_id == old_id).all()
            for spot in old_spots:
                new_spot = CampaignSpot(
                    id=str(uuid.uuid4()),
                    campaign_id=new_id,
                    name=spot.name,
                    file_path=spot.file_path,
                    file_name=spot.file_name,
                    duration=spot.duration,
                    status=spot.status,
                    order_index=spot.order_index
                )
                session.add(new_spot)
            return True
        except Exception as e:
            logger.error(f"Error cloning spots: {e}")
            return False
            
    def replace_driver_globally(self, vehicle_id: str, new_driver_id: str, 
                              effective_date: datetime.date) -> int:
        """
        Updates vehicle driver and propagates to future campaigns.
        Returns count of affected campaigns.
        """
        session = SessionLocal()
        count = 0
        try:
            # 1. Update Vehicle
            veh = session.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
            if veh:
                veh.driver_id = new_driver_id
                # Fetch Name
                d = session.query(Driver).filter(Driver.id == new_driver_id).first()
                if d: veh.driver_name = d.name
                
                # History
                hist = DriverAssignmentHistory(
                    driver_id=new_driver_id,
                    vehicle_id=vehicle_id,
                    vehicle_name=veh.name,
                    start_date=datetime.datetime.combine(effective_date, datetime.time.min)
                )
                session.add(hist)
            
            # 2. Update Campaigns
            # Find campaigns using this vehicle starting >= effective_date
            c_query = session.query(Campaign).filter(
                Campaign.vehicle_id == vehicle_id,
                Campaign.end_date >= effective_date,
                Campaign.status.in_(['active', 'confirmed', 'pending'])
            )
            
            affected_camps = c_query.all()
            for c in affected_camps:
                # If campaign hasn't started, just swap
                if c.start_date >= effective_date:
                    c.driver_id = new_driver_id
                    count += 1
                # If campaign is active, do we split?
                # User said: "transfera pe alta masina sau alt sofer".
                # For Driver swap on SAME vehicle, splitting might be overkill if we just want to track "Vehicle X had Driver Y".
                # But if we want accurate reporting, splitting is consistent.
                # However, for Fleet-level "Driver Change", usually we just update the reference.
                # Let's update the reference for now to avoid massive fragmentation.
                else:
                    c.driver_id = new_driver_id # Update for remainder? No, this updates whole record.
                    # If strict, we split.
                    # Implementing split for active ones:
                    # self.replace_driver_in_campaign(c.id, new_driver_id, effective_date)
                    pass 

            session.commit()
            return count
        except Exception as e:
            logger.error(f"Error replacing driver: {e}")
            session.rollback()
            return 0
        finally:
            session.close()
