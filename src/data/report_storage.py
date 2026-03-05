import logging
import json
from typing import List, Dict, Any, Optional
from sqlalchemy import desc
from src.data.db_config import SessionLocal
from src.data.models import GeneratedReport, Campaign

logger = logging.getLogger(__name__)

class ReportStorage:
    def __init__(self):
        pass

    def save_report_metadata(self, campaign_id: str, report_type: str, file_path: str, file_name: str, frozen_data: Dict[str, Any]) -> str:
        """Save report metadata and frozen metrics to the database"""
        session = SessionLocal()
        try:
            report = GeneratedReport(
                campaign_id=campaign_id,
                report_type=report_type,
                file_path=file_path,
                file_name=file_name,
                frozen_data=frozen_data
            )
            session.add(report)
            session.commit()
            session.refresh(report)
            return report.id
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving report metadata: {e}")
            raise e
        finally:
            session.close()

    def get_reports_by_campaign(self, campaign_id: str) -> List[Dict[str, Any]]:
        """Get all generated reports for a specific campaign"""
        session = SessionLocal()
        try:
            reports = session.query(GeneratedReport)\
                .filter(GeneratedReport.campaign_id == campaign_id)\
                .order_by(desc(GeneratedReport.created_at))\
                .all()
            return [self._to_dict(r) for r in reports]
        finally:
            session.close()

    def get_latest_metrics(self, campaign_id: str, report_type: str = 'standard') -> Optional[Dict[str, Any]]:
        """Get the frozen metrics from the latest report of a specific type"""
        session = SessionLocal()
        try:
            report = session.query(GeneratedReport)\
                .filter(GeneratedReport.campaign_id == campaign_id, GeneratedReport.report_type == report_type)\
                .order_by(desc(GeneratedReport.created_at))\
                .first()
            return report.frozen_data if report else None
        finally:
            session.close()

    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get a single report's metadata"""
        session = SessionLocal()
        try:
            report = session.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
            return self._to_dict(report) if report else None
        finally:
            session.close()

    def delete_report(self, report_id: str) -> bool:
        """Remove report metadata from database (does not delete physical file)"""
        session = SessionLocal()
        try:
            report = session.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
            if report:
                session.delete(report)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting report metadata: {e}")
            return False
        finally:
            session.close()

    def _to_dict(self, report: GeneratedReport) -> Dict[str, Any]:
        """Convert SQLAlchemy object to dictionary"""
        return {
            'id': report.id,
            'campaign_id': report.campaign_id,
            'report_type': report.report_type,
            'file_path': report.file_path,
            'file_name': report.file_name,
            'frozen_data': report.frozen_data or {},
            'created_at': report.created_at.isoformat() if report.created_at else None
        }
