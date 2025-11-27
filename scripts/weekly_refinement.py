#!/usr/bin/env python3
"""
Weekly Refinement Job

Analyzes editor feedback and generates suggestions for improving article selection.
Designed to run once per week (e.g., Sunday morning via cron).

Usage:
    python scripts/weekly_refinement.py
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Run weekly refinement job."""
    start_time = datetime.now(timezone.utc)
    logger.info("=" * 60)
    logger.info("WEEKLY REFINEMENT JOB STARTING")
    logger.info(f"Start time: {start_time.isoformat()}")
    logger.info("=" * 60)

    try:
        # Import here to ensure path is set up
        from app.services.refinement import run_weekly_refinement
        from app.services.email import send_refinement_report

        # Run the refinement job
        results = run_weekly_refinement()

        # Log results
        logger.info("=" * 60)
        logger.info("REFINEMENT RESULTS:")
        logger.info(f"  Feedback collected: {results.get('feedback_collected', 0)}")
        logger.info(f"  Trust scores updated: {results.get('trust_scores_updated', 0)}")
        logger.info(f"  Suggestions generated: {len(results.get('suggestions', []))}")
        logger.info(f"  Duration: {results.get('duration_seconds', 0):.1f}s")

        if results.get('errors'):
            logger.error(f"  Errors: {results['errors']}")

        # Send email report if configured
        editor_email = os.environ.get('EDITOR_EMAIL')
        if editor_email and results.get('feedback_collected', 0) > 0:
            logger.info("Sending refinement report email...")
            try:
                send_refinement_report(
                    to_email=editor_email,
                    results=results
                )
                logger.info("Report email sent successfully")
            except Exception as e:
                logger.error(f"Failed to send report email: {e}")
        else:
            logger.info("Skipping email (no EDITOR_EMAIL or no feedback)")

        logger.info("=" * 60)
        logger.info("WEEKLY REFINEMENT JOB COMPLETE")
        logger.info("=" * 60)

        return 0 if not results.get('errors') else 1

    except Exception as e:
        logger.error(f"Weekly refinement job failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
