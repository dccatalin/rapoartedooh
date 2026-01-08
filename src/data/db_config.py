import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

# Default to local SQLite database
DB_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
if not os.path.exists(DB_FOLDER):
    os.makedirs(DB_FOLDER)

DB_PATH = os.path.join(DB_FOLDER, 'rapoartedooh.db')
DATABASE_URL = f"sqlite:///{DB_PATH}"

# For MySQL, the URL would be:
# DATABASE_URL = "mysql+pymysql://user:password@host/dbname"

# Caching for Streamlit
try:
    import streamlit as st
    from streamlit.runtime import exists as streamlit_exists
    
    if streamlit_exists():
        @st.cache_resource
        def _get_engine_and_session():
            _engine = create_engine(DATABASE_URL, echo=False)
            _SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=_engine))
            return _engine, _SessionLocal

        @st.cache_resource
        def _get_declarative_base():
            return declarative_base()

        engine, SessionLocal = _get_engine_and_session()
        Base = _get_declarative_base()
    else:
        engine = create_engine(DATABASE_URL, echo=False)
        SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
        Base = declarative_base()
except (ImportError, Exception):
    engine = create_engine(DATABASE_URL, echo=False)
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
