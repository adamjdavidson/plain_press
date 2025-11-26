"""
Contract tests for Email Service

Tests that SendGrid integration works correctly with mocked responses.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from app.services.email import (
    send_email,
    render_email_html,
    create_email_batch,
    update_articles_to_emailed,
    get_template_env,
)
from app.models import Article, ArticleStatus, EmailBatch, EmailStatus, Source


class TestRenderEmail:
    """Tests for email template rendering."""
    
    def test_render_email_with_articles(self, db_session):
        """Test email renders correctly with articles."""
        from app.models import SourceType
        
        # Create test source
        source = Source(
            name="Test Source Email Render",
            type=SourceType.RSS,
            url="https://example.com/feed.xml",
        )
        db_session.add(source)
        db_session.flush()
        
        import uuid
        
        # Create test articles
        articles = []
        for i in range(3):
            article = Article(
                headline=f"Test Article {i}",
                external_url=f"https://example.com/article-render-{uuid.uuid4()}",
                source_id=source.id,
                source_name="Test Source",
                filter_score=0.85 - (i * 0.1),
                summary=f"Summary for article {i}",
                amish_angle=f"Amish angle for article {i}",
                status=ArticleStatus.PENDING,
            )
            db_session.add(article)
            articles.append(article)
        
        db_session.commit()
        
        # Render email
        with patch.dict('os.environ', {'FEEDBACK_URL_BASE': 'http://test.local'}):
            html = render_email_html(articles, "November 26, 2024")
        
        # Verify content
        assert "Plain News Candidates" in html
        assert "November 26, 2024" in html
        assert "3 articles for review" in html
        
        for article in articles:
            assert article.headline in html
            assert article.summary in html
            assert article.amish_angle in html
            assert f"http://test.local/feedback/{article.id}/good" in html
            assert f"http://test.local/feedback/{article.id}/no" in html
            assert f"http://test.local/feedback/{article.id}/why_not" in html
    
    def test_render_email_empty_articles(self, db_session):
        """Test email renders with no articles."""
        html = render_email_html([], "November 26, 2024")
        
        assert "Plain News Candidates" in html
        assert "0 articles" in html


class TestSendEmail:
    """Tests for SendGrid email sending."""
    
    @patch('app.services.email.SendGridAPIClient')
    def test_send_email_success(self, mock_client_class):
        """Test successful email send."""
        # Mock successful response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_client.send.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        with patch.dict('os.environ', {
            'SENDGRID_API_KEY': 'test-key',
            'SENDGRID_FROM_EMAIL': 'from@test.com'
        }):
            success, error = send_email(
                to_email='to@test.com',
                subject='Test Subject',
                html_content='<p>Test content</p>'
            )
        
        assert success is True
        assert error is None
        mock_client.send.assert_called_once()
    
    @patch('app.services.email.SendGridAPIClient')
    def test_send_email_client_error_no_retry(self, mock_client_class):
        """Test that 4xx errors don't trigger retry."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.body = "Bad request"
        mock_client.send.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        with patch.dict('os.environ', {
            'SENDGRID_API_KEY': 'test-key',
            'SENDGRID_FROM_EMAIL': 'from@test.com'
        }):
            success, error = send_email(
                to_email='to@test.com',
                subject='Test Subject',
                html_content='<p>Test content</p>'
            )
        
        assert success is False
        assert "client error" in error.lower()
        # Should only call once (no retry for 4xx)
        assert mock_client.send.call_count == 1
    
    @patch('app.services.email.SendGridAPIClient')
    @patch('app.services.email.RETRY_DELAYS', [0.01, 0.01, 0.01])
    def test_send_email_server_error_retries(self, mock_client_class):
        """Test that 5xx errors trigger retry."""
        mock_client = MagicMock()
        
        # First two calls fail, third succeeds
        mock_fail = MagicMock()
        mock_fail.status_code = 500
        
        mock_success = MagicMock()
        mock_success.status_code = 202
        
        mock_client.send.side_effect = [mock_fail, mock_fail, mock_success]
        mock_client_class.return_value = mock_client
        
        with patch.dict('os.environ', {
            'SENDGRID_API_KEY': 'test-key',
            'SENDGRID_FROM_EMAIL': 'from@test.com'
        }):
            success, error = send_email(
                to_email='to@test.com',
                subject='Test Subject',
                html_content='<p>Test content</p>'
            )
        
        assert success is True
        assert error is None
        assert mock_client.send.call_count == 3


class TestEmailBatch:
    """Tests for EmailBatch record creation."""
    
    def test_create_email_batch_sent(self, db_session):
        """Test creating a sent email batch record."""
        batch = create_email_batch(
            session=db_session,
            recipient_email='test@example.com',
            article_count=10,
            subject='Test Subject',
            status=EmailStatus.SENT,
        )
        
        db_session.commit()
        
        assert batch.id is not None
        assert batch.recipient_emails == ['test@example.com']
        assert batch.article_count == 10
        assert batch.subject_line == 'Test Subject'
        assert batch.status == EmailStatus.SENT
        assert batch.error_message is None
    
    def test_create_email_batch_failed(self, db_session):
        """Test creating a failed email batch record."""
        batch = create_email_batch(
            session=db_session,
            recipient_email='test@example.com',
            article_count=10,
            subject='Test Subject',
            status=EmailStatus.FAILED,
            error_message='Connection timeout',
        )
        
        db_session.commit()
        
        assert batch.status == EmailStatus.FAILED
        assert batch.error_message == 'Connection timeout'


class TestUpdateArticles:
    """Tests for article status updates after email."""
    
    def test_update_articles_to_emailed(self, db_session):
        """Test updating article status after successful email."""
        from app.models import SourceType
        
        # Create test source
        source = Source(
            name="Test Source Update Email",
            type=SourceType.RSS,
            url="https://example.com/feed.xml",
        )
        db_session.add(source)
        db_session.flush()
        
        # Create email batch
        batch = EmailBatch(
            sent_at=datetime.now(timezone.utc),
            recipient_emails=['test@example.com'],
            article_count=3,
            subject_line='Test',
            status=EmailStatus.SENT,
        )
        db_session.add(batch)
        db_session.flush()
        
        import uuid
        
        # Create test articles
        articles = []
        for i in range(3):
            article = Article(
                headline=f"Test Article {i}",
                external_url=f"https://example.com/article-update-{uuid.uuid4()}",
                source_id=source.id,
                source_name="Test Source",
                summary=f"Summary for article {i}",
                amish_angle=f"Amish angle for article {i}",
                filter_score=0.8,
                status=ArticleStatus.PENDING,
            )
            db_session.add(article)
            articles.append(article)
        
        db_session.flush()
        
        # Update articles
        count = update_articles_to_emailed(db_session, articles, batch.id)
        db_session.commit()
        
        assert count == 3
        
        for article in articles:
            db_session.refresh(article)
            assert article.status == ArticleStatus.EMAILED
            assert article.email_batch_id == batch.id
            assert article.emailed_date is not None

