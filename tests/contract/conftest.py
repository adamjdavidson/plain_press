"""
Pytest configuration for contract tests

Provides fixtures for database setup/teardown
"""
import pytest
from dotenv import load_dotenv
from sqlalchemy import text

# Load environment variables for tests
load_dotenv()


@pytest.fixture(scope="session")
def database_setup():
    """
    Session-level fixture for database setup
    
    Contract tests run against the actual database (Railway PostgreSQL)
    to verify constraints are enforced at the database level.
    """
    # Database is already set up via Alembic migrations
    # This fixture exists for future setup needs
    yield
    # No teardown needed - tests use transactions that rollback


@pytest.fixture(scope="function", autouse=True)
def cleanup_test_data(request):
    """
    Auto-cleanup test data after each test
    
    Deletes test data created during tests to prevent
    duplicate key violations on subsequent runs
    """
    yield
    
    # Cleanup after test completes
    from app.database import SessionLocal
    session = SessionLocal()
    try:
        # Delete feedback records first (foreign key to articles)
        session.execute(text("DELETE FROM feedback WHERE article_id IN (SELECT id FROM articles WHERE external_url LIKE 'https://example.com/%')"))
        
        # Delete test articles (cascades to feedback and deep_dives)
        session.execute(text("DELETE FROM articles WHERE external_url LIKE 'https://example.com/%'"))
        
        # Delete test sources
        session.execute(text("DELETE FROM sources WHERE name LIKE 'Test Source%'"))
        
        # Delete test email batches
        session.execute(text("DELETE FROM email_batches WHERE subject_line LIKE 'Test%' OR subject_line = 'Plain News Candidates'"))
        
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()

