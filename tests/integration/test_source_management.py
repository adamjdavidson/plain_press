"""
Integration tests for RSS Source Management feature.

Tests the /admin/sources routes for:
- Listing sources
- Adding new sources
- Pausing/resuming sources
- Deleting sources
"""

import pytest
from uuid import uuid4

from app.database import SessionLocal
from app.models import Source, SourceType, Article, ArticleStatus


@pytest.fixture
def test_source(test_session):
    """Create a test RSS source."""
    source = Source(
        name="Test Feed",
        type=SourceType.RSS,
        url="https://example.com/test-feed.xml",
        is_active=True,
        trust_score=0.5,
        notes="Test source for integration tests",
    )
    test_session.add(source)
    test_session.commit()
    test_session.refresh(source)
    return source


@pytest.fixture
def paused_source(test_session):
    """Create a paused RSS source."""
    source = Source(
        name="Paused Feed",
        type=SourceType.RSS,
        url="https://example.com/paused-feed.xml",
        is_active=False,
        trust_score=0.5,
    )
    test_session.add(source)
    test_session.commit()
    test_session.refresh(source)
    return source


class TestListSources:
    """Tests for GET /admin/sources"""
    
    def test_list_sources_empty(self, client, test_session):
        """Should show empty state when no RSS sources exist."""
        # Remove any existing RSS sources
        test_session.query(Source).filter(Source.type == SourceType.RSS).delete()
        test_session.commit()
        
        response = client.get('/admin/sources')
        assert response.status_code == 200
        assert b'No RSS feeds found' in response.data
    
    def test_list_sources_with_data(self, client, test_source):
        """Should display RSS sources in table."""
        response = client.get('/admin/sources')
        assert response.status_code == 200
        assert b'Test Feed' in response.data
        assert b'example.com/test-feed.xml' in response.data
    
    def test_list_sources_filter_active(self, client, test_source, paused_source):
        """Should filter to show only active sources."""
        response = client.get('/admin/sources?status=active')
        assert response.status_code == 200
        assert b'Test Feed' in response.data
        assert b'Paused Feed' not in response.data
    
    def test_list_sources_filter_paused(self, client, test_source, paused_source):
        """Should filter to show only paused sources."""
        response = client.get('/admin/sources?status=paused')
        assert response.status_code == 200
        assert b'Test Feed' not in response.data
        assert b'Paused Feed' in response.data
    
    def test_list_sources_sort_by_name(self, client, test_source, paused_source):
        """Should sort sources by name."""
        response = client.get('/admin/sources?sort=name')
        assert response.status_code == 200
        # Paused Feed comes before Test Feed alphabetically
        data = response.data.decode()
        paused_pos = data.find('Paused Feed')
        test_pos = data.find('Test Feed')
        assert paused_pos < test_pos


class TestAddSource:
    """Tests for POST /admin/sources"""
    
    def test_add_source_missing_name(self, client):
        """Should reject when name is missing."""
        response = client.post('/admin/sources', data={
            'url': 'https://example.com/feed.xml',
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Feed name is required' in response.data
    
    def test_add_source_missing_url(self, client):
        """Should reject when URL is missing."""
        response = client.post('/admin/sources', data={
            'name': 'New Feed',
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Feed URL is required' in response.data
    
    def test_add_source_duplicate_name(self, client, test_source):
        """Should reject duplicate source names."""
        response = client.post('/admin/sources', data={
            'name': 'Test Feed',  # Same as test_source
            'url': 'https://different.com/feed.xml',
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'already exists' in response.data
    
    def test_add_source_duplicate_url(self, client, test_source):
        """Should reject duplicate URLs."""
        response = client.post('/admin/sources', data={
            'name': 'Different Name',
            'url': 'https://example.com/test-feed.xml',  # Same as test_source
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'already exists' in response.data


class TestPauseSource:
    """Tests for POST /admin/sources/<id>/pause"""
    
    def test_pause_active_source(self, client, test_source, test_session):
        """Should pause an active source."""
        response = client.post(f'/admin/sources/{test_source.id}/pause')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['is_active'] is False
        
        # Verify in database
        test_session.refresh(test_source)
        assert test_source.is_active is False
    
    def test_pause_nonexistent_source(self, client):
        """Should return 404 for nonexistent source."""
        fake_id = uuid4()
        response = client.post(f'/admin/sources/{fake_id}/pause')
        assert response.status_code == 404


class TestResumeSource:
    """Tests for POST /admin/sources/<id>/resume"""
    
    def test_resume_paused_source(self, client, paused_source, test_session):
        """Should resume a paused source."""
        response = client.post(f'/admin/sources/{paused_source.id}/resume')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['is_active'] is True
        
        # Verify in database
        test_session.refresh(paused_source)
        assert paused_source.is_active is True
    
    def test_resume_nonexistent_source(self, client):
        """Should return 404 for nonexistent source."""
        fake_id = uuid4()
        response = client.post(f'/admin/sources/{fake_id}/resume')
        assert response.status_code == 404


class TestDeleteSource:
    """Tests for POST /admin/sources/<id>/delete"""
    
    def test_delete_source_no_articles(self, client, test_source, test_session):
        """Should delete source with no articles."""
        source_id = test_source.id
        response = client.post(f'/admin/sources/{source_id}/delete')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        
        # Verify deleted
        deleted = test_session.query(Source).filter(Source.id == source_id).first()
        assert deleted is None
    
    def test_delete_source_with_articles(self, client, test_source, test_session):
        """Should reject deletion if source has articles."""
        # Create an article linked to this source
        article = Article(
            external_url="https://example.com/article",
            headline="Test Article",
            source_name=test_source.name,
            source_id=test_source.id,
            summary="Test summary",
            amish_angle="Test angle",
            filter_score=0.5,
            status=ArticleStatus.PENDING,
        )
        test_session.add(article)
        test_session.commit()
        
        response = client.post(f'/admin/sources/{test_source.id}/delete')
        assert response.status_code == 400
        data = response.get_json()
        assert 'existing articles' in data['error']
        
        # Clean up
        test_session.delete(article)
        test_session.commit()
    
    def test_delete_nonexistent_source(self, client):
        """Should return 404 for nonexistent source."""
        fake_id = uuid4()
        response = client.post(f'/admin/sources/{fake_id}/delete')
        assert response.status_code == 404

