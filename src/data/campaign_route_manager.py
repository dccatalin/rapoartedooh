from typing import List, Dict, Any, Optional
from src.data.db_config import SessionLocal
from src.data.models import CampaignRoute
import datetime
import logging

logger = logging.getLogger(__name__)

class CampaignRouteManager:
    """Manages CRUD operations for CampaignRoute model"""
    
    def get_routes_for_campaign(self, campaign_id: str) -> List[Dict[str, Any]]:
        """Fetch all routes for a specific campaign"""
        db = SessionLocal()
        try:
            routes = db.query(CampaignRoute).filter(CampaignRoute.campaign_id == campaign_id).all()
            return [self._to_dict(r) for r in routes]
        finally:
            db.close()

    def get_route(self, route_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a specific route by ID"""
        db = SessionLocal()
        try:
            route = db.query(CampaignRoute).filter(CampaignRoute.id == route_id).first()
            return self._to_dict(route) if route else None
        finally:
            db.close()

    def add_route(self, data: Dict[str, Any]) -> Optional[str]:
        """Add a new route to a campaign or as a template"""
        db = SessionLocal()
        try:
            new_route = CampaignRoute(
                campaign_id=data.get('campaign_id'),
                name=data.get('name', 'Unnamed Route'),
                geojson_data=data.get('geojson_data'),
                waypoints=data.get('waypoints'),
                is_template=data.get('is_template', False),
                vehicle_id=data.get('vehicle_id'),
                date_start=data.get('date_start'),
                date_end=data.get('date_end'),
                time_start=data.get('time_start'),
                time_end=data.get('time_end')
            )
            db.add(new_route)
            db.commit()
            db.refresh(new_route)
            return new_route.id
        except Exception as e:
            logger.error(f"Error adding campaign route: {e}")
            db.rollback()
            return None
        finally:
            db.close()

    def update_route(self, route_id: str, data: Dict[str, Any]) -> bool:
        """Update an existing campaign route"""
        db = SessionLocal()
        try:
            route = db.query(CampaignRoute).filter(CampaignRoute.id == route_id).first()
            if not route:
                return False
            
            if 'name' in data: route.name = data['name']
            if 'geojson_data' in data: route.geojson_data = data['geojson_data']
            if 'waypoints' in data: route.waypoints = data['waypoints']
            if 'is_template' in data: route.is_template = data['is_template']
            if 'vehicle_id' in data: route.vehicle_id = data['vehicle_id']
            if 'date_start' in data: route.date_start = data['date_start']
            if 'date_end' in data: route.date_end = data['date_end']
            if 'time_start' in data: route.time_start = data['time_start']
            if 'time_end' in data: route.time_end = data['time_end']
            
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating campaign route: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def delete_route(self, route_id: str) -> bool:
        """Delete a campaign route"""
        db = SessionLocal()
        try:
            route = db.query(CampaignRoute).filter(CampaignRoute.id == route_id).first()
            if not route:
                return False
            db.delete(route)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting campaign route: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def get_route_templates(self) -> List[Dict[str, Any]]:
        """Fetch all routes marked as templates (global library)"""
        db = SessionLocal()
        try:
            routes = db.query(CampaignRoute).filter(CampaignRoute.is_template == True).all()
            return [self._to_dict(r) for r in routes]
        finally:
            db.close()

    def _to_dict(self, route: CampaignRoute) -> Dict[str, Any]:
        """Convert SQLAlchemy object to dictionary"""
        return {
            'id': route.id,
            'campaign_id': route.campaign_id,
            'name': route.name,
            'geojson_data': route.geojson_data,
            'waypoints': route.waypoints,
            'is_template': route.is_template,
            'vehicle_id': route.vehicle_id,
            'date_start': route.date_start.isoformat() if route.date_start else None,
            'date_end': route.date_end.isoformat() if route.date_end else None,
            'time_start': route.time_start,
            'time_end': route.time_end,
            'created_at': route.created_at.isoformat() if route.created_at else None,
            'last_modified': route.last_modified.isoformat() if route.last_modified else None
        }
