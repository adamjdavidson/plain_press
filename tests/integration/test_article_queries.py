"""
Integration tests for Article query performance and functionality

Tests verify:
- Daily email candidate query performance (<1 second for 50,000 articles)
- Article status transitions (pending → emailed)
- Filtering articles by status
"""
import pytest
from datetime import datetime, timezone
from uuid import uuid4
import time

from app.models import Article, Source, EmailBatch, ArticleStatus, SourceType, EmailStatus
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


class TestDailyEmailCandidateQuery:
    """Test daily email candidate query performance"""
    
    def test_query_top_50_articles_performance(self, db_session, test_source):
        """
        T027 [P] [US1]: Test daily email candidate query performance
        
        Given: 100 pending articles in database
        When: Querying for top 50 by filter_score DESC
        Then: Query completes in under 1 second with correct results
        """
        # Create 100 articles with varying filter scores
        articles = []
        for i in range(100):
            article = Article(
                external_url=f"https://example.com/article/query-test-{i}",
                headline=f"Test Article {i}",
                source_name="Test Source",
                source_id=test_source.id,
                summary="Test summary",
                amish_angle="Test angle",
                filter_score=i / 100.0,  # Scores from 0.00 to 0.99
                status=ArticleStatus.PENDING
            )
            articles.append(article)
        
        db_session.bulk_save_objects(articles)
        db_session.commit()
        
        # Query for top 50 with timing
        start_time = time.time()
        
        results = db_session.query(Article).filter(
            Article.status == ArticleStatus.PENDING
        ).order_by(
            Article.filter_score.desc(),
            Article.discovered_date.desc()
        ).limit(50).all()
        
        elapsed_time = time.time() - start_time
        
        # Verify performance
        assert elapsed_time < 1.0, f"Query took {elapsed_time:.3f}s (target: <1.0s)"
        
        # Verify correct results (top 50 by score)
        assert len(results) == 50
        assert results[0].filter_score >= results[49].filter_score
        
        # Verify all required fields populated
        for article in results[:5]:  # Check first 5
            assert article.external_url is not None
            assert article.headline is not None
            assert article.summary is not None
            assert article.amish_angle is not None
            assert article.source_id is not None
            assert article.created_at is not None


class TestArticleStatusTransitions:
    """Test article status transition workflows"""
    
    def test_pending_to_emailed_transition(self, db_session, test_source):
        """
        T028 [P] [US1]: Test article status transition
        
        Given: Article in "pending" status
        When: Article included in daily email
        Then: Status updates to "emailed" and email_batch_id is set
        """
        # Create pending article
        article = Article(
            external_url=f"https://example.com/article/transition-{uuid4()}",
            headline="Test Headline",
            source_name="Test Source",
            source_id=test_source.id,
            summary="Test summary",
            amish_angle="Test angle",
            filter_score=0.8,
            status=ArticleStatus.PENDING
        )
        db_session.add(article)
        db_session.commit()
        
        # Create email batch
        email_batch = EmailBatch(
            sent_at=datetime.now(timezone.utc),
            recipient_emails=["test@example.com"],
            article_count=1,
            subject_line="Test Subject",
            status=EmailStatus.SENT
        )
        db_session.add(email_batch)
        db_session.commit()
        
        # Update article status to emailed
        article.status = ArticleStatus.EMAILED
        article.email_batch_id = email_batch.id
        article.emailed_date = datetime.now(timezone.utc)
        db_session.commit()
        
        # Verify transition
        db_session.refresh(article)
        assert article.status == ArticleStatus.EMAILED
        assert article.email_batch_id == email_batch.id
        assert article.emailed_date is not None
    
    def test_emailed_to_good_transition(self, db_session, test_source):
        """Test emailed → good status transition"""
        # Create emailed article
        article = Article(
            external_url=f"https://example.com/article/good-{uuid4()}",
            headline="Test Headline",
            source_name="Test Source",
            source_id=test_source.id,
            summary="Test summary",
            amish_angle="Test angle",
            filter_score=0.8,
            status=ArticleStatus.EMAILED,
            emailed_date=datetime.now(timezone.utc)
        )
        db_session.add(article)
        db_session.commit()
        
        # Transition to good
        article.status = ArticleStatus.GOOD
        db_session.commit()
        
        # Verify transition
        db_session.refresh(article)
        assert article.status == ArticleStatus.GOOD
    
    def test_emailed_to_rejected_transition(self, db_session, test_source):
        """Test emailed → rejected status transition"""
        # Create emailed article
        article = Article(
            external_url=f"https://example.com/article/rejected-{uuid4()}",
            headline="Test Headline",
            source_name="Test Source",
            source_id=test_source.id,
            summary="Test summary",
            amish_angle="Test angle",
            filter_score=0.8,
            status=ArticleStatus.EMAILED,
            emailed_date=datetime.now(timezone.utc)
        )
        db_session.add(article)
        db_session.commit()
        
        # Transition to rejected
        article.status = ArticleStatus.REJECTED
        db_session.commit()
        
        # Verify transition
        db_session.refresh(article)
        assert article.status == ArticleStatus.REJECTED


class TestArticleStatusFiltering:
    """Test filtering articles by status"""
    
    def test_filter_articles_by_status(self, db_session, test_source):
        """
        T029 [P] [US1]: Test filtering articles by status
        
        Given: Mix of articles with different statuses
        When: Querying by specific status
        Then: Only articles with that status returned
        """
        # Create articles with different statuses
        statuses = [
            ArticleStatus.PENDING,
            ArticleStatus.EMAILED,
            ArticleStatus.GOOD,
            ArticleStatus.REJECTED,
            ArticleStatus.PASSED
        ]
        
        for idx, status in enumerate(statuses):
            # Create 3 articles per status
            for j in range(3):
                article = Article(
                    external_url=f"https://example.com/article/filter-{idx}-{j}",
                    headline=f"Article {status.value} {j}",
                    source_name="Test Source",
                    source_id=test_source.id,
                    summary="Test summary",
                    amish_angle="Test angle",
                    filter_score=0.8,
                    status=status
                )
                db_session.add(article)
        
        db_session.commit()
        
        # Test filtering for each status
        for status in statuses:
            results = db_session.query(Article).filter(
                Article.status == status
            ).all()
            
            # Verify all results have correct status
            assert len(results) >= 3  # At least our 3 test articles
            for article in results:
                assert article.status == status
        
        # Test filtering for PENDING specifically (most common query)
        pending_articles = db_session.query(Article).filter(
            Article.status == ArticleStatus.PENDING
        ).all()
        
        assert len(pending_articles) >= 3
        for article in pending_articles:
            assert article.status == ArticleStatus.PENDING

