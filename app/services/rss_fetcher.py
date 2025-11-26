"""
RSS Feed Fetcher Service

Fetches and parses RSS/Atom feeds using feedparser.
Handles errors gracefully, updates source metrics.
"""

import logging
import sys
import time
from datetime import datetime, timezone
from typing import Optional

import feedparser

from app.database import SessionLocal
from app.models import Source, SourceType

logger = logging.getLogger(__name__)


def _log_rss(msg: str):
    """Log RSS progress with immediate flush."""
    full_msg = f"RSS: {msg}"
    logger.info(full_msg)
    print(full_msg, file=sys.stdout, flush=True)

# Configuration
RSS_FETCH_TIMEOUT = 30  # seconds
RSS_FETCH_DELAY = 1.0   # seconds between fetches
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0  # seconds


def fetch_rss_feed(url: str, timeout: int = RSS_FETCH_TIMEOUT) -> list[dict]:
    """
    Fetch and parse a single RSS feed.

    Args:
        url: RSS feed URL
        timeout: Request timeout in seconds

    Returns:
        List of article dicts with keys: headline, url, published_date, content, source_url
    """
    articles = []
    short_url = url[:60] + "..." if len(url) > 60 else url

    for attempt in range(MAX_RETRIES):
        try:
            _log_rss(f"Fetching {short_url} (attempt {attempt + 1})...")
            fetch_start = time.time()
            # feedparser handles most edge cases gracefully
            result = feedparser.parse(url, request_headers={'User-Agent': 'AmishNewsFinder/1.0'})
            fetch_time = time.time() - fetch_start
            _log_rss(f"Fetched {short_url} in {fetch_time:.1f}s")
            
            # Helper to get value from dict or object
            def get_val(obj, key, default=None):
                if isinstance(obj, dict):
                    return obj.get(key, default)
                return getattr(obj, key, default)
            
            # Check HTTP status
            status = get_val(result, 'status', 200)
            if isinstance(status, int) and status >= 400:
                logger.warning(f"RSS fetch failed for {url}: HTTP {status}")
                if status >= 500 and attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_BASE_DELAY * (2 ** attempt))
                    continue
                return []
            
            # Check for parsing issues (bozo flag)
            bozo = get_val(result, 'bozo', False)
            if bozo:
                bozo_exc = get_val(result, 'bozo_exception')
                logger.warning(f"RSS parsing issue for {url}: {bozo_exc}")
                # Continue anyway - feedparser often recovers partial data
            
            # Extract articles from entries
            entries = get_val(result, 'entries', [])
            for entry in entries:
                article = _parse_entry(entry, url)
                if article:
                    articles.append(article)
            
            logger.info(f"Fetched {len(articles)} articles from {url}")
            return articles
            
        except Exception as e:
            logger.error(f"RSS fetch error for {url} (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BASE_DELAY * (2 ** attempt))
            else:
                return []
    
    return articles


def _parse_entry(entry: dict, source_url: str) -> Optional[dict]:
    """
    Parse a feedparser entry into our article format.
    
    Args:
        entry: feedparser entry dict
        source_url: URL of the source feed
        
    Returns:
        Article dict or None if required fields missing
    """
    # Required fields
    headline = entry.get('title', '').strip()
    url = entry.get('link', '').strip()
    
    if not headline or not url:
        return None
    
    # Optional fields
    content = ''
    entry_content = entry.get('content')
    if entry_content and len(entry_content) > 0:
        content = entry_content[0].get('value', '')
    elif 'summary' in entry:
        content = entry.get('summary', '')
    elif 'description' in entry:
        content = entry.get('description', '')
    
    # Parse publication date
    published_date = None
    published_parsed = entry.get('published_parsed')
    updated_parsed = entry.get('updated_parsed')
    
    if published_parsed:
        try:
            published_date = datetime(*published_parsed[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass
    elif updated_parsed:
        try:
            published_date = datetime(*updated_parsed[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass
    
    return {
        'headline': headline,
        'url': url,
        'published_date': published_date,
        'content': content,
        'source_url': source_url,
    }


def fetch_all_rss_sources() -> tuple[list[dict], dict]:
    """
    Fetch articles from all active RSS sources.

    Returns:
        Tuple of (articles list, stats dict with source results)
    """
    _log_rss("Getting database session...")
    session = SessionLocal()
    _log_rss("Database session acquired")
    all_articles = []
    stats = {
        'sources_total': 0,
        'sources_succeeded': 0,
        'sources_failed': 0,
        'articles_total': 0,
    }

    try:
        # Query active RSS sources
        _log_rss("Querying active RSS sources from database...")
        sources = session.query(Source).filter(
            Source.type == SourceType.RSS,
            Source.is_active == True
        ).all()
        _log_rss(f"Found {len(sources)} active RSS sources")

        stats['sources_total'] = len(sources)
        logger.info(f"Fetching from {len(sources)} RSS sources")

        for idx, source in enumerate(sources):
            _log_rss(f"[{idx + 1}/{len(sources)}] Processing source '{source.name}'...")
            try:
                articles = fetch_rss_feed(source.url)
                
                # Add source metadata to each article
                for article in articles:
                    article['source_id'] = source.id
                    article['source_name'] = source.name
                
                all_articles.extend(articles)
                
                # Update source metrics
                source.last_fetched = datetime.now(timezone.utc)
                source.total_surfaced += len(articles)
                
                stats['sources_succeeded'] += 1
                stats['articles_total'] += len(articles)
                
                logger.info(f"Source '{source.name}': {len(articles)} articles")
                
                # Rate limiting between sources
                time.sleep(RSS_FETCH_DELAY)
                
            except Exception as e:
                logger.error(f"Failed to fetch source '{source.name}': {e}")
                stats['sources_failed'] += 1
        
        session.commit()
        
    except Exception as e:
        logger.error(f"Error in fetch_all_rss_sources: {e}")
        session.rollback()
        raise
    finally:
        session.close()
    
    logger.info(f"RSS fetch complete: {stats['articles_total']} articles from {stats['sources_succeeded']}/{stats['sources_total']} sources")
    return all_articles, stats

