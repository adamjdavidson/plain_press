# Research: RSS Feed Management

**Feature**: 005-rss-feed-management  
**Date**: 2025-11-28

## Overview

This document consolidates research findings for implementing the RSS feed management admin interface. All technical decisions are based on existing codebase patterns.

---

## Decision 1: RSS Feed Validation Approach

**Decision**: Use feedparser library to validate RSS/Atom URLs before saving

**Rationale**: 
- feedparser is already a project dependency (used in `app/services/rss_fetcher.py`)
- It handles both RSS and Atom formats transparently
- The `bozo` flag indicates parsing errors, providing clear validation feedback
- HTTP status codes reveal connectivity/access issues

**Alternatives Considered**:
- HEAD request only: Rejected because it doesn't validate feed content
- Third-party validation service: Rejected for cost discipline (adds dependency and potential API costs)

**Implementation Pattern** (from existing `rss_fetcher.py`):
```python
result = feedparser.parse(url, request_headers={'User-Agent': USER_AGENT})
is_valid = not result.bozo and len(result.entries) >= 0
```

---

## Decision 2: Admin Page Pattern

**Decision**: Follow existing `/admin/articles` pattern for routes and templates

**Rationale**:
- Consistent UI/UX with existing admin interface
- Reuses established Flask blueprint structure
- Same styling and interaction patterns John is familiar with

**Alternatives Considered**:
- Separate admin app: Rejected for simplicity (overkill for single-user system)
- API-only with frontend framework: Rejected to maintain simple Jinja2 templating

**Reference Implementation**: `app/routes.py` lines 286-561 (admin_articles and related routes)

---

## Decision 3: Source Entity Usage

**Decision**: Use existing Source model without modifications

**Rationale**:
- Source model already has all required fields: name, type, url, is_active, trust_score, total_surfaced, total_approved, total_rejected, last_fetched, notes
- SourceType.RSS enum exists for type classification
- No database migrations needed

**Alternatives Considered**:
- New RSSFeed model: Rejected because Source already serves this purpose
- Add fields to Source: Not needed, all fields exist

**Existing Model Fields** (from `app/models.py`):
- `id`: UUID primary key
- `name`: String(200), unique
- `type`: SourceType enum (RSS, SEARCH_QUERY, MANUAL)
- `url`: String(500), nullable
- `is_active`: Boolean, default True
- `trust_score`: Float, default 0.5
- `total_surfaced`, `total_approved`, `total_rejected`: Integer counters
- `last_fetched`: DateTime
- `notes`: Text, nullable

---

## Decision 4: Delete Behavior

**Decision**: Hard delete with confirmation, preserve article references

**Rationale**:
- Article model stores `source_name` as denormalized string, so article display survives source deletion
- Foreign key `source_id` on Article has `ondelete="RESTRICT"`, so deletion will fail if articles exist
- Solution: Either handle FK constraint in UI (warn user) or change to SET NULL

**Implementation Note**: 
The FK constraint means we need to handle deletion carefully:
1. Option A: Show error if source has articles (safest)
2. Option B: Set article.source_id to NULL before deleting (allows cleanup)

**Recommendation**: Option A for Phase 1 (show error), consider Option B if needed later.

---

## Decision 5: URL Duplicate Detection

**Decision**: Check for URL uniqueness before insert using database query

**Rationale**:
- Source.url is not unique in schema (allows NULL for SEARCH_QUERY types)
- Must validate at application level for RSS sources
- Query by url and type=RSS before insert

**Implementation**:
```python
existing = session.query(Source).filter(
    Source.url == url,
    Source.type == SourceType.RSS
).first()
if existing:
    return error("Feed URL already exists")
```

---

## Decision 6: Form Handling

**Decision**: Server-side form handling with Flask-WTF patterns (or plain forms)

**Rationale**:
- Consistent with existing feedback form handling in routes.py
- No JavaScript required for basic operations
- Progressive enhancement possible for better UX

**Alternatives Considered**:
- AJAX-only API: Rejected for simplicity (requires JS, more complex error handling)
- Full SPA: Rejected (overkill for simple CRUD, violates Single-User Simplicity)

---

## Open Questions (Resolved)

| Question | Resolution |
|----------|------------|
| How to validate RSS feeds? | Use feedparser (existing dependency) |
| Where to add routes? | Extend app/routes.py with /admin/sources/* |
| New model needed? | No, use existing Source model |
| How to handle delete with FK? | Show error if articles exist (Phase 1) |
| Authentication needed? | No, single-user system |

---

## Dependencies

No new dependencies required. All functionality uses:
- Flask (existing)
- SQLAlchemy (existing)
- feedparser (existing)
- Jinja2 templates (existing)

