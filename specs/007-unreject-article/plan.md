# Implementation Plan: Unreject Article Button

**Branch**: `007-unreject-article` | **Date**: 2025-11-29 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/007-unreject-article/spec.md`

## Summary

Add "Unreject" buttons to the filter runs admin pages that allow John to override filter rejections with a single click. The button updates an article's `status` to "pending" and `filter_status` to "passed", making it a candidate for the next email batch.

**Technical approach**: Add a new Flask route that accepts POST requests to unreject articles by URL. Add inline forms with buttons to the existing Jinja2 templates. Use simple form POST with redirect for reliability (AJAX optional enhancement).

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: Flask, SQLAlchemy, Jinja2  
**Storage**: PostgreSQL  
**Testing**: pytest  
**Target Platform**: Railway (Linux server)  
**Project Type**: Web application (Flask monolith)  
**Performance Goals**: Button click responds within 2 seconds  
**Constraints**: Single-user system, no authentication beyond basic  
**Scale/Scope**: Single admin user (John)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify alignment with `.specify/memory/constitution.md`:

- [x] **Single-User Simplicity**: Helps John's workflow by allowing quick override of filter decisions. No added complexity for theoretical users.
- [x] **Volume Over Precision**: Supports catching false negatives by enabling manual rescue of incorrectly rejected articles.
- [x] **Reliability Over Performance**: Simple database update with no external API calls. State change persisted immediately.

**Violations**: None. This feature directly supports constitution principles.

## Project Structure

### Documentation (this feature)

```text
specs/007-unreject-article/
├── plan.md              # This file
├── research.md          # Phase 0 output (minimal - simple feature)
├── contracts/           # Phase 1 output
│   └── admin-routes.md  # New unreject endpoint
└── quickstart.md        # Implementation guide
```

### Source Code (repository root)

```text
app/
├── routes.py            # Add POST /admin/unreject-article route
└── templates/
    └── admin/
        ├── rejection_analysis.html  # Add unreject button
        ├── article_journey.html     # Add unreject button
        └── filter_run_detail.html   # Add unreject button (optional)
```

**Structure Decision**: Existing Flask app structure. Add one new route and modify three templates.

## Key Design Decisions

1. **Form POST over AJAX**: Use simple HTML form POST for reliability. Page refreshes after action to show updated state. AJAX can be added later as enhancement.

2. **URL-based identification**: Use article URL (external_url) as identifier since it's unique and visible in the admin views.

3. **Redirect back to referring page**: After unreject, redirect to the page user came from using HTTP Referer header.

4. **Button styling**: Use distinct "Unreject" button with green/success color to indicate positive action.

5. **Success feedback**: Flash message after redirect confirms action succeeded.

## Complexity Tracking

No violations - feature is simple and aligned with constitution.
