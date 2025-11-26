#!/usr/bin/env python
"""
Daily Pipeline Runner - Plain Press

Runs the full daily workflow:
1. Discover articles (RSS + Exa)
2. Filter with Claude (using structured outputs)
3. Send email to editor
"""

import sys
import os

# Force unbuffered output for Railway logs
os.environ['PYTHONUNBUFFERED'] = '1'

def log(msg):
    """Print with immediate flush for Railway logs."""
    print(msg, flush=True)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def main():
    log("=" * 50)
    log("DAILY PIPELINE START")
    log("=" * 50)
    
    # Step 1: Run discovery job
    log("[1/2] Running article discovery...")
    try:
        from scripts.daily_job import main as run_discovery
        run_discovery()
        log("Discovery complete")
    except Exception as e:
        log(f"ERROR - Discovery failed: {e}")
        import traceback
        traceback.print_exc()
        # Continue to email even if discovery fails - we might have pending articles
    
    # Step 2: Send daily email
    log("[2/2] Sending daily email...")
    try:
        from scripts.email_job import main as run_email
        run_email()
        log("Email complete")
    except Exception as e:
        log(f"ERROR - Email failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    log("=" * 50)
    log("DAILY PIPELINE COMPLETE")
    log("=" * 50)


if __name__ == "__main__":
    main()

