"""
Document Manager - Handles CRUD operations for documents with file storage
"""
import os
import shutil
import datetime
import uuid
from typing import List, Dict, Optional
from src.data.db_config import SessionLocal
from src.data.models import Document, Vehicle, Driver

class DocumentManager:
    """Manages documents for vehicles and drivers with file upload support"""
    
    # Predefined document types
    VEHICLE_TYPES = [
        'RCA',
        'ITP',
        'Rovinieta',
        'CASCO',
        'Talon',
        'Carte Masina',
        'Asigurare Internationala',
        'Custom'
    ]
    
    DRIVER_TYPES = [
        'Contract Munca',
        'Fisa SSM',
        'Fisa PSI',
        'Medicina Muncii',
        'Permis Conducere',
        'Carte Identitate',
        'Cazier Judiciar',
        'Aviz Psihologic',
        'Custom'
    ]
    
    # File storage settings
    DOCUMENTS_DIR = 'documents'
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png'}
    
    def __init__(self):
        # Ensure documents directory exists
        os.makedirs(self.DOCUMENTS_DIR, exist_ok=True)
        os.makedirs(os.path.join(self.DOCUMENTS_DIR, 'vehicles'), exist_ok=True)
        os.makedirs(os.path.join(self.DOCUMENTS_DIR, 'drivers'), exist_ok=True)
    
    def add_document(self, entity_type: str, entity_id: str, document_type: str,
                    expiry_date: datetime.date = None, issue_date: datetime.date = None,
                    custom_type_name: str = None, notes: str = None,
                    file_path: str = None) -> Optional[str]:
        """
        Add a new document
        
        Args:
            entity_type: 'vehicle' or 'driver'
            entity_id: ID of the vehicle or driver
            document_type: Type of document
            expiry_date: Expiry date (optional)
            issue_date: Issue date (optional)
            custom_type_name: Name for custom document types
            notes: Additional notes
            file_path: Path to file to upload (optional)
        
        Returns:
            Document ID if successful, None otherwise
        """
        session = SessionLocal()
        try:
            doc = Document(
                entity_type=entity_type,
                entity_id=entity_id,
                document_type=document_type,
                custom_type_name=custom_type_name,
                issue_date=issue_date,
                expiry_date=expiry_date,
                notes=notes
            )
            
            # Handle file upload
            if file_path and os.path.exists(file_path):
                stored_path = self._store_file(file_path, entity_type, entity_id, document_type)
                if stored_path:
                    doc.file_path = stored_path
                    doc.file_name = os.path.basename(file_path)
                    doc.uploaded_at = datetime.datetime.now()
            
            session.add(doc)
            session.commit()
            
            # Sync with vehicle if applicable
            if entity_type == 'vehicle' and expiry_date:
                self._sync_vehicle_expiry(session, entity_id, document_type, expiry_date)
            elif entity_type == 'driver' and expiry_date:
                self._sync_driver_expiry(session, entity_id, document_type, expiry_date)
                
            return doc.id
            
        except Exception as e:
            session.rollback()
            print(f"Error adding document: {e}")
            return None
        finally:
            session.close()
    
    def get_documents(self, entity_type: str, entity_id: str, 
                     include_expired: bool = True) -> List[Dict]:
        """Get all documents for an entity"""
        session = SessionLocal()
        try:
            query = session.query(Document).filter(
                Document.entity_type == entity_type,
                Document.entity_id == entity_id
            )
            
            documents = query.all()
            
            result = []
            for doc in documents:
                doc_dict = {
                    'id': doc.id,
                    'document_type': doc.document_type,
                    'custom_type_name': doc.custom_type_name,
                    'issue_date': doc.issue_date,
                    'expiry_date': doc.expiry_date,
                    'file_path': doc.file_path,
                    'file_name': doc.file_name,
                    'uploaded_at': doc.uploaded_at,
                    'notes': doc.notes,
                    'status': self._get_document_status(doc.expiry_date)
                }
                
                if include_expired or doc_dict['status'] != 'expired':
                    result.append(doc_dict)
            
            return result
            
        finally:
            session.close()
    
    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get a single document by ID"""
        session = SessionLocal()
        try:
            doc = session.query(Document).filter(Document.id == doc_id).first()
            if not doc:
                return None
            
            return {
                'id': doc.id,
                'entity_type': doc.entity_type,
                'entity_id': doc.entity_id,
                'document_type': doc.document_type,
                'custom_type_name': doc.custom_type_name,
                'issue_date': doc.issue_date,
                'expiry_date': doc.expiry_date,
                'file_path': doc.file_path,
                'file_name': doc.file_name,
                'uploaded_at': doc.uploaded_at,
                'notes': doc.notes,
                'status': self._get_document_status(doc.expiry_date)
            }
        finally:
            session.close()
    
    def update_document(self, doc_id: str, updates: Dict, new_file_path: str = None) -> bool:
        """Update a document"""
        session = SessionLocal()
        try:
            doc = session.query(Document).filter(Document.id == doc_id).first()
            if not doc:
                return False
            
            # Update fields
            for key, value in updates.items():
                if hasattr(doc, key):
                    setattr(doc, key, value)
            
            # Handle file replacement
            if new_file_path and os.path.exists(new_file_path):
                # Delete old file if exists
                if doc.file_path:
                    old_file = self.get_document_file_path(doc_id)
                    if old_file and os.path.exists(old_file):
                        os.remove(old_file)
                
                # Store new file
                stored_path = self._store_file(new_file_path, doc.entity_type, 
                                              doc.entity_id, doc.document_type)
                if stored_path:
                    doc.file_path = stored_path
                    doc.file_name = os.path.basename(new_file_path)
                    doc.uploaded_at = datetime.datetime.now()
            
            doc.last_modified = datetime.datetime.now()
            session.commit()
            
            # Sync with vehicle if applicable
            if doc.entity_type == 'vehicle' and doc.expiry_date:
                self._sync_vehicle_expiry(session, doc.entity_id, doc.document_type, doc.expiry_date)
            elif doc.entity_type == 'driver' and doc.expiry_date:
                self._sync_driver_expiry(session, doc.entity_id, doc.document_type, doc.expiry_date)
                
            return True
            
        except Exception as e:
            session.rollback()
            print(f"Error updating document: {e}")
            return False
        finally:
            session.close()
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document and its file"""
        session = SessionLocal()
        try:
            doc = session.query(Document).filter(Document.id == doc_id).first()
            if not doc:
                return False
            
            # Delete file if exists
            if doc.file_path:
                file_path = self.get_document_file_path(doc_id)
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            
            session.delete(doc)
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            print(f"Error deleting document: {e}")
            return False
        finally:
            session.close()
    
    def get_expired_documents(self, entity_type: str = None, 
                            days_threshold: int = 30) -> List[Dict]:
        """Get expired or expiring documents"""
        session = SessionLocal()
        try:
            query = session.query(Document)
            
            if entity_type:
                query = query.filter(Document.entity_type == entity_type)
            
            # Filter for documents with expiry dates
            query = query.filter(Document.expiry_date.isnot(None))
            
            documents = query.all()
            
            result = []
            today = datetime.date.today()
            threshold_date = today + datetime.timedelta(days=days_threshold)
            
            for doc in documents:
                if doc.expiry_date <= threshold_date:
                    result.append({
                        'id': doc.id,
                        'entity_type': doc.entity_type,
                        'entity_id': doc.entity_id,
                        'document_type': doc.document_type,
                        'expiry_date': doc.expiry_date,
                        'status': self._get_document_status(doc.expiry_date),
                        'days_until_expiry': (doc.expiry_date - today).days
                    })
            
            return result
            
        finally:
            session.close()
    
    def get_document_file_path(self, doc_id: str) -> Optional[str]:
        """Get absolute path to document file"""
        session = SessionLocal()
        try:
            doc = session.query(Document).filter(Document.id == doc_id).first()
            if not doc or not doc.file_path:
                return None
            
            return os.path.abspath(doc.file_path)
        finally:
            session.close()
    
    def _store_file(self, source_path: str, entity_type: str, 
                   entity_id: str, doc_type: str) -> Optional[str]:
        """Store uploaded file in organized directory structure"""
        try:
            # Validate file
            if not os.path.exists(source_path):
                return None
            
            file_size = os.path.getsize(source_path)
            if file_size > self.MAX_FILE_SIZE:
                print(f"File too large: {file_size} bytes")
                return None
            
            ext = os.path.splitext(source_path)[1].lower()
            if ext not in self.ALLOWED_EXTENSIONS:
                print(f"File type not allowed: {ext}")
                return None
            
            # Create entity directory
            entity_dir = os.path.join(self.DOCUMENTS_DIR, f"{entity_type}s", entity_id)
            os.makedirs(entity_dir, exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            original_name = os.path.basename(source_path)
            safe_doc_type = doc_type.replace(' ', '_').replace('/', '_')
            new_filename = f"{safe_doc_type}_{timestamp}_{original_name}"
            
            dest_path = os.path.join(entity_dir, new_filename)
            
            # Copy file
            shutil.copy2(source_path, dest_path)
            
            # Return relative path
            return os.path.relpath(dest_path)
            
        except Exception as e:
            print(f"Error storing file: {e}")
            return None
    
    def _get_document_status(self, expiry_date: datetime.date) -> str:
        """Determine document status based on expiry date"""
        if not expiry_date:
            return 'no_expiry'
        
        today = datetime.date.today()
        if expiry_date < today:
            return 'expired'
        elif expiry_date <= today + datetime.timedelta(days=30):
            return 'expiring'
        else:
            return 'valid'

    def _sync_vehicle_expiry(self, session, vehicle_id: str, doc_type: str, expiry_date: datetime.date):
        """Sync document expiry date back to the Vehicle record"""
        try:
            # Map document types to vehicle fields
            mapping = {
                'RCA': 'rca_expiry',
                'ITP': 'itp_expiry',
                'Rovinieta': 'rovinieta_expiry',
                'CASCO': 'casco_expiry'
            }
            
            field_name = mapping.get(doc_type)
            if not field_name:
                return
            
            vehicle = session.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
            if vehicle:
                # Only update if the new expiry is later or if current is None
                current_expiry = getattr(vehicle, field_name)
                if current_expiry is None or expiry_date > current_expiry:
                    setattr(vehicle, field_name, expiry_date)
                    session.commit()
                    print(f"Synced {doc_type} expiry ({expiry_date}) to vehicle {vehicle.registration}")
        except Exception as e:
            print(f"Error syncing expiry: {e}")

    def _sync_driver_expiry(self, session, driver_id: str, doc_type: str, expiry_date: datetime.date):
        """Sync document expiry date back to the Driver record"""
        try:
            # Map document types to driver fields
            mapping = {
                'Carte Identitate': 'identity_card_expiry',
                'Medicina Muncii': 'medical_exam_expiry',
                'Aviz Psihologic': 'psychological_exam_expiry'
            }
            
            field_name = mapping.get(doc_type)
            if not field_name:
                return
            
            driver = session.query(Driver).filter(Driver.id == driver_id).first()
            if driver:
                # Only update if the new expiry is later or if current is None
                current_expiry = getattr(driver, field_name)
                if current_expiry is None or expiry_date > current_expiry:
                    setattr(driver, field_name, expiry_date)
                    session.commit()
                    print(f"Synced {doc_type} expiry ({expiry_date}) to driver {driver.name}")
        except Exception as e:
            print(f"Error syncing driver expiry: {e}")
