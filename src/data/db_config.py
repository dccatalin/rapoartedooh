import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

# Default to local SQLite database in project root / src / data
# We use absolute paths to avoid issues on different environments
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # This is 'src/'
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DB_FOLDER = os.path.join(BASE_DIR, 'data')

if not os.path.exists(DB_FOLDER):
    try:
        os.makedirs(DB_FOLDER, exist_ok=True)
    except:
        # Fallback to current directory if src/data is not writable
        DB_FOLDER = os.getcwd()

DB_PATH = os.path.join(DB_FOLDER, 'rapoartedooh.db')
DATABASE_URL = f"sqlite:///{os.path.abspath(DB_PATH)}"

# For SQLite with many threads (like Streamlit), we need check_same_thread=False
ENGINE_ARGS = {
    "connect_args": {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
}

# Caching for Streamlit
try:
    import streamlit as st
    from streamlit.runtime import exists as streamlit_exists
    
    if streamlit_exists():
        @st.cache_resource
        def _get_engine_and_session():
            _engine = create_engine(DATABASE_URL, echo=False, **ENGINE_ARGS)
            _SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=_engine))
            return _engine, _SessionLocal

        @st.cache_resource
        def _get_declarative_base():
            return declarative_base()

        engine, SessionLocal = _get_engine_and_session()
        Base = _get_declarative_base()
    else:
        engine = create_engine(DATABASE_URL, echo=False, **ENGINE_ARGS)
        SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
        Base = declarative_base()
except (ImportError, Exception):
    engine = create_engine(DATABASE_URL, echo=False, **ENGINE_ARGS)
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
