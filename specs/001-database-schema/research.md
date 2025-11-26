# Research: Database Schema Foundation

**Feature**: 001-database-schema  
**Date**: 2025-11-26  
**Status**: Complete

## Overview

This document consolidates research for implementing the Amish News Finder database schema using SQLAlchemy ORM with PostgreSQL. Research covers: (1) SQLAlchemy 2.0 best practices, (2) indexing strategies for query performance, (3) Alembic migration patterns, (4) UUID vs integer primary keys, (5) JSON storage for structured data, (6) connection pooling, and (7) constraint enforcement at database level.

---

## Decision 1: SQLAlchemy 2.0 Declarative Models

**Chosen**: SQLAlchemy 2.0+ with declarative base and type annotations

**Rationale**:
- SQLAlchemy 2.0 introduces modern Python typing support (better IDE autocomplete, type checking)
- Declarative models keep model definitions in one place (reduces boilerplate)
- Explicit relationship definitions enable cascade rules and eager/lazy loading control
- Mature, well-documented ORM with excellent PostgreSQL support
- Alembic integration is first-class (auto-generates migrations from model changes)

**Alternatives Considered**:
- **Raw SQL with psycopg2**: More control but loses type safety, requires manual migration management, violates DRY (duplicates schema in code and migrations)
- **Django ORM**: Excellent but tightly coupled to Django framework; overkill for Flask app
- **SQLAlchemy 1.4**: Older API style; 2.0 is production-ready and recommended for new projects
- **Pydantic + SQL**: Good for validation but adds layer; SQLAlchemy handles validation via column types

**Implementation Notes**:
- Use `declarative_base()` for base class
- Type hints: `Mapped[str]`, `Mapped[Optional[datetime]]`
- Use `relationship()` for foreign keys with explicit `back_populates`
- Avoid lazy loading traps: use `selectinload()` for relationships when needed

---

## Decision 2: UUID Primary Keys

**Chosen**: UUID (v4) primary keys for all entities

**Rationale**:
- No sequence contention (relevant for concurrent writes from multiple processes)
- Better for distributed systems if we ever need replicas
- Harder to enumerate records (mild security benefit)
- No coordination needed between app instances
- Railway PostgreSQL supports `gen_random_uuid()` natively

**Alternatives Considered**:
- **Integer sequences**: Simpler, smaller indexes, better query performance. Rejected because distribution benefits outweigh minor performance cost in our single-user, low-traffic context.
- **ULIDs**: Sortable UUIDs with timestamp prefix. Rejected as unnecessary complexity; sorting by created_at is sufficient.

**Implementation Notes**:
- Use PostgreSQL `UUID` type, not `CHAR(36)`
- Set `server_default=func.gen_random_uuid()` for auto-generation
- Python type: `UUID` from `uuid` module
- Convert to string only for serialization (JSON, URLs)

---

## Decision 3: Indexing Strategy

**Chosen**: Composite indexes for common query patterns, single-column indexes for foreign keys

**Rationale**:
- Daily email query needs `(status, filter_score DESC, discovered_date DESC)` composite index
- Weekly feedback analysis needs `clicked_at` range index
- Foreign key lookups (article_id, source_id) need single-column indexes
- PostgreSQL supports partial indexes (e.g., `WHERE status = 'pending'`) but adds complexity; start with full indexes

**Query Patterns Identified**:
1. **Daily email candidates**: `WHERE status = 'pending' ORDER BY filter_score DESC, discovered_date DESC LIMIT 50`
   - Index: `(status, filter_score DESC, discovered_date DESC)`

2. **Weekly feedback analysis**: `WHERE clicked_at >= '2025-11-19' AND clicked_at < '2025-11-26'`
   - Index: `(clicked_at)`

3. **Source trust score**: `WHERE is_active = true ORDER BY trust_score DESC`
   - Index: `(is_active, trust_score DESC)` (if we pre-calculate) OR just `(is_active)` (if we calculate on-the-fly)

4. **Article by URL**: `WHERE external_url = 'https://...'` (uniqueness check)
   - Index: `UNIQUE (external_url)` (already enforced by constraint)

5. **Feedback by article**: `WHERE article_id = <uuid>`
   - Index: `(article_id)` (foreign key index)

