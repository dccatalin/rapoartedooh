import datetime
from typing import List, Dict, Any
from src.data.db_config import SessionLocal
from src.data.models import Vehicle, Driver, Campaign, Document, DriverSchedule, VehicleSchedule
from src.data.company_settings import CompanySettings
from src.services.email_service import EmailService

class NotificationManager:
    """
    Scans the system for various issues and generates notifications.
    Supports app-side display and email alerts.
    """
    def __init__(self):
        self.cs = CompanySettings()
        self.email_service = EmailService()
        
    def get_all_notifications(self) -> List[Dict[str, Any]]:
        """
        Aggregate all system notifications based on current state.
        Returns a list of dicts: {id, type, severity, message, details, category}
        """
        notifications = []
        session = SessionLocal()
        try:
            settings = self.cs.get_settings()
            expiry_threshold = int(settings.get('notification_expiry_days', 7))
            
            # 1. Check Vehicle Expiries (Fixed Fields)
            notifications.extend(self._check_vehicle_fixed_expiries(session, expiry_threshold))
            
            # 2. Check Other Documents (Document Table)
            notifications.extend(self._check_all_documents(session, expiry_threshold))
            
            # 3. Check Campaign Issues
            notifications.extend(self._check_campaign_gaps(session))
            
            # 4. Check Status Impacts (Defects, Driver Leave)
            notifications.extend(self._check_status_conflicts(session))
            
            return notifications
        finally:
            session.close()

    def _check_vehicle_fixed_expiries(self, session, threshold) -> List[Dict]:
        alerts = []
        vehicles = session.query(Vehicle).filter(Vehicle.status != 'inactive').all()
        today = datetime.date.today()
        future_limit = today + datetime.timedelta(days=threshold)
        
        for v in vehicles:
            expiries = {
                'RCA': v.rca_expiry,
                'ITP': v.itp_expiry,
                'Rovinieta': v.rovinieta_expiry,
                'CASCO': v.casco_expiry
            }
            for name, date in expiries.items():
                if not date:
                    continue
                if date < today:
                    alerts.append({
                        'id': f"veh_exp_{v.id}_{name}",
                        'type': 'EXPIRARE',
                        'severity': 'error',
                        'category': 'Fleet',
                        'message': f"{name} EXPIRAT pentru {v.registration} ({v.name})",
                        'details': f"Documentul a expirat la data de {date.strftime('%d.%m.%Y')}.",
                        'entity_id': v.id,
                        'entity_type': 'vehicle'
                    })
                elif date <= future_limit:
                    alerts.append({
                        'id': f"veh_exp_{v.id}_{name}",
                        'type': 'EXPIRARE CURÂND',
                        'severity': 'warning',
                        'category': 'Fleet',
                        'message': f"{name} expiră în curând pentru {v.registration}",
                        'details': f"Documentul va expira la data de {date.strftime('%d.%m.%Y')} (în {(date-today).days} zile).",
                        'entity_id': v.id,
                        'entity_type': 'vehicle'
                    })
        return alerts

    def _check_all_documents(self, session, threshold) -> List[Dict]:
        alerts = []
        today = datetime.date.today()
        future_limit = today + datetime.timedelta(days=threshold)
        
        docs = session.query(Document).filter(Document.expiry_date != None).all()
        for d in docs:
            date = d.expiry_date
            
            # Resolve entity name for better readability
            entity_label = "Necunoscut"
            if d.entity_type == 'vehicle':
                v = session.query(Vehicle).filter(Vehicle.id == d.entity_id).first()
                entity_label = f"{v.registration} ({v.name})" if v else f"Vehicul {d.entity_id[:8]}"
            elif d.entity_type == 'driver':
                dr = session.query(Driver).filter(Driver.id == d.entity_id).first()
                entity_label = f"{dr.name}" if dr else f"Șofer {d.entity_id[:8]}"

            if date < today:
                alerts.append({
                    'id': f"doc_exp_{d.id}",
                    'type': 'EXPIRARE',
                    'severity': 'error',
                    'category': 'Documents',
                    'message': f"{d.document_type} EXPIRAT: {entity_label}",
                    'details': f"Documentul a expirat la data de {date.strftime('%d.%m.%Y')}.",
                    'entity_id': d.entity_id,
                    'entity_type': d.entity_type
                })
            elif date <= future_limit:
                alerts.append({
                    'id': f"doc_exp_{d.id}",
                    'type': 'EXPIRARE CURÂND',
                    'severity': 'warning',
                    'category': 'Documents',
                    'message': f"{d.document_type} expiră în curând: {entity_label}",
                    'details': f"Documentul va expira la data de {date.strftime('%d.%m.%Y')}.",
                    'entity_id': d.entity_id,
                    'entity_type': d.entity_type
                })
        return alerts

    def _check_campaign_gaps(self, session) -> List[Dict]:
        alerts = []
        # Only active campaigns
        today = datetime.date.today()
        campaigns = session.query(Campaign).filter(Campaign.end_date >= today, Campaign.status != 'cancelled').all()
        
        for c in campaigns:
            # Check Vehicle - Include future ones
            if not c.vehicle_id and not (c.additional_vehicles and len(c.additional_vehicles) > 0):
                alerts.append({
                    'id': f"camp_gap_veh_{c.id}",
                    'type': 'LIPSĂ_RESURSĂ',
                    'severity': 'error',
                    'category': 'Campaigns',
                    'message': f"Campanie fără vehicul: {c.campaign_name}",
                    'details': f"Nu a fost alocat niciun vehicul pentru campania programată între {c.start_date} și {c.end_date}.",
                    'entity_id': c.id,
                    'entity_type': 'campaign'
                })
            
            # Check Driver (if vehicle is primary)
            if c.vehicle_id and not c.driver_id:
                alerts.append({
                    'id': f"camp_gap_drv_{c.id}",
                    'type': 'LIPSĂ_RESURSĂ',
                    'severity': 'warning',
                    'category': 'Campaigns',
                    'message': f"Vehicul fără șofer: {c.campaign_name}",
                    'details': "Vehiculul principal nu are un șofer alocat pentru această campanie.",
                    'entity_id': c.id,
                    'entity_type': 'campaign'
                })
                
            # Check Spots
            if not c.has_spots or c.spot_count == 0:
                 alerts.append({
                    'id': f"camp_gap_spot_{c.id}",
                    'type': 'LIPSĂ_ASSET',
                    'severity': 'error',
                    'category': 'Campaigns',
                    'message': f"Campanie fără spoturi: {c.campaign_name}",
                    'details': "Campania nu are niciun spot media încărcat.",
                    'entity_id': c.id,
                    'entity_type': 'campaign'
                })
        return alerts

    def _check_status_conflicts(self, session) -> List[Dict]:
        alerts = []
        today = datetime.date.today()
        
        # 1. Defective Vehicles Impacting Campaigns (Current & Future)
        from sqlalchemy import or_
        defective_vehicles = session.query(Vehicle).filter(Vehicle.status.in_(['defective', 'maintenance'])).all()
        for v in defective_vehicles:
            impacted_campaigns = session.query(Campaign).filter(
                Campaign.end_date >= today,
                Campaign.status != 'cancelled',
                or_(
                    Campaign.vehicle_id == v.id,
                    Campaign.additional_vehicles.contains([{'vehicle_id': v.id}])
                )
            ).all()
            
            for c in impacted_campaigns:
                # Severity depends on if it's running now or in the future
                is_active_now = (c.start_date <= today <= c.end_date)
                severity = 'critical' if is_active_now else 'warning'
                status_label = "ACTIVĂ" if is_active_now else "VIITOARE"
                
                alerts.append({
                    'id': f"conflict_veh_{v.id}_{c.id}",
                    'type': 'IMPACT_DEFECTIUNE',
                    'severity': severity,
                    'category': 'Fleet',
                    'message': f"Mașină {v.status.upper()} în campanie {status_label}: {v.registration}",
                    'details': f"Campania '{c.campaign_name}' ({c.start_date} - {c.end_date}) este afectată deoarece vehiculul {v.registration} are statusul '{v.status}'.",
                    'entity_id': v.id,
                    'entity_type': 'vehicle'
                })

        # 2. Driver Leave Impacting Campaigns
        active_campaigns = session.query(Campaign).filter(Campaign.end_date >= today, Campaign.status != 'cancelled').all()
        for c in active_campaigns:
            if not c.driver_id: continue
            
            # Check if driver has leave/free during campaign
            conflicts = session.query(DriverSchedule).filter(
                DriverSchedule.driver_id == c.driver_id,
                DriverSchedule.event_type.in_(['vacation', 'medical', 'unpaid', 'free']),
                DriverSchedule.start_date <= c.end_date,
                DriverSchedule.end_date >= c.start_date
            ).all()
            
            for conflict in conflicts:
                alerts.append({
                    'id': f"conflict_drv_{c.driver_id}_{c.id}_{conflict.id}",
                    'type': 'IMPACT_CONCEDIU',
                    'severity': 'error',
                    'category': 'Fleet',
                    'message': f"Șofer în CONCEDIU: {c.campaign_name}",
                    'details': f"Șoferul alocat este în {conflict.event_type} în perioada {conflict.start_date} - {conflict.end_date}.",
                    'entity_id': c.driver_id,
                    'entity_type': 'driver'
                })
                
        return alerts

    def process_email_notifications(self):
        """
        Scan and send emails for new or critical notifications.
        This would typically be called by a cron job or background task.
        """
        settings = self.cs.get_settings()
        if not settings.get('enable_email_notifications'):
            return
            
        recipient = settings.get('notification_email_recipient')
        if not recipient:
            return
            
        notifications = self.get_all_notifications()
        # Filter for critical/error if requested by settings
        # For now, send everything that is 'error' or 'critical'
        
        for n in notifications:
            if n['severity'] in ['error', 'critical']:
                # Simple logic: avoid spamming by tracking sent alerts? 
                # For this implementation, we assume it's triggered periodically.
                self.email_service.send_notification(
                    recipient, 
                    n['type'], 
                    f"Mesaj: {n['message']}<br/>Detalii: {n['details']}"
                )
