#!/usr/bin/env python3
"""
Daily Email Job

Sends the daily candidate email at 9:00 AM EST.
Designed to be run as a Railway cron job.

Schedule: 0 14 * * * (14:00 UTC = 9:00 AM EST)
"""

import logging
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for email job."""
    logger.info("=" * 60)
    logger.info("Starting daily email job")
    logger.info(f"Time: {datetime.now().isoformat()}")
    logger.info("=" * 60)
    
    try:
        from app.services.email import send_daily_candidates
        
        # Send the email
        stats = send_daily_candidates()
        
        # Log results
        logger.info("-" * 40)
        logger.info("Email Job Results:")
        logger.info(f"  Articles found: {stats['articles_found']}")
        logger.info(f"  Articles sent: {stats['articles_sent']}")
        logger.info(f"  Email sent: {stats['email_sent']}")
        
        if stats['error']:
            logger.error(f"  Error: {stats['error']}")
            return 1
        
        if not stats['email_sent'] and stats['articles_found'] == 0:
            logger.warning("  No pending articles to send")
            return 0
        
        logger.info("-" * 40)
        logger.info("Daily email job completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Email job failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

