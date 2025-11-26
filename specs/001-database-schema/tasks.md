# Tasks: Database Schema Foundation

**Input**: Design documents from `/specs/001-database-schema/`
**Prerequisites**: plan.md (complete), spec.md (complete), data-model.md (complete), quickstart.md (complete), research.md (complete)

**Tests**: Contract and integration tests are REQUIRED per constitution's Pragmatic Testing principle (test external APIs and core workflows). This feature tests database constraints and query performance.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. However, since this is a foundational database schema feature, all models must be created together in Phase 2 (Foundational) before individual user story validation can begin.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `app/`, `tests/`, `migrations/` at repository root
- Paths follow plan.md structure decision (Flask backend-focused web application)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create project directory structure (app/, migrations/, tests/contract/, tests/integration/, tests/fixtures/, scripts/)
- [x] T002 Initialize Python project with requirements.txt including SQLAlchemy==2.0.23, Alembic==1.12.1, psycopg2-binary==2.9.9, pytest==7.4.3, pytest-postgresql==5.0.0, python-dotenv==1.0.0
- [x] T003 [P] Create .env.example with DATABASE_URL, FLASK_ENV, FLASK_DEBUG placeholders
- [x] T004 [P] Create .gitignore for Python (.env, __pycache__/, *.pyc, venv/, .pytest_cache/)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core database infrastructure that MUST be complete before ANY user story can be validated

**⚠️ CRITICAL**: No user story validation can begin until this phase is complete

- [x] T005 Create app/__init__.py with Flask app factory stub
- [x] T006 Create app/database.py with SQLAlchemy Base, engine creation function (pool_size=5, max_overflow=10, pool_pre_ping=True, pool_recycle=3600), and SessionLocal factory
- [x] T007 Initialize Alembic configuration with `alembic init migrations` command
- [x] T008 Configure migrations/env.py to import Base from app.models, load DATABASE_URL from environment, and set target_metadata=Base.metadata
- [x] T009 Update alembic.ini to remove hardcoded sqlalchemy.url (overridden by env.py)
- [x] T010 Create app/models.py with Base import and all enum classes (ArticleStatus, SourceType, FeedbackRating, RuleType, RuleSource, EmailStatus)
- [x] T011 [US1] Define Article model in app/models.py with all fields, relationships, and indexes per data-model.md
- [x] T012 [P] [US1] Define Source model in app/models.py with all fields, relationships, and indexes per data-model.md
- [x] T013 [P] [US2] Define Feedback model in app/models.py with all fields, relationships, and indexes per data-model.md
- [x] T014 [P] [US4] Define FilterRule model in app/models.py with all fields, relationships, and indexes per data-model.md
- [x] T015 [P] [US5] Define EmailBatch model in app/models.py with all fields, relationships, and indexes per data-model.md
- [x] T016 [P] [US5] Define DeepDive model in app/models.py with all fields, relationships, and indexes per data-model.md
- [x] T017 [P] [US6] Define RefinementLog model in app/models.py with all fields, relationships, and indexes per data-model.md
- [x] T018 Generate initial Alembic migration with `alembic revision --autogenerate -m "Initial schema"`
- [x] T019 Review and edit generated migration to add CHECK constraint on articles.filter_score (>= 0.0 AND <= 1.0) and CREATE EXTENSION IF NOT EXISTS pgcrypto
- [x] T020 Create local PostgreSQL database `amish_news_dev` (or configure DATABASE_URL for existing database)
- [x] T021 Run initial migration with `alembic upgrade head` to create all tables

**Checkpoint**: ✅ Foundation ready - database schema created, all tables and constraints exist

---

## Phase 3: User Story 1 - Store and Retrieve Article Candidates (Priority: P1) 🎯 MVP COMPLETE

**Goal**: Validate that articles can be persisted with all required fields, uniqueness constraints enforced, and status transitions work correctly

**Independent Test**: Insert article records with various statuses, query them back, verify uniqueness constraint prevents duplicates, confirm status transitions

### Contract Tests for User Story 1 (REQUIRED per constitution) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before migration is applied**

