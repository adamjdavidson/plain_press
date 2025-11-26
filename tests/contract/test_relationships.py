"""
Contract tests for database relationships and foreign key constraints

Tests verify:
- Foreign key CASCADE behavior (Feedback → Article, DeepDive → Article)
- Foreign key RESTRICT behavior (Article → Source)
- Foreign key SET NULL behavior (Article → EmailBatch)
- One-to-one relationship enforcement (Article ↔ Feedback, Article ↔ DeepDive)
"""
import pytest
from sqlalchemy.exc import IntegrityError
from uuid import uuid4

from app.models import (
    Article, Source, Feedback, DeepDive, EmailBatch,
    ArticleStatus, SourceType, FeedbackRating, EmailStatus
)
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
    """Create a test source"""
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


@pytest.fixture
def test_article(db_session, test_source):
    """Create a test article"""
    article = Article(
        external_url=f"https://example.com/article/{uuid4()}",
        headline="Test Headline",
        source_name="Test Source",
        source_id=test_source.id,
        summary="Test summary",
        amish_angle="Test angle",
        filter_score=0.8,
        status=ArticleStatus.EMAILED
    )
    db_session.add(article)
    db_session.commit()
    db_session.refresh(article)
    return article


class TestArticleSourceRelationship:
    """Test Article → Source foreign key (RESTRICT on delete)"""
    
    def test_cannot_delete_source_with_articles(self, db_session, test_source, test_article):
        """
        T026 [P] [US1]: Test Article → Source RESTRICT on delete
        
        Given: Source has associated articles
        When: Attempting to delete the source
        Then: IntegrityError raised (foreign key violation)
        """
        source_id = test_source.id
        
        # Verify article exists
        assert test_article.source_id == source_id
        
        # Attempt to delete source (should fail)
        db_session.delete(test_source)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        error_msg = str(exc_info.value).lower()
        assert "foreign key" in error_msg or "violates" in error_msg
        
        # Rollback and verify source still exists
        db_session.rollback()
        source_check = db_session.query(Source).filter_by(id=source_id).first()
        assert source_check is not None


class TestArticleFeedbackRelationship:
    """Test Article ↔ Feedback one-to-one relationship"""
    
    def test_one_feedback_per_article_enforced(self, db_session, test_article):
        """
        T033 [P] [US2]: Test Article → Feedback one-to-one relationship
        
        Given: An article already has feedback
        When: Attempting to create second feedback for same article
        Then: IntegrityError raised (unique constraint violation on article_id)
        """
        article_id = test_article.id
        
        # Create first feedback
        feedback1 = Feedback(
            article_id=article_id,
            rating=FeedbackRating.GOOD,
            notes="First feedback"
        )
        db_session.add(feedback1)
        db_session.commit()
        
        # Attempt to create second feedback (should fail)
        feedback2 = Feedback(
            article_id=article_id,  # Same article
            rating=FeedbackRating.NO,
            notes="Second feedback"
        )
        db_session.add(feedback2)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        error_msg = str(exc_info.value).lower()
        assert "article_id" in error_msg
        assert "unique" in error_msg or "duplicate" in error_msg
    
    def test_feedback_cascade_delete_on_article_delete(self, db_session, test_source):
        """
        T034 [P] [US2]: Test Feedback → Article CASCADE on delete
        
        Given: Article has associated feedback
        When: Article is deleted via raw SQL (tests database CASCADE)
        Then: Feedback is automatically deleted (CASCADE)
        """
        from sqlalchemy import text
        
        # Create article via raw SQL to avoid ORM relationship issues
        article_id_result = db_session.execute(text("""
            INSERT INTO articles (
                external_url, headline, source_name, source_id,
                summary, amish_angle, filter_score, status
            ) VALUES (
                :url, :headline, :source_name, :source_id,
                :summary, :amish_angle, :filter_score, 'EMAILED'
            ) RETURNING id
        """), {
            "url": f"https://example.com/article/cascade-{uuid4()}",
            "headline": "Test Article",
            "source_name": "Test Source",
            "source_id": test_source.id,
            "summary": "Test summary",
            "amish_angle": "Test angle",
            "filter_score": 0.8
        })
        article_id = article_id_result.fetchone()[0]
        
        # Create feedback
        feedback_id_result = db_session.execute(text("""
            INSERT INTO feedback (article_id, rating)
            VALUES (:article_id, 'GOOD') RETURNING id
        """), {"article_id": article_id})
        feedback_id = feedback_id_result.fetchone()[0]
        
        db_session.commit()
        
        # Delete article (should cascade to feedback)
        db_session.execute(text("DELETE FROM articles WHERE id = :id"), {"id": article_id})
        db_session.commit()
        
        # Verify feedback was automatically deleted
        result = db_session.execute(
            text("SELECT COUNT(*) FROM feedback WHERE id = :id"),
            {"id": feedback_id}
        )
        assert result.scalar() == 0


