#!/usr/bin/env python
"""
Daily Article Discovery Job

Runs at 8am EST via Railway cron to:
1. Fetch articles from RSS feeds
2. Search articles via Exa API
3. Filter through Claude Haiku
4. Store candidates in database

Usage:
    python scripts/daily_job.py

Exit codes:
    0 - Success
    1 - Failure (partial or complete)
"""

import logging
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.services.discovery import run_discovery_job

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('daily_job')


def main():
    """Main entry point for daily discovery job."""
    logger.info("=" * 60)
    logger.info("DAILY ARTICLE DISCOVERY JOB STARTING")
    logger.info("=" * 60)
    
    try:
        result = run_discovery_job()
        
        # Log summary
        logger.info("=" * 60)
        logger.info("JOB SUMMARY")
        logger.info("=" * 60)
        logger.info(f"RSS Articles:      {result.get('rss_articles', 0)}")
        logger.info(f"Exa Articles:      {result.get('exa_articles', 0)}")
        logger.info(f"Total Discovered:  {result.get('total_discovered', 0)}")
        logger.info(f"Duplicates:        {result.get('duplicates_removed', 0)}")
        logger.info(f"Filtered:          {result.get('total_filtered', 0)}")
        logger.info(f"Kept (≥0.5):       {result.get('total_kept', 0)}")
        logger.info(f"Stored:            {result.get('total_stored', 0)}")
        logger.info(f"Cost Estimate:     ${result.get('cost_estimate', 0):.2f}")
        logger.info(f"Duration:          {result.get('duration_seconds', 0):.1f}s")
        
        if result.get('errors'):
            logger.warning(f"Errors: {result['errors']}")
        
        # Check for complete failure
        if result.get('total_stored', 0) == 0 and result.get('total_discovered', 0) > 0:
            logger.error("No candidates stored despite discovering articles - job may have failed")
            # TODO: Send alert email (Feature 003)
            return 1
        
        logger.info("=" * 60)
        logger.info("JOB COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        return 0
        
    except Exception as e:
        logger.error(f"JOB FAILED: {e}", exc_info=True)
        # TODO: Send alert email (Feature 003)
        return 1


if __name__ == '__main__':
    sys.exit(main())