**Alternatives Considered**:
- **No indexes**: Unacceptable; queries would slow to >10 seconds with 50k articles
- **Index every column**: Wasteful; increases write time and storage
- **Partial indexes**: More efficient but harder to maintain; defer to optimization phase if needed

**Implementation Notes**:
- Use SQLAlchemy `Index()` class with `postgresql_using='btree'` (default)
- For composite indexes, order matters: most selective column first (status in daily query)
- Monitor slow query log; add indexes if queries exceed targets

---

## Decision 4: Enum Handling

**Chosen**: PostgreSQL `ENUM` types for status fields (article.status, feedback.rating, etc.)

**Rationale**:
- Database-level validation (prevents invalid values)
- Better performance than `CHECK` constraints with strings
- Clear intent in schema (documents valid values)
- SQLAlchemy `Enum` type maps Python enums to PostgreSQL enums

**Alternatives Considered**:
- **String with CHECK constraint**: More flexible (can add values without migrations) but loses type safety
- **Integer codes**: Obscures meaning; requires lookup table
- **Python enum without DB enum**: Validation only in app layer; data can be corrupted by direct SQL

**Implementation Notes**:
- Define Python `enum.Enum` classes (e.g., `ArticleStatus`, `FeedbackRating`)
- Use SQLAlchemy `Enum(ArticleStatus, native_enum=True)` to create PostgreSQL ENUM type
- Migrations: Adding enum values requires `ALTER TYPE ... ADD VALUE` (handle carefully)
- Use descriptive names: `pending`, `emailed`, `good`, not `p`, `e`, `g`

---

## Decision 5: JSON Storage (JSONB)

**Chosen**: PostgreSQL `JSONB` for structured data (DeepDive.additional_sources, RefinementLog.suggestions)

**Rationale**:
- JSONB is binary format (faster than JSON text)
- Supports indexing (GIN indexes) if we need to query within JSON
- Flexible schema for evolving data (suggestions format may change)
- SQLAlchemy supports JSONB with native Python dict/list types

**Alternatives Considered**:
- **Separate tables**: More normalized but overkill for infrequently queried nested data
- **TEXT with manual parsing**: Loses validation, querying ability
- **JSON (text)**: Slower than JSONB, no indexing support

**Implementation Notes**:
- Use `JSONB` column type in PostgreSQL
- SQLAlchemy type: `sa.dialects.postgresql.JSONB`
- Python representation: `dict` or `list[dict]`
- Validate structure in application layer (Pydantic models optional)

---

## Decision 6: Timestamps and Timezones

**Chosen**: Store all timestamps as UTC `TIMESTAMP WITH TIME ZONE`, convert to EST at application layer

**Rationale**:
- UTC prevents daylight saving time bugs
- PostgreSQL `TIMESTAMPTZ` stores UTC, displays in session timezone
- SQLAlchemy `DateTime(timezone=True)` maps to Python `datetime` with timezone
- Convert to EST only for display (email templates, logs)

**Alternatives Considered**:
- **Store as EST**: Breaks during DST transitions, harder to coordinate with external APIs
- **Naive timestamps**: Ambiguous, causes bugs when comparing across timezones

**Implementation Notes**:
- All SQLAlchemy columns: `DateTime(timezone=True)`
- Use `func.now()` for server-side defaults (PostgreSQL `NOW()`)
- Python: `datetime.now(timezone.utc)` for explicit timestamps
- Display: `dt.astimezone(ZoneInfo("America/New_York"))`

---

## Decision 7: Alembic Migration Strategy

**Chosen**: Auto-generate migrations from model changes, review and edit before applying

**Rationale**:
- Alembic `autogenerate` detects model changes (new columns, indexes, constraints)
- Manual review catches edge cases (column renames detected as drop+add)
- Version control migration files for rollback capability
- Railway runs migrations automatically via startup script

**Alternatives Considered**:
- **Manual migrations**: Error-prone, tedious, easy to miss constraints
- **ORM auto-migrate (like Django)**: Convenient but less control over DDL
- **Raw SQL scripts**: Full control but no change detection, duplication of model definitions

