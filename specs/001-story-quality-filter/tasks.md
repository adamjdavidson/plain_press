# Tasks: Story Quality Filter

**Input**: Design documents from `/specs/001-story-quality-filter/`  
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, quickstart.md ✓

**Tests**: Integration tests included per constitution (Principle IV) - core filtering workflow modification requires validation.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1, US2, US3)
- Exact file paths included

## Path Conventions

- Single Flask application structure per plan.md
- Models: `app/models.py`
- Services: `app/services/claude_filter.py`
- Migrations: `migrations/versions/`
- Tests: `tests/integration/`

---

## Phase 1: Setup

**Purpose**: Verify prerequisites and prepare for implementation

- [x] T001 Verify Python 3.11+ environment is active in `/home/adamd/projects/amish_news`
- [x] T002 Verify PostgreSQL database is accessible and migrations are current via `alembic current`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database schema and model changes that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Create Alembic migration for quality filter fields via `alembic revision -m "add_quality_filter_fields"` in `migrations/versions/`
- [x] T004 Implement migration upgrade() to add `content_type VARCHAR(50)` and `wow_score FLOAT` columns in generated migration file
- [x] T005 Implement migration downgrade() to drop both columns in generated migration file
- [x] T006 Run migration via `alembic upgrade head`
- [x] T007 Add `content_type` field to Article class in `app/models.py`
- [x] T008 Add `wow_score` field to Article class in `app/models.py`
- [x] T009 Add `WOW_SCORE_THRESHOLD` configuration constant in `app/services/claude_filter.py`

**Checkpoint**: Schema ready - user story implementation can begin

---

## Phase 3: User Story 1 - Filter Out Non-News Content (Priority: P1) 🎯 MVP

**Goal**: Strictly reject event listings, directory pages, about pages, and other non-news content before editorial evaluation

**Independent Test**: Run filter on batch of known non-news URLs → all rejected with content_type reason and score 0.0

### Integration Test for User Story 1

- [x] T010 [US1] Create integration test file `tests/integration/test_filtering_quality.py`
- [x] T011 [US1] Implement `test_event_listing_rejected()` - verify event listing content gets content_type="event_listing" and score 0.0 in `tests/integration/test_filtering_quality.py`
- [x] T012 [US1] Implement `test_about_page_rejected()` - verify about page content gets content_type="about_page" and score 0.0 in `tests/integration/test_filtering_quality.py`
- [x] T013 [US1] Implement `test_directory_page_rejected()` - verify directory content gets content_type="directory_page" and score 0.0 in `tests/integration/test_filtering_quality.py`
- [x] T014 [US1] Implement `test_news_article_passes_content_check()` - verify actual news gets content_type="news_article" in `tests/integration/test_filtering_quality.py`

### Implementation for User Story 1

- [x] T015 [US1] Update `filter_all_articles()` content type enforcement to use continue statement after rejection in `app/services/claude_filter.py`
- [x] T016 [US1] Format content_type rejection in filter_notes as "Rejected: content_type={type} | {explanation}" in `app/services/claude_filter.py`
- [x] T017 [US1] Verify existing CONTENT TYPE CLASSIFICATION prompt section is adequate in `app/services/claude_filter.py`
- [x] T018 [US1] Run US1 integration tests to verify content type filtering works

**Checkpoint**: Non-news content reliably rejected with clear reasons - US1 independently testable

---

## Phase 4: User Story 2 - Reject Boring/Mundane News (Priority: P2)

**Goal**: Evaluate news articles for "wow factor" and reject mundane/boring stories that wouldn't make someone say "wow"

**Independent Test**: Run filter on boring headlines vs delightful headlines → verify score separation and threshold filtering

### Integration Test for User Story 2

- [x] T019 [US2] Implement `test_boring_news_low_wow_score()` - verify mundane news gets low wow_score in `tests/integration/test_filtering_quality.py`
- [x] T020 [US2] Implement `test_wow_news_high_wow_score()` - verify surprising/delightful news gets high wow_score in `tests/integration/test_filtering_quality.py`
- [x] T021 [US2] Implement `test_wow_threshold_rejection()` - verify articles below WOW_SCORE_THRESHOLD are rejected in `tests/integration/test_filtering_quality.py`

### Implementation for User Story 2

- [x] T022 [US2] Add `wow_score` property (type: number) to `ARTICLE_RESULT_SCHEMA` items in `app/services/claude_filter.py`
- [x] T023 [US2] Add `wow_notes` property (type: string) to `ARTICLE_RESULT_SCHEMA` items in `app/services/claude_filter.py`
- [x] T024 [US2] Add `wow_score` and `wow_notes` to required array in `ARTICLE_RESULT_SCHEMA` in `app/services/claude_filter.py`
- [x] T025 [US2] Add WOW FACTOR EVALUATION section to `SYSTEM_PROMPT_TEMPLATE` after CONTENT TYPE section in `app/services/claude_filter.py`
- [x] T026 [US2] Include wow scoring criteria (0.8-1.0 remarkable, 0.5-0.7 interesting, 0.2-0.4 mild, 0.0-0.2 boring) in prompt
- [x] T027 [US2] Include wow examples in prompt (traffic light NOT wow-worthy, singing traffic light IS wow-worthy)
- [x] T028 [US2] Update output instructions in prompt to include wow_score and wow_notes fields
- [x] T029 [US2] Extract wow_score and wow_notes from Claude response in `filter_all_articles()` in `app/services/claude_filter.py`
- [x] T030 [US2] Add wow_score to article dict in merge loop in `app/services/claude_filter.py`
- [x] T031 [US2] Add Gate 2: wow_score threshold check after content_type check in `filter_all_articles()` in `app/services/claude_filter.py`
- [x] T032 [US2] Format wow_score rejection in filter_notes as "Rejected: wow_score={score:.2f} (threshold: {threshold}) | {wow_notes}" in `app/services/claude_filter.py`
- [x] T033 [US2] Run US2 integration tests to verify wow factor filtering works

