#!/usr/bin/env python
"""
Daily Pipeline Runner

Runs the full daily workflow:
1. Discover articles (RSS + Exa)
2. Filter with Claude
3. Send email to editor

Run via Railway cron at 8am EST daily.
"""

import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 50)
    logger.info("DAILY PIPELINE START")
    logger.info("=" * 50)
    
    # Step 1: Run discovery job
    logger.info("\n[1/2] Running article discovery...")
    try:
        from scripts.daily_job import main as run_discovery
        run_discovery()
        logger.info("Discovery complete")
    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        # Continue to email even if discovery fails - we might have pending articles
    
    # Step 2: Send daily email
    logger.info("\n[2/2] Sending daily email...")
    try:
        from scripts.email_job import main as run_email
        run_email()
        logger.info("Email complete")
    except Exception as e:
        logger.error(f"Email failed: {e}")
        raise
    
    logger.info("\n" + "=" * 50)
    logger.info("DAILY PIPELINE COMPLETE")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()

