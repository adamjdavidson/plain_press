"""
Discovery Service - Job Orchestration

Orchestrates the complete daily article discovery workflow:
1. Fetch RSS feeds
2. Execute Exa searches
3. Deduplicate URLs
4. Filter through Claude Sonnet 4.5 (structured outputs)
5. Store candidates
6. Update metrics
"""

import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert

logger = logging.getLogger(__name__)


def _log_progress(msg: str, start_time: float = None):
    """Log with timestamp and elapsed time, flush immediately."""
    elapsed = f"[{time.time() - start_time:.1f}s]" if start_time else ""
    full_msg = f"{elapsed} DISCOVERY: {msg}"
    logger.info(full_msg)
    # Also print directly to ensure Railway sees it
    print(full_msg, file=sys.stdout, flush=True)


# Delay imports to track where hangs occur
def _import_dependencies(start_time: float):
    """Import dependencies with progress logging."""
    global SessionLocal, Article, ArticleStatus, Source
    global fetch_all_rss_sources, search_all_queries
    global deduplicate_articles, normalize_url, filter_all_articles

    _log_progress("Importing database module...", start_time)
    from app.database import SessionLocal
    _log_progress("Database module imported", start_time)

    _log_progress("Importing models...", start_time)
    from app.models import Article, ArticleStatus, Source
    _log_progress("Models imported", start_time)

    _log_progress("Importing rss_fetcher...", start_time)
    from app.services.rss_fetcher import fetch_all_rss_sources
    _log_progress("rss_fetcher imported", start_time)

    _log_progress("Importing exa_searcher...", start_time)
    from app.services.exa_searcher import search_all_queries
    _log_progress("exa_searcher imported", start_time)

    _log_progress("Importing url_normalizer...", start_time)
    from app.services.url_normalizer import deduplicate_articles, normalize_url
    _log_progress("url_normalizer imported", start_time)

    _log_progress("Importing claude_filter...", start_time)
    from app.services.claude_filter import filter_all_articles
    _log_progress("claude_filter imported", start_time)


def run_discovery_job() -> dict:
    """
    Run the complete daily article discovery job.

    Returns:
        Stats dict with job results
    """
    job_start = time.time()
    start_time = datetime.now(timezone.utc)

    _log_progress("Job starting - importing dependencies...", job_start)
    _import_dependencies(job_start)
    _log_progress("All dependencies imported", job_start)

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
        _log_progress("Step 1: Starting RSS fetch...", job_start)
        try:
            rss_articles, rss_stats = fetch_all_rss_sources()
            stats['rss_articles'] = rss_stats['articles_total']
            stats['rss_sources_succeeded'] = rss_stats['sources_succeeded']
            stats['rss_sources_failed'] = rss_stats['sources_failed']
            _log_progress(f"Step 1: RSS complete - {stats['rss_articles']} articles from {stats['rss_sources_succeeded']} sources", job_start)
        except Exception as e:
            _log_progress(f"Step 1: RSS FAILED - {e}", job_start)
            logger.error(f"RSS fetch failed: {e}")
            stats['errors'].append(f"RSS fetch: {e}")
            rss_articles = []

        # Step 2: Execute Exa searches
        _log_progress("Step 2: Starting Exa searches...", job_start)
        try:
            exa_articles, exa_stats = search_all_queries()
            stats['exa_articles'] = exa_stats['articles_total']
            stats['exa_queries_succeeded'] = exa_stats['queries_succeeded']
            stats['exa_queries_failed'] = exa_stats['queries_failed']
            stats['cost_estimate'] += exa_stats['cost_estimate']
            _log_progress(f"Step 2: Exa complete - {stats['exa_articles']} articles from {stats['exa_queries_succeeded']} queries", job_start)
        except Exception as e:
            _log_progress(f"Step 2: Exa FAILED - {e}", job_start)
            logger.error(f"Exa search failed: {e}")
            stats['errors'].append(f"Exa search: {e}")
            exa_articles = []

        # Step 3: Combine and deduplicate
        _log_progress("Step 3: Deduplicating articles...", job_start)
        all_articles = rss_articles + exa_articles
        stats['total_discovered'] = len(all_articles)

        unique_articles, duplicates = deduplicate_articles(all_articles)
        stats['duplicates_removed'] = duplicates
        _log_progress(f"Step 3: Dedup complete - {len(unique_articles)} unique from {len(all_articles)} total", job_start)

        if not unique_articles:
            _log_progress("Step 3: No articles to filter - ending early", job_start)
            stats['end_time'] = datetime.now(timezone.utc).isoformat()
            return stats

        # Step 4: Filter through Claude Sonnet 4.5
        _log_progress(f"Step 4: Starting Claude Sonnet 4.5 filtering ({len(unique_articles)} articles)...", job_start)
        try:
            kept_articles, discarded_articles, filter_stats = filter_all_articles(unique_articles)
            stats['total_filtered'] = filter_stats['total_evaluated']
            stats['total_kept'] = filter_stats['total_kept']
            stats['cost_estimate'] += filter_stats['cost_estimate']
            _log_progress(f"Step 4: Claude complete - kept {stats['total_kept']}/{stats['total_filtered']} articles", job_start)
        except Exception as e:
            _log_progress(f"Step 4: Claude FAILED - {e}", job_start)
            logger.error(f"Claude filtering failed: {e}")
            stats['errors'].append(f"Claude filter: {e}")
            kept_articles = []

        # Step 5: Store candidates
        _log_progress(f"Step 5: Storing {len(kept_articles)} candidates...", job_start)
        if kept_articles:
            try:
                stored_count = store_candidates(kept_articles)
                stats['total_stored'] = stored_count
                _log_progress(f"Step 5: Storage complete - {stored_count} stored", job_start)
            except Exception as e:
                _log_progress(f"Step 5: Storage FAILED - {e}", job_start)
                logger.error(f"Storage failed: {e}")
                stats['errors'].append(f"Storage: {e}")
        else:
            _log_progress("Step 5: No candidates to store", job_start)

        # Log volume warnings per constitution
        if stats['total_kept'] < 40:
            logger.warning(f"Low candidate volume: {stats['total_kept']} (target: 40-60)")
        elif stats['total_kept'] > 80:
            logger.warning(f"High candidate volume: {stats['total_kept']} (target: 40-60)")

    except Exception as e:
        _log_progress(f"JOB FAILED: {e}", job_start)
        logger.error(f"Discovery job failed: {e}")
        stats['errors'].append(f"Job failure: {e}")

    # Final stats
    end_time = datetime.now(timezone.utc)
    stats['end_time'] = end_time.isoformat()
    stats['duration_seconds'] = (end_time - start_time).total_seconds()

    _log_progress(f"JOB COMPLETE: {stats['total_stored']} stored, ${stats['cost_estimate']:.2f} cost, {stats['duration_seconds']:.1f}s total", job_start)

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

