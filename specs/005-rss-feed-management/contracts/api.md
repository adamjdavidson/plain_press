# API Contract: RSS Feed Management

**Feature**: 005-rss-feed-management  
**Date**: 2025-11-28  
**Base URL**: `/admin/sources`

## Overview

REST API endpoints for managing RSS feed sources. Follows the pattern established by `/admin/articles` routes.

---

## Endpoints

### GET /admin/sources

List all RSS feed sources.

**Response**: HTML page with source list

**Query Parameters** (optional):
| Parameter | Type | Description |
|-----------|------|-------------|
| status | string | Filter by "active" or "paused" |
| sort | string | Sort by "name", "trust_score", "last_fetched" (default: name) |

**Response Body**: Rendered HTML template `admin/sources.html`

**Template Context**:
```python
{
    "sources": [Source],      # List of RSS sources
    "stats": {
        "total": int,         # Total RSS sources
        "active": int,        # Active sources
        "paused": int,        # Paused sources
    },
    "filters": {
        "status": str,        # Current filter value
        "sort": str,          # Current sort value
    }
}
```

---

### POST /admin/sources

Add a new RSS feed source.

**Request**: Form data (application/x-www-form-urlencoded)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Display name for the feed |
| url | string | Yes | RSS/Atom feed URL |
| notes | string | No | Optional notes about the source |

**Validation**:
1. `name` must not be empty
2. `name` must be unique
3. `url` must be a valid URL format
4. `url` must point to a valid RSS/Atom feed
5. `url` must not already exist for another RSS source

**Success Response**: Redirect to GET /admin/sources with flash message

**Error Response**: Re-render form with error messages

**Error Cases**:
| Error | Message |
|-------|---------|
| Empty name | "Feed name is required" |
| Duplicate name | "A source with this name already exists" |
| Invalid URL format | "Please enter a valid URL" |
| Not a valid feed | "URL does not point to a valid RSS/Atom feed" |
| Duplicate URL | "This feed URL already exists" |

---

### POST /admin/sources/{source_id}/pause

Pause an active RSS feed.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| source_id | UUID | Source identifier |

**Request Body**: None

**Success Response**: 
```json
{
    "success": true,
    "is_active": false
}
```

**Error Response**:
```json
{
    "error": "Source not found"
}
```
Status: 404

---

### POST /admin/sources/{source_id}/resume

Resume a paused RSS feed.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| source_id | UUID | Source identifier |

**Request Body**: None

**Success Response**:
```json
{
    "success": true,
    "is_active": true
}
```

**Error Response**:
```json
{
    "error": "Source not found"
}
```
Status: 404

---

### POST /admin/sources/{source_id}/delete

Delete an RSS feed source.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| source_id | UUID | Source identifier |

**Request Body**: None

**Preconditions**:
- Source must exist
- Source must have no associated articles (FK constraint)

**Success Response**:
```json
{
    "success": true
}
```

**Error Responses**:

Source not found:
```json
{
    "error": "Source not found"
}
```
Status: 404

Has articles (FK constraint):
```json
{
    "error": "Cannot delete source with existing articles. Pause it instead."
}
```
Status: 400

---

## Data Types

### Source Object (JSON representation)

```json
{
    "id": "uuid-string",
    "name": "Feed Name",
    "type": "rss",
    "url": "https://example.com/feed.xml",
    "is_active": true,
    "trust_score": 0.65,
    "total_surfaced": 142,
    "total_approved": 23,
    "total_rejected": 45,
    "last_fetched": "2025-11-28T08:00:00Z",
    "notes": "Optional notes",
    "created_at": "2025-11-01T10:00:00Z",
    "updated_at": "2025-11-28T08:00:00Z"
}
```

---

## Security Considerations

- No authentication required (single-user system per constitution)
- All routes accessible via same origin only (no CORS)
- CSRF protection via Flask-WTF (if forms use WTForms)

---

## Integration with Existing Systems

### RSS Fetcher Service

The `fetch_all_rss_sources()` function in `app/services/rss_fetcher.py` already filters by `is_active`:

```python
sources = session.query(Source).filter(
    Source.type == SourceType.RSS,
    Source.is_active == True  # Respects pause state
).all()
```

No changes required to fetcher service.

### Admin Navigation

Add link to source management in admin UI (if navigation exists) or document URL for John.

