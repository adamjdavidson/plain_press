#!/usr/bin/env python
"""
Background Filter Worker

Continuously processes unfiltered articles through the multi-stage filtering pipeline.
Runs as a persistent Railway worker service - no timeout constraints.
Records all filter decisions to enable funnel analysis via /admin/filter-runs.

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
from uuid import UUID

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Article, ArticleStatus, FilterStatus, PipelineRun, PipelineRunStatus, FilterTrace
from app.services.filter_news_check import filter_news_check
from app.services.filter_wow_factor import filter_wow_factor
from app.services.filter_values_fit import filter_values_fit, load_filter_rules

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

# Current pipeline run (created per worker session)
current_run: PipelineRun = None
current_run_id: UUID = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


def create_worker_run(session: Session, queue_size: int) -> PipelineRun:
    """Create a new PipelineRun for this worker session."""
    run = PipelineRun(
        status=PipelineRunStatus.RUNNING,
        input_count=queue_size
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    logger.info(f"Created worker run {run.id} (queue size: {queue_size})")
    return run


def record_trace(
    session: Session,
    run_id: UUID,
    article: Article,
    filter_name: str,
    filter_order: int,
    decision: str,
    reasoning: str,
    score: float = None,
    input_tokens: int = None,
    output_tokens: int = None,
    latency_ms: int = None
):
    """Record a filter decision trace."""
    trace = FilterTrace(
        run_id=run_id,
        article_url=article.external_url,
        article_title=article.headline[:500],
        filter_name=filter_name,
        filter_order=filter_order,
        decision=decision,
        score=score,
        reasoning=reasoning[:2000] if reasoning else "",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms
    )
    session.add(trace)
    # Don't commit yet - let caller batch commits


def update_run_counts(session: Session, run: PipelineRun, f1: int, f2: int, f3: int):
    """Update the pipeline run with current counts."""
    run.filter1_pass_count = f1
    run.filter2_pass_count = f2
    run.filter3_pass_count = f3
    session.commit()


def finalize_run(session: Session, run: PipelineRun, status: PipelineRunStatus, error: str = None):
    """Mark the pipeline run as complete."""
    run.status = status
    run.completed_at = datetime.now(timezone.utc)
    run.error_message = error
    session.commit()
    logger.info(f"Finalized run {run.id}: {status.value}")


def claim_next_article(session: Session) -> Article | None:
    """
    Atomically claim the next unfiltered article for processing.
    Uses SELECT FOR UPDATE SKIP LOCKED to prevent race conditions.
    """
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
    article = session.query(Article).filter(Article.id == row[0]).first()
    return article


def process_article_with_tracing(session: Session, article: Article, run_id: UUID, rules: dict) -> tuple[bool, str]:
    """
    Process a single article through all filters with full tracing.
    
    Returns:
        (passed: bool, rejection_stage: str or None)
    """
    article_data = {
        'url': article.external_url,
        'title': article.headline,
        'content': article.raw_content or ''
    }
    
    # =========================================
    # FILTER 1: News Check
    # =========================================
    try:
        start_ms = int(time.time() * 1000)
        result1 = filter_news_check(article_data)
        latency1 = int(time.time() * 1000) - start_ms
        
        record_trace(
            session, run_id, article,
            filter_name="news_check",
            filter_order=1,
            decision="pass" if result1.passed else "reject",
            reasoning=result1.reasoning,
            input_tokens=result1.input_tokens,
            output_tokens=result1.output_tokens,
            latency_ms=latency1
        )
        
        if not result1.passed:
            article.content_type = result1.category
            article.filter_score = 0.0
            article.filter_notes = f"Rejected at news_check: {result1.reasoning}"
            return False, "news_check"
            
    except Exception as e:
        logger.error(f"News check error: {e}")
        article.filter_notes = f"Error in news_check: {e}"
        return False, "news_check_error"
    
    # =========================================
    # FILTER 2: Wow Factor
    # =========================================
    try:
        start_ms = int(time.time() * 1000)
        result2 = filter_wow_factor(article_data)
        latency2 = int(time.time() * 1000) - start_ms
        
        record_trace(
            session, run_id, article,
            filter_name="wow_factor",
            filter_order=2,
            decision="pass" if result2.passed else "reject",
            reasoning=result2.reasoning,
            score=result2.score,
            input_tokens=result2.input_tokens,
            output_tokens=result2.output_tokens,
            latency_ms=latency2
        )
        
        article.wow_score = result2.score
        
        if not result2.passed:
            article.content_type = "news_article"
            article.filter_score = 0.0
            article.filter_notes = f"Rejected at wow_factor: {result2.reasoning}"
            return False, "wow_factor"
            
    except Exception as e:
        logger.error(f"Wow factor error: {e}")
        article.filter_notes = f"Error in wow_factor: {e}"
        return False, "wow_factor_error"
    
    # =========================================
    # FILTER 3: Values Fit
    # =========================================
    try:
        start_ms = int(time.time() * 1000)
        result3 = filter_values_fit(article_data, rules)
        latency3 = int(time.time() * 1000) - start_ms
        
        record_trace(
            session, run_id, article,
            filter_name="values_fit",
            filter_order=3,
            decision="pass" if result3.passed else "reject",
            reasoning=result3.reasoning,
            score=result3.score,
            input_tokens=result3.input_tokens,
            output_tokens=result3.output_tokens,
            latency_ms=latency3
        )
        
        article.filter_score = result3.score or 0.0
        
        if not result3.passed:
            article.content_type = "news_article"
            article.filter_notes = f"Rejected at values_fit: {result3.reasoning}"
            return False, "values_fit"
            
    except Exception as e:
        logger.error(f"Values fit error: {e}")
        article.filter_notes = f"Error in values_fit: {e}"
        return False, "values_fit_error"
    
    # =========================================
    # PASSED ALL FILTERS
    # =========================================
    article.content_type = "news_article"
    article.filter_notes = f"Passed all filters. Wow: {result2.score:.2f}. Values: {result3.score:.2f}"
    return True, None


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
    """Main worker loop - runs continuously until shutdown signal."""
    global current_run, current_run_id
    
    logger.info("=" * 60)
    logger.info("FILTER WORKER STARTING")
    logger.info(f"Sleep interval: {SLEEP_INTERVAL}s")
    logger.info(f"Batch size: {BATCH_SIZE}")
    logger.info("=" * 60)
    
    # Counters for current run
    filter1_pass = 0
    filter2_pass = 0
    filter3_pass = 0
    total_processed = 0
    
    # Load filter rules once
    rules = load_filter_rules()
    
    # Create initial session to set up run
    session = SessionLocal()
    try:
        stats = get_queue_stats(session)
        current_run = create_worker_run(session, stats['unfiltered'])
        current_run_id = current_run.id
    finally:
        session.close()
    
    while not shutdown_requested:
        session = SessionLocal()
        
        try:
            # Check queue status
            stats = get_queue_stats(session)
            
            if stats['unfiltered'] == 0:
                # Update run counts before sleeping
                run = session.query(PipelineRun).filter(PipelineRun.id == current_run_id).first()
                if run:
                    update_run_counts(session, run, filter1_pass, filter2_pass, filter3_pass)
                
                logger.info(f"Queue empty. Sleeping {SLEEP_INTERVAL}s... (passed={filter3_pass}, rejected={total_processed - filter3_pass})")
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
                
                logger.info(f"Processing: {article.headline[:50]}...")
                start_time = time.time()
                
                # Process with tracing
                passed, rejection_stage = process_article_with_tracing(
                    session, article, current_run_id, rules
                )
                
                # Update article status
                if passed:
                    article.filter_status = FilterStatus.PASSED
                    article.status = ArticleStatus.PENDING
                    filter1_pass += 1
                    filter2_pass += 1
                    filter3_pass += 1
                    logger.info(f"PASSED: {article.headline[:50]} (score={article.filter_score:.2f})")
                else:
                    article.filter_status = FilterStatus.REJECTED
                    article.status = ArticleStatus.REJECTED
                    # Update pass counts based on where it failed
                    if rejection_stage not in ["news_check", "news_check_error"]:
                        filter1_pass += 1
                    if rejection_stage not in ["news_check", "news_check_error", "wow_factor", "wow_factor_error"]:
                        filter2_pass += 1
                    logger.info(f"REJECTED at {rejection_stage}: {article.headline[:50]}")
                
                # Link article to run
                article.last_run_id = current_run_id
                
                session.commit()
                total_processed += 1
                
                duration = time.time() - start_time
                logger.info(f"Processed in {duration:.1f}s (total: {total_processed})")
            
            # Update run counts periodically (every batch)
            run = session.query(PipelineRun).filter(PipelineRun.id == current_run_id).first()
            if run:
                update_run_counts(session, run, filter1_pass, filter2_pass, filter3_pass)
            
            # Brief pause between batches
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            time.sleep(5)
            
        finally:
            session.close()
    
    # Finalize run on shutdown
    session = SessionLocal()
    try:
        run = session.query(PipelineRun).filter(PipelineRun.id == current_run_id).first()
        if run:
            finalize_run(session, run, PipelineRunStatus.COMPLETED)
    finally:
        session.close()
    
    logger.info("=" * 60)
    logger.info("FILTER WORKER SHUTTING DOWN")
    logger.info(f"Total processed: {total_processed}")
    logger.info(f"Passed all filters: {filter3_pass}")
    logger.info("=" * 60)


def main():
    """Entry point for the filter worker."""
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
