# Data Model: RSS Feed Management

**Feature**: 005-rss-feed-management  
**Date**: 2025-11-28

## Overview

This feature uses the **existing Source model** with no schema changes required. This document describes how the existing model supports RSS feed management operations.

## Entities

### Source (Existing)

The Source entity represents content sources for article discovery. RSS feeds are sources with `type = SourceType.RSS`.

**Table**: `sources`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, auto-generated | Unique identifier |
| name | String(200) | NOT NULL, UNIQUE | Display name for the feed |
| type | SourceType | NOT NULL | RSS, SEARCH_QUERY, or MANUAL |
| url | String(500) | NULLABLE | RSS feed URL (required for RSS type) |
| search_query | String(500) | NULLABLE | Exa search query (for SEARCH_QUERY type) |
| is_active | Boolean | NOT NULL, default=True | Whether feed is actively fetched |
| trust_score | Float | NOT NULL, default=0.5 | Performance score (0.0-1.0) |
| total_surfaced | Integer | NOT NULL, default=0 | Articles discovered from this source |
| total_approved | Integer | NOT NULL, default=0 | Articles marked "Good" |
| total_rejected | Integer | NOT NULL, default=0 | Articles marked "No" or "Why Not" |
| last_fetched | DateTime | NULLABLE | Last successful fetch timestamp |
| notes | Text | NULLABLE | Admin notes about the source |
| created_at | DateTime | NOT NULL, auto | Record creation timestamp |
| updated_at | DateTime | NOT NULL, auto | Last modification timestamp |

**Indexes**:
- `ix_sources_is_active` - Filter active sources
- `ix_sources_trust_score` - Sort by performance

**Relationships**:
- `articles`: One-to-many with Article (FK: article.source_id)

### SourceType Enum (Existing)

```python
class SourceType(enum.Enum):
    RSS = "rss"
    SEARCH_QUERY = "search_query"
    MANUAL = "manual"
```

## Operations

### Create RSS Feed

**Validation Rules**:
1. `name` must be unique across all sources
2. `url` must be a valid RSS/Atom feed (validated via feedparser)
3. `url` must not already exist for another RSS source

**Default Values**:
- `type`: SourceType.RSS
- `is_active`: True
- `trust_score`: 0.5
- `total_surfaced`: 0
- `total_approved`: 0
- `total_rejected`: 0

### Read RSS Feeds

**Query Pattern**:
```python
sources = session.query(Source).filter(
    Source.type == SourceType.RSS
).order_by(Source.name).all()
```

**Display Fields**:
- name, url, is_active, trust_score
- total_surfaced, total_approved, total_rejected
- last_fetched, notes

### Update (Pause/Resume)

**Pause**: Set `is_active = False`
**Resume**: Set `is_active = True`

The `rss_fetcher.py` service already filters by `is_active`:
```python
sources = session.query(Source).filter(
    Source.type == SourceType.RSS,
    Source.is_active == True
).all()
```

### Delete RSS Feed

**Constraint**: Article.source_id has `ondelete="RESTRICT"`

**Behavior**:
- If source has associated articles: Deletion fails with FK violation
- If source has no articles: Source is deleted

**Recommended UI Approach**:
1. Check if articles exist for this source
2. If yes: Show error "Cannot delete source with existing articles"
3. If no: Delete with confirmation

## State Transitions

```
┌─────────────┐     pause      ┌─────────────┐
│   Active    │ ──────────────▶│   Paused    │
│ is_active=T │                │ is_active=F │
└─────────────┘ ◀────────────── └─────────────┘
                    resume
```

## Migration Requirements

**No migrations required.** All fields exist in current schema.

Verified against: `migrations/versions/ba6e853ec41a_initial_schema.py`