class TestArticleDeepDiveRelationship:
    """Test Article ↔ DeepDive one-to-one relationship"""
    
    def test_one_deep_dive_per_article_enforced(self, db_session, test_article):
        """
        T055 [P] [US5]: Test Article → DeepDive one-to-one relationship
        
        Given: An article already has deep dive report
        When: Attempting to create second deep dive for same article
        Then: IntegrityError raised (unique constraint violation on article_id)
        """
        article_id = test_article.id
        
        # Create first deep dive
        deep_dive1 = DeepDive(
            article_id=article_id,
            headline_suggestion="First Suggestion",
            key_points=["Point 1", "Point 2"],
            additional_sources={"sources": []},
            full_report_text="First report",
            google_doc_id="doc123",
            google_doc_url="https://docs.google.com/doc123"
        )
        db_session.add(deep_dive1)
        db_session.commit()
        
        # Attempt to create second deep dive (should fail)
        deep_dive2 = DeepDive(
            article_id=article_id,  # Same article
            headline_suggestion="Second Suggestion",
            key_points=["Point 3", "Point 4"],
            additional_sources={"sources": []},
            full_report_text="Second report",
            google_doc_id="doc456",
            google_doc_url="https://docs.google.com/doc456"
        )
        db_session.add(deep_dive2)
        
        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        
        error_msg = str(exc_info.value).lower()
        assert "article_id" in error_msg
        assert "unique" in error_msg or "duplicate" in error_msg
    
    def test_deep_dive_cascade_delete_on_article_delete(self, db_session, test_source):
        """
        T056 [P] [US5]: Test DeepDive → Article CASCADE on delete
        
        Given: Article has associated deep dive
        When: Article is deleted via raw SQL (tests database CASCADE)
        Then: DeepDive is automatically deleted (CASCADE)
        """
        from sqlalchemy import text
        
        # Create article via raw SQL
        article_id_result = db_session.execute(text("""
            INSERT INTO articles (
                external_url, headline, source_name, source_id,
                summary, amish_angle, filter_score, status
            ) VALUES (
                :url, :headline, :source_name, :source_id,
                :summary, :amish_angle, :filter_score, 'GOOD'
            ) RETURNING id
        """), {
            "url": f"https://example.com/article/deepdive-cascade-{uuid4()}",
            "headline": "Test Article",
            "source_name": "Test Source",
            "source_id": test_source.id,
            "summary": "Test summary",
            "amish_angle": "Test angle",
            "filter_score": 0.9
        })
        article_id = article_id_result.fetchone()[0]
        
        # Create deep dive
        deep_dive_id_result = db_session.execute(text("""
            INSERT INTO deep_dives (
                article_id, headline_suggestion, key_points,
                additional_sources, full_report_text,
                google_doc_id, google_doc_url
            ) VALUES (
                :article_id, :headline, :key_points,
                :additional_sources, :report_text,
                :doc_id, :doc_url
            ) RETURNING id
        """), {
            "article_id": article_id,
            "headline": "Test Headline",
            "key_points": ["Point 1"],
            "additional_sources": '{"sources": []}',
            "report_text": "Test report",
            "doc_id": "doc_cascade_test",
            "doc_url": "https://docs.google.com/doc_cascade_test"
        })
        deep_dive_id = deep_dive_id_result.fetchone()[0]
        
        db_session.commit()
        
        # Delete article (should cascade to deep dive)
        db_session.execute(text("DELETE FROM articles WHERE id = :id"), {"id": article_id})
        db_session.commit()
        
        # Verify deep dive was automatically deleted
        result = db_session.execute(
            text("SELECT COUNT(*) FROM deep_dives WHERE id = :id"),
            {"id": deep_dive_id}
        )
        assert result.scalar() == 0


class TestArticleEmailBatchRelationship:
    """Test Article → EmailBatch foreign key (SET NULL on delete)"""
    
    def test_email_batch_delete_sets_article_batch_id_to_null(self, db_session, test_article):
        """
        T054 [P] [US5]: Test Article → EmailBatch SET NULL on delete
        
        Given: Article is linked to email batch
        When: EmailBatch is deleted
        Then: Article.email_batch_id set to NULL (not deleted)
        """
        # Create email batch
        email_batch = EmailBatch(
            sent_at=test_article.created_at,
            recipient_emails=["test@example.com"],
            article_count=1,
            subject_line="Test Subject",
            status=EmailStatus.SENT
        )
        db_session.add(email_batch)
        db_session.commit()
        email_batch_id = email_batch.id
        
        # Link article to batch
        test_article.email_batch_id = email_batch_id
        test_article.status = ArticleStatus.EMAILED
        db_session.commit()
        article_id = test_article.id
        
        # Delete email batch
        db_session.delete(email_batch)
        db_session.commit()
        
        # Verify article still exists with email_batch_id = NULL
        article_check = db_session.query(Article).filter_by(id=article_id).first()
        assert article_check is not None
        assert article_check.email_batch_id is None

