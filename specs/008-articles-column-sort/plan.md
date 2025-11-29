# Implementation Plan: Sortable Article Columns

**Branch**: `008-articles-column-sort` | **Date**: 2025-11-29 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/008-articles-column-sort/spec.md`

## Summary

Add sortable column headers to the `/admin/articles` page. Clicking a column header sorts articles by that column; clicking again reverses the direction. Sort state is maintained via URL parameters (`sort` and `dir`) for consistency with pagination and filters.

**Technical approach**: Server-side sorting via SQLAlchemy `order_by()`. Column headers become clickable links that preserve existing filter parameters while adding/toggling sort parameters.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: Flask, SQLAlchemy, Jinja2  
**Storage**: PostgreSQL  
**Testing**: pytest  
**Target Platform**: Railway (Linux server)  
**Project Type**: Web application (Flask monolith)  
**Performance Goals**: Sort response under 1 second for ~2,000 articles  
**Constraints**: Must work with existing pagination and filters  
**Scale/Scope**: Single admin user (John)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify alignment with `.specify/memory/constitution.md`:

- [x] **Single-User Simplicity**: Helps John quickly find articles by date/score. No added complexity for theoretical users.
- [x] **Volume Over Precision**: Does not affect filtering or candidate volume.
- [x] **Reliability Over Performance**: No external API calls. Simple database query modification.

**Violations**: None. This feature directly supports John's workflow.

## Project Structure

### Documentation (this feature)

```text
specs/008-articles-column-sort/
├── plan.md              # This file
├── research.md          # Phase 0 output (minimal - simple feature)
├── contracts/           # Phase 1 output
│   └── admin-routes.md  # Updated articles route
└── quickstart.md        # Implementation guide
```

### Source Code (repository root)

```text
app/
├── routes.py            # Modify admin_articles() to support sort params
└── templates/
    └── admin/
        └── articles.html  # Add clickable sort headers with indicators
```

**Structure Decision**: Existing Flask app structure. Modify one route and one template.

## Key Design Decisions

1. **Server-side sorting**: Sort via SQLAlchemy `order_by()` for consistency with pagination. No JavaScript sorting.

2. **URL parameters**: `?sort=<column>&dir=<asc|desc>` preserves sort state across page loads and pagination.

3. **Column mapping**: Map URL column names to SQLAlchemy model attributes:
   - `date` → `Article.discovered_at`
   - `score` → `Article.filter_score`
   - `status` → `Article.status`
   - `source` → `Article.source_name`
   - `headline` → `Article.headline`

4. **Default sort**: Change from `filter_score.desc()` to `discovered_at.desc()` (newest first) as per spec FR-007.

5. **Visual indicators**: CSS arrows (▲/▼) on sorted column header.

6. **Null handling**: Use `NULLS LAST` for PostgreSQL to push empty values to the end.

## Complexity Tracking

No violations - feature is simple and aligned with constitution.