**Implementation Notes**:
- Initial migration: `alembic revision --autogenerate -m "Initial schema"`
- Review generated migration, add any manual steps (data migrations, renames)
- Test migration up and down: `alembic upgrade head && alembic downgrade -1`
- Railway deployment: `alembic upgrade head` in startup script (before app starts)

---

## Decision 8: Connection Pooling

**Chosen**: SQLAlchemy connection pool with 5-10 connections, default settings

**Rationale**:
- Flask-SQLAlchemy manages pool automatically
- Railway PostgreSQL supports 20 concurrent connections (default tier)
- Our traffic pattern: cron jobs (sequential) + occasional feedback clicks (low concurrency)
- 5-10 connections sufficient for single-user app

**Alternatives Considered**:
- **No pooling**: Reconnecting for every query adds latency (~50ms per connection)
- **PgBouncer**: Overkill for low-traffic app, adds operational complexity
- **Large pool (50+)**: Wastes database resources, no benefit at our scale

**Implementation Notes**:
- SQLAlchemy default pool size: 5 connections
- Set `pool_pre_ping=True` to detect stale connections (Railway may disconnect idle)
- Set `pool_recycle=3600` (1 hour) to prevent long-lived connection issues
- Monitor connection usage; increase pool if we see timeouts

---

## Decision 9: Foreign Key Cascade Rules

**Chosen**: `CASCADE` on delete for EmailBatch → Article, `RESTRICT` for Source → Article

**Rationale**:
- EmailBatch deletion (if we implement) should remove email_batch_id references (SET NULL cascade)
- Source deletion should be blocked if articles exist (RESTRICT) to preserve historical data
- Article deletion should cascade to Feedback and DeepDive (1:1 relationships)

**Implementation Notes**:
- SQLAlchemy: `ondelete='CASCADE'` in `ForeignKey()`
- Test cascade behavior in contract tests
- Document cascade rules in data-model.md for clarity

---

## Decision 10: Text Field Sizing

**Chosen**: `VARCHAR(500)` for constrained fields (headlines, URLs), `TEXT` for unlimited (notes, reports)

**Rationale**:
- Headlines rarely exceed 200 chars; 500 buffer prevents truncation
- URLs can be long (query params); 500 chars adequate for 99% of cases
- Notes and reports: unlimited length (John's explanations may be detailed)
- TEXT has no performance penalty in PostgreSQL (TOAST storage for large values)

**Alternatives Considered**:
- **All VARCHAR**: Must guess max length, risks truncation
- **All TEXT**: Works but loses validation (e.g., headline > 500 chars likely indicates data error)

**Implementation Notes**:
- Use `String(500)` for headlines, URLs, names
- Use `Text` for notes, reports, full article content
- Application layer validation: warn if headline > 200 chars (user error likely)

---

## Implementation Checklist

Based on research above, implementation must:

- [x] Use SQLAlchemy 2.0+ declarative models with type annotations
- [x] Define UUID primary keys with `server_default=gen_random_uuid()`
- [x] Create composite index for daily email query: `(status, filter_score DESC, discovered_date DESC)`
- [x] Use PostgreSQL ENUM types for status fields
- [x] Use JSONB for structured data (additional_sources, suggestions)
- [x] Store timestamps as UTC with `TIMESTAMPTZ`
- [x] Configure Alembic for auto-generated migrations
- [x] Set connection pool: `pool_pre_ping=True`, `pool_recycle=3600`
- [x] Define foreign key cascades: `ondelete='CASCADE'` for EmailBatch, `RESTRICT` for Source
- [x] Use VARCHAR(500) for constrained fields, TEXT for unlimited
- [x] Create initial migration with `alembic revision --autogenerate`
- [x] Write contract tests for constraints (unique URL, enum validation, foreign keys)
- [x] Write integration tests for query performance (<1s for daily email candidates)

---

## References

- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [PostgreSQL ENUM Types](https://www.postgresql.org/docs/current/datatype-enum.html)
- [PostgreSQL JSONB](https://www.postgresql.org/docs/current/datatype-json.html)
- [PostgreSQL Indexing Best Practices](https://www.postgresql.org/docs/current/indexes.html)

---

**Research Complete**: All technical decisions documented. Ready for Phase 1 (data model definition and quickstart guide).

