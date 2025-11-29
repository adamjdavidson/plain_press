# API Contract: Admin Articles Route

**Feature**: 008-articles-column-sort  
**Date**: 2025-11-29

## GET /admin/articles

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| status | string | No | "" | Filter by article status (pending, emailed, good, rejected, published) |
| min_score | float | No | "" | Filter by minimum filter score |
| source | string | No | "" | Filter by source name |
| search | string | No | "" | Search in headline |
| page | int | No | 1 | Page number for pagination |
| **sort** | string | No | "date" | Column to sort by: date, score, status, source, headline |
| **dir** | string | No | "desc" | Sort direction: asc, desc |

### Sort Column Mapping

| URL Value | Database Column | Default Direction |
|-----------|-----------------|-------------------|
| date | discovered_at | desc (newest first) |
| score | filter_score | desc (highest first) |
| status | status | asc (alphabetical) |
| source | source_name | asc (alphabetical) |
| headline | headline | asc (alphabetical) |

### Response

HTML page rendering `admin/articles.html` with:

```python
{
    'articles': [...],  # List of Article objects, sorted per parameters
    'stats': {...},     # Count statistics
    'sources': [...],   # Unique source names for filter dropdown
    'filters': {
        'status': str,
        'min_score': str,
        'source': str,
        'search': str,
    },
    'sort': str,        # NEW: Current sort column
    'dir': str,         # NEW: Current sort direction
    'page': int,
    'total_pages': int,
}
```

### Example Requests

```
# Default (newest first)
GET /admin/articles

# By score (highest first)
GET /admin/articles?sort=score&dir=desc

# Oldest first
GET /admin/articles?sort=date&dir=asc

# Combined with filters
GET /admin/articles?status=pending&sort=score&dir=desc&page=2

# Combined with search
GET /admin/articles?search=amish&sort=date&dir=desc
```

### Invalid Parameters

- Invalid `sort` value: Falls back to "date"
- Invalid `dir` value: Falls back to column's default direction
- No error responses, graceful fallback to defaults

