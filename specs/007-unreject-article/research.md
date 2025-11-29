# Research: Unreject Article Button

**Feature**: 007-unreject-article  
**Date**: 2025-11-29

## Overview

This is a straightforward feature with no significant technical unknowns. Research focused on existing patterns in the codebase.

## Decision 1: Request Method

**Decision**: Use POST with form submission  
**Rationale**: 
- Follows REST conventions (state-changing action = POST)
- Works without JavaScript
- Existing admin routes use this pattern
- CSRF protection via Flask-WTF if needed later

**Alternatives considered**:
- AJAX/fetch: More complex, requires JavaScript, no clear benefit for single-user admin
- GET with redirect: Violates REST conventions, allows accidental triggering

## Decision 2: Article Identification

**Decision**: Use article URL (external_url) as identifier  
**Rationale**:
- Already displayed in all admin views
- Unique constraint in database
- URL-safe when properly encoded
- Avoids exposing internal UUIDs

**Alternatives considered**:
- Article UUID: Works but UUIDs not shown in current templates
- Article ID (int): Not used in this schema (UUID-based)

## Decision 3: Post-Action Redirect

**Decision**: Redirect to HTTP Referer (or fallback to filter-runs list)  
**Rationale**:
- User stays in context after action
- Simple implementation
- Standard pattern for admin actions

**Alternatives considered**:
- Always redirect to articles list: Loses context
- Return JSON for AJAX: Over-engineering for single-user admin

## Decision 4: Status Update

**Decision**: Update both `status` (to PENDING) and `filter_status` (to PASSED)  
**Rationale**:
- Article becomes candidate for email selection (`status=PENDING`)
- Article won't be re-processed by filter worker (`filter_status=PASSED`)
- Consistent with passed articles from pipeline

**Alternatives considered**:
- Only update `status`: Would leave `filter_status=REJECTED`, confusing in admin views
- Reset to `UNFILTERED`: Would cause re-filtering, not desired

## Existing Patterns Reference

Reviewed existing admin routes in `app/routes.py`:
- `/admin/filter-runs/<run_id>/rejections/<filter_name>` - Rejection analysis view
- `/admin/filter-runs/<run_id>/article/<path:article_url>` - Article journey view
- Standard pattern: Query database, render Jinja2 template

No existing POST actions in filter-runs admin, but feedback routes use form POST pattern.

