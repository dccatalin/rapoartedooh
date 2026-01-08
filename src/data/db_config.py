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
IS_STREAMLIT_CLOUD = os.environ.get('STREAMLIT_RUNTIME_ENV') is not None

if IS_STREAMLIT_CLOUD:
    # On Streamlit Cloud, the repo is often read-only. 
    # We copy the DB to /tmp to make it writable and allowed to create journals.
    TEMP_DB_PATH = "/tmp/rapoartedooh.db"
    
    # Try to copy the original DB to /tmp if it exists and hasn't been copied yet
    if os.path.exists(ORIGINAL_DB_PATH):
        try:
            # We copy it every time to ensure we have the latest data from GitHub on reboot
            # but only if it's not already there or if we want to reset
            shutil.copy2(ORIGINAL_DB_PATH, TEMP_DB_PATH)
            DB_PATH = TEMP_DB_PATH
            print(f"DEBUG: Copied database to {DB_PATH}")
        except Exception as e:
            print(f"DEBUG: Failed to copy DB to /tmp: {e}")
            DB_PATH = ORIGINAL_DB_PATH
    else:
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
        cursor.execute("PRAGMA journal_mode=WAL") # WAL is often better for concurrent reads/writes
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
    """Initialize the database (create tables)"""
    import src.data.models  # Import models to register them with Base
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency for getting DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
