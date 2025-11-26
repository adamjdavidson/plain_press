"""
Discovery Service - Job Orchestration

Orchestrates the complete daily article discovery workflow:
1. Fetch RSS feeds
2. Execute Exa searches
3. Deduplicate URLs
4. Filter through Claude Haiku
5. Store candidates
6. Update metrics
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert

from app.database import SessionLocal
from app.models import Article, ArticleStatus, Source
from app.services.rss_fetcher import fetch_all_rss_sources
from app.services.exa_searcher import search_all_queries
from app.services.url_normalizer import deduplicate_articles, normalize_url
from app.services.claude_filter import filter_all_articles

logger = logging.getLogger(__name__)


def run_discovery_job() -> dict:
    """
    Run the complete daily article discovery job.
    
    Returns:
        Stats dict with job results
    """
    start_time = datetime.now(timezone.utc)
    logger.info(json.dumps({
        "event": "job_start",
        "timestamp": start_time.isoformat(),
    }))
    
    stats = {
        'start_time': start_time.isoformat(),
        'rss_articles': 0,
        'exa_articles': 0,
        'total_discovered': 0,
        'duplicates_removed': 0,
        'total_filtered': 0,
        'total_kept': 0,
        'total_stored': 0,
        'rss_sources_succeeded': 0,
        'rss_sources_failed': 0,
        'exa_queries_succeeded': 0,
        'exa_queries_failed': 0,
        'cost_estimate': 0.0,
        'errors': [],
    }
    
    try:
        # Step 1: Fetch RSS feeds
        logger.info("Step 1: Fetching RSS feeds...")
        try:
            rss_articles, rss_stats = fetch_all_rss_sources()
            stats['rss_articles'] = rss_stats['articles_total']
            stats['rss_sources_succeeded'] = rss_stats['sources_succeeded']
            stats['rss_sources_failed'] = rss_stats['sources_failed']
        except Exception as e:
            logger.error(f"RSS fetch failed: {e}")
            stats['errors'].append(f"RSS fetch: {e}")
            rss_articles = []
        
        # Step 2: Execute Exa searches
        logger.info("Step 2: Executing Exa searches...")
        try:
            exa_articles, exa_stats = search_all_queries()
            stats['exa_articles'] = exa_stats['articles_total']
            stats['exa_queries_succeeded'] = exa_stats['queries_succeeded']
            stats['exa_queries_failed'] = exa_stats['queries_failed']
            stats['cost_estimate'] += exa_stats['cost_estimate']
        except Exception as e:
            logger.error(f"Exa search failed: {e}")
            stats['errors'].append(f"Exa search: {e}")
            exa_articles = []
        
        # Step 3: Combine and deduplicate
        logger.info("Step 3: Deduplicating articles...")
        all_articles = rss_articles + exa_articles
        stats['total_discovered'] = len(all_articles)
        
        unique_articles, duplicates = deduplicate_articles(all_articles)
        stats['duplicates_removed'] = duplicates
        
        if not unique_articles:
            logger.warning("No articles to filter after deduplication")
            stats['end_time'] = datetime.now(timezone.utc).isoformat()
            return stats
        
        # Step 4: Filter through Claude Haiku
        logger.info("Step 4: Filtering through Claude Haiku...")
        try:
            kept_articles, discarded_articles, filter_stats = filter_all_articles(unique_articles)
            stats['total_filtered'] = filter_stats['total_evaluated']
            stats['total_kept'] = filter_stats['total_kept']
            stats['cost_estimate'] += filter_stats['cost_estimate']
        except Exception as e:
            logger.error(f"Claude filtering failed: {e}")
            stats['errors'].append(f"Claude filter: {e}")
            kept_articles = []
        
        # Step 5: Store candidates
        logger.info("Step 5: Storing candidates...")
        if kept_articles:
            try:
                stored_count = store_candidates(kept_articles)
                stats['total_stored'] = stored_count
            except Exception as e:
                logger.error(f"Storage failed: {e}")
                stats['errors'].append(f"Storage: {e}")
        
        # Log volume warnings per constitution
        if stats['total_kept'] < 40:
            logger.warning(f"Low candidate volume: {stats['total_kept']} (target: 40-60)")
        elif stats['total_kept'] > 80:
            logger.warning(f"High candidate volume: {stats['total_kept']} (target: 40-60)")
        
    except Exception as e:
        logger.error(f"Discovery job failed: {e}")
        stats['errors'].append(f"Job failure: {e}")
    
    # Final stats
    end_time = datetime.now(timezone.utc)
    stats['end_time'] = end_time.isoformat()
    stats['duration_seconds'] = (end_time - start_time).total_seconds()
    
    logger.info(json.dumps({
        "event": "job_complete",
        **stats
    }))
    
    return stats


def store_candidates(articles: list[dict]) -> int:
    """
    Store filtered candidate articles in database.
    
    Uses INSERT ... ON CONFLICT DO NOTHING to handle any remaining duplicates.
    
    Args:
        articles: List of article dicts with filter results
        
    Returns:
        Number of articles actually stored
    """
    session = SessionLocal()
    stored_count = 0
    
    try:
        for article in articles:
            # Normalize URL for storage
            normalized_url = article.get('normalized_url') or normalize_url(article.get('url', ''))
            
            # Skip if no URL
            if not normalized_url:
                continue
            
            # Build article record
            article_data = {
                'external_url': normalized_url,
                'headline': article.get('headline', '')[:500],
                'source_name': article.get('source_name', 'Unknown'),
                'published_date': article.get('published_date'),
                'summary': article.get('summary', '')[:2000],
                'amish_angle': article.get('amish_angle', '')[:1000],
                'filter_score': article.get('filter_score', 0.0),
                'filter_notes': article.get('filter_notes', ''),
                'raw_content': article.get('content', '')[:10000],
                'status': ArticleStatus.PENDING,
                'source_id': article.get('source_id'),
            }
            
            # Use upsert to handle duplicates
            stmt = insert(Article).values(**article_data)
            stmt = stmt.on_conflict_do_nothing(index_elements=['external_url'])
            
            result = session.execute(stmt)
            if result.rowcount > 0:
                stored_count += 1
        
        session.commit()
        logger.info(f"Stored {stored_count}/{len(articles)} candidate articles")
        
    except Exception as e:
        logger.error(f"Error storing candidates: {e}")
        session.rollback()
        raise
    finally:
        session.close()
    
    return stored_count

