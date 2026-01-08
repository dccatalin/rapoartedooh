import os
import shutil
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

# Default to local SQLite database in project root / src / data
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # This is 'src/'
DB_FOLDER = os.path.join(BASE_DIR, 'data')
ORIGINAL_DB_PATH = os.path.join(DB_FOLDER, 'rapoartedooh.db')

# Robust path detection for Streamlit Cloud
# STREAMLIT_SHARING is a reliable indicator on Streamlit Cloud
IS_STREAMLIT_CLOUD = os.environ.get('STREAMLIT_SHARING') == 'true' or os.environ.get('STREAMLIT_RUNTIME_ENV') is not None

if IS_STREAMLIT_CLOUD:
    # On Streamlit Cloud, the repo is read-only. 
    # We copy the DB to /tmp to make it writable and allow it to create journals.
    # Using a unique name to avoid collisions if multiple apps on same machine (unlikely but safe)
    TEMP_DB_PATH = "/tmp/rapoartedooh_writable.db"
    
    # Try to copy the original DB to /tmp
    if os.path.exists(ORIGINAL_DB_PATH):
        try:
            # We copy it to ensure we have the latest data from GitHub on each reboot
            # or if it doesn't exist yet in /tmp
            if not os.path.exists(TEMP_DB_PATH) or os.path.getmtime(ORIGINAL_DB_PATH) > os.path.getmtime(TEMP_DB_PATH):
                shutil.copy2(ORIGINAL_DB_PATH, TEMP_DB_PATH)
                # Ensure permissions are writable
                os.chmod(TEMP_DB_PATH, 0o666)
            DB_PATH = TEMP_DB_PATH
            print(f"DEBUG: Using writable database at {DB_PATH}")
        except Exception as e:
            print(f"DEBUG: Failed to copy DB to /tmp: {e}")
            DB_PATH = ORIGINAL_DB_PATH
    else:
        # If original doesn't exist, we'll hit errors anyway, 
        # but let's point to /tmp just in case init_db can create it
        DB_PATH = TEMP_DB_PATH
else:
    DB_PATH = ORIGINAL_DB_PATH

DB_PATH = os.path.abspath(DB_PATH)
DATABASE_URL = f"sqlite:///{DB_PATH}"

# For SQLite with many threads (like Streamlit), we need check_same_thread=False
ENGINE_ARGS = {
    "connect_args": {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    "pool_pre_ping": True
}

def set_sqlite_pragma(dbapi_connection, connection_record):
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        # WAL mode requires write access to the directory
        # If we are in /tmp, this should work.
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

# Caching for Streamlit
try:
    import streamlit as st
    from streamlit.runtime import exists as streamlit_exists
    
    if streamlit_exists():
        @st.cache_resource
        def _get_engine_and_session():
            _engine = create_engine(DATABASE_URL, echo=False, **ENGINE_ARGS)
            event.listen(_engine, "connect", set_sqlite_pragma)
            _SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=_engine))
            return _engine, _SessionLocal

        @st.cache_resource
        def _get_declarative_base():
            return declarative_base()

        engine, SessionLocal = _get_engine_and_session()
        Base = _get_declarative_base()
    else:
        engine = create_engine(DATABASE_URL, echo=False, **ENGINE_ARGS)
        event.listen(engine, "connect", set_sqlite_pragma)
        SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
        Base = declarative_base()
except (ImportError, Exception):
    engine = create_engine(DATABASE_URL, echo=False, **ENGINE_ARGS)
    event.listen(engine, "connect", set_sqlite_pragma)
    SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
    Base = declarative_base()

def init_db():
    """Initialize the database (create tables and migrate columns)"""
    import src.data.models  # Import models to register them with Base
    # metadata.create_all is safe to call even if tables exist
    Base.metadata.create_all(bind=engine)
    
    # Auto-migration for missing columns (robust for Streamlit Cloud)
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check drivers table
        cursor.execute("PRAGMA table_info(drivers)")
        columns = [row[1] for row in cursor.fetchall()]
        
        new_cols = [
            ("identity_card_expiry", "DATE"),
            ("medical_exam_expiry", "DATE"),
            ("psychological_exam_expiry", "DATE"),
            ("email", "VARCHAR(100)")
        ]
        
        for col_name, col_type in new_cols:
            if col_name not in columns:
                try:
                    print(f"Auto-migrating: Adding {col_name} to drivers table")
                    cursor.execute(f"ALTER TABLE drivers ADD COLUMN {col_name} {col_type}")
                except Exception as e:
                    print(f"Error adding column {col_name}: {e}")
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Auto-migration error: {e}")

def get_db():
    """Dependency for getting DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
