"""
Exa Search Service

Executes AI-powered web searches via Exa API.
Handles rate limits with exponential backoff.
"""

import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

from exa_py import Exa

from app.database import SessionLocal
from app.models import Source, SourceType

logger = logging.getLogger(__name__)

# Configuration
EXA_NUM_RESULTS = 15
EXA_MAX_CHARACTERS = 2000
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0  # seconds
COST_PER_QUERY = 0.03   # USD estimate


def get_exa_client() -> Exa:
    """Get Exa client with API key from environment."""
    api_key = os.environ.get('EXA_API_KEY')
    if not api_key:
        raise ValueError("EXA_API_KEY environment variable not set")
    return Exa(api_key=api_key)


def search_articles(
    query: str,
    num_results: int = EXA_NUM_RESULTS,
    days_back: int = 30
) -> list[dict]:
    """
    Search for articles using Exa API.
    
    Args:
        query: Search query text
        num_results: Number of results to return
        days_back: Only include articles from last N days
        
    Returns:
        List of article dicts with keys: headline, url, published_date, content
    """
    client = get_exa_client()
    articles = []
    
    # Calculate date filter
    start_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime('%Y-%m-%d')
    
    for attempt in range(MAX_RETRIES):
        try:
            result = client.search_and_contents(
                query=query,
                num_results=num_results,
                type="neural",
                use_autoprompt=True,
                start_published_date=start_date,
                text={"max_characters": EXA_MAX_CHARACTERS}
            )
            
            # Parse results
            for item in result.results:
                article = _parse_exa_result(item)
                if article:
                    articles.append(article)
            
            # Log cost estimate
            logger.info(f"Exa search '{query[:50]}...': {len(articles)} results (~${COST_PER_QUERY:.2f})")
            return articles
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check for rate limit (429)
            if '429' in error_str or 'rate limit' in error_str:
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(f"Exa rate limit hit, waiting {delay}s (attempt {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(delay)
                    continue
            
            logger.error(f"Exa search error for '{query[:50]}...' (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BASE_DELAY * (2 ** attempt))
            else:
                return []
    
    return articles


def _parse_exa_result(item) -> Optional[dict]:
    """
    Parse an Exa result into our article format.
    
    Args:
        item: Exa result object
        
    Returns:
        Article dict or None if required fields missing
    """
    headline = getattr(item, 'title', '').strip()
    url = getattr(item, 'url', '').strip()
    
    if not headline or not url:
        return None
    
    content = getattr(item, 'text', '') or ''
    
    # Parse publication date
    published_date = None
    pub_date_str = getattr(item, 'published_date', None)
    if pub_date_str:
        try:
            # Exa returns ISO format dates
            published_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass
    
    return {
        'headline': headline,
        'url': url,
        'published_date': published_date,
        'content': content,
    }


def search_all_queries() -> tuple[list[dict], dict]:
    """
    Execute all active Exa search queries.
    
    Returns:
        Tuple of (articles list, stats dict with query results)
    """
    session = SessionLocal()
    all_articles = []
    stats = {
        'queries_total': 0,
        'queries_succeeded': 0,
        'queries_failed': 0,
        'articles_total': 0,
        'cost_estimate': 0.0,
    }
    
    try:
        # Query active search query sources
        sources = session.query(Source).filter(
            Source.type == SourceType.SEARCH_QUERY,
            Source.is_active == True
        ).all()
        
        stats['queries_total'] = len(sources)
        logger.info(f"Executing {len(sources)} Exa search queries")
        
        for source in sources:
            if not source.search_query:
                logger.warning(f"Source '{source.name}' has no search_query, skipping")
                continue
                
            try:
                articles = search_articles(source.search_query)
                
                # Add source metadata to each article
                for article in articles:
                    article['source_id'] = source.id
                    article['source_name'] = source.name
                
                all_articles.extend(articles)
                
                # Update source metrics
                source.last_fetched = datetime.now(timezone.utc)
                source.total_surfaced += len(articles)
                
                stats['queries_succeeded'] += 1
                stats['articles_total'] += len(articles)
                stats['cost_estimate'] += COST_PER_QUERY
                
                logger.info(f"Query '{source.name}': {len(articles)} articles")
                
            except Exception as e:
                logger.error(f"Failed to execute query '{source.name}': {e}")
                stats['queries_failed'] += 1
        
        session.commit()
        
    except Exception as e:
        logger.error(f"Error in search_all_queries: {e}")
        session.rollback()
        raise
    finally:
        session.close()
    
    logger.info(f"Exa search complete: {stats['articles_total']} articles from {stats['queries_succeeded']}/{stats['queries_total']} queries (~${stats['cost_estimate']:.2f})")
    return all_articles, stats

