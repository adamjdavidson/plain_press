"""
Contract tests for Article model database constraints

Tests verify database-level constraints are enforced:
- UNIQUE constraint on external_url
- NOT NULL constraints on required fields
- CHECK constraint on filter_score range
- ENUM validation on article.status
"""
import pytest
from sqlalchemy.exc import IntegrityError, DataError
from uuid import uuid4

from app.models import Article, Source, ArticleStatus, SourceType
from app.database import SessionLocal


@pytest.fixture
def db_session():
    """Create a database session for testing"""
    session = SessionLocal()
    try:
        yield session
        session.rollback()
    finally:
        session.close()


@pytest.fixture
def test_source(db_session):
    """Create a test source for article relationships"""
    source = Source(
        name=f"Test Source {uuid4()}",
        type=SourceType.RSS,
        url="https://example.com/feed.xml",
        is_active=True,
        trust_score=0.5,
        total_surfaced=0,
        total_approved=0,
        total_rejected=0
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)
    return source


class TestUniqueConstraints:
    """Test UNIQUE constraint on article.external_url"""
    
    def test_duplicate_url_rejected(self, db_session, test_source):
        """
        T022 [P] [US1]: Test UNIQUE constraint on external_url
        
        Given: An article exists with a specific URL
        When: Attempting to insert another article with the same URL
        Then: IntegrityError raised (duplicate key violation)
        """
        url = "https://example.com/article/123"
        
        # Create first article
        article1 = Article(
            external_url=url,
            headline="First Article",
            source_name="Test Source",
            source_id=test_source.id,
            summary="Test summary",
            amish_angle="Test angle",
            filter_score=0.8,
            status=ArticleStatus.PENDING
        )
        db_session.add(article1)
        db_session.commit()
        
        # Attempt to create duplicate
        article2 = Article(
            external_url=url,  # Same URL
            headline="Second Article",
            source_name="Test Source",
            source_id=test_source.id,
            summary="Different summary",
            amish_angle="Different angle",
            filter_score=0.9,
            status=ArticleStatus.PENDING
        )
        db_session.add(article2)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "external_url" in str(exc_info.value).lower()
        assert "unique" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()


class TestNotNullConstraints:
    """Test NOT NULL constraints on required fields"""
    
    def test_missing_headline_rejected(self, db_session, test_source):
        """
        T023 [P] [US1]: Test NOT NULL constraint on headline
        
        Given: Attempting to create article without headline
        When: Committing to database
        Then: IntegrityError raised (not null violation)
        """
        article = Article(
            external_url="https://example.com/article/456",
            headline=None,  # Missing required field
            source_name="Test Source",
            source_id=test_source.id,
            summary="Test summary",
            amish_angle="Test angle",
            filter_score=0.7,
            status=ArticleStatus.PENDING
        )
        db_session.add(article)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "headline" in str(exc_info.value).lower()
        assert "null" in str(exc_info.value).lower()
    
    def test_missing_summary_rejected(self, db_session, test_source):
        """Test NOT NULL constraint on summary"""
        article = Article(
            external_url="https://example.com/article/789",
            headline="Test Headline",
            source_name="Test Source",
            source_id=test_source.id,
            summary=None,  # Missing required field
            amish_angle="Test angle",
            filter_score=0.7,
            status=ArticleStatus.PENDING
        )
        db_session.add(article)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "summary" in str(exc_info.value).lower()
        assert "null" in str(exc_info.value).lower()
    
    def test_missing_amish_angle_rejected(self, db_session, test_source):
        """Test NOT NULL constraint on amish_angle"""
        article = Article(
            external_url="https://example.com/article/101",
            headline="Test Headline",
            source_name="Test Source",
            source_id=test_source.id,
            summary="Test summary",
            amish_angle=None,  # Missing required field
            filter_score=0.7,
            status=ArticleStatus.PENDING
        )
        db_session.add(article)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "amish_angle" in str(exc_info.value).lower()
        assert "null" in str(exc_info.value).lower()
    
    def test_missing_source_id_rejected(self, db_session):
        """Test NOT NULL constraint on source_id (foreign key)"""
        article = Article(
            external_url="https://example.com/article/102",
            headline="Test Headline",
            source_name="Test Source",
            source_id=None,  # Missing required foreign key
            summary="Test summary",
            amish_angle="Test angle",
            filter_score=0.7,
            status=ArticleStatus.PENDING
        )
        db_session.add(article)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "source_id" in str(exc_info.value).lower()