- [x] T022 [P] [US1] Create tests/contract/test_article_constraints.py with test for UNIQUE constraint on external_url (insert duplicate URL, verify IntegrityError raised)
- [x] T023 [P] [US1] Add test to test_article_constraints.py for NOT NULL constraints on required fields (headline, summary, amish_angle, filter_score, source_id)
- [x] T024 [P] [US1] Add test to test_article_constraints.py for CHECK constraint on filter_score (test values -0.1, 0.0, 0.5, 1.0, 1.1)
- [x] T025 [P] [US1] Add test to test_article_constraints.py for ENUM validation on article.status (test invalid status value)
- [x] T026 [P] [US1] Create tests/contract/test_relationships.py with test for Article → Source foreign key (verify RESTRICT on source deletion)

### Integration Tests for User Story 1 (REQUIRED per constitution) ⚠️

- [x] T027 [P] [US1] Create tests/integration/test_article_queries.py with test for daily email candidate query (create 100 pending articles, query top 50 by filter_score DESC, verify <1 second)
- [x] T028 [P] [US1] Add test to test_article_queries.py for article status transition (pending → emailed, verify email_batch_id set correctly)
- [x] T029 [P] [US1] Add test to test_article_queries.py for filtering articles by status (create mix of pending/emailed/good articles, query each status separately)

### Implementation for User Story 1

- [x] T030 [US1] Create tests/fixtures/sample_data.py with factory functions for creating test Article, Source, and EmailBatch instances
- [x] T031 [US1] Run contract tests for US1, verify all constraints enforced (T022-T026 should PASS)
- [x] T032 [US1] Run integration tests for US1, verify query performance meets targets (T027-T029 should PASS)

**Checkpoint**: ✅ User Story 1 validated - articles persist correctly, constraints enforced, queries performant (22 tests PASSING)

---

## Phase 4: User Story 2 - Track John's Feedback Over Time (Priority: P1)

**Goal**: Validate that feedback records link to articles correctly, one-to-one relationship enforced, and feedback queries support pattern analysis

**Independent Test**: Create feedback for articles, verify one feedback per article constraint, query feedback by date ranges and rating types

### Contract Tests for User Story 2 (REQUIRED per constitution) ⚠️

- [ ] T033 [P] [US2] Add test to tests/contract/test_relationships.py for Article → Feedback one-to-one relationship (create article, add feedback, attempt second feedback, verify IntegrityError)
- [ ] T034 [P] [US2] Add test to tests/contract/test_relationships.py for Feedback → Article CASCADE on delete (create article + feedback, delete article, verify feedback deleted)
- [ ] T035 [P] [US2] Add test to tests/contract/test_article_constraints.py for ENUM validation on feedback.rating (test invalid rating value)

### Integration Tests for User Story 2 (REQUIRED per constitution) ⚠️

- [ ] T036 [P] [US2] Create tests/integration/test_feedback_queries.py with test for weekly feedback query (create 30 days of feedback, query past 7 days, verify <2 seconds)
- [ ] T037 [P] [US2] Add test to test_feedback_queries.py for feedback pattern grouping (create 10 "why_not" feedbacks with similar notes text, group by phrase, verify counts)
- [ ] T038 [P] [US2] Add test to test_feedback_queries.py for feedback creation updates article status (create article status=emailed, add feedback rating=good, verify article status=good)

### Implementation for User Story 2

- [ ] T039 [US2] Add Feedback factory function to tests/fixtures/sample_data.py
- [ ] T040 [US2] Run contract tests for US2, verify one-to-one relationship and cascades enforced (T033-T035 should PASS)
- [ ] T041 [US2] Run integration tests for US2, verify feedback queries performant (T036-T038 should PASS)

**Checkpoint**: User Story 2 validated - feedback persists correctly, one-to-one relationship enforced, pattern queries work

---

## Phase 5: User Story 3 - Monitor Source Quality and Trust (Priority: P2)

**Goal**: Validate that sources track article counts correctly and trust score calculation matches expected formula

**Independent Test**: Create sources, link articles, add feedback, verify trust score calculation (approved / (approved + rejected))

