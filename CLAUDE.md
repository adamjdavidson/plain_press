# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

app/
  models.py            # SQLAlchemy: Article, Source, Feedback, FilterRule, EmailBatch, DeepDive, RefinementLog
  routes.py            # Flask: /good/<id>, /no/<id>, /why-not/<id>, /feedback, /rules, /health
  services/
    search.py          # Exa API + RSS fetching
    filter.py          # Claude filtering against criteria
    email.py           # SendGrid HTML emails with action buttons
    deep_dive.py       # Report generation for approved articles
    google.py          # Drive/Sheets/Docs integration
    refinement.py      # Weekly feedback analysis
```

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

- **Article**: News story with status (pending→emailed→good/rejected/passed), filter_score, google_doc_id
- **Source**: RSS feed or Exa search query with trust_score based on approval rate
- **FilterRule**: Editorial criteria (must_have, must_avoid, good_topic, borderline)
- **Feedback**: Editor ratings with optional explanation notes

## Editorial Criteria Summary

Stories must be wholesome, surprising, and relatable at 8th-grade reading level. Focus on:
- Animals, food oddities, community efforts, nature, small-town traditions

Avoid:
- Individual hero/achievement stories (conflicts with Amish humility values)
- Modern technology, death/tragedy, violence, politics, military content

See [an_story_criteria.md](an_story_criteria.md) for complete editorial guidelines.

## Environment Variables

```
DATABASE_URL, ANTHROPIC_API_KEY, EXA_API_KEY, SENDGRID_API_KEY, FROM_EMAIL
GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_DRIVE_FOLDER_ID, GOOGLE_SHEET_ID
EMAIL_RECIPIENTS, FLASK_SECRET_KEY, BASE_URL
```

## Project Status

This repository currently contains only design documentation. Implementation has not started.

## Active Technologies
- Python 3.11+ + SQLAlchemy 2.0+, Alembic 1.12+, psycopg2-binary 2.9+ (PostgreSQL adapter) (001-database-schema)
- PostgreSQL 15+ on Railway (with automated backups) (001-database-schema)

## Recent Changes
- 001-database-schema: Added Python 3.11+ + SQLAlchemy 2.0+, Alembic 1.12+, psycopg2-binary 2.9+ (PostgreSQL adapter)
