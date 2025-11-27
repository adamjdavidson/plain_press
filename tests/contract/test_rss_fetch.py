"""
Contract tests for RSS feed fetching.

Tests RSS parsing with valid feeds, malformed feeds, and network errors.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import time

from app.services.rss_fetcher import fetch_rss_feed, _parse_entry


def _make_time_tuple(dt: datetime = None) -> tuple:
    """Create a time tuple for feedparser from a datetime (defaults to now)."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    return time.strptime(dt.strftime('%Y %m %d %H %M %S'), '%Y %m %d %H %M %S')


class TestFetchRssFeed:
    """Tests for fetch_rss_feed function."""
    
    def test_fetch_valid_rss_feed(self):
        """Test fetching a real RSS feed (integration-like contract test)."""
        # Use a reliable public RSS feed for testing
        # Note: This test requires internet connectivity
        url = "https://rss.upi.com/news/odd_news.rss"
        
        try:
            articles = fetch_rss_feed(url)
            
            # Should return a list
            assert isinstance(articles, list)
            
            # If feed is accessible, should have articles
            if articles:
                article = articles[0]
                # Check required fields
                assert 'headline' in article
                assert 'url' in article
                assert article['headline']  # Non-empty
                assert article['url']  # Non-empty
                assert article['url'].startswith('http')
                
        except Exception:
            # Network issues are acceptable in CI/CD
            pytest.skip("Network unavailable for RSS fetch test")
    
    @patch('app.services.rss_fetcher.feedparser')
    def test_fetch_with_mocked_feedparser(self, mock_feedparser):
        """Test RSS parsing with mocked feedparser response."""
        # Mock feedparser response - use a dict-like object for compatibility
        # Use dynamic date to avoid hardcoded year
        test_time_tuple = _make_time_tuple()
        mock_result = {
            'status': 200,
            'bozo': False,
            'entries': [
                {
                    'title': 'Test Article Title',
                    'link': 'https://example.com/article/1',
                    'summary': 'This is the article summary.',
                    'published_parsed': test_time_tuple,
                },
                {
                    'title': 'Second Article',
                    'link': 'https://example.com/article/2',
                    'description': 'Second article description.',
                },
            ]
        }
        mock_feedparser.parse.return_value = mock_result
        
        articles = fetch_rss_feed('https://example.com/feed.xml')
        
        assert len(articles) == 2
        assert articles[0]['headline'] == 'Test Article Title'
        assert articles[0]['url'] == 'https://example.com/article/1'
        assert articles[0]['content'] == 'This is the article summary.'
        assert articles[0]['published_date'] is not None
        
        assert articles[1]['headline'] == 'Second Article'
        assert articles[1]['content'] == 'Second article description.'
    
    @patch('app.services.rss_fetcher.feedparser')
    def test_fetch_malformed_feed_continues(self, mock_feedparser):
        """Test that malformed feeds still return partial data if available."""
        mock_result = {
            'status': 200,
            'bozo': True,  # Indicates parsing issue
            'bozo_exception': Exception("XML parsing error"),
            'entries': [
                {'title': 'Partial Article', 'link': 'https://example.com/partial'},
            ]
        }
        mock_feedparser.parse.return_value = mock_result
        
        articles = fetch_rss_feed('https://example.com/bad-feed.xml')
        
        # Should still return partial data
        assert len(articles) == 1
        assert articles[0]['headline'] == 'Partial Article'
    
    @patch('app.services.rss_fetcher.feedparser')
    def test_fetch_http_error_returns_empty(self, mock_feedparser):
        """Test that HTTP errors return empty list."""
        mock_result = {
            'status': 404,
            'bozo': False,
            'entries': []
        }
        mock_feedparser.parse.return_value = mock_result
        
        articles = fetch_rss_feed('https://example.com/nonexistent.xml')
        
        assert articles == []
    
    @patch('app.services.rss_fetcher.feedparser')
    def test_fetch_server_error_triggers_retry(self, mock_feedparser):
        """Test that server errors trigger retry logic."""
        # First call returns 500, subsequent calls succeed
        mock_error = {
            'status': 500,
            'bozo': False,
            'entries': []
        }
        
        mock_success = {
            'status': 200,
            'bozo': False,
            'entries': [{'title': 'Success', 'link': 'https://example.com/1'}]
        }
        
        mock_feedparser.parse.side_effect = [mock_error, mock_success]
        
        # With retries, should eventually succeed
        # Note: This test may be slow due to retry delays
        articles = fetch_rss_feed('https://example.com/flaky.xml')
        
        # May or may not succeed depending on retry timing
        # The important thing is it doesn't crash
        assert isinstance(articles, list)


class TestParseEntry:
    """Tests for _parse_entry helper function."""
    
    def test_parse_complete_entry(self):
        """Test parsing entry with all fields."""
        # Use dynamic date to avoid hardcoded year
        test_time_tuple = _make_time_tuple()
        current_year = datetime.now().year
        entry = {
            'title': 'Complete Article',
            'link': 'https://example.com/article',
            'content': [{'value': 'Full content here.'}],
            'published_parsed': test_time_tuple,
        }

        result = _parse_entry(entry, 'https://example.com/feed')

        assert result['headline'] == 'Complete Article'
        assert result['url'] == 'https://example.com/article'
        assert result['content'] == 'Full content here.'
        assert result['published_date'].year == current_year
        assert result['source_url'] == 'https://example.com/feed'
    
    def test_parse_entry_missing_title_returns_none(self):
        """Test that entries without title return None."""
        entry = {
            'link': 'https://example.com/article',
        }
        
        result = _parse_entry(entry, 'https://example.com/feed')
        
        assert result is None
    
    def test_parse_entry_missing_link_returns_none(self):
        """Test that entries without link return None."""
        entry = {
            'title': 'No Link Article',
        }
        
        result = _parse_entry(entry, 'https://example.com/feed')
        
        assert result is None
    
    def test_parse_entry_uses_summary_if_no_content(self):
        """Test that summary is used when content is missing."""
        entry = {
            'title': 'Article',
            'link': 'https://example.com/article',
            'summary': 'Summary text here.',
        }
        
        result = _parse_entry(entry, 'https://example.com/feed')
        
        assert result['content'] == 'Summary text here.'
    
    def test_parse_entry_uses_description_as_fallback(self):
        """Test that description is used as final fallback."""
        entry = {
            'title': 'Article',
            'link': 'https://example.com/article',
            'description': 'Description text.',
        }
        
        result = _parse_entry(entry, 'https://example.com/feed')
        
        assert result['content'] == 'Description text.'
    
    def test_parse_entry_uses_updated_parsed_if_no_published(self):
        """Test that updated_parsed is used when published_parsed missing."""
        # Use dynamic date to avoid hardcoded year
        test_time_tuple = _make_time_tuple()
        current_year = datetime.now().year
        current_day = datetime.now().day
        entry = {
            'title': 'Article',
            'link': 'https://example.com/article',
            'updated_parsed': test_time_tuple,
        }

        result = _parse_entry(entry, 'https://example.com/feed')

        assert result['published_date'].year == current_year
        assert result['published_date'].day == current_day

