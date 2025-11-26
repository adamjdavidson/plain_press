# Implementation Plan: Database Schema Foundation

**Branch**: `001-database-schema` | **Date**: 2025-11-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-database-schema/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Establish the foundational data model for Amish News Finder, defining all entities (Article, Source, FilterRule, Feedback, EmailBatch, DeepDive, RefinementLog) with proper relationships, constraints, and indexes. This feature implements persistent storage using PostgreSQL with SQLAlchemy ORM and Alembic migrations. The data model supports John's complete workflow: article discovery → email delivery → feedback collection → deep dive generation → weekly refinement analysis. All entities include timestamps, proper foreign key relationships, and indexes optimized for daily job queries (<1 second for top 50 articles) and weekly feedback analysis (<2 seconds for 7-day ranges).

**Technical Approach**: Use SQLAlchemy declarative models with UUID primary keys, Alembic for schema migrations, and PostgreSQL JSONB for structured data (additional sources, refinement suggestions). Implement database-level constraints (unique URLs, enum validation, foreign keys with CASCADE rules) to ensure data integrity. Create composite indexes for common query patterns identified in success criteria.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: SQLAlchemy 2.0+, Alembic 1.12+, psycopg2-binary 2.9+ (PostgreSQL adapter)  
**Storage**: PostgreSQL 15+ on Railway (with automated backups)  
**Testing**: pytest 7.4+ with pytest-postgresql for integration tests  
**Target Platform**: Linux server (Railway container)  
**Project Type**: Web application (Flask backend + scripts for cron jobs)  
**Performance Goals**: 
- Daily email query (50 articles): <1 second
- Weekly feedback analysis (7 days): <2 seconds
- Source trust score calculation (50 sources): <500ms
- Concurrent feedback writes (10 simultaneous): no data corruption

**Constraints**: 
- Database size: <2GB for first year (50 articles/day × 365 days = 18,250 articles + relationships)
- Connection pool: 5-10 connections (Railway default)
- Query timeout: 30 seconds maximum
- Transaction isolation: READ COMMITTED (PostgreSQL default)

**Scale/Scope**: 
- Single user (John Lapp)
- ~50 articles/day = 18,000/year
- ~10-20 feedback records/day
- ~50 active sources
- ~30 filter rules
- Weekly refinement logs (52/year)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify alignment with `.specify/memory/constitution.md`:

- [x] **Single-User Simplicity**: Does this feature serve John's workflow, or add complexity for theoretical users?
  - ✅ Data model is single-tenant by design; no user_id fields, no multi-tenancy abstractions
  - ✅ All relationships direct (no user-scoped filtering needed)
  - ✅ Simple schema focused on John's article review → feedback → refinement workflow

- [x] **Volume Over Precision**: Does this maintain 40-60 candidates/day without aggressive filtering?
  - ✅ Article table supports unlimited storage (no deletion, TEXT fields for content)
  - ✅ filter_score field preserves AI confidence for analysis without blocking low scores
  - ✅ Status transitions allow articles to remain "pending" indefinitely if not emailed

- [x] **Cost Discipline**: Will this keep monthly costs under $50? Document API cost impact.
  - ✅ PostgreSQL on Railway: included in $10-15/month app hosting cost (no separate DB fee)
  - ✅ Database size stays under 2GB for first year (well within Railway limits)
  - ✅ No expensive queries (all critical paths indexed, <2 second targets)
  - ✅ No external database APIs or services needed

- [x] **Reliability Over Performance**: Are external API calls idempotent? Is state persisted before actions?
  - ✅ No external API calls in data layer (this is pure persistence)
  - ✅ All state persisted via SQLAlchemy transactions before application proceeds
  - ✅ Foreign key constraints prevent orphaned records
  - ✅ Unique constraints prevent duplicate article processing
  - ✅ Enum validation prevents invalid status values

**Violations**: None. This feature aligns with all constitution principles.

## Project Structure

### Documentation (this feature)

