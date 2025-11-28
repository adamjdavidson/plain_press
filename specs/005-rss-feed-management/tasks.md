# Tasks: RSS Feed Management

**Input**: Design documents from `/specs/005-rss-feed-management/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md

**Tests**: Integration tests included per constitution (Principle IV) - required for core workflows.

**Organization**: Tasks grouped by user story. US1 and US2 are combined (both P1, same page).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Minimal setup - infrastructure already exists

- [x] T001 Verify Source model has all required fields in app/models.py (read-only check)
- [x] T002 Review existing admin/articles.html template pattern in app/templates/admin/articles.html

**Checkpoint**: Confirmed existing infrastructure supports feature

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Helper function for RSS validation needed by add feature

- [x] T003 Create RSS URL validation helper function in app/routes.py (uses feedparser to validate URL returns valid RSS/Atom)

**Checkpoint**: Foundation ready - user story implementation can begin

---

## Phase 3: User Story 1 + 2 - Add & View RSS Feeds (Priority: P1) 🎯 MVP

**Goal**: Editor can view all RSS feeds and add new ones via a single admin page

**Independent Test**: Navigate to /admin/sources, see existing feeds listed, add a new feed URL, verify it appears in list

### Implementation for User Stories 1 & 2

- [x] T004 [US1+2] Create sources.html template with feed list and add form in app/templates/admin/sources.html
- [x] T005 [US1+2] Implement GET /admin/sources route (list all RSS sources with stats) in app/routes.py
- [x] T006 [US1+2] Implement POST /admin/sources route (add new feed with validation) in app/routes.py
- [x] T007 [US1+2] Add flash message support for success/error feedback in app/routes.py
- [x] T008 [US1+2] Add duplicate URL check (query existing RSS sources by URL) in app/routes.py
- [x] T009 [US1+2] Add duplicate name check (query existing sources by name) in app/routes.py

**Checkpoint**: MVP complete - editor can view feeds and add new ones

---

## Phase 4: User Story 3 - Pause/Resume RSS Feed (Priority: P2)

**Goal**: Editor can temporarily disable feeds without deleting them

**Independent Test**: Click Pause on active feed, verify shows as paused; click Resume, verify shows as active

### Implementation for User Story 3

- [x] T010 [P] [US3] Add Pause/Resume buttons to feed list rows in app/templates/admin/sources.html
- [x] T011 [US3] Implement POST /admin/sources/{id}/pause route in app/routes.py
- [x] T012 [US3] Implement POST /admin/sources/{id}/resume route in app/routes.py
- [x] T013 [US3] Add JavaScript for async pause/resume with UI update in app/templates/admin/sources.html

**Checkpoint**: User Story 3 complete - pause/resume works independently

---

## Phase 5: User Story 4 - Delete RSS Feed (Priority: P3)

**Goal**: Editor can permanently remove unwanted feeds

**Independent Test**: Click Delete on feed with no articles, confirm, verify feed removed from list

### Implementation for User Story 4

- [x] T014 [P] [US4] Add Delete button with confirmation dialog to feed list in app/templates/admin/sources.html
- [x] T015 [US4] Implement POST /admin/sources/{id}/delete route in app/routes.py
- [x] T016 [US4] Add FK constraint check (show error if source has articles) in app/routes.py

**Checkpoint**: User Story 4 complete - delete with confirmation works

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Testing and final touches

- [x] T017 [P] Create integration tests for source CRUD in tests/integration/test_source_management.py
- [x] T018 [P] Add navigation link to /admin/sources from /admin/articles in app/templates/admin/articles.html
- [ ] T019 Manual testing: Run through quickstart.md checklist
- [x] T020 Verify existing RSS fetcher respects is_active flag (read-only check of app/services/rss_fetcher.py)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - verification only
- **Foundational (Phase 2)**: Depends on Setup - creates validation helper
- **US1+2 (Phase 3)**: Depends on Foundational - core MVP
- **US3 (Phase 4)**: Depends on US1+2 template existing
- **US4 (Phase 5)**: Depends on US1+2 template existing
- **Polish (Phase 6)**: Depends on all user stories complete

### User Story Dependencies

- **US1+2 (P1)**: Can start after Foundational - MVP target
- **US3 (P2)**: Extends US1+2 template with pause/resume buttons
- **US4 (P3)**: Extends US1+2 template with delete button

### Task Dependencies Within Phases

**Phase 3 (US1+2)**:
```
T004 (template) → T005 (GET route) → T006 (POST route) → T007/T008/T009 (validation)
```

**Phase 4 (US3)**:
```
T010 (buttons) can run parallel with T011/T012 (routes)
T013 (JS) depends on T010, T011, T012
```

**Phase 5 (US4)**:
```
T014 (button) can run parallel with T015/T016 (route)
```

### Parallel Opportunities

- T001, T002 can run in parallel (read-only checks)
- T010 can run parallel with T011, T012 (different concerns)
- T014 can run parallel with T015, T016 (different concerns)
- T017, T018 can run parallel (different files)

---

## Parallel Example: Phase 4 (User Story 3)

```bash
# These can run in parallel:
Task T010: "Add Pause/Resume buttons to feed list rows in app/templates/admin/sources.html"
Task T011: "Implement POST /admin/sources/{id}/pause route in app/routes.py"
Task T012: "Implement POST /admin/sources/{id}/resume route in app/routes.py"

# Then sequentially:
Task T013: "Add JavaScript for async pause/resume with UI update" (depends on T010, T011, T012)
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup (verification)
2. Complete Phase 2: Foundational (RSS validation helper)
3. Complete Phase 3: US1+2 (view + add feeds)
4. **STOP and VALIDATE**: Test add/view independently
5. Deploy if ready - editor can now manage feeds!

### Incremental Delivery

1. Setup + Foundational → Ready to build
2. US1+2 (Add + View) → **MVP - Deploy/Demo**
3. US3 (Pause/Resume) → Enhanced control → Deploy
4. US4 (Delete) → Full CRUD → Deploy
5. Polish → Tests + navigation → Final release

### Single Developer Flow

```
Phase 1 → Phase 2 → Phase 3 (MVP!) → Phase 4 → Phase 5 → Phase 6
```

---

## Files Modified/Created

| File | Action | Phase |
|------|--------|-------|
| app/routes.py | Modify (add 5 routes + validation helper) | 2, 3, 4, 5 |
| app/templates/admin/sources.html | Create (new template) | 3, 4, 5 |
| app/templates/admin/articles.html | Modify (add nav link) | 6 |
| tests/integration/test_source_management.py | Create (new tests) | 6 |

---

## Notes

- No database migrations needed (Source model exists)
- No new services needed (feedparser already available)
- Follows /admin/articles pattern for consistency
- Tests deferred to Phase 6 (integration tests for core workflow per constitution)
- Each phase adds deployable value

