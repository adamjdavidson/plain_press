"""
Database configuration and session management for Amish News Finder
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create declarative base for all models
Base = declarative_base()

# Lazy initialization - don't connect until needed
_engine = None
_SessionLocal = None


def get_database_url():
    """Get database URL from environment."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL environment variable not set")
    return url


def get_engine():
    """Get or create database engine (lazy initialization)."""
    global _engine
    if _engine is None:
        database_url = get_database_url()
        _engine = create_engine(
            database_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=os.getenv("FLASK_DEBUG", "False") == "True"
        )
    return _engine


def SessionLocal():
    """Get a new database session."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal()


def get_session():
    """
    Get a database session (context manager compatible)
    
    Usage:
        with get_session() as session:
            session.query(Article).all()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# For backwards compatibility - but these are now lazy
engine = property(lambda self: get_engine())


def create_db_engine(database_url=None):
    """Legacy function - use get_engine() instead."""
    if database_url:
        return create_engine(database_url, pool_pre_ping=True)
    return get_engine()

