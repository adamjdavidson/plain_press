"""
Pytest configuration for integration tests

Provides performance measurement fixtures and session management
"""
import pytest
import time
from dotenv import load_dotenv
from sqlalchemy import text

# Load environment variables for tests
load_dotenv()


@pytest.fixture
def performance_timer():
    """
    Context manager for measuring test execution time
    
    Usage:
        with performance_timer() as timer:
            # ... code to measure ...
        
        assert timer.elapsed < 1.0  # Verify < 1 second
    """
    class Timer:
        def __init__(self):
            self.start = None
            self.end = None
            self.elapsed = None
        
        def __enter__(self):
            self.start = time.time()
            return self
        
        def __exit__(self, *args):
            self.end = time.time()
            self.elapsed = self.end - self.start
    
    return Timer()


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

