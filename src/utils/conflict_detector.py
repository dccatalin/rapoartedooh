"""
Conflict Detection Service
Checks for vehicle scheduling conflicts and overlaps.
"""
import datetime
from typing import List, Dict, Any, Tuple
from src.data.campaign_storage import CampaignStorage

class ConflictDetector:
    """Detects scheduling conflicts for vehicles"""
    
    def __init__(self):
        self.storage = CampaignStorage()
        
    def check_vehicle_conflicts(self, vehicle_id: str, start_date: datetime.date, 
                                end_date: datetime.date, city_periods: Dict[str, Any] = None,
                                exclude_campaign_id: str = None) -> Tuple[List[Dict], List[Dict]]:
        """
        Check for conflicts with existing campaigns for a vehicle.
        
        Args:
            vehicle_id: ID of vehicle to check
            start_date: Campaign start date
            end_date: Campaign end date
            city_periods: Optional per-city periods
            exclude_campaign_id: Campaign ID to exclude (for editing existing campaigns)
            
        Returns:
            Tuple of (blocking_conflicts, warnings)
            - blocking_conflicts: List of exclusive campaigns that block this campaign
            - warnings: List of non-exclusive campaigns that overlap
        """
        all_campaigns = self.storage.get_all_campaigns()
        
        blocking_conflicts = []
        warnings = []
        
        for campaign in all_campaigns:
            # Skip if it's the same campaign (editing case)
            if exclude_campaign_id and campaign.get('id') == exclude_campaign_id:
                continue
                
            # Skip if different vehicle
            if campaign.get('vehicle_id') != vehicle_id:
                continue
                
            # Get campaign dates
            try:
                c_start = datetime.date.fromisoformat(str(campaign['start_date']))
                c_end = datetime.date.fromisoformat(str(campaign['end_date']))
            except:
                continue
                
            # Check for date overlap
            if self._dates_overlap(start_date, end_date, c_start, c_end):
                # Check if existing campaign is exclusive
                if campaign.get('is_exclusive', False):
                    blocking_conflicts.append({
                        'campaign_id': campaign.get('id'),
                        'client_name': campaign.get('client_name'),
                        'campaign_name': campaign.get('campaign_name'),
                        'start_date': c_start,
                        'end_date': c_end,
                        'type': 'exclusive'
                    })
                else:
                    warnings.append({
                        'campaign_id': campaign.get('id'),
                        'client_name': campaign.get('client_name'),
                        'campaign_name': campaign.get('campaign_name'),
                        'start_date': c_start,
                        'end_date': c_end,
                        'type': 'non-exclusive'
                    })
                    
        # If city_periods provided, do more granular checking
        if city_periods:
            blocking_conflicts, warnings = self._check_city_level_conflicts(
                vehicle_id, city_periods, exclude_campaign_id, 
                blocking_conflicts, warnings
            )
            
        return blocking_conflicts, warnings
        
    def _dates_overlap(self, start1: datetime.date, end1: datetime.date,
                       start2: datetime.date, end2: datetime.date) -> bool:
        """Check if two date ranges overlap"""
        return start1 <= end2 and end1 >= start2
        
    def _check_city_level_conflicts(self, vehicle_id: str, city_periods: Dict[str, Any],
                                     exclude_campaign_id: str,
                                     existing_blocks: List[Dict], 
                                     existing_warnings: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Check for conflicts at city level (more granular).
        If campaigns are in different cities during overlapping dates, they don't conflict.
        """
        all_campaigns = self.storage.get_all_campaigns()
        
        blocking_conflicts = list(existing_blocks)
        warnings = list(existing_warnings)
        
        for campaign in all_campaigns:
            if exclude_campaign_id and campaign.get('id') == exclude_campaign_id:
                continue
            if campaign.get('vehicle_id') != vehicle_id:
                continue
                
            # Get existing campaign's city periods
            c_city_periods = campaign.get('city_periods', {})
            
            # If no city periods in existing campaign, use global dates
            if not c_city_periods:
                continue  # Already handled in main check
                
            # Check each city in new campaign against existing campaign cities
            for city, period in city_periods.items():
                try:
                    new_start = datetime.date.fromisoformat(str(period['start']))
                    new_end = datetime.date.fromisoformat(str(period['end']))
                except:
                    continue
                    
                for c_city, c_period in c_city_periods.items():
                    # If different cities, no conflict
                    if city != c_city:
                        continue
                        
                    try:
                        c_start = datetime.date.fromisoformat(str(c_period['start']))
                        c_end = datetime.date.fromisoformat(str(c_period['end']))
                    except:
                        continue
                        
                    # Same city, check date overlap
                    if self._dates_overlap(new_start, new_end, c_start, c_end):
                        conflict_info = {
                            'campaign_id': campaign.get('id'),
                            'client_name': campaign.get('client_name'),
                            'campaign_name': campaign.get('campaign_name'),
                            'city': city,
                            'start_date': c_start,
                            'end_date': c_end,
                            'type': 'exclusive' if campaign.get('is_exclusive') else 'non-exclusive'
                        }
                        
                        # Avoid duplicates
                        if campaign.get('is_exclusive'):
                            if not any(c['campaign_id'] == campaign.get('id') for c in blocking_conflicts):
                                blocking_conflicts.append(conflict_info)
                        else:
                            if not any(c['campaign_id'] == campaign.get('id') for c in warnings):
                                warnings.append(conflict_info)
                                
        return blocking_conflicts, warnings
        
    def format_conflict_message(self, conflicts: List[Dict], conflict_type: str = "blocking") -> str:
        """Format conflict information for display"""
        if not conflicts:
            return ""
            
        if conflict_type == "blocking":
            msg = "⛔ <b>CONFLICT DETECTED - Cannot Save!</b><br/><br/>"
            msg += "The following exclusive campaigns block this vehicle:<br/><br/>"
        else:
            msg = "⚠️ <b>Warning - Overlapping Campaigns</b><br/><br/>"
            msg += "The following campaigns overlap with this schedule:<br/><br/>"
            
        for conflict in conflicts:
            msg += f"• <b>{conflict['client_name']}</b> - {conflict['campaign_name']}<br/>"
            msg += f"  Dates: {conflict['start_date'].strftime('%d.%m.%Y')} - {conflict['end_date'].strftime('%d.%m.%Y')}<br/>"
            if 'city' in conflict:
                msg += f"  City: {conflict['city']}<br/>"
            msg += "<br/>"
            
        return msg
