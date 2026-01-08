import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

# Default to local SQLite database in project root / src / data
# We use absolute paths to avoid issues on different environments
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # This is 'src/'
DB_FOLDER = os.path.join(BASE_DIR, 'data')

# Robust path detection for Streamlit Cloud
if os.environ.get('STREAMLIT_RUNTIME_ENV'):
    # In Streamlit Cloud, the root is usually /mount/src/rapoartedooh
    # Let's try to detect the project root
    cwd = os.getcwd()
    potential_db = os.path.join(cwd, 'src', 'data', 'rapoartedooh.db')
    if os.path.exists(potential_db):
        DB_PATH = potential_db
    else:
        DB_PATH = os.path.join(DB_FOLDER, 'rapoartedooh.db')
else:
    DB_PATH = os.path.join(DB_FOLDER, 'rapoartedooh.db')

DB_PATH = os.path.abspath(DB_PATH)
DATABASE_URL = f"sqlite:///{DB_PATH}"

print(f"DEBUG: Using Database at {DB_PATH}")

# For SQLite with many threads (like Streamlit), we need check_same_thread=False
ENGINE_ARGS = {
    "connect_args": {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    "pool_pre_ping": True
}

def set_sqlite_pragma(dbapi_connection, connection_record):
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        # Helps with read-only filesystems or multiple threads
        cursor.execute("PRAGMA journal_mode=MEMORY")
        cursor.execute("PRAGMA synchronous=OFF")
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
