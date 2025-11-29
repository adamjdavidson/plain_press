# Tasks: Multi-Stage Filtering Pipeline with Tracing

**Input**: Design documents from `/specs/006-multi-stage-filtering/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Per constitution (Principle IV: Pragmatic Testing), tests are OPTIONAL. Integration tests included for core pipeline workflow only.

**Organization**: Tasks grouped by user story. Core filters (US3-5) are foundational for admin views (US1, US2, US6).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to

---

## Phase 1: Setup

**Purpose**: Project configuration for new filtering system

- [x] T001 Add environment variables to `.env.example` for filter thresholds and model selection
- [x] T002 [P] Create `PipelineRunStatus` enum in `app/models.py`

---

## Phase 2: Foundational (Database & Models)

**Purpose**: Core infrastructure that MUST be complete before filter implementation

**⚠️ CRITICAL**: No filter work can begin until this phase is complete

- [x] T003 Create Alembic migration for `pipeline_runs` table in `migrations/versions/`
- [x] T004 Create Alembic migration for `filter_traces` table in `migrations/versions/`
- [x] T005 Add `PipelineRun` model to `app/models.py` with all columns and indexes per data-model.md
- [x] T006 Add `FilterTrace` model to `app/models.py` with all columns, indexes, and FK to PipelineRun
- [x] T007 Add `last_run_id` FK column to Article model in `app/models.py`
- [x] T008 Run migrations to create new tables

**Checkpoint**: Database ready - filter implementation can begin

---

## Phase 3: Core Filters (US3, US4, US5) - Priority P1 🎯 MVP

**Goal**: Implement three focused filters that each evaluate ONE criterion

**Independent Test**: Each filter can be tested in isolation with sample articles

### US3 - News Check Filter

- [x] T009 [P] [US3] Create `app/services/filter_news_check.py` with Haiku model config
- [x] T010 [US3] Implement `NEWS_CHECK_SCHEMA` structured output schema in `app/services/filter_news_check.py`
- [x] T011 [US3] Implement `NEWS_CHECK_PROMPT` focused on "Is this actual news?" in `app/services/filter_news_check.py`
- [x] T012 [US3] Implement `filter_news_check(article)` function returning FilterResult in `app/services/filter_news_check.py`
- [x] T013 [US3] Add content truncation to 8,000 chars in `app/services/filter_news_check.py`

### US4 - Wow Factor Filter

- [x] T014 [P] [US4] Create `app/services/filter_wow_factor.py` with Sonnet model config
- [x] T015 [US4] Implement `WOW_FACTOR_SCHEMA` structured output schema in `app/services/filter_wow_factor.py`
- [x] T016 [US4] Implement `WOW_FACTOR_PROMPT` focused on "Would this make someone go wow?" in `app/services/filter_wow_factor.py`
- [x] T017 [US4] Implement `filter_wow_factor(article)` function returning FilterResult in `app/services/filter_wow_factor.py`
- [x] T018 [US4] Add configurable threshold via `FILTER_WOW_THRESHOLD` env var in `app/services/filter_wow_factor.py`

### US5 - Values Fit Filter

- [x] T019 [P] [US5] Create `app/services/filter_values_fit.py` with Sonnet model config
- [x] T020 [US5] Implement `VALUES_FIT_SCHEMA` structured output schema in `app/services/filter_values_fit.py`
- [x] T021 [US5] Implement `VALUES_FIT_PROMPT` focused on "Does this fit Amish values?" in `app/services/filter_values_fit.py`
- [x] T022 [US5] Implement `load_filter_rules()` to get must_have/must_avoid from FilterRule table in `app/services/filter_values_fit.py`
- [x] T023 [US5] Implement `filter_values_fit(article, rules)` function returning FilterResult in `app/services/filter_values_fit.py`
- [x] T024 [US5] Add configurable threshold via `FILTER_VALUES_THRESHOLD` env var in `app/services/filter_values_fit.py`

**Checkpoint**: All three filters can be called independently and return structured results

---

## Phase 4: Pipeline Orchestrator

**Goal**: Combine filters into sequential pipeline with tracing

**Independent Test**: Run pipeline on batch of articles, verify traces created

- [x] T025 Create `app/services/filter_pipeline.py` with imports and config
- [x] T026 Implement `FilterResult` dataclass in `app/services/filter_pipeline.py`
- [x] T027 Implement `create_pipeline_run()` to insert PipelineRun record in `app/services/filter_pipeline.py`
- [x] T028 Implement `record_trace()` to insert FilterTrace record in `app/services/filter_pipeline.py`
- [x] T029 Implement `run_pipeline(articles)` orchestrating 3 filters sequentially in `app/services/filter_pipeline.py`
- [x] T030 Add early exit logic - rejected articles skip subsequent filters in `app/services/filter_pipeline.py`
- [x] T031 Implement `update_pipeline_run()` to set final counts and status in `app/services/filter_pipeline.py`
- [x] T032 Add error handling - continue on individual article failures in `app/services/filter_pipeline.py`
- [x] T033 Add `FILTER_TRACING_ENABLED` env var toggle in `app/services/filter_pipeline.py`

**Checkpoint**: Pipeline runs end-to-end, traces persisted to database

---

## Phase 5: US1 - View Pipeline Funnel (Priority: P1)

**Goal**: John sees funnel showing article counts at each filter stage

**Independent Test**: View `/admin/filter-runs` and click into a run to see funnel visualization

- [x] T034 [US1] Create `templates/admin/filter_runs.html` with runs list table
- [x] T035 [US1] Implement `GET /admin/filter-runs` route in `app/routes.py` querying PipelineRun table
- [x] T036 [US1] Create `templates/admin/filter_run_detail.html` with funnel visualization
- [x] T037 [US1] Implement `GET /admin/filter-runs/<run_id>` route in `app/routes.py` with funnel data
- [x] T038 [US1] Add funnel SQL query aggregating FilterTrace counts by filter_name in `app/routes.py`
- [x] T039 [US1] Add article lists (passed/rejected) per filter stage in `templates/admin/filter_run_detail.html`
- [x] T040 [US1] Add navigation link to filter runs from admin nav in `templates/admin/base.html` or equivalent

**Checkpoint**: Funnel view works - John can see where articles are being filtered out

---

## Phase 6: US2 - Review Individual Article Decisions (Priority: P2)

**Goal**: John clicks an article to see its complete journey through all filters

**Independent Test**: Click any article in funnel view to see journey with all filter decisions

- [x] T041 [US2] Create `templates/admin/article_journey.html` showing filter decision timeline
- [x] T042 [US2] Implement `GET /admin/filter-runs/<run_id>/article/<url_hash>` route in `app/routes.py`
- [x] T043 [US2] Add `get_article_journey(run_id, article_url)` query in `app/routes.py`
- [x] T044 [US2] Display each filter's decision, score, and full reasoning in `templates/admin/article_journey.html`
- [x] T045 [US2] Add "final outcome" indicator (accepted/rejected_at_X) in `templates/admin/article_journey.html`
- [x] T046 [US2] Add clickable article links in funnel view to navigate to journey in `templates/admin/filter_run_detail.html`

**Checkpoint**: Article journey works - John can understand any individual decision

---

## Phase 7: US6 - Analyze Rejection Patterns (Priority: P2)

**Goal**: John sees aggregated rejection reasons to identify systematic issues

**Independent Test**: View rejection analysis for any filter, see patterns grouped

- [x] T047 [US6] Create `templates/admin/rejection_analysis.html` with pattern table
- [x] T048 [US6] Implement `GET /admin/filter-runs/<run_id>/rejections/<filter_name>` route in `app/routes.py`
- [x] T049 [US6] Add SQL query grouping rejections by reasoning (truncated) in `app/routes.py`
- [x] T050 [US6] Display rejection patterns with counts and percentages in `templates/admin/rejection_analysis.html`
- [x] T051 [US6] Add example articles for each pattern in `templates/admin/rejection_analysis.html`
- [x] T052 [US6] Implement `GET /admin/filter-runs/<run_id>/rejections/<filter_name>/export` CSV endpoint in `app/routes.py`
- [x] T053 [US6] Add "View Rejections" link per filter in funnel view in `templates/admin/filter_run_detail.html`

**Checkpoint**: Rejection analysis works - John can identify systematic filtering issues

---

## Phase 8: Integration with Discovery Pipeline

**Goal**: Connect new multi-stage pipeline to existing article discovery flow

- [x] T054 Add `USE_MULTI_STAGE_FILTER` feature flag check in `app/services/discovery.py`
- [x] T055 Import and call `run_pipeline()` from filter_pipeline in `app/services/discovery.py`
- [x] T056 Update article storage to use pipeline results (content_type, wow_score, filter_score) in `app/services/discovery.py`
- [x] T057 Set `last_run_id` on processed articles in `app/services/discovery.py`
- [x] T058 Keep fallback to old `claude_filter.py` when feature flag is false in `app/services/discovery.py`

**Checkpoint**: Pipeline integrated - real articles flow through new filters

---

## Phase 9: Cleanup & Retention

**Goal**: Automatic cleanup of old trace data per 7-day retention policy

- [x] T059 Create `scripts/cleanup_traces.py` with 7-day retention delete query
- [x] T060 Add cascade delete for PipelineRun when all traces deleted in `scripts/cleanup_traces.py`
- [x] T061 Add logging of deleted record counts in `scripts/cleanup_traces.py`
- [x] T062 Document cleanup script in Railway scheduled jobs or cron setup

**Checkpoint**: Cleanup ready - traces won't grow indefinitely

---

## Phase 10: Polish & Validation

**Purpose**: Final validation and documentation

- [ ] T063 Manual test: Run pipeline with dry-run and verify traces created
- [ ] T064 Manual test: View funnel, click articles, check rejection patterns
- [ ] T065 Manual test: Verify feature flag rollback works (USE_MULTI_STAGE_FILTER=false)
- [x] T066 Update CLAUDE.md with new services and admin routes
- [x] T067 [P] Integration test for full pipeline in `tests/integration/test_filter_pipeline.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all filter work
- **Core Filters (Phase 3)**: Depends on Foundational - US3/4/5 can run in parallel
- **Pipeline (Phase 4)**: Depends on all three filters complete
- **Admin Views (Phase 5-7)**: Depend on Pipeline - US1/2/6 can run in parallel
- **Integration (Phase 8)**: Depends on Pipeline
- **Cleanup (Phase 9)**: Can run after Foundational
- **Polish (Phase 10)**: Depends on everything else