### Integration Tests for User Story 3 (REQUIRED per constitution) ⚠️

- [ ] T042 [P] [US3] Create tests/integration/test_source_trust_scores.py with test for trust score calculation (create source with 5 approved, 15 rejected articles, verify trust_score = 0.25)
- [ ] T043 [P] [US3] Add test to test_source_trust_scores.py for insufficient data default (create source with 3 approved, 2 rejected, verify trust_score = 0.5)
- [ ] T044 [P] [US3] Add test to test_source_trust_scores.py for active source filtering (create 20 sources, 10 active, 10 inactive, query active sources ordered by trust_score DESC, verify <500ms)

### Implementation for User Story 3

- [ ] T045 [US3] Create helper function in app/models.py or app/services/ for calculate_trust_score(source: Source) -> float implementing formula from data-model.md
- [ ] T046 [US3] Run integration tests for US3, verify trust score calculations correct (T042-T044 should PASS)

**Checkpoint**: User Story 3 validated - source trust scores calculate correctly, active source queries performant

---

## Phase 6: User Story 4 - Maintain and Query Filter Rules (Priority: P2)

**Goal**: Validate that filter rules store with correct priority ordering and can be queried efficiently for AI filtering

**Independent Test**: Create filter rules of different types and origins, query active rules ordered by priority, verify ordering correct

### Integration Tests for User Story 4 (REQUIRED per constitution) ⚠️

- [ ] T047 [P] [US4] Create tests/integration/test_filter_rules.py with test for active rule query (create 30 rules, 20 active, 10 inactive, query active ordered by priority ASC, verify <200ms)
- [ ] T048 [P] [US4] Add test to test_filter_rules.py for rule origin tracking (create rules with source=original/learned/manual, query each type separately)
- [ ] T049 [P] [US4] Add test to test_filter_rules.py for priority ordering (create rules with priorities 1,3,5,2,4, query active rules, verify order 1,2,3,4,5)

### Implementation for User Story 4

- [ ] T050 [US4] Create scripts/seed_filter_rules.py to seed initial rules from an_story_criteria.md (at least 5 rules covering must_have, must_avoid, good_topic)
- [ ] T051 [US4] Add FilterRule factory function to tests/fixtures/sample_data.py
- [ ] T052 [US4] Run seed_filter_rules.py to populate initial rules
- [ ] T053 [US4] Run integration tests for US4, verify rule queries performant (T047-T049 should PASS)

**Checkpoint**: User Story 4 validated - filter rules persist with origin tracking, priority ordering works, queries performant

---

## Phase 7: User Story 5 - Log Email Deliveries and Deep Dive Reports (Priority: P3)

**Goal**: Validate that email batches and deep dives persist with correct relationships to articles

**Independent Test**: Create email batch and deep dive records, verify foreign key relationships, query delivery history

### Contract Tests for User Story 5 (REQUIRED per constitution) ⚠️

- [ ] T054 [P] [US5] Add test to tests/contract/test_relationships.py for Article → EmailBatch SET NULL on delete (create article linked to batch, delete batch, verify article.email_batch_id = NULL)
- [ ] T055 [P] [US5] Add test to tests/contract/test_relationships.py for Article → DeepDive one-to-one relationship (create article, add deep dive, attempt second deep dive, verify IntegrityError)
- [ ] T056 [P] [US5] Add test to tests/contract/test_relationships.py for DeepDive → Article CASCADE on delete (create article + deep dive, delete article, verify deep dive deleted)

### Integration Tests for User Story 5 (REQUIRED per constitution) ⚠️

- [ ] T057 [P] [US5] Create tests/integration/test_email_batches.py with test for delivery success rate query (create 30 days of email batches, 25 sent, 5 failed, calculate success rate, verify <1 second)
- [ ] T058 [P] [US5] Add test to test_email_batches.py for email batch article linking (create batch with 50 articles, query articles by batch_id, verify count = 50)
- [ ] T059 [P] [US5] Create tests/integration/test_deep_dives.py with test for deep dive JSONB structure (create deep dive with additional_sources JSON, query and validate structure matches expected format from data-model.md)

### Implementation for User Story 5