```text
specs/001-database-schema/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output: SQLAlchemy best practices, index strategies
├── data-model.md        # Phase 1 output: Complete entity definitions with DDL
├── quickstart.md        # Phase 1 output: Database setup and migration guide
├── contracts/           # Phase 1 output: Not applicable (no API endpoints in data layer)
└── checklists/
    └── requirements.md  # Validation checklist (already created)
```

### Source Code (repository root)

```text
app/
├── __init__.py          # Flask app factory
├── models.py            # SQLAlchemy models (Article, Source, FilterRule, etc.)
├── database.py          # Database connection and session management
├── routes.py            # Flask routes (future: feedback endpoints)
└── services/            # Service layer (future: filtering, email, etc.)

migrations/
├── versions/            # Alembic migration files
│   └── 001_initial_schema.py  # Initial database schema
├── env.py               # Alembic environment config
├── script.py.mako       # Migration template
└── alembic.ini          # Alembic configuration

tests/
├── contract/            # Contract tests for database constraints
│   ├── test_article_constraints.py
│   ├── test_relationships.py
│   └── test_unique_constraints.py
├── integration/         # Integration tests for queries
│   ├── test_article_queries.py
│   ├── test_feedback_queries.py
│   └── test_source_trust_scores.py
└── fixtures/            # Test data fixtures
    └── sample_data.py

scripts/
├── daily_job.py         # 8am EST cron (future: uses models)
└── weekly_refinement.py # Sunday cron (future: uses models)

.env.example             # Environment variable template
requirements.txt         # Python dependencies
alembic.ini              # Alembic migration config (at root)
```

**Structure Decision**: Web application structure (Option 2 adapted). The project uses Flask as a web framework with backend-focused structure. Since this is a backend-heavy application with minimal frontend needs (simple feedback forms), we use a single `app/` directory rather than separating `backend/` and `frontend/`. Cron jobs live in `scripts/` and import models from `app/`. Tests are organized by type (contract vs integration) as specified in constitution's pragmatic testing principle.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. This section is not needed.

---

## Phase 0: Research Complete ✅

**Artifacts Generated**:
- `research.md` - Comprehensive research on SQLAlchemy 2.0, indexing strategies, UUID primary keys, JSONB storage, Alembic migrations, connection pooling, and constraint enforcement

**Key Decisions**:
1. SQLAlchemy 2.0+ declarative models with type annotations
2. UUID (v4) primary keys for all entities
3. Composite indexes for common query patterns
4. PostgreSQL ENUM types for status fields
5. JSONB for structured data (additional_sources, suggestions)
6. UTC timestamps with TIMESTAMPTZ
7. Alembic autogenerate migrations with manual review
8. Connection pool: 5-10 connections with pre_ping
9. Foreign key cascades: CASCADE for EmailBatch, RESTRICT for Source
10. VARCHAR(500) for constrained fields, TEXT for unlimited

---

## Phase 1: Design Complete ✅

**Artifacts Generated**:
- `data-model.md` - Complete SQLAlchemy model definitions for all 7 entities with relationships, indexes, and constraints
- `quickstart.md` - Step-by-step guide for database setup, Alembic configuration, migration generation, and deployment
- Agent context updated: `CLAUDE.md` now includes PostgreSQL, SQLAlchemy, Alembic in tech stack

**Entities Defined**:
1. **Article** - News story candidates with lifecycle tracking (pending → emailed → good/rejected/passed)
2. **Source** - RSS feeds/Exa queries with trust scoring (approval rate calculation)
3. **Feedback** - John's ratings (good/no/why_not) with optional notes
4. **FilterRule** - Editorial criteria with origin tracking (original/learned/manual)
5. **EmailBatch** - Daily email delivery logs for debugging
6. **DeepDive** - Research reports for approved articles with Google Doc references
7. **RefinementLog** - Weekly feedback analysis results with suggestion audit trail

**Indexes Created**:
- Composite: `(status, filter_score DESC, discovered_date DESC)` for daily email query
- Single: `clicked_at`, `is_active`, `source_id`, `article_id`, `status`, `trust_score`

