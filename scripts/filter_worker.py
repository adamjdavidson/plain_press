#!/usr/bin/env python
"""
Background Filter Worker

Continuously processes unfiltered articles through the multi-stage filtering pipeline.
Runs as a persistent Railway worker service - no timeout constraints.

Usage:
    python scripts/filter_worker.py

Environment:
    FILTER_WORKER_SLEEP_INTERVAL - Seconds to sleep when idle (default: 60)
    FILTER_WORKER_BATCH_SIZE - Articles to claim per cycle (default: 1)
"""

import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Article, ArticleStatus, FilterStatus
from app.services.filter_pipeline import run_pipeline_for_article

# Configuration
SLEEP_INTERVAL = int(os.environ.get("FILTER_WORKER_SLEEP_INTERVAL", "60"))
BATCH_SIZE = int(os.environ.get("FILTER_WORKER_BATCH_SIZE", "1"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('filter_worker')

# Graceful shutdown flag
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


def claim_next_article(session: Session) -> Article | None:
    """
    Atomically claim the next unfiltered article for processing.
    
    Uses SELECT FOR UPDATE SKIP LOCKED to prevent race conditions
    if multiple workers are running.
    
    Args:
        session: Database session
        
    Returns:
        Article if one was claimed, None otherwise
    """
    from sqlalchemy import text
    
    # Use raw SQL for atomic claim with SKIP LOCKED
    # This ensures concurrent workers don't claim the same article
    stmt = text("""
        UPDATE articles 
        SET filter_status = 'filtering'
        WHERE id = (
            SELECT id FROM articles 
            WHERE filter_status = 'unfiltered'
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        )
        RETURNING id
    """)
    
    result = session.execute(stmt)
    row = result.fetchone()
    
    if row is None:
        return None
    
    session.commit()
    
    # Now fetch the full article
    article = session.query(Article).filter(Article.id == row[0]).first()
    return article


def process_article(session: Session, article: Article) -> bool:
    """
    Process a single article through the filter pipeline.
    
    Args:
        session: Database session
        article: Article to process
        
    Returns:
        True if article passed all filters, False otherwise
    """
    logger.info(f"Processing article: {article.headline[:50]}...")
    
    start_time = time.time()
    
    try:
        # Run through the pipeline
        result = run_pipeline_for_article(article)
        
        # Update the article with results
        article.filter_score = result.filter_score
        article.filter_notes = result.filter_notes
        article.content_type = result.content_type
        article.wow_score = result.wow_score
        
        if result.passed:
            article.filter_status = FilterStatus.PASSED
            article.status = ArticleStatus.PENDING  # Ready for email selection
            logger.info(f"PASSED: {article.headline[:50]} (score={result.filter_score:.2f})")
        else:
            article.filter_status = FilterStatus.REJECTED
            article.status = ArticleStatus.REJECTED
            logger.info(f"REJECTED: {article.headline[:50]} - {result.filter_notes[:80]}")
        
        session.commit()
        
        duration = time.time() - start_time
        logger.info(f"Processed in {duration:.1f}s")
        
        return result.passed
        
    except Exception as e:
        logger.error(f"Error processing article {article.id}: {e}")
        
        # Mark as rejected with error
        article.filter_status = FilterStatus.REJECTED
        article.status = ArticleStatus.REJECTED
        article.filter_notes = f"Processing error: {e}"
        session.commit()
        
        return False


def get_queue_stats(session: Session) -> dict:
    """Get current queue statistics."""
    unfiltered = session.query(Article).filter(
        Article.filter_status == FilterStatus.UNFILTERED
    ).count()
    
    filtering = session.query(Article).filter(
        Article.filter_status == FilterStatus.FILTERING
    ).count()
    
    passed = session.query(Article).filter(
        Article.filter_status == FilterStatus.PASSED
    ).count()
    
    rejected = session.query(Article).filter(
        Article.filter_status == FilterStatus.REJECTED
    ).count()
    
    return {
        'unfiltered': unfiltered,
        'filtering': filtering,
        'passed': passed,
        'rejected': rejected
    }


def run_worker_loop():
    """
    Main worker loop - runs continuously until shutdown signal.
    """
    logger.info("=" * 60)
    logger.info("FILTER WORKER STARTING")
    logger.info(f"Sleep interval: {SLEEP_INTERVAL}s")
    logger.info(f"Batch size: {BATCH_SIZE}")
    logger.info("=" * 60)
    
    total_processed = 0
    total_passed = 0
    
    while not shutdown_requested:
        session = SessionLocal()
        
        try:
            # Check queue status
            stats = get_queue_stats(session)
            
            if stats['unfiltered'] == 0:
                logger.info(f"Queue empty. Sleeping {SLEEP_INTERVAL}s... (passed={stats['passed']}, rejected={stats['rejected']})")
                session.close()
                time.sleep(SLEEP_INTERVAL)
                continue
            
            logger.info(f"Queue: {stats['unfiltered']} unfiltered, {stats['filtering']} in progress")
            
            # Process articles
            for _ in range(BATCH_SIZE):
                if shutdown_requested:
                    break
                    
                article = claim_next_article(session)
                
                if article is None:
                    break
                
                passed = process_article(session, article)
                total_processed += 1
                if passed:
                    total_passed += 1
            
            # Brief pause between batches to avoid hammering the database
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            time.sleep(5)  # Brief pause before retrying
            
        finally:
            session.close()
    
    logger.info("=" * 60)
    logger.info("FILTER WORKER SHUTTING DOWN")
    logger.info(f"Total processed: {total_processed}")
    logger.info(f"Total passed: {total_passed}")
    logger.info("=" * 60)


def main():
    """Entry point for the filter worker."""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        run_worker_loop()
        return 0
    except Exception as e:
        logger.error(f"Worker failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

