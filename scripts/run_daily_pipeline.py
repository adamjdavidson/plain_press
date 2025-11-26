#!/usr/bin/env python
"""Daily Pipeline Runner - Plain Press"""

# FIRST THING: Print to prove we're running
import sys
import time
print("=== PIPELINE SCRIPT STARTING ===", file=sys.stdout, flush=True)
print("=== PIPELINE SCRIPT STARTING ===", file=sys.stderr, flush=True)

import os
os.environ['PYTHONUNBUFFERED'] = '1'

# Track timing from the very start
_SCRIPT_START = time.time()

def log(msg):
    """Print with immediate flush for Railway logs, including elapsed time."""
    elapsed = time.time() - _SCRIPT_START
    timestamp = f"[{elapsed:7.1f}s]"
    print(f"{timestamp} {msg}", file=sys.stdout, flush=True)
    print(f"{timestamp} {msg}", file=sys.stderr, flush=True)

log("Step 0: Imports starting...")

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

log("Step 0: Loading dotenv...")
from dotenv import load_dotenv
load_dotenv()

log("Step 0: Checking environment variables...")
# Check critical env vars before any imports that might use them
critical_vars = ['DATABASE_URL', 'ANTHROPIC_API_KEY', 'EXA_API_KEY', 'SENDGRID_API_KEY']
for var in critical_vars:
    val = os.environ.get(var)
    if val:
        log(f"  {var}: SET ({len(val)} chars)")
    else:
        log(f"  {var}: NOT SET - WARNING!")

log("Step 0: Imports complete")


def main():
    log("=" * 50)
    log("DAILY PIPELINE START")
    log("=" * 50)

    # Step 1: Run discovery job
    log("[1/2] Running article discovery...")
    log("[1/2] Importing daily_job module...")
    try:
        from scripts.daily_job import main as run_discovery
        log("[1/2] Import complete, calling run_discovery()...")
        run_discovery()
        log("[1/2] Discovery complete")
    except Exception as e:
        log(f"ERROR - Discovery failed: {e}")
        import traceback
        traceback.print_exc()
        # Continue to email even if discovery fails - we might have pending articles

    # Step 2: Send daily email
    log("[2/2] Sending daily email...")
    log("[2/2] Importing email_job module...")
    try:
        from scripts.email_job import main as run_email
        log("[2/2] Import complete, calling run_email()...")
        run_email()
        log("[2/2] Email complete")
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