class TestCheckConstraints:
    """Test CHECK constraint on filter_score"""
    
    def test_filter_score_below_zero_rejected(self, db_session, test_source):
        """
        T024 [P] [US1]: Test CHECK constraint on filter_score
        
        Given: Attempting to create article with filter_score < 0.0
        When: Committing to database
        Then: IntegrityError raised (check violation)
        """
        article = Article(
            external_url="https://example.com/article/200",
            headline="Test Headline",
            source_name="Test Source",
            source_id=test_source.id,
            summary="Test summary",
            amish_angle="Test angle",
            filter_score=-0.1,  # Invalid: below 0.0
            status=ArticleStatus.PENDING
        )
        db_session.add(article)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "filter_score" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()
    
    def test_filter_score_zero_accepted(self, db_session, test_source):
        """Test filter_score = 0.0 is valid (boundary case)"""
        article = Article(
            external_url="https://example.com/article/201",
            headline="Test Headline",
            source_name="Test Source",
            source_id=test_source.id,
            summary="Test summary",
            amish_angle="Test angle",
            filter_score=0.0,  # Valid boundary
            status=ArticleStatus.PENDING
        )
        db_session.add(article)
        db_session.commit()
        
        assert article.filter_score == 0.0
    
    def test_filter_score_one_accepted(self, db_session, test_source):
        """Test filter_score = 1.0 is valid (boundary case)"""
        article = Article(
            external_url="https://example.com/article/202",
            headline="Test Headline",
            source_name="Test Source",
            source_id=test_source.id,
            summary="Test summary",
            amish_angle="Test angle",
            filter_score=1.0,  # Valid boundary
            status=ArticleStatus.PENDING
        )
        db_session.add(article)
        db_session.commit()
        
        assert article.filter_score == 1.0
    
    def test_filter_score_above_one_rejected(self, db_session, test_source):
        """Test filter_score > 1.0 is rejected"""
        article = Article(
            external_url="https://example.com/article/203",
            headline="Test Headline",
            source_name="Test Source",
            source_id=test_source.id,
            summary="Test summary",
            amish_angle="Test angle",
            filter_score=1.1,  # Invalid: above 1.0
            status=ArticleStatus.PENDING
        )
        db_session.add(article)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        assert "filter_score" in str(exc_info.value).lower() or "check" in str(exc_info.value).lower()


class TestEnumValidation:
    """Test ENUM validation on article.status"""
    
    def test_invalid_status_rejected(self, db_session, test_source):
        """
        T025 [P] [US1]: Test ENUM validation on article.status
        
        Given: Attempting to create article with invalid status value
        When: Committing article with invalid status string
        Then: Database rejects with IntegrityError (enum validation)
        """
        # Note: SQLAlchemy allows setting status to string at Python level,
        # but PostgreSQL ENUM type rejects it at commit time
        from sqlalchemy import text
        
        # Attempt to insert article with invalid status via raw SQL
        # (bypasses Python enum to test database-level validation)
        with pytest.raises(DataError) as exc_info:
            db_session.execute(text("""
                INSERT INTO articles (
                    id, external_url, headline, source_name, source_id,
                    summary, amish_angle, filter_score, status
                ) VALUES (
                    gen_random_uuid(),
                    :url,
                    'Test Headline',
                    'Test Source',
                    :source_id,
                    'Test summary',
                    'Test angle',
                    0.8,
                    'INVALID_STATUS'
                )
            """), {"url": f"https://example.com/article/enum-test-{uuid4()}", "source_id": test_source.id})
            db_session.commit()
        
        # Verify it's specifically an enum validation error
        assert "article_status" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()
    
    def test_valid_status_values_accepted(self, db_session, test_source):
        """Test all valid ArticleStatus enum values are accepted"""
        valid_statuses = [
            ArticleStatus.PENDING,
            ArticleStatus.EMAILED,
            ArticleStatus.GOOD,
            ArticleStatus.REJECTED,
            ArticleStatus.PASSED
        ]
        
        for idx, status in enumerate(valid_statuses):
            article = Article(
                external_url=f"https://example.com/article/30{idx}",
                headline="Test Headline",
                source_name="Test Source",
                source_id=test_source.id,
                summary="Test summary",
                amish_angle="Test angle",
                filter_score=0.8,
                status=status
            )
            db_session.add(article)
        
        db_session.commit()
        
        # Verify all created successfully
        count = db_session.query(Article).filter(
            Article.external_url.like("https://example.com/article/30%")
        ).count()
        assert count == 5