- [ ] T060 [US5] Add EmailBatch and DeepDive factory functions to tests/fixtures/sample_data.py
- [ ] T061 [US5] Run contract tests for US5, verify relationships and cascades correct (T054-T056 should PASS)
- [ ] T062 [US5] Run integration tests for US5, verify batch and deep dive queries work (T057-T059 should PASS)

**Checkpoint**: User Story 5 validated - email batches and deep dives persist correctly, relationships enforced

---

## Phase 8: User Story 6 - Store Weekly Refinement Analysis (Priority: P3)

**Goal**: Validate that refinement logs persist with correct JSONB structure for suggestions

**Independent Test**: Create refinement log with suggestions JSON, query by week range, verify JSON structure correct

### Integration Tests for User Story 6 (REQUIRED per constitution) ⚠️

- [ ] T063 [P] [US6] Create tests/integration/test_refinement_logs.py with test for week range query (create 12 weeks of logs, query all ordered by week_start DESC, verify <1 second)
- [ ] T064 [P] [US6] Add test to test_refinement_logs.py for suggestions JSONB structure (create log with suggestions array matching format from data-model.md, query and validate structure)
- [ ] T065 [P] [US6] Add test to test_refinement_logs.py for accepted suggestions update (create log, update accepted_suggestions JSON, query and verify update persisted)

### Implementation for User Story 6

- [ ] T066 [US6] Add RefinementLog factory function to tests/fixtures/sample_data.py
- [ ] T067 [US6] Run integration tests for US6, verify refinement log queries and JSON handling work (T063-T065 should PASS)

**Checkpoint**: User Story 6 validated - refinement logs persist with correct JSON structure, queries performant

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation

- [ ] T068 [P] Create tests/contract/conftest.py with pytest fixtures for database setup/teardown using pytest-postgresql
- [ ] T069 [P] Create tests/integration/conftest.py with performance measurement fixtures and session management
- [ ] T070 [P] Create scripts/test_connection.py to validate database connectivity and list all tables
- [ ] T071 Run full test suite (all contract + integration tests), verify 100% pass rate
- [ ] T072 Verify all indexes created correctly by querying pg_indexes for articles, feedback, sources, filter_rules tables
- [ ] T073 Verify all ENUM types created correctly by querying pg_type for article_status, source_type, feedback_rating, rule_type, rule_source, email_status
- [ ] T074 Measure and document query performance benchmarks (daily email query, weekly feedback query, source trust scores) in specs/001-database-schema/performance-results.md
- [ ] T075 [P] Create Railway deployment configuration (railway.toml or Procfile) with start command: `alembic upgrade head && gunicorn app:create_app()`
- [ ] T076 [P] Document database backup/restore procedure in quickstart.md (Railway automated backups section)
- [ ] T077 Run quickstart.md validation (follow guide step-by-step in fresh environment, verify all steps work)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
  - User stories can proceed in priority order: US1 (P1) → US2 (P1) → US3 (P2) → US4 (P2) → US5 (P3) → US6 (P3)
  - US1 and US2 should complete before US3 (US3 trust scores depend on feedback data from US2)
  - US3 and US4 can proceed in parallel after US1-US2
  - US5 and US6 can proceed in parallel after US1-US4
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 3 (P2)**: Depends on US1 (Article model) and US2 (Feedback model) for trust score calculation
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 5 (P3)**: Depends on US1 (Article model) for EmailBatch and DeepDive relationships
- **User Story 6 (P3)**: Depends on US2 (Feedback model) and US4 (FilterRule model) for refinement suggestion structure

### Within Each User Story

- Contract tests before integration tests (validate constraints exist before testing queries)
- Tests before implementation verification
- All tests must PASS before moving to next story

### Parallel Opportunities