### User Story Dependencies

| Story | Depends On | Can Start After |
|-------|------------|-----------------|
| US3 (News Check) | Foundational | Phase 2 complete |
| US4 (Wow Factor) | Foundational | Phase 2 complete |
| US5 (Values Fit) | Foundational | Phase 2 complete |
| US1 (Funnel) | Pipeline | Phase 4 complete |
| US2 (Journey) | Pipeline | Phase 4 complete |
| US6 (Patterns) | Pipeline | Phase 4 complete |

### Parallel Opportunities

**Phase 3 - Core Filters** (all can run in parallel):
```
T009-T013 (US3) || T014-T018 (US4) || T019-T024 (US5)
```

**Phase 5-7 - Admin Views** (all can run in parallel after Phase 4):
```
T034-T040 (US1) || T041-T046 (US2) || T047-T053 (US6)
```

---

## Implementation Strategy

### MVP First (Filters + Funnel)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (database)
3. Complete Phase 3: All three filters (US3/4/5)
4. Complete Phase 4: Pipeline orchestrator
5. Complete Phase 5: Funnel view (US1)
6. **STOP and VALIDATE**: Run pipeline, view funnel, verify traces

### Incremental Delivery

1. **After Phase 5**: John can see the funnel and understand filter effectiveness
2. **After Phase 6**: John can drill into individual article decisions
3. **After Phase 7**: John can analyze rejection patterns for prompt tuning
4. **After Phase 8**: Real articles flow through new pipeline

---

## Notes

- All filters use Anthropic structured outputs beta for guaranteed JSON
- Filter 1 uses Haiku (fast/cheap), Filters 2-3 use Sonnet (nuanced)
- Article content truncated to 8,000 chars before sending to Claude
- Trace retention is 7 days - cleanup script deletes older records
- Feature flag `USE_MULTI_STAGE_FILTER` allows safe rollback

