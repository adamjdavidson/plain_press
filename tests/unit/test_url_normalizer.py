"""
Unit tests for URL normalization.

Tests all normalization rules: tracking params, www, https, trailing slash, edge cases.
"""

import pytest
from app.services.url_normalizer import normalize_url, deduplicate_articles


class TestNormalizeUrl:
    """Tests for normalize_url function."""
    
    def test_basic_url_unchanged(self):
        """Basic URL should normalize to https without www."""
        url = "https://example.com/article/123"
        expected = "https://example.com/article/123"
        assert normalize_url(url) == expected
    
    def test_http_converted_to_https(self):
        """HTTP URLs should be converted to HTTPS."""
        url = "http://example.com/article"
        expected = "https://example.com/article"
        assert normalize_url(url) == expected
    
    def test_www_removed(self):
        """www prefix should be removed."""
        url = "https://www.example.com/article"
        expected = "https://example.com/article"
        assert normalize_url(url) == expected
    
    def test_trailing_slash_removed(self):
        """Trailing slashes should be removed."""
        url = "https://example.com/article/"
        expected = "https://example.com/article"
        assert normalize_url(url) == expected
    
    def test_multiple_trailing_slashes_removed(self):
        """Multiple trailing slashes should be removed."""
        url = "https://example.com/article///"
        expected = "https://example.com/article"
        assert normalize_url(url) == expected
    
    def test_lowercase_conversion(self):
        """URLs should be lowercased."""
        url = "HTTPS://EXAMPLE.COM/Article"
        expected = "https://example.com/article"
        assert normalize_url(url) == expected
    
    def test_utm_params_removed(self):
        """UTM tracking parameters should be removed."""
        url = "https://example.com/article?utm_source=twitter&utm_medium=social"
        expected = "https://example.com/article"
        assert normalize_url(url) == expected
    
    def test_fbclid_removed(self):
        """Facebook click ID should be removed."""
        url = "https://example.com/article?fbclid=abc123"
        expected = "https://example.com/article"
        assert normalize_url(url) == expected
    
    def test_article_id_preserved(self):
        """Article ID parameters should be preserved."""
        url = "https://example.com/story?id=12345"
        expected = "https://example.com/story?id=12345"
        assert normalize_url(url) == expected
    
    def test_combined_normalization(self):
        """Multiple normalization rules should apply together."""
        url = "http://www.EXAMPLE.com/article/?utm_source=rss&id=123&fbclid=xyz"
        expected = "https://example.com/article?id=123"
        assert normalize_url(url) == expected
    
    def test_fragment_removed(self):
        """URL fragments should be removed."""
        url = "https://example.com/article#section1"
        expected = "https://example.com/article"
        assert normalize_url(url) == expected
    
    def test_empty_url_returns_empty(self):
        """Empty URL should return empty string."""
        assert normalize_url("") == ""
        assert normalize_url(None) == ""
    
    def test_root_url(self):
        """Root URL should normalize correctly."""
        url = "https://example.com/"
        expected = "https://example.com"
        assert normalize_url(url) == expected


class TestDeduplicateArticles:
    """Tests for deduplicate_articles function."""
    
    def test_no_duplicates(self):
        """Articles with unique URLs should all be kept."""
        articles = [
            {"url": "https://example.com/article/1", "headline": "Article 1"},
            {"url": "https://example.com/article/2", "headline": "Article 2"},
            {"url": "https://example.com/article/3", "headline": "Article 3"},
        ]
        unique, count = deduplicate_articles(articles)
        assert len(unique) == 3
        assert count == 0
    
    def test_exact_duplicate_removed(self):
        """Exact duplicate URLs should be removed."""
        articles = [
            {"url": "https://example.com/article/1", "headline": "Article 1"},
            {"url": "https://example.com/article/1", "headline": "Duplicate"},
        ]
        unique, count = deduplicate_articles(articles)
        assert len(unique) == 1
        assert count == 1
        assert unique[0]["headline"] == "Article 1"  # First one kept
    
    def test_normalized_duplicate_removed(self):
        """URLs that normalize to same value should be deduplicated."""
        articles = [
            {"url": "https://example.com/article/1", "headline": "First"},
            {"url": "http://www.example.com/article/1/", "headline": "Duplicate"},
        ]
        unique, count = deduplicate_articles(articles)
        assert len(unique) == 1
        assert count == 1
    
    def test_tracking_params_cause_dedup(self):
        """Same article with different tracking params should deduplicate."""
        articles = [
            {"url": "https://example.com/article?utm_source=rss", "headline": "RSS"},
            {"url": "https://example.com/article?utm_source=twitter", "headline": "Twitter"},
        ]
        unique, count = deduplicate_articles(articles)
        assert len(unique) == 1
        assert count == 1
    
    def test_different_ids_not_deduplicated(self):
        """Different article IDs should not be deduplicated."""
        articles = [
            {"url": "https://example.com/story?id=123", "headline": "Story 123"},
            {"url": "https://example.com/story?id=124", "headline": "Story 124"},
        ]
        unique, count = deduplicate_articles(articles)
        assert len(unique) == 2
        assert count == 0
    
    def test_normalized_url_added_to_article(self):
        """Normalized URL should be added to article dict."""
        articles = [
            {"url": "http://www.example.com/article/", "headline": "Test"},
        ]
        unique, _ = deduplicate_articles(articles)
        assert unique[0]["normalized_url"] == "https://example.com/article"
    
    def test_empty_url_skipped(self):
        """Articles with empty URLs should be skipped."""
        articles = [
            {"url": "", "headline": "No URL"},
            {"url": "https://example.com/article", "headline": "Has URL"},
        ]
        unique, count = deduplicate_articles(articles)
        assert len(unique) == 1
        assert unique[0]["headline"] == "Has URL"

