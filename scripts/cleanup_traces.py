#!/usr/bin/env python3
"""
Cleanup script for filter pipeline traces.

Deletes FilterTrace and PipelineRun records older than 7 days.
Should be run daily via cron or Railway scheduled job.

Usage:
    python scripts/cleanup_traces.py
    
Environment:
    DATABASE_URL - PostgreSQL connection string
    TRACE_RETENTION_DAYS - Override default 7-day retention (optional)
"""

import logging
import os
import sys
from datetime import datetime, timedelta, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import FilterTrace, PipelineRun

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
# Silence verbose SQLAlchemy logging (prevents Railway rate limit issues)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Default retention period
DEFAULT_RETENTION_DAYS = 7


def cleanup_old_traces(retention_days: int = None) -> dict:
    """
    Delete filter traces and pipeline runs older than retention period.
    
    Args:
        retention_days: Number of days to retain. Defaults to TRACE_RETENTION_DAYS
                       env var or 7 days.
    
    Returns:
        Dict with counts of deleted records
    """
    if retention_days is None:
        retention_days = int(os.environ.get("TRACE_RETENTION_DAYS", DEFAULT_RETENTION_DAYS))
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    
    logger.info(f"Starting cleanup - deleting records older than {cutoff.isoformat()}")
    
    session = SessionLocal()
    stats = {
        'traces_deleted': 0,
        'runs_deleted': 0,
        'retention_days': retention_days,
        'cutoff_date': cutoff.isoformat()
    }
    
    try:
        # Step 1: Delete old traces
        # This will cascade-delete due to FK relationship
        traces_result = session.query(FilterTrace).filter(
            FilterTrace.created_at < cutoff
        ).delete(synchronize_session=False)
        
        stats['traces_deleted'] = traces_result
        logger.info(f"Deleted {traces_result} filter traces")
        
        # Step 2: Delete orphaned pipeline runs (no remaining traces)
        # Find runs with no traces left
        from sqlalchemy import not_, exists
        
        orphan_runs = session.query(PipelineRun).filter(
            PipelineRun.started_at < cutoff,
            ~exists().where(FilterTrace.run_id == PipelineRun.id)
        ).all()
        
        for run in orphan_runs:
            session.delete(run)
        
        stats['runs_deleted'] = len(orphan_runs)
        logger.info(f"Deleted {len(orphan_runs)} orphaned pipeline runs")
        
        session.commit()
        logger.info(f"Cleanup complete - {stats['traces_deleted']} traces, {stats['runs_deleted']} runs deleted")
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()
    
    return stats


def main():
    """Run cleanup with command line support."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Cleanup old filter traces')
    parser.add_argument(
        '--days', 
        type=int, 
        default=None,
        help=f'Retention period in days (default: {DEFAULT_RETENTION_DAYS})'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        retention_days = args.days or int(os.environ.get("TRACE_RETENTION_DAYS", DEFAULT_RETENTION_DAYS))
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        
        session = SessionLocal()
        try:
            trace_count = session.query(FilterTrace).filter(
                FilterTrace.created_at < cutoff
            ).count()
            
            from sqlalchemy import not_, exists
            run_count = session.query(PipelineRun).filter(
                PipelineRun.started_at < cutoff
            ).count()
            
            logger.info(f"DRY RUN - Would delete:")
            logger.info(f"  - {trace_count} filter traces older than {cutoff.date()}")
            logger.info(f"  - Up to {run_count} pipeline runs")
        finally:
            session.close()
    else:
        stats = cleanup_old_traces(args.days)
        print(f"Cleanup complete: {stats['traces_deleted']} traces, {stats['runs_deleted']} runs deleted")


if __name__ == '__main__':
    main()

