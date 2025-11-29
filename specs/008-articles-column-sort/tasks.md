# Implementation Tasks: Sortable Article Columns

**Feature**: 008-articles-column-sort  
**Date**: 2025-11-29  
**Plan**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md)

## Task Summary

| Phase | Tasks | Parallel |
|-------|-------|----------|
| Phase 1: Setup | 0 | 0 |
| Phase 2: Foundational | 2 | 0 |
| Phase 3: US1 - Date Sort | 2 | 0 |
| Phase 4: US2-4 - Other Columns | 3 | 3 |
| Phase 5: Polish | 1 | 0 |
| **Total** | **8** | **3** |

---

## Phase 1: Setup

No setup tasks required - using existing Flask application structure.

---

## Phase 2: Foundational

These tasks create the shared sorting infrastructure used by all user stories.

- [x] T001 Add sort column mapping and default directions in `app/routes.py`
- [x] T002 Update `admin_articles()` route to parse sort params and apply sort order in `app/routes.py`

**Completion Gate**: Route accepts `?sort=date&dir=desc` and returns sorted results.

---

## Phase 3: User Story 1 - Sort by Date (P1)

**Goal**: John can click "Added" column header to sort articles by date.

**Independent Test**: Visit `/admin/articles`, click "Added" column header, verify articles reorder by date (newest first), click again to reverse.

### Tasks

- [x] T003 [US1] Add sortable column CSS styles to `app/templates/admin/articles.html`
- [x] T004 [US1] Convert "Added" column header to clickable sort link with indicator in `app/templates/admin/articles.html`

**Completion Gate**: Clicking "Added" header sorts by date, visual indicator shows direction.

---

## Phase 4: User Stories 2-4 - Other Columns (P2-P4)

**Goal**: John can sort by Score, Status, Source, and Headline columns.

**Independent Test**: Click each column header, verify sorting works and indicator shows.

### Tasks

- [x] T005 [P] [US2] Convert "Score" column header to clickable sort link in `app/templates/admin/articles.html`
- [x] T006 [P] [US3] Convert "Status" column header to clickable sort link in `app/templates/admin/articles.html`
- [x] T007 [P] [US4] Convert "Source" and "Headline" columns to clickable sort links in `app/templates/admin/articles.html`

**Completion Gate**: All five sortable columns work with visual indicators.

---

## Phase 5: Polish & Cross-Cutting

- [x] T008 Manual testing: verify sort works with filters, pagination, and handles edge cases (nulls, empty values)

---

## Dependencies

```
Phase 2 (Foundational) ─> Phase 3 (US1) ─> Phase 4 (US2-4) ─> Phase 5 (Polish)
                                          └─> T005, T006, T007 can run in parallel
```

**Key Dependencies**:
- T001, T002 must complete before any template changes (backend must accept sort params)
- T003, T004 establish the template pattern used by T005-T007
- T005, T006, T007 are independent (different columns, same file but different sections)

## Parallel Execution

After completing Phase 3 (US1), the following can run in parallel:

**Parallel Group A** (after T004):
- T005 [US2] - Score column
- T006 [US3] - Status column  
- T007 [US4] - Source and Headline columns

## Implementation Strategy

### MVP Scope (Recommended)
- **Phase 2 + Phase 3 (US1)** = Core functionality
- Delivers: Date sorting (primary user request)
- Estimated: 10-15 minutes implementation

### Full Scope
- All phases including US2-4
- Delivers: All 5 sortable columns
- Estimated: 20-25 minutes total

### Incremental Delivery
1. Deploy after US1 complete → John can sort by date immediately
2. Add remaining columns in one batch (they're simple additions)

