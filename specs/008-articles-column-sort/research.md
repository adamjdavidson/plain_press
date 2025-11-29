# Research: Sortable Article Columns

**Feature**: 008-articles-column-sort  
**Date**: 2025-11-29

## Decisions

### 1. Server-side vs Client-side Sorting

**Decision**: Server-side sorting via SQLAlchemy

**Rationale**:
- Consistent with existing pagination (pages show correct sorted results)
- Works with filters (search, status, source)
- No JavaScript complexity
- PostgreSQL handles sort efficiently for ~2,000 articles

**Alternatives considered**:
- Client-side JavaScript sorting: Rejected because it only works on current page, not full dataset

### 2. Sort State Persistence

**Decision**: URL query parameters (`?sort=date&dir=desc`)

**Rationale**:
- Shareable/bookmarkable URLs
- Works with browser back/forward
- Preserves existing filter parameters
- Standard pattern for server-side sorting

**Alternatives considered**:
- Session storage: Rejected because sort should be visible in URL
- Cookies: Rejected for same reason

### 3. Default Sort Column

**Decision**: Date (discovered_at) descending

**Rationale**:
- User specifically requested seeing "more recent or older articles"
- Newest articles most relevant for daily workflow
- Matches spec FR-007

**Alternatives considered**:
- Keep current filter_score default: Rejected per explicit user request

### 4. Null Value Handling

**Decision**: PostgreSQL `NULLS LAST`

**Rationale**:
- Articles with missing values should not appear at top
- Consistent behavior across all columns
- SQLAlchemy supports `nullslast()` modifier

**Alternatives considered**:
- Default null behavior: Inconsistent across databases

## Implementation Notes

### SQLAlchemy Sort Mapping

```python
SORT_COLUMNS = {
    'date': Article.discovered_at,
    'score': Article.filter_score,
    'status': Article.status,
    'source': Article.source_name,
    'headline': Article.headline,
}

DEFAULT_DIRECTIONS = {
    'date': 'desc',      # Newest first
    'score': 'desc',     # Highest first
    'status': 'asc',     # Alphabetical
    'source': 'asc',     # Alphabetical
    'headline': 'asc',   # Alphabetical
}
```

### URL Parameter Examples

- Default: `/admin/articles` (same as `?sort=date&dir=desc`)
- By score: `/admin/articles?sort=score&dir=desc`
- With filters: `/admin/articles?status=pending&sort=date&dir=asc`

