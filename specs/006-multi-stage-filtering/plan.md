# Implementation Plan: Multi-Stage Filtering Pipeline with Tracing

**Branch**: `006-multi-stage-filtering` | **Date**: 2025-11-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-multi-stage-filtering/spec.md`

## Summary

Replace the current single-pass Claude filter with three sequential focused filters (News Check → Wow Factor → Values Fit), each evaluating ONE criterion. Add comprehensive tracing to record every filter decision, enabling John to view funnel analytics, drill into individual article journeys, and analyze rejection patterns for prompt tuning.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: Flask, SQLAlchemy, Anthropic SDK, Jinja2  
**Storage**: PostgreSQL (existing)  
**Testing**: pytest (existing test patterns)  
**Target Platform**: Linux server (Railway)  
**Project Type**: Web application (Flask monolith)  
**Performance Goals**: Funnel view loads in <3 seconds for 1,000 articles  
**Constraints**: 8,000 character article truncation limit, 7-day trace retention  
**Scale/Scope**: ~500 articles/day input, single user (John)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify alignment with `.specify/memory/constitution.md`:

- [x] **Single-User Simplicity**: Admin views serve John's workflow (funnel analysis, article journey review). No multi-user features.
- [x] **Volume Over Precision**: Three focused filters with configurable thresholds allow tuning toward inclusion. Default 0.5 thresholds are generous.
- [x] **Reliability Over Performance**: Trace records persisted immediately after each filter. Pipeline continues on individual article failures.

**Violations**: None. Feature directly serves John's need to understand and tune the filtering system.

## Project Structure

### Documentation (this feature)

```text
specs/006-multi-stage-filtering/
├── plan.md              # This file
├── research.md          # Phase 0 output - design decisions
├── data-model.md        # Phase 1 output - new entities
├── quickstart.md        # Phase 1 output - implementation guide
├── contracts/           # Phase 1 output - API contracts
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
app/
├── models.py                    # Add PipelineRun, FilterTrace models
├── routes.py                    # Add admin views for filter runs
└── services/
    ├── claude_filter.py         # REPLACE: Refactor to multi-stage
    ├── filter_news_check.py     # NEW: Filter 1 - Is this news?
    ├── filter_wow_factor.py     # NEW: Filter 2 - Would this make someone go wow?
    ├── filter_values_fit.py     # NEW: Filter 3 - Does this fit our values?
    ├── filter_pipeline.py       # NEW: Orchestrates 3 filters with tracing
    └── discovery.py             # MODIFY: Use new filter pipeline

templates/
└── admin/
    ├── filter_runs.html         # NEW: Pipeline runs list
    ├── filter_run_detail.html   # NEW: Funnel view for one run
    └── article_journey.html     # NEW: Single article's filter path

migrations/
└── versions/
    └── xxx_add_filter_tracing.py  # NEW: PipelineRun, FilterTrace tables

scripts/
└── cleanup_traces.py            # NEW: Delete traces older than 7 days
```

**Structure Decision**: Follows existing Flask monolith pattern. New filter services are separate modules (one per filter) orchestrated by `filter_pipeline.py`. Admin views added to existing routes.py using `main` blueprint.

## Complexity Tracking

> No constitution violations. No complexity justification needed.