**Checkpoint**: Boring news reliably rejected with clear wow_score reasons - US2 independently testable

---

## Phase 5: User Story 3 - See Clear Rejection Reasons (Priority: P3)

**Goal**: Ensure John can quickly understand why any story was rejected by reviewing filter_notes in admin panel

**Independent Test**: Review filter_notes for rejected articles → all contain specific, actionable rejection reasons with category and explanation

### Integration Test for User Story 3

- [x] T034 [US3] Implement `test_content_type_rejection_reason_format()` - verify filter_notes contains "Rejected: content_type=" pattern in `tests/integration/test_filtering_quality.py`
- [x] T035 [US3] Implement `test_wow_score_rejection_reason_format()` - verify filter_notes contains "Rejected: wow_score=" pattern with threshold in `tests/integration/test_filtering_quality.py`
- [x] T036 [US3] Implement `test_editorial_rejection_reason_format()` - verify filter_notes for editorial rejections contain score and reason in `tests/integration/test_filtering_quality.py`

### Implementation for User Story 3

- [x] T037 [US3] Verify content_type rejection format includes explanation from Claude in `app/services/claude_filter.py`
- [x] T038 [US3] Verify wow_score rejection format includes wow_notes explanation in `app/services/claude_filter.py`
- [x] T039 [US3] Update editorial rejection format to show "Rejected: filter_score={score:.2f} | {filter_notes}" in `app/services/claude_filter.py`
- [x] T040 [US3] Run US3 integration tests to verify rejection reason clarity

**Checkpoint**: All rejection reasons are clear and actionable - US3 independently testable

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup

- [x] T041 [P] Update article persistence in `app/services/discovery.py` to save content_type and wow_score fields
- [x] T042 Run full integration test suite via `pytest tests/integration/test_filtering_quality.py -v`
- [ ] T043 Manual test: Run `python scripts/run_daily_pipeline.py --dry-run` and verify logs show content types and wow scores
- [ ] T044 Manual test: Verify rejected articles in admin show clear filter_notes
- [x] T045 Validate implementation against `specs/001-story-quality-filter/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup
    ↓
Phase 2: Foundational (migration + model)
    ↓
    ↓ BLOCKS ALL USER STORIES
    ↓
┌───────────────────────────────────────────────┐
│  User stories can proceed after Foundational  │
│                                               │
│  US1 (P1) ──────┐                             │
│                 │                             │
│  US2 (P2) ──────┼──→ US3 (P3) depends on     │
│                 │    US1 + US2 filter_notes   │
│                 │                             │
└───────────────────────────────────────────────┘
    ↓
Phase 6: Polish (after all stories)
```

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational - Independent of US1 (different gate in filtering pipeline)
- **User Story 3 (P3)**: Depends on US1 and US2 - validates rejection reasons from both gates

### Within Each User Story

1. Integration tests written first (verify they fail)
2. Implementation tasks in order
3. Run tests to verify pass
4. Checkpoint before next story

### Parallel Opportunities

**Phase 2 (Foundational)**:
- T007 and T008 (model fields) can run in parallel [P]
- T003-T006 must be sequential (migration creation → run)

**Phase 3-4 (US1 and US2)**:
- US1 and US2 can run in parallel after Foundational (different code paths)
- Within US1: T011-T014 tests can run in parallel [P]
- Within US2: T019-T021 tests can run in parallel [P]

**Phase 6 (Polish)**:
- T041 can run in parallel with other polish tasks [P]

---

## Parallel Example: Phase 2 Model Updates

```bash
# These can be done in parallel (different fields, same file section):
Task T007: "Add content_type field to Article class in app/models.py"
Task T008: "Add wow_score field to Article class in app/models.py"
```

## Parallel Example: US1 + US2

```bash
# After Foundational complete, these story phases can proceed in parallel:

# Developer A - User Story 1:
Task T010-T018: Content type filtering

# Developer B - User Story 2:
Task T019-T033: Wow factor filtering

# Then converge for US3 (depends on both)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup ✓
2. Complete Phase 2: Foundational (migration + model)
3. Complete Phase 3: User Story 1 (content type filtering)
4. **STOP and VALIDATE**: Test US1 independently
5. Deploy if ready - non-news content now filtered!

### Incremental Delivery

| Increment | Stories | Value Delivered |
|-----------|---------|-----------------|
| MVP | US1 | Event listings, about pages, directories rejected |
| +1 | US1 + US2 | Boring/mundane news also rejected |
| Complete | US1 + US2 + US3 | Clear rejection reasons for trust verification |

### Suggested Approach

1. **Solo developer**: US1 → US2 → US3 sequentially (P1 priority order)
2. **Two developers**: US1 ∥ US2 in parallel, then US3 together
3. **Stop after MVP**: If US1 alone solves most of the "terrible stories" problem, US2 and US3 can wait

---

## Notes

- [P] tasks = different files or independent code sections
- [Story] label tracks which user story each task serves
- Each story checkpoint = independently testable increment
- Constitution: Tests included because this modifies core filtering workflow
- Constitution: Cost impact negligible (~$4.50/month increase per research.md)
- Rollback: `alembic downgrade -1` + `git checkout app/models.py app/services/claude_filter.py`