- **Setup tasks (Phase 1)**: T002, T003, T004 can run in parallel
- **Foundational models (Phase 2)**: T012-T017 can run in parallel (different model definitions in same file, but separate enough to implement concurrently)
- **US1 contract tests**: T022-T026 can run in parallel (different test files or test functions)
- **US1 integration tests**: T027-T029 can run in parallel (different test functions)
- **US2 contract tests**: T033-T035 can run in parallel
- **US2 integration tests**: T036-T038 can run in parallel
- **US3 integration tests**: T042-T044 can run in parallel
- **US4 integration tests**: T047-T049 can run in parallel
- **US5 contract tests**: T054-T056 can run in parallel
- **US5 integration tests**: T057-T059 can run in parallel
- **US6 integration tests**: T063-T065 can run in parallel
- **Polish tasks**: T068-T070, T072-T073, T075-T076 can run in parallel

---

## Parallel Example: Foundational Phase

```bash
# After T010 (enum classes defined), launch all model definitions together:
Task T011: "Define Article model in app/models.py"
Task T012: "Define Source model in app/models.py"
Task T013: "Define Feedback model in app/models.py"
Task T014: "Define FilterRule model in app/models.py"
Task T015: "Define EmailBatch model in app/models.py"
Task T016: "Define DeepDive model in app/models.py"
Task T017: "Define RefinementLog model in app/models.py"
```

---

## Parallel Example: User Story 1

```bash
# Launch all contract tests for US1 together:
Task T022: "UNIQUE constraint test in tests/contract/test_article_constraints.py"
Task T023: "NOT NULL constraints test in tests/contract/test_article_constraints.py"
Task T024: "CHECK constraint test in tests/contract/test_article_constraints.py"
Task T025: "ENUM validation test in tests/contract/test_article_constraints.py"
Task T026: "Foreign key RESTRICT test in tests/contract/test_relationships.py"

# Launch all integration tests for US1 together:
Task T027: "Daily email query performance test in tests/integration/test_article_queries.py"
Task T028: "Status transition test in tests/integration/test_article_queries.py"
Task T029: "Status filtering test in tests/integration/test_article_queries.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1-2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - creates all tables)
3. Complete Phase 3: User Story 1 (article persistence)
4. Complete Phase 4: User Story 2 (feedback persistence)
5. **STOP and VALIDATE**: Run all US1+US2 tests, verify database supports article and feedback workflows
6. This MVP database supports future features: article discovery (002) and email delivery (003)

### Incremental Delivery

1. Complete Setup + Foundational → All tables created, database operational
2. Add User Story 1 + User Story 2 → Test independently → Core article+feedback workflows validated (MVP! ✅)
3. Add User Story 3 + User Story 4 → Test independently → Source trust and filter rule management validated
4. Add User Story 5 + User Story 6 → Test independently → Logging and refinement audit trails validated
5. Each story adds validation without breaking previous stories

### Full Implementation Strategy

With single developer:

1. Phase 1 (Setup): ~30 minutes
2. Phase 2 (Foundational): ~3 hours (all model definitions + migration)
3. Phase 3 (US1): ~1.5 hours (contract tests + integration tests + validation)
4. Phase 4 (US2): ~1 hour (contract tests + integration tests + validation)
5. Phase 5 (US3): ~45 minutes (integration tests + trust score function)
6. Phase 6 (US4): ~1 hour (integration tests + seed script)
7. Phase 7 (US5): ~1 hour (contract tests + integration tests)
8. Phase 8 (US6): ~45 minutes (integration tests)
9. Phase 9 (Polish): ~1 hour (conftest fixtures, performance benchmarks, Railway config)

**Total Estimated Time**: 10-12 hours for complete implementation + testing

---

## Notes

- **[P] tasks**: Different files or functions, no dependencies - can parallelize if resources available
- **[Story] labels**: Map tasks to specific user stories for traceability
- **Contract tests REQUIRED**: Constitution mandates testing external APIs (database) and core workflows (queries)
- **All models created together**: Foundational phase creates all 7 models before user story validation begins (relationships require all tables to exist)
- **Tests written FIRST**: Contract tests verify constraints exist, integration tests verify query performance
- **Each user story independently testable**: After Foundational phase, can validate each story's database functionality in isolation
- **Commit after each phase checkpoint**: Enables rollback if issues discovered

---

**Task Generation Complete**: 77 tasks total, organized by 6 user stories with clear dependencies and parallel opportunities.

