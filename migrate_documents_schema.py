"""
Migration script to create documents table and migrate existing vehicle expiry dates
"""
import sqlite3
import os
import datetime
import uuid

DB_PATH = 'src/data/rapoartedooh.db'

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if documents table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
        if cursor.fetchone():
            print("Documents table already exists.")
        else:
            print("Creating documents table...")
            cursor.execute("""
                CREATE TABLE documents (
                    id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    custom_type_name TEXT,
                    issue_date DATE,
                    expiry_date DATE,
                    file_path TEXT,
                    file_name TEXT,
                    uploaded_at DATETIME,
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_modified DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("Documents table created successfully.")
        
        # Migrate existing vehicle expiry dates to documents
        print("\nMigrating existing vehicle expiry dates...")
        cursor.execute("""
            SELECT id, rca_expiry, itp_expiry, rovinieta_expiry, casco_expiry 
            FROM vehicles
        """)
        
        vehicles = cursor.fetchall()
        migrated_count = 0
        
        for vehicle in vehicles:
            vehicle_id, rca, itp, rov, casco = vehicle
            
            # Migrate RCA
            if rca:
                doc_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO documents (id, entity_type, entity_id, document_type, expiry_date, created_at)
                    VALUES (?, 'vehicle', ?, 'RCA', ?, ?)
                """, (doc_id, vehicle_id, rca, datetime.datetime.now()))
                migrated_count += 1
            
            # Migrate ITP
            if itp:
                doc_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO documents (id, entity_type, entity_id, document_type, expiry_date, created_at)
                    VALUES (?, 'vehicle', ?, 'ITP', ?, ?)
                """, (doc_id, vehicle_id, itp, datetime.datetime.now()))
                migrated_count += 1
            
            # Migrate Rovinieta
            if rov:
                doc_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO documents (id, entity_type, entity_id, document_type, expiry_date, created_at)
                    VALUES (?, 'vehicle', ?, 'Rovinieta', ?, ?)
                """, (doc_id, vehicle_id, rov, datetime.datetime.now()))
                migrated_count += 1
            
            # Migrate CASCO
            if casco:
                doc_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO documents (id, entity_type, entity_id, document_type, expiry_date, created_at)
                    VALUES (?, 'vehicle', ?, 'CASCO', ?, ?)
                """, (doc_id, vehicle_id, casco, datetime.datetime.now()))
                migrated_count += 1
        
        print(f"Migrated {migrated_count} document records from {len(vehicles)} vehicles.")
        
        conn.commit()
        print("\nMigration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
