# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**CRITICAL: ALWAYS check the current date from user_info. NEVER assume old versions. ALWAYS use Context7 (mcp_context7_resolve-library-id and mcp_context7_get-library-docs) to look up current library versions before writing any code that uses external dependencies.**

**Governance**: All development must align with `.specify/memory/constitution.md`. Key principles: Single-User Simplicity, Cost Discipline (<$50/month), Pragmatic Testing, Volume Over Precision.

## Project Overview

Plain Press Finder is an automated system that discovers news articles suitable for Plain Press, an Amish newspaper. The system finds ~50 article candidates daily, filters them against editorial criteria, and presents them to the editor for review via email. Approved articles trigger deep-dive reports delivered via email and Google Docs.

**Single user**: John Lapp, the editor. No public interface.

## Tech Stack (Planned)

- **Hosting**: Railway (app, database, cron)
- **Language**: Python 3.11+
- **Web Framework**: Flask
- **Database**: PostgreSQL with SQLAlchemy ORM, Alembic for migrations
- **Email**: SendGrid
- **AI**: Anthropic Claude API (Haiku for filtering, Sonnet for deep dives)
- **Search**: Exa API + RSS feeds via feedparser
- **Google Integration**: Drive, Sheets, Docs APIs

## Architecture

```
scripts/
  daily_job.py         # 8am EST cron - fetch articles, filter, send email
  weekly_refinement.py # Sunday cron - analyze feedback, suggest rule changes
  cleanup_traces.py    # Daily cron - delete trace records older than 7 days

app/
  models.py            # SQLAlchemy: Article, Source, Feedback, FilterRule, EmailBatch, DeepDive, RefinementLog, PipelineRun, FilterTrace
  routes.py            # Flask routes including admin views
  services/
    discovery.py       # Orchestrates RSS/Exa fetch → filter → store
    rss_fetcher.py     # RSS feed fetching
    exa_searcher.py    # Exa API search
    claude_filter.py   # Legacy single-pass Claude filtering
    filter_pipeline.py # Multi-stage filter orchestrator (News → Wow → Values)
    filter_news_check.py   # Filter 1: Is this actual news? (Haiku)
    filter_wow_factor.py   # Filter 2: Would this make someone go wow? (Sonnet)
    filter_values_fit.py   # Filter 3: Does this fit Amish values? (Sonnet)
    email.py           # SendGrid HTML emails with action buttons
    deep_dive.py       # Report generation for approved articles
    google_docs.py     # Drive/Sheets/Docs integration
    refinement.py      # Weekly feedback analysis
```

## Admin Routes

- `/admin/articles` - Article management
- `/admin/sources` - RSS feed management
- `/admin/filter-runs` - Pipeline run list with funnel stats
- `/admin/filter-runs/<run_id>` - Funnel detail view
- `/admin/filter-runs/<run_id>/article/<url>` - Individual article journey
- `/admin/filter-runs/<run_id>/rejections/<filter_name>` - Rejection analysis
- `/admin/filter-runs/<run_id>/rejections/<filter_name>/export` - CSV export

## Data Flow

1. Daily job fetches 200-300 articles from Exa + RSS sources
2. Claude filters to ~50 candidates using FilterRule criteria
3. Email sent with Good/No/Why Not buttons per article
4. Button clicks hit Flask routes:
   - "Good" → triggers deep dive report → email + Google Doc + Sheet row
   - "No" → logs rejection
   - "Why Not" → opens feedback form → saves explanation
5. Weekly job analyzes feedback patterns → suggests rule adjustments

## Key Entities

- **Article**: News story with status (pending→emailed→good/rejected/passed), filter_score, wow_score, content_type, google_doc_id
- **Source**: RSS feed or Exa search query with trust_score based on approval rate
- **FilterRule**: Editorial criteria (must_have, must_avoid, good_topic, borderline)
- **Feedback**: Editor ratings with optional explanation notes
- **PipelineRun**: A single execution of the multi-stage filter pipeline with funnel counts
- **FilterTrace**: Record of one filter evaluating one article (decision, score, reasoning)

## Editorial Criteria Summary

Stories must be wholesome, surprising, and relatable at 8th-grade reading level. Focus on:
- Animals, food oddities, community efforts, nature, small-town traditions

Avoid:
- Individual hero/achievement stories (conflicts with Amish humility values)
- Modern technology, death/tragedy, violence, politics, military content

See [an_story_criteria.md](an_story_criteria.md) for complete editorial guidelines.

## Environment Variables

```
# Core
DATABASE_URL, ANTHROPIC_API_KEY, EXA_API_KEY, SENDGRID_API_KEY, FROM_EMAIL
GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_DRIVE_FOLDER_ID, GOOGLE_SHEET_ID
EMAIL_RECIPIENTS, FLASK_SECRET_KEY, BASE_URL

# Multi-Stage Filtering
USE_MULTI_STAGE_FILTER=true         # Enable new 3-stage pipeline
FILTER_WOW_THRESHOLD=0.5            # Wow factor pass threshold (0.0-1.0)
FILTER_VALUES_THRESHOLD=0.5         # Values fit pass threshold (0.0-1.0)
FILTER_NEWS_CHECK_MODEL=claude-haiku-4-5    # Model for Filter 1
FILTER_WOW_FACTOR_MODEL=claude-sonnet-4-5   # Model for Filter 2
FILTER_VALUES_FIT_MODEL=claude-sonnet-4-5   # Model for Filter 3
FILTER_TRACING_ENABLED=true         # Enable trace recording
TRACE_RETENTION_DAYS=7              # Days to keep trace data
```

## Project Status

This repository currently contains only design documentation. Implementation has not started.

## Active Technologies
- Python 3.11+ + SQLAlchemy 2.0+, Alembic 1.12+, psycopg2-binary 2.9+ (PostgreSQL adapter) (001-database-schema)
- PostgreSQL 15+ on Railway (with automated backups) (001-database-schema)
- Python 3.11 (per existing codebase) + Flask, SQLAlchemy, feedparser (all existing) (005-rss-feed-management)
- PostgreSQL (existing Source model) (005-rss-feed-management)
- Python 3.11+ + Anthropic Claude API (existing), SQLAlchemy 2.0+ (existing) (001-story-quality-filter)
- PostgreSQL (existing Article model - minor schema extension) (001-story-quality-filter)
- Python 3.11 + Flask, SQLAlchemy, Anthropic SDK, Jinja2 (006-multi-stage-filtering)
- PostgreSQL (existing) (006-multi-stage-filtering)

## Recent Changes
- 001-database-schema: Added Python 3.11+ + SQLAlchemy 2.0+, Alembic 1.12+, psycopg2-binary 2.9+ (PostgreSQL adapter)
