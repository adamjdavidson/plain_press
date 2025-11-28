# Implementation Plan: RSS Feed Management

**Branch**: `005-rss-feed-management` | **Date**: 2025-11-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-rss-feed-management/spec.md`

## Summary

Build an admin interface for managing RSS feed sources. The editor can add new RSS feeds by pasting a URL and name, view all existing feeds with performance metrics, pause/resume feeds to temporarily disable fetching, and delete feeds with confirmation. This extends the existing `/admin/articles` pattern to source management.

## Technical Context

**Language/Version**: Python 3.11 (per existing codebase)  
**Primary Dependencies**: Flask, SQLAlchemy, feedparser (all existing)  
**Storage**: PostgreSQL (existing Source model)  
**Testing**: pytest (contract/, integration/)  
**Target Platform**: Linux server (Railway hosting)  
**Project Type**: Web application (Flask with Jinja2 templates)  
**Performance Goals**: Page load < 2s, operations < 1s (per success criteria)  
**Constraints**: Single-user system, no authentication beyond basic access  
**Scale/Scope**: ~40 RSS sources currently, expected growth to ~100

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify alignment with `.specify/memory/constitution.md`:

- [x] **Single-User Simplicity**: Simple admin page for John's workflow. No multi-user features, no complex permissions. Three actions: add, pause/resume, delete.
- [x] **Volume Over Precision**: N/A - This feature manages sources, not filtering. Does not affect candidate volume.
- [x] **Cost Discipline**: Zero additional API costs. Uses existing Flask routes, templates, and database. No new services required.
- [x] **Reliability Over Performance**: CRUD operations persist to database immediately. feedparser validation is synchronous and safe.

**Violations**: None. Feature fully aligns with constitution.

## Project Structure

### Documentation (this feature)

```text
specs/005-rss-feed-management/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── api.md           # REST API contract
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
app/
├── models.py            # Source model (existing, no changes)
├── routes.py            # Add /admin/sources routes
├── services/
│   └── rss_fetcher.py   # Existing (uses Source.is_active filter)
└── templates/
    └── admin/
        ├── articles.html    # Existing pattern to follow
        └── sources.html     # NEW: RSS feed management page

tests/
├── contract/
│   └── test_rss_fetch.py    # Existing RSS tests
├── integration/
│   └── test_source_management.py  # NEW: Source CRUD tests
└── unit/                    # No unit tests needed (simple CRUD)
```

**Structure Decision**: Follows existing Flask monolith structure. New code adds routes to `routes.py` and a single template `sources.html`. No new services needed - feedparser already handles validation.

## Complexity Tracking

> No violations to document. Feature uses existing patterns with minimal additions.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | — | — |
