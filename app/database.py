"""
Database configuration and session management for Amish News Finder
"""
import os
import sys
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create declarative base for all models
Base = declarative_base()


def _log_db(msg: str):
    """Log database progress with immediate flush."""
    full_msg = f"DATABASE: {msg}"
    print(full_msg, file=sys.stdout, flush=True)


def create_db_engine(database_url=None):
    """
    Create SQLAlchemy engine with connection pooling

    Args:
        database_url: Optional database URL override

    Returns:
        SQLAlchemy engine instance
    """
    _log_db("create_db_engine called")

    if database_url is None:
        database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    # Log sanitized URL (hide password)
    if '@' in database_url:
        parts = database_url.split('@')
        sanitized = parts[0].split(':')[0] + ':***@' + parts[1]
    else:
        sanitized = database_url[:30] + "..."
    _log_db(f"Connecting to: {sanitized}")

    # Create engine with connection pooling settings
    _log_db("Creating SQLAlchemy engine...")
    engine_start = time.time()
    engine = create_engine(
        database_url,
        pool_size=5,               # Base connection pool size
        max_overflow=10,           # Max additional connections
        pool_pre_ping=True,        # Verify connections before use
        pool_recycle=3600,         # Recycle connections after 1 hour
        connect_args={"connect_timeout": 30},  # 30 second connection timeout
        echo=os.getenv("FLASK_DEBUG", "False") == "True"  # SQL logging in debug mode
    )
    engine_time = time.time() - engine_start
    _log_db(f"Engine created in {engine_time:.1f}s")

    return engine


# Create default engine and session factory
_log_db("Module loading - creating default engine...")
_module_start = time.time()
engine = create_db_engine()
_log_db(f"Default engine ready (module load took {time.time() - _module_start:.1f}s)")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
_log_db("SessionLocal factory created")


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

