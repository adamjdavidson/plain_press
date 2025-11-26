#!/usr/bin/env python
"""
Seed Data Script

Seeds the database with initial sources (RSS feeds, Exa queries) 
and filter rules from JSON files.

Usage:
    python scripts/seed_data.py --sources     # Seed sources only
    python scripts/seed_data.py --rules       # Seed filter rules only
    python scripts/seed_data.py --all         # Seed everything

Idempotent: Running multiple times will not create duplicates.
"""

import argparse
import json
import logging
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models import Source, SourceType, FilterRule, RuleType, RuleSource

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('seed_data')

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')


def load_json(filename: str) -> list:
    """Load JSON file from data directory."""
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, 'r') as f:
        return json.load(f)


def seed_sources():
    """Seed RSS feeds and Exa search queries."""
    session = SessionLocal()
    created = 0
    skipped = 0
    
    try:
        sources = load_json('sources.json')
        logger.info(f"Loading {len(sources)} sources from sources.json")
        
        for source_data in sources:
            # Check if exists
            existing = session.query(Source).filter_by(name=source_data['name']).first()
            if existing:
                logger.debug(f"Source '{source_data['name']}' already exists, skipping")
                skipped += 1
                continue
            
            # Map type string to enum
            type_map = {
                'rss': SourceType.RSS,
                'search_query': SourceType.SEARCH_QUERY,
                'manual': SourceType.MANUAL,
            }
            
            source = Source(
                name=source_data['name'],
                type=type_map.get(source_data['type'], SourceType.RSS),
                url=source_data.get('url'),
                search_query=source_data.get('search_query'),
                is_active=source_data.get('is_active', True),
                trust_score=source_data.get('trust_score', 0.5),
                notes=source_data.get('notes'),
            )
            session.add(source)
            created += 1
            logger.info(f"Created source: {source_data['name']}")
        
        session.commit()
        logger.info(f"Sources seeding complete: {created} created, {skipped} skipped")
        
    except FileNotFoundError:
        logger.error("data/sources.json not found - please create it first")
        raise
    except Exception as e:
        logger.error(f"Error seeding sources: {e}")
        session.rollback()
        raise
    finally:
        session.close()
    
    return created, skipped


def seed_filter_rules():
    """Seed filter rules from story criteria."""
    session = SessionLocal()
    created = 0
    skipped = 0
    
    try:
        rules = load_json('filter_rules.json')
        logger.info(f"Loading {len(rules)} filter rules from filter_rules.json")
        
        for rule_data in rules:
            # Check if exists (by rule_text to avoid exact duplicates)
            existing = session.query(FilterRule).filter_by(rule_text=rule_data['rule_text']).first()
            if existing:
                logger.debug(f"Rule '{rule_data['rule_text'][:50]}...' already exists, skipping")
                skipped += 1
                continue
            
            # Map type string to enum
            type_map = {
                'must_have': RuleType.MUST_HAVE,
                'must_avoid': RuleType.MUST_AVOID,
                'good_topic': RuleType.GOOD_TOPIC,
                'borderline': RuleType.BORDERLINE,
            }
            
            source_map = {
                'original': RuleSource.ORIGINAL,
                'learned': RuleSource.LEARNED,
                'manual': RuleSource.MANUAL,
            }
            
            rule = FilterRule(
                rule_type=type_map.get(rule_data['rule_type'], RuleType.MUST_HAVE),
                rule_text=rule_data['rule_text'],
                priority=rule_data.get('priority', 50),
                is_active=rule_data.get('is_active', True),
                source=source_map.get(rule_data.get('source', 'original'), RuleSource.ORIGINAL),
            )
            session.add(rule)
            created += 1
            logger.info(f"Created rule: {rule_data['rule_text'][:60]}...")
        
        session.commit()
        logger.info(f"Filter rules seeding complete: {created} created, {skipped} skipped")
        
    except FileNotFoundError:
        logger.error("data/filter_rules.json not found - please create it first")
        raise
    except Exception as e:
        logger.error(f"Error seeding filter rules: {e}")
        session.rollback()
        raise
    finally:
        session.close()
    
    return created, skipped


def main():
    parser = argparse.ArgumentParser(description='Seed database with initial data')
    parser.add_argument('--sources', action='store_true', help='Seed sources (RSS feeds, Exa queries)')
    parser.add_argument('--rules', action='store_true', help='Seed filter rules')
    parser.add_argument('--all', action='store_true', help='Seed everything')
    
    args = parser.parse_args()
    
    # Default to --all if nothing specified
    if not (args.sources or args.rules or args.all):
        args.all = True
    
    try:
        if args.sources or args.all:
            logger.info("=" * 40)
            logger.info("SEEDING SOURCES")
            logger.info("=" * 40)
            seed_sources()
        
        if args.rules or args.all:
            logger.info("=" * 40)
            logger.info("SEEDING FILTER RULES")
            logger.info("=" * 40)
            seed_filter_rules()
        
        logger.info("=" * 40)
        logger.info("SEEDING COMPLETE")
        logger.info("=" * 40)
        return 0
        
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())

