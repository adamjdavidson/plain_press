# Implementation Tasks: Unreject Article Button

**Feature**: 007-unreject-article  
**Date**: 2025-11-29  
**Plan**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md)

## Task Summary

| Phase | Tasks | Parallel |
|-------|-------|----------|
| Phase 1: Setup | 1 | 0 |
| Phase 2: Foundational | 2 | 0 |
| Phase 3: US1 - Rejection Analysis | 2 | 0 |
| Phase 4: US2 - Article Journey | 1 | 1 |
| Phase 5: US3 - Run Detail | 1 | 1 |
| Phase 6: Polish | 1 | 0 |
| **Total** | **8** | **2** |

---

## Phase 1: Setup

No setup tasks required - using existing Flask application structure.

---

## Phase 2: Foundational

These tasks create the shared backend functionality used by all user stories.

- [x] T001 Add `unreject_article` route to `app/routes.py` per contract spec
- [x] T002 Ensure flash message support exists in admin templates

**Completion Gate**: Route responds to POST requests and updates article status correctly.

---

## Phase 3: User Story 1 - Rejection Analysis (P1)

**Goal**: John can unreject articles from the rejection analysis page.

**Independent Test**: Visit `/admin/filter-runs/<run_id>/rejections/<filter_name>`, click "Unreject" on any article, verify article status changes to pending.

### Tasks

- [x] T003 [US1] Add unreject button form to `app/templates/admin/rejection_analysis.html`
- [x] T004 [US1] Style button with success/green color for positive action

**Completion Gate**: Clicking "Unreject" on rejection analysis page changes article to pending with flash confirmation.

---

## Phase 4: User Story 2 - Article Journey (P2)

**Goal**: John can unreject articles from the article journey detail view.

**Independent Test**: Visit `/admin/filter-runs/<run_id>/article/<url>`, click "Unreject" button, verify article becomes pending.

### Tasks

- [x] T005 [P] [US2] Add unreject button form to `app/templates/admin/article_journey.html` (show only for rejected articles)

**Completion Gate**: Clicking "Unreject" on article journey page changes article to pending.

---

## Phase 5: User Story 3 - Run Detail (P3)

**Goal**: John can unreject articles from the pipeline run detail/funnel view.

**Independent Test**: From run detail page, click "Unreject" on any rejected article and verify status change.

### Tasks

- [x] T006 [P] [US3] Add unreject button to rejected articles in `app/templates/admin/filter_run_detail.html`

**Completion Gate**: Clicking "Unreject" on run detail page changes article to pending.

---

## Phase 6: Polish & Cross-Cutting

- [x] T007 Manual testing: verify unreject works across all three views and handles edge cases (already pending, not found)

---

## Dependencies

```
Phase 2 (Foundational) ─┬─> Phase 3 (US1) ─> Phase 6 (Polish)
                        ├─> Phase 4 (US2) ─┘
                        └─> Phase 5 (US3) ─┘
```

**User Story Independence**:
- US1, US2, US3 can be implemented in parallel after Phase 2
- Each story only requires adding a button to its respective template
- All stories share the same backend route (T001)

## Parallel Execution

After completing Phase 2 (Foundational), the following can run in parallel:

**Parallel Group A** (after T002):
- T005 [US2] - Article journey button
- T006 [US3] - Run detail button

Note: T003-T004 [US1] should complete first as the primary use case.

## Implementation Strategy

### MVP Scope (Recommended)
- **Phase 2 + Phase 3 (US1)** = Core functionality
- Delivers: Unreject from rejection analysis page (primary use case)
- Estimated: 15-20 minutes implementation

### Full Scope
- All phases including US2 and US3
- Delivers: Unreject from all admin views
- Estimated: 30-40 minutes total

### Incremental Delivery
1. Deploy after US1 complete → John can start using immediately
2. Add US2, US3 in subsequent deploys as convenience features

