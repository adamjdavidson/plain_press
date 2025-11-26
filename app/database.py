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


def create_db_engine(database_url=None):
    """
    Create SQLAlchemy engine with connection pooling
    
    Args:
        database_url: Optional database URL override
        
    Returns:
        SQLAlchemy engine instance
    """
    if database_url is None:
        database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    # Create engine with connection pooling settings
    engine = create_engine(
        database_url,
        pool_size=5,               # Base connection pool size
        max_overflow=10,           # Max additional connections
        pool_pre_ping=True,        # Verify connections before use
        pool_recycle=3600,         # Recycle connections after 1 hour
        echo=os.getenv("FLASK_DEBUG", "False") == "True"  # SQL logging in debug mode
    )
    
    return engine


# Create default engine and session factory
engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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

