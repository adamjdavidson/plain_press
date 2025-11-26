"""
Root pytest configuration for Amish News Finder tests

Adds project root to Python path and provides common fixtures
"""
import sys
import os

import pytest
from dotenv import load_dotenv

# Add project root to Python path so tests can import app
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()


@pytest.fixture(scope="function")
def db_session():
    """
    Provides a database session for tests.
    
    Session is automatically closed after each test.
    Tests should use transactions and rollback for isolation.
    """
    from app.database import SessionLocal
    
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

