#!/usr/bin/env python
"""
Quick diagnostic script to check article queue status.

Run: python scripts/check_queue.py
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from datetime import datetime, timezone, timedelta
from app.database import SessionLocal
from app.models import Article, ArticleStatus, FilterStatus, PipelineRun


def main():
    session = SessionLocal()
    
    try:
        print("=" * 60)
        print("ARTICLE QUEUE DIAGNOSTIC")
        print("=" * 60)
        
        # Check filter_status counts
        print("\n📊 Filter Status Breakdown:")
        for status in FilterStatus:
            count = session.query(Article).filter(Article.filter_status == status).count()
            print(f"  {status.value:15} : {count:5}")
        
        # Check article status counts
        print("\n📊 Article Status Breakdown:")
        for status in ArticleStatus:
            count = session.query(Article).filter(Article.status == status).count()
            print(f"  {status.value:15} : {count:5}")
        
        # Check articles from today
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_articles = session.query(Article).filter(
            Article.discovered_date >= today_start
        ).count()
        print(f"\n📅 Articles discovered today: {today_articles}")
        
        # Check recent unfiltered articles
        unfiltered = session.query(Article).filter(
            Article.filter_status == FilterStatus.UNFILTERED
        ).order_by(Article.discovered_date.desc()).limit(5).all()
        
        if unfiltered:
            print("\n🔴 Recent UNFILTERED articles (stuck in queue):")
            for art in unfiltered:
                print(f"  - {art.headline[:50]}...")
                print(f"    Discovered: {art.discovered_date}")
                print(f"    Source: {art.source_name}")
        else:
            print("\n✅ No unfiltered articles in queue")
        
        # Check for articles stuck in 'filtering' state
        filtering = session.query(Article).filter(
            Article.filter_status == FilterStatus.FILTERING
        ).count()
        if filtering > 0:
            print(f"\n⚠️  {filtering} articles stuck in 'filtering' state (worker may have crashed)")
        
        # Check recent pipeline runs
        print("\n📋 Recent Pipeline Runs:")
        runs = session.query(PipelineRun).order_by(
            PipelineRun.started_at.desc()
        ).limit(5).all()
        
        if runs:
            for run in runs:
                passed = run.filter3_pass_count or 0
                print(f"  - {run.started_at.strftime('%Y-%m-%d %H:%M')} | Status: {run.status.value} | Input: {run.input_count} | Passed: {passed}")
        else:
            print("  No pipeline runs found!")
        
        print("\n" + "=" * 60)
        
        # Recommendation
        unfiltered_count = session.query(Article).filter(
            Article.filter_status == FilterStatus.UNFILTERED
        ).count()
        
        if unfiltered_count > 0:
            print("\n⚠️  ISSUE DETECTED:")
            print(f"   {unfiltered_count} articles are stuck with filter_status='unfiltered'")
            print("\n   This means the filter_worker is NOT running or crashed.")
            print("\n   Solutions:")
            print("   1. Check if Railway worker service is running")
            print("   2. Restart the worker service on Railway")
            print("   3. Run filter_worker.py locally to process backlog:")
            print("      python scripts/filter_worker.py")
        
    finally:
        session.close()


if __name__ == "__main__":
    main()

