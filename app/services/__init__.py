"""
Article Discovery Services

This package contains services for the daily article discovery pipeline:
- rss_fetcher: Fetch articles from RSS/Atom feeds
- exa_searcher: Search articles via Exa API
- url_normalizer: Normalize URLs for deduplication
- claude_filter: Filter articles via Claude Haiku
- discovery: Orchestrate the complete discovery workflow
"""

from app.services.rss_fetcher import fetch_rss_feed, fetch_all_rss_sources
from app.services.exa_searcher import search_articles, search_all_queries
from app.services.url_normalizer import normalize_url, deduplicate_articles
from app.services.claude_filter import filter_articles, filter_all_articles
from app.services.discovery import run_discovery_job

__all__ = [
    'fetch_rss_feed',
    'fetch_all_rss_sources',
    'search_articles',
    'search_all_queries',
    'normalize_url',
    'deduplicate_articles',
    'filter_articles',
    'filter_all_articles',
    'run_discovery_job',
]

