"""
Integration tests for Feedback Flow

Tests the complete flow from email click to feedback recording.
"""

import pytest
from datetime import datetime, timezone

from app import create_app
from app.database import SessionLocal
from app.models import Article, ArticleStatus, Feedback, FeedbackRating, Source


@pytest.fixture
def client():
    """Create test client."""
    app = create_app({'TESTING': True})
    with app.test_client() as client:
        yield client


@pytest.fixture
def test_article(db_session):
    """Create a test article for feedback tests."""
    from app.models import SourceType
    
    source = Source(
        name=f"Test Source Feedback {datetime.now().timestamp()}",
        type=SourceType.RSS,
        url="https://example.com/feed.xml",
    )
    db_session.add(source)
    db_session.flush()
    
    article = Article(
        headline="Test Article for Feedback",
        external_url=f"https://example.com/feedback-test-{datetime.now().timestamp()}",
        source_id=source.id,
        source_name="Test Source",
        summary="This is a test summary",
        amish_angle="Relevant to plain community values",
        filter_score=0.85,
        status=ArticleStatus.EMAILED,
    )
    db_session.add(article)
    db_session.commit()
    
    return article


class TestHealthCheck:
    """Tests for health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check returns healthy status."""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert 'timestamp' in data


class TestGoodFeedback:
    """Tests for Good feedback button."""
    
    def test_good_feedback_success(self, client, test_article, db_session):
        """Test clicking Good button records feedback."""
        response = client.get(f'/feedback/{test_article.id}/good')
        
        assert response.status_code == 200
        assert b"Marked as Good" in response.data
        
        # Verify feedback was recorded
        feedback = db_session.query(Feedback).filter(
            Feedback.article_id == test_article.id
        ).first()
        
        assert feedback is not None
        assert feedback.rating == FeedbackRating.GOOD
        
        # Verify article status updated
        db_session.refresh(test_article)
        assert test_article.status == ArticleStatus.GOOD
    
    def test_good_feedback_duplicate(self, client, test_article, db_session):
        """Test duplicate Good click shows already recorded."""
        # First click
        client.get(f'/feedback/{test_article.id}/good')
        
        # Second click
        response = client.get(f'/feedback/{test_article.id}/good')
        
        assert response.status_code == 200
        assert b"already recorded" in response.data.lower()
        
        # Should only have one feedback record
        count = db_session.query(Feedback).filter(
            Feedback.article_id == test_article.id
        ).count()
        
        assert count == 1


class TestNoFeedback:
    """Tests for No feedback button."""
    
    def test_no_feedback_success(self, client, test_article, db_session):
        """Test clicking No button records feedback."""
        response = client.get(f'/feedback/{test_article.id}/no')
        
        assert response.status_code == 200
        assert b"Marked as No" in response.data
        
        # Verify feedback was recorded
        feedback = db_session.query(Feedback).filter(
            Feedback.article_id == test_article.id
        ).first()
        
        assert feedback is not None
        assert feedback.rating == FeedbackRating.NO
        
        # Verify article status updated
        db_session.refresh(test_article)
        assert test_article.status == ArticleStatus.REJECTED


class TestWhyNotFeedback:
    """Tests for Why Not feedback button."""
    
    def test_why_not_shows_form(self, client, test_article):
        """Test Why Not GET shows feedback form."""
        response = client.get(f'/feedback/{test_article.id}/why_not')
        
        assert response.status_code == 200
        assert b"Why doesn" in response.data
        assert test_article.headline.encode() in response.data
    
    def test_why_not_submit_with_notes(self, client, test_article, db_session):
        """Test Why Not POST with notes records feedback."""
        response = client.post(
            f'/feedback/{test_article.id}/why_not',
            data={'notes': 'Too focused on individual achievement'}
        )
        
        assert response.status_code == 200
        assert b"Thanks for the feedback" in response.data
        
        # Verify feedback was recorded
        feedback = db_session.query(Feedback).filter(
            Feedback.article_id == test_article.id
        ).first()
        
        assert feedback is not None
        assert feedback.rating == FeedbackRating.WHY_NOT
        assert feedback.notes == 'Too focused on individual achievement'
        
        # Verify article status updated
        db_session.refresh(test_article)
        assert test_article.status == ArticleStatus.REJECTED
    
    def test_why_not_submit_without_notes(self, client, test_article, db_session):
        """Test Why Not POST without notes still works."""
        response = client.post(
            f'/feedback/{test_article.id}/why_not',
            data={'notes': ''}
        )
        
        assert response.status_code == 200
        
        # Verify feedback was recorded with null notes
        feedback = db_session.query(Feedback).filter(
            Feedback.article_id == test_article.id
        ).first()
        
        assert feedback is not None
        assert feedback.notes is None


class TestInvalidArticle:
    """Tests for invalid article IDs."""
    
    def test_invalid_uuid_returns_404(self, client):
        """Test invalid UUID format returns 404."""
        response = client.get('/feedback/not-a-uuid/good')
        assert response.status_code == 404
    
    def test_nonexistent_article_returns_404(self, client):
        """Test nonexistent article UUID returns 404."""
        fake_uuid = '00000000-0000-0000-0000-000000000000'
        response = client.get(f'/feedback/{fake_uuid}/good')
        assert response.status_code == 404


class TestSourceMetrics:
    """Tests for source metrics updates on feedback."""
    
    def test_good_feedback_increments_approved(self, client, test_article, db_session):
        """Test Good feedback increments source approved count."""
        # Get initial source metrics
        source = db_session.query(Source).filter(Source.id == test_article.source_id).first()
        initial_approved = source.total_approved
        
        # Click Good
        client.get(f'/feedback/{test_article.id}/good')
        
        # Verify source metrics updated
        db_session.refresh(source)
        assert source.total_approved == initial_approved + 1
    
    def test_no_feedback_increments_rejected(self, client, test_article, db_session):
        """Test No feedback increments source rejected count."""
        # Get initial source metrics
        source = db_session.query(Source).filter(Source.id == test_article.source_id).first()
        initial_rejected = source.total_rejected
        
        # Click No
        client.get(f'/feedback/{test_article.id}/no')
        
        # Verify source metrics updated
        db_session.refresh(source)
        assert source.total_rejected == initial_rejected + 1

