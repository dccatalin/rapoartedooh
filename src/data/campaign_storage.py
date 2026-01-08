import json
import os
import datetime
import uuid
import csv
import logging
import shutil
from typing import Dict, Any, Optional, List

from src.data.db_config import SessionLocal
from src.data.models import Campaign, Driver, CampaignSpot

logger = logging.getLogger(__name__)

class CampaignStorage:
    """
    Manages storage and retrieval of campaign data using Database.
    """
    def __init__(self) -> None:
        pass

    def _to_dict(self, campaign: Campaign) -> Dict[str, Any]:
        """Convert SQLAlchemy object to dictionary for compatibility"""
        from src.data.vehicle_manager import VehicleManager
        if not campaign:
            return {}
            
        # Hydrate vehicle/driver info
        vehicle_name = "N/A"
        driver_name = "N/A"
        
        if campaign.vehicle_id:
            vm = VehicleManager()
            vehicle = vm.get_vehicle(campaign.vehicle_id)
            if vehicle:
                vehicle_name = vehicle.get('name', 'N/A')
                # Hydrate driver name if vehicle has one
                if vehicle.get('driver_name'):
                    driver_name = vehicle.get('driver_name')
                elif campaign.driver_id or vehicle.get('driver_id'):
                    # If vehicle missing name but has ID, or we have campaign ID, try to fetch driver
                    d_id = campaign.driver_id or vehicle.get('driver_id')
                    try:
                        session = SessionLocal()
                        driver_obj = session.query(Driver).filter(Driver.id == d_id).first()
                        if driver_obj:
                            driver_name = driver_obj.name
                    except Exception:
                        pass # Keep as N/A
                    finally:
                        session.close()

        # Hydrate additional vehicles
        additional_vehicles = campaign.additional_vehicles or []
        hydrated_additional = []
        if additional_vehicles:
            try:
                vm = VehicleManager()
                # We need a session for driver lookup if needed
                session = SessionLocal()
                
                for veh_data in additional_vehicles:
                    v_item = veh_data.copy()
                    v_id = v_item.get('vehicle_id')
                    d_id = v_item.get('driver_id')
                    
                    if v_id:
                        veh_obj = vm.get_vehicle(v_id)
                        if veh_obj:
                            v_item['vehicle_name'] = veh_obj.get('name', 'N/A')
                            v_item['vehicle_registration'] = veh_obj.get('registration', '')
                            # If driver not explicitly set in list item, use vehicle's current driver
                            if not d_id and veh_obj.get('driver_id'):
                                v_item['driver_id'] = veh_obj.get('driver_id')
                                v_item['driver_name'] = veh_obj.get('driver_name')
                    
                    # Resolve driver name if we have ID but no name (or overridden)
                    current_d_id = v_item.get('driver_id')
                    if current_d_id and not v_item.get('driver_name'):
                        try:
                            driver_obj = session.query(Driver).filter(Driver.id == current_d_id).first()
                            if driver_obj:
                                v_item['driver_name'] = driver_obj.name
                        except:
                            pass
                            
                    hydrated_additional.append(v_item)
                
            except Exception as e:
                logger.error(f"Error hydrating additional vehicles: {e}")
                hydrated_additional = additional_vehicles # Fallback
            finally:
                if 'session' in locals():
                    session.close()
        
        return {
            'id': campaign.id,
            'campaign_name': campaign.campaign_name,
            'client_name': campaign.client_name,
            'start_date': campaign.start_date.isoformat() if campaign.start_date else None,
            'end_date': campaign.end_date.isoformat() if campaign.end_date else None,
            'vehicle_id': campaign.vehicle_id,
            'vehicle_name': vehicle_name,
            'driver_id': campaign.driver_id,
            'driver_name': driver_name, # Hydrated content
            'additional_vehicles': hydrated_additional,
            'status': campaign.status,
            'total_impressions': campaign.total_impressions,
            'unique_reach': campaign.unique_reach,
            
            # New fields
            'cities': campaign.cities or [],
            'spot_duration': campaign.spot_duration,
            'is_exclusive': campaign.is_exclusive,
            'campaign_mode': campaign.campaign_mode, # Added field
            'po_number': campaign.po_number,
            'daily_hours': campaign.daily_hours,
            'known_distance_total': campaign.known_distance_total,
            'route_data': campaign.route_data or {},
            'city_schedules': campaign.city_schedules or {},
            'city_periods': campaign.city_periods or {},
            'transit_periods': campaign.transit_periods or [],
            
            # Vehicle Performance
            'vehicle_speed_kmh': campaign.vehicle_speed_kmh,
            'stationing_min_per_hour': campaign.stationing_min_per_hour,
            
            # Spot Management
            'has_spots': campaign.has_spots,
            'spot_count': campaign.spot_count,
            
            'hourly_data': campaign.hourly_data or {},
            'demographics': campaign.demographics or {},
            'locations': campaign.locations or {},
            'created_at': campaign.created_at.isoformat() if campaign.created_at else None,
            'last_modified': campaign.last_modified.isoformat() if campaign.last_modified else None
        }

    def save_campaign(self, campaign_data: Dict[str, Any], campaign_id: Optional[str] = None) -> str:
        """
        Save a campaign.
        If campaign_id is provided, updates existing.
        Otherwise creates new ID.
        Returns the campaign ID.
        """
        session = SessionLocal()
        try:
            if campaign_id:
                campaign = session.query(Campaign).filter(Campaign.id == campaign_id).first()
                if not campaign:
                    # If ID provided but not found, create new with that ID (rare case)
                    campaign = Campaign(id=campaign_id)
                    session.add(campaign)
            else:
                campaign = Campaign()
                session.add(campaign)
            
            # Update fields
            campaign.campaign_name = campaign_data.get('campaign_name')
            campaign.client_name = campaign_data.get('client_name')
            
            # Handle dates
            start = campaign_data.get('start_date')
            if isinstance(start, str):
                try:
                    campaign.start_date = datetime.date.fromisoformat(start)
                except ValueError:
                    pass
            elif isinstance(start, (datetime.date, datetime.datetime)):
                campaign.start_date = start
                
            end = campaign_data.get('end_date')
            if isinstance(end, str):
                try:
                    campaign.end_date = datetime.date.fromisoformat(end)
                except ValueError:
                    pass
            elif isinstance(end, (datetime.date, datetime.datetime)):
                campaign.end_date = end

            campaign.vehicle_id = campaign_data.get('vehicle_id')
            campaign.driver_id = campaign_data.get('driver_id')
            campaign.status = campaign_data.get('status')
            campaign.total_impressions = campaign_data.get('total_impressions', 0)
            campaign.unique_reach = campaign_data.get('unique_reach', 0)
            
            # New fields
            campaign.cities = campaign_data.get('cities', [])
            campaign.spot_duration = campaign_data.get('spot_duration')
            campaign.is_exclusive = campaign_data.get('is_exclusive', False)
            campaign.campaign_mode = campaign_data.get('campaign_mode') # Added field
            campaign.po_number = campaign_data.get('po_number')
            campaign.daily_hours = campaign_data.get('daily_hours')
            campaign.known_distance_total = campaign_data.get('known_distance_total', 0)
            campaign.route_data = campaign_data.get('route_data', {})
            campaign.city_schedules = campaign_data.get('city_schedules', {})
            campaign.city_periods = campaign_data.get('city_periods', {})
            campaign.transit_periods = campaign_data.get('transit_periods', [])
            campaign.additional_vehicles = campaign_data.get('additional_vehicles', [])
            
            # Vehicle Performance
            campaign.vehicle_speed_kmh = campaign_data.get('vehicle_speed_kmh', 25)
            campaign.stationing_min_per_hour = campaign_data.get('stationing_min_per_hour', 15)
            
            # Spot Management
            campaign.has_spots = campaign_data.get('has_spots', False)
            campaign.spot_count = campaign_data.get('spot_count', 0)
            
            # JSON fields
            campaign.hourly_data = campaign_data.get('hourly_data', {})
            campaign.demographics = campaign_data.get('demographics', {})
            campaign.locations = campaign_data.get('locations', {})
            
            session.commit()
            return campaign.id
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving campaign: {e}")
            return ""
        finally:
            session.close()
        
    def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific campaign by ID"""
        session = SessionLocal()
        try:
            campaign = session.query(Campaign).filter(Campaign.id == campaign_id).first()
            return self._to_dict(campaign) if campaign else None
        finally:
            session.close()
        
    def get_all_campaigns(self) -> List[Dict[str, Any]]:
        """Get all campaigns, sorted by last modified (newest first)"""
        session = SessionLocal()
        try:
            campaigns = session.query(Campaign).order_by(Campaign.last_modified.desc()).all()
            return [self._to_dict(c) for c in campaigns]
        finally:
            session.close()
        
    def delete_campaign(self, campaign_id: str) -> bool:
        """Delete a campaign and all associated spots"""
        session = SessionLocal()
        try:
            campaign = session.query(Campaign).filter(Campaign.id == campaign_id).first()
            if not campaign:
                logger.warning(f"Campaign {campaign_id} not found for deletion")
                return False
            
            # Log campaign details before deletion
            campaign_name = campaign.campaign_name
            logger.info(f"Attempting to delete campaign: {campaign_name} (ID: {campaign_id})")
            
            # Check for associated spots (for logging purposes)
            from src.data.models import CampaignSpot
            spots = session.query(CampaignSpot).filter(CampaignSpot.campaign_id == campaign_id).all()
            if spots:
                logger.info(f"Campaign has {len(spots)} associated spots that will be deleted via CASCADE")
            
            # Delete campaign (CASCADE will handle spots)
            session.delete(campaign)
            session.commit()
            
            logger.info(f"✅ Successfully deleted campaign: {campaign_name} (ID: {campaign_id})")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error deleting campaign {campaign_id}: {type(e).__name__}: {str(e)}")
            logger.exception("Full traceback:")
            return False
        finally:
            session.close()
    
    def export_to_json(self, campaign_id: str, output_path: str) -> bool:
        """Export campaign to JSON file"""
        try:
            campaign = self.get_campaign(campaign_id)
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found")
                return False
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(campaign, f, indent=4, ensure_ascii=False, default=str)
            
            logger.info(f"Exported campaign {campaign_id} to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting campaign to JSON: {e}")
            return False
    
    def export_to_csv(self, campaign_id: str, output_path: str) -> bool:
        """Export campaign to CSV file"""
        try:
            campaign = self.get_campaign(campaign_id)
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found")
                return False
            
            # Flatten nested data for CSV
            flat_data = {}
            for key, value in campaign.items():
                if isinstance(value, (list, dict)):
                    flat_data[key] = json.dumps(value, default=str)
                else:
                    flat_data[key] = str(value)
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=flat_data.keys())
                writer.writeheader()
                writer.writerow(flat_data)
            
            logger.info(f"Exported campaign {campaign_id} to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting campaign to CSV: {e}")
            return False
    
    def import_from_json(self, input_path: str) -> Optional[str]:
        """Import campaign from JSON file"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                campaign_data = json.load(f)
            
            # Remove old ID and create new one
            if 'id' in campaign_data:
                del campaign_data['id']
            
            # Save as new campaign
            new_id = self.save_campaign(campaign_data)
            logger.info(f"Imported campaign from {input_path} with ID {new_id}")
            return new_id
            
        except Exception as e:
            logger.error(f"Error importing campaign from JSON: {e}")
            return None
    
    def import_from_csv(self, input_path: str) -> Optional[str]:
        """Import campaign from CSV file"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                row = next(reader)
            
            # Parse JSON fields back
            campaign_data = {}
            for key, value in row.items():
                try:
                    # Try to parse as JSON
                    campaign_data[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    campaign_data[key] = value
            
            # Remove old ID
            if 'id' in campaign_data:
                del campaign_data['id']
            
            # Save as new campaign
            new_id = self.save_campaign(campaign_data)
            logger.info(f"Imported campaign from {input_path} with ID {new_id}")
            return new_id
            
        except Exception as e:
            logger.error(f"Error importing campaign from CSV: {e}")
            return None
    
    def clone_campaign(self, campaign_id: str) -> Optional[str]:
        """Clone an existing campaign with a new ID"""
        try:
            campaign = self.get_campaign(campaign_id)
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found")
                return None
            
            # Create copy
            cloned = campaign.copy()
            
            # Remove ID and modify name
            if 'id' in cloned:
                del cloned['id']
            
            # Append "(Copy)" to campaign name
            if 'campaign_name' in cloned:
                cloned['campaign_name'] = f"{cloned['campaign_name']} (Copy)"
            
            # Save as new campaign
            new_id = self.save_campaign(cloned)
            logger.info(f"Cloned campaign {campaign_id} to {new_id}")
            return new_id
            
        except Exception as e:
            logger.error(f"Error cloning campaign: {e}")
            return None

    # --- Spot Management ---
    
    def get_campaign_spots(self, campaign_id: str, include_archived: bool = True) -> List[Dict[str, Any]]:
        """Get all spots for a campaign, sorted by order_index"""
        session = SessionLocal()
        try:
            query = session.query(CampaignSpot).filter(CampaignSpot.campaign_id == campaign_id)
            if not include_archived:
                query = query.filter(CampaignSpot.is_active == True)
            
            # Sort by order_index (primary) then uploaded_at
            # Helper to safely decode JSON
            def safe_json_load(data):
                if not data: return None
                if isinstance(data, list) or isinstance(data, dict): return data
                try:
                    import json
                    return json.loads(data)
                except:
                    return None
            
            spots = query.order_by(CampaignSpot.order_index.asc(), CampaignSpot.uploaded_at.desc()).all()

            return [{
                'id': s.id,
                'campaign_id': s.campaign_id,
                'name': s.name,
                'file_path': s.file_path,
                'file_name': s.file_name,
                'duration': s.duration,
                'status': s.status if hasattr(s, 'status') else 'OK',
                'order_index': s.order_index if hasattr(s, 'order_index') else 0,
                'target_cities': safe_json_load(s.target_cities) if hasattr(s, 'target_cities') else None,
                'target_vehicles': safe_json_load(s.target_vehicles) if hasattr(s, 'target_vehicles') else None,
                'spot_periods': safe_json_load(s.spot_periods) if hasattr(s, 'spot_periods') else {},
                'spot_schedules': safe_json_load(s.spot_schedules) if hasattr(s, 'spot_schedules') else {},
                'spot_shared_mode': s.spot_shared_mode if hasattr(s, 'spot_shared_mode') else True,
                
                'start_date': s.start_date.isoformat() if (hasattr(s, 'start_date') and s.start_date) else None,
                'end_date': s.end_date.isoformat() if (hasattr(s, 'end_date') and s.end_date) else None,
                'hourly_schedule': s.hourly_schedule if hasattr(s, 'hourly_schedule') else None,
                'is_active': s.is_active,
                'uploaded_at': s.uploaded_at.isoformat() if s.uploaded_at else None,
                'notes': s.notes
            } for s in spots]
        finally:
            session.close()

    def save_spot(self, spot_data: Dict[str, Any], temp_file_path: Optional[str] = None) -> Optional[str]:
        """Save a spot and its file. Handles both create and update."""
        session = SessionLocal()
        try:
            from sqlalchemy import func
            spot_id = spot_data.get('id')
            if spot_id:
                spot = session.query(CampaignSpot).filter(CampaignSpot.id == spot_id).first()
            else:
                spot = CampaignSpot(campaign_id=spot_data['campaign_id'])
                # Set order_index for new spots
                max_idx = session.query(func.max(CampaignSpot.order_index)).filter(CampaignSpot.campaign_id == spot_data['campaign_id']).scalar() or 0
                spot.order_index = max_idx + 1
                session.add(spot)
            
            spot.name = spot_data.get('name', spot.name if spot_id else 'Unnamed Spot')
            spot.duration = spot_data.get('duration', spot.duration if spot_id else 10)
            spot.is_active = spot_data.get('is_active', spot.is_active if spot_id else True)
            spot.notes = spot_data.get('notes', spot.notes if spot_id else '')
            spot.status = spot_data.get('status', spot.status if spot_id else 'OK')
            
            # Debug incoming data
            print(f"DEBUG: save_spot received: {spot_data}")
            
            # Targeting fields
            target_cities = spot_data.get('target_cities', spot.target_cities if spot_id else None)
            # Ensure list if it's not None
            if target_cities is not None and not isinstance(target_cities, list):
                # If it's a string, try to decode? Or it might be already encoded json string?
                # For safety, let's treat it as is, but SQLAlchemy JSON column expects python object (list/dict)
                pass
            
            spot.target_cities = target_cities
            
            # Complex Scheduling
            spot.target_vehicles = spot_data.get('target_vehicles', spot.target_vehicles if spot_id else None)
            spot.spot_periods = spot_data.get('spot_periods', spot.spot_periods if spot_id else {})
            spot.spot_schedules = spot_data.get('spot_schedules', spot.spot_schedules if spot_id else {})
            spot.spot_shared_mode = spot_data.get('spot_shared_mode', spot.spot_shared_mode if spot_id else True)
            
            spot.hourly_schedule = spot_data.get('hourly_schedule', spot.hourly_schedule if spot_id else None)
            
            # Date fields - handle both string and date objects
            if 'start_date' in spot_data:
                sd = spot_data['start_date']
                if isinstance(sd, str) and sd:
                    spot.start_date = datetime.datetime.fromisoformat(sd).date()
                elif sd:
                    spot.start_date = sd
            
            if 'end_date' in spot_data:
                ed = spot_data['end_date']
                if isinstance(ed, str) and ed:
                    spot.end_date = datetime.datetime.fromisoformat(ed).date()
                elif ed:
                    spot.end_date = ed
            
            if temp_file_path and os.path.exists(temp_file_path):
                # Handle file storage: data/spots/<campaign_id>/<filename>
                spots_base = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'spots')
                campaign_dir = os.path.join(spots_base, spot.campaign_id)
                os.makedirs(campaign_dir, exist_ok=True)
                
                # Cleanup old file if exists and path changed
                if spot.file_path and os.path.exists(spot.file_path):
                    try: os.remove(spot.file_path)
                    except: pass
                
                file_name = os.path.basename(temp_file_path)
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                save_name = f"{timestamp}_{file_name}"
                dest_path = os.path.join(campaign_dir, save_name)
                
                shutil.copy2(temp_file_path, dest_path)
                
                spot.file_path = dest_path
                spot.file_name = file_name
                spot.uploaded_at = datetime.datetime.now()
            
            session.commit()
            return spot.id
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving spot: {e}")
            return None
        finally:
            session.close()

    def reorder_spots(self, campaign_id: str, spot_id: str, direction: str) -> bool:
        """Move a spot up or down in the list"""
        session = SessionLocal()
        try:
            spots = session.query(CampaignSpot).filter(CampaignSpot.campaign_id == campaign_id).order_by(CampaignSpot.order_index.asc()).all()
            
            idx = -1
            for i, s in enumerate(spots):
                if s.id == spot_id:
                    idx = i
                    break
            
            if idx == -1: return False
            
            target_idx = -1
            if direction == 'up' and idx > 0:
                target_idx = idx - 1
            elif direction == 'down' and idx < len(spots) - 1:
                target_idx = idx + 1
            
            if target_idx != -1:
                # Swap order_index
                curr_spot = spots[idx]
                target_spot = spots[target_idx]
                
                curr_order = curr_spot.order_index
                curr_spot.order_index = target_spot.order_index
                target_spot.order_index = curr_order
                
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error reordering spots: {e}")
            return False
        finally:
            session.close()

    def delete_spot(self, spot_id: str) -> bool:
        """Delete a spot and its file"""
        session = SessionLocal()
        try:
            spot = session.query(CampaignSpot).filter(CampaignSpot.id == spot_id).first()
            if spot:
                if spot.file_path and os.path.exists(spot.file_path):
                    try: os.remove(spot.file_path)
                    except: pass
                session.delete(spot)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting spot: {e}")
            return False
        finally:
            session.close()

    def toggle_spot_active(self, spot_id: str, is_active: bool) -> bool:
        """Archive or reactivate a spot"""
        session = SessionLocal()
        try:
            spot = session.query(CampaignSpot).filter(CampaignSpot.id == spot_id).first()
            if spot:
                spot.is_active = is_active
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error toggling spot status: {e}")
            return False
        finally:
            session.close()