**Constraints Enforced**:
- UNIQUE: `article.external_url`, `feedback.article_id`, `deep_dive.article_id`, `source.name`
- CHECK: `filter_score` between 0.0 and 1.0
- FOREIGN KEY: Articles → Source (RESTRICT), Articles → EmailBatch (SET NULL), Feedback → Article (CASCADE), DeepDive → Article (CASCADE)
- ENUM: All status fields validated at database level

---

## Post-Phase 1 Constitution Re-Check ✅

**Re-verification after design completion**:

- [x] **Single-User Simplicity**: ✅ CONFIRMED
  - Data model review: No user_id columns, no tenant isolation, no multi-user abstractions
  - All entities directly support John's workflow without indirection
  
- [x] **Volume Over Precision**: ✅ CONFIRMED
  - Article storage unlimited (no TTL, no automatic deletion)
  - filter_score preserved for analysis without blocking borderline candidates
  - Database design supports 50 articles/day indefinitely
  
- [x] **Cost Discipline**: ✅ CONFIRMED
  - PostgreSQL on Railway included in $10-15/month hosting (verified in Railway pricing)
  - Database size projection: 2GB/year well within Railway limits (50GB included)
  - Index strategy keeps queries under performance targets without expensive operations
  
- [x] **Reliability Over Performance**: ✅ CONFIRMED
  - All constraints enforced at database level (uniqueness, foreign keys, enums)
  - Cascade rules prevent orphaned records
  - Transaction isolation (READ COMMITTED) ensures data consistency
  - Connection pooling with pre_ping prevents stale connections

**Final Verdict**: ✅ Design fully aligns with constitution. No violations introduced during research or design phases.

---

## Implementation Readiness

**Blocked By**: None. All prerequisites complete.

**Ready For**:
1. ✅ `/speckit.tasks` - Generate task breakdown for implementation
2. ✅ Implementation - Create `app/models.py` with SQLAlchemy models
3. ✅ Migration - Generate initial Alembic migration
4. ✅ Testing - Write contract tests for constraints and integration tests for queries

**Next Steps**:
1. Run `/speckit.tasks` to generate implementation task list
2. Create `app/models.py` with entity definitions from `data-model.md`
3. Configure Alembic per `quickstart.md`
4. Generate and review initial migration
5. Write contract tests for uniqueness and foreign key constraints
6. Write integration tests for daily email query performance
7. Deploy to Railway and verify migration runs automatically

---

## Planning Complete

**Branch**: `001-database-schema`  
**Status**: ✅ Planning Phase Complete  
**Generated Artifacts**:
- `plan.md` (this file)
- `research.md` (10 technical decisions documented)
- `data-model.md` (7 entities with complete SQLAlchemy models)
- `quickstart.md` (setup guide with 8 steps + troubleshooting)
- `checklists/requirements.md` (specification validation - passed)

**Ready for**: Task generation (`/speckit.tasks`) and implementation.

---

## Implementation Status

**Status**: ✅ **MVP COMPLETE** (32/77 tasks = Phases 1-3)

**Completed**:
- Phase 1: Setup (4 tasks)
- Phase 2: Foundational (17 tasks) - All 7 models, Alembic, migration applied to Railway
- Phase 3: User Story 1 (11 tasks) - Contract + integration tests (22 tests PASSING)

**Database**: ✅ Live on Railway PostgreSQL
- 7 tables created with proper relationships
- 6 ENUM types with validation
- 11 indexes for performance
- All constraints enforced (UNIQUE, CHECK, foreign keys with CASCADE/RESTRICT)

**Test Coverage**: ✅ 22 tests (100% pass rate)
- 11 contract tests (constraints, relationships, cascades)
- 11 integration tests (query performance, status transitions)

**Remaining Tasks**: 45 tasks (Phases 4-9)
- Additional test coverage for US2-US6
- Performance benchmarking
- Railway deployment config

**Decision**: Per constitution's Pragmatic Testing principle, proceeding to Feature 002 (Article Discovery) with sufficient MVP test coverage.

---

**Command `/speckit.plan` execution complete.**
