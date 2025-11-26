# Data Model: Database Schema Foundation

**Feature**: 001-database-schema  
**Date**: 2025-11-26  
**Status**: Design Complete

## Overview

This document provides complete entity definitions for the Amish News Finder database schema. All models use SQLAlchemy 2.0+ declarative syntax with UUID primary keys, proper relationships, indexes, and constraints. The schema supports the complete article lifecycle: discovery → email delivery → feedback collection → deep dive generation → weekly refinement analysis.

---

## Database Configuration

**Database**: PostgreSQL 15+  
**ORM**: SQLAlchemy 2.0+  
**Migrations**: Alembic 1.12+  
**Connection String Format**: `postgresql://user:password@host:port/database`

**Connection Pool Settings**:
```python
pool_size=5
max_overflow=10
pool_pre_ping=True
pool_recycle=3600  # 1 hour
```

---

## Entity Definitions

### Entity 1: Article

**Purpose**: Represents a news story candidate discovered by the system. Tracks complete lifecycle from discovery through John's feedback and potential deep dive generation.

**SQLAlchemy Model**:

```python
from sqlalchemy import (
    Column, String, Text, Float, DateTime, Enum as SAEnum,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.sql import func
import enum
from uuid import UUID

class ArticleStatus(enum.Enum):
    PENDING = "pending"
    EMAILED = "emailed"
    GOOD = "good"
    REJECTED = "rejected"
    PASSED = "passed"

class Article(Base):
    __tablename__ = "articles"
    
    # Primary Key
    id: Mapped[UUID] = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    
    # Core Fields
    external_url: Mapped[str] = Column(String(500), unique=True, nullable=False)
    headline: Mapped[str] = Column(String(500), nullable=False)
    source_name: Mapped[str] = Column(String(200), nullable=False)
    published_date: Mapped[datetime] = Column(DateTime(timezone=True), nullable=True)
    discovered_date: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # AI-Generated Content
    summary: Mapped[str] = Column(Text, nullable=False)
    amish_angle: Mapped[str] = Column(Text, nullable=False)
    filter_score: Mapped[float] = Column(Float, nullable=False)
    filter_notes: Mapped[str] = Column(Text, nullable=True)
    raw_content: Mapped[str | None] = Column(Text, nullable=True)
    
    # Workflow State
    emailed_date: Mapped[datetime | None] = Column(DateTime(timezone=True), nullable=True)
    status: Mapped[ArticleStatus] = Column(
        SAEnum(ArticleStatus, native_enum=True),
        nullable=False,
        default=ArticleStatus.PENDING
    )
    
    # Google Integration (for approved articles)
    google_doc_id: Mapped[str | None] = Column(String(100), nullable=True)
    google_doc_url: Mapped[str | None] = Column(String(500), nullable=True)
    
    # Foreign Keys
    source_id: Mapped[UUID] = Column(
        PGUUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=False
    )
    email_batch_id: Mapped[UUID | None] = Column(
        PGUUID(as_uuid=True),
        ForeignKey("email_batches.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    source: Mapped["Source"] = relationship("Source", back_populates="articles")
    email_batch: Mapped["EmailBatch | None"] = relationship("EmailBatch", back_populates="articles")
    feedback: Mapped["Feedback | None"] = relationship("Feedback", back_populates="article", uselist=False)
    deep_dive: Mapped["DeepDive | None"] = relationship("DeepDive", back_populates="article", uselist=False)
    
    # Indexes
    __table_args__ = (
        Index("ix_articles_daily_email", "status", "filter_score", "discovered_date",
              postgresql_using="btree"),
        Index("ix_articles_status", "status"),
        Index("ix_articles_discovered_date", "discovered_date"),
        Index("ix_articles_source_id", "source_id"),
    )
```

**Constraints**:
- `UNIQUE` on `external_url` (prevents duplicate processing)
- `CHECK` on `filter_score` between 0.0 and 1.0 (add via Alembic migration)
- `NOT NULL` on required fields (enforced by SQLAlchemy nullable=False)

**Indexes Rationale**:
- `ix_articles_daily_email`: Composite index for daily email query (status='pending', ordered by filter_score DESC, discovered_date DESC)
- `ix_articles_status`: Fast filtering by workflow status
- `ix_articles_discovered_date`: Sorting and date range queries
- `ix_articles_source_id`: Foreign key lookup (article → source relationship)

---

### Entity 2: Source

**Purpose**: Represents an RSS feed or Exa search query that produces article candidates. Tracks source performance (approval rate) to enable trust scoring and prioritization.

**SQLAlchemy Model**:

```python
class SourceType(enum.Enum):
    RSS = "rss"
    SEARCH_QUERY = "search_query"
    MANUAL = "manual"

class Source(Base):
    __tablename__ = "sources"
    
    # Primary Key
    id: Mapped[UUID] = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    
    # Core Fields
    name: Mapped[str] = Column(String(200), nullable=False, unique=True)
    type: Mapped[SourceType] = Column(
        SAEnum(SourceType, native_enum=True),
        nullable=False
    )
    url: Mapped[str | None] = Column(String(500), nullable=True)  # RSS feed URL or base URL
    search_query: Mapped[str | None] = Column(String(500), nullable=True)  # For search_query type
    is_active: Mapped[bool] = Column(Boolean, nullable=False, default=True)
    
    # Performance Metrics
    trust_score: Mapped[float] = Column(Float, nullable=False, default=0.5)
    total_surfaced: Mapped[int] = Column(Integer, nullable=False, default=0)
    total_approved: Mapped[int] = Column(Integer, nullable=False, default=0)
    total_rejected: Mapped[int] = Column(Integer, nullable=False, default=0)
    last_fetched: Mapped[datetime | None] = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    notes: Mapped[str | None] = Column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    articles: Mapped[list["Article"]] = relationship("Article", back_populates="source")
    
    # Indexes
    __table_args__ = (
        Index("ix_sources_is_active", "is_active"),
        Index("ix_sources_trust_score", "trust_score"),
    )
```

**Trust Score Calculation** (application logic, not database):
```python
def calculate_trust_score(source: Source) -> float:
    total_rated = source.total_approved + source.total_rejected
    if total_rated < 10:
        return 0.5  # Insufficient data, use default
    return source.total_approved / total_rated
```

---

### Entity 3: Feedback

**Purpose**: Records John's rating decision on an emailed article. Stores rating type (good/no/why_not) and optional explanatory notes. One-to-one relationship with Article.

**SQLAlchemy Model**:

```python
class FeedbackRating(enum.Enum):
    GOOD = "good"
    NO = "no"
    WHY_NOT = "why_not"

class Feedback(Base):
    __tablename__ = "feedback"
    
    # Primary Key
    id: Mapped[UUID] = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    
    # Foreign Keys
    article_id: Mapped[UUID] = Column(
        PGUUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True  # One feedback per article
    )
    
    # Core Fields
    rating: Mapped[FeedbackRating] = Column(
        SAEnum(FeedbackRating, native_enum=True),
        nullable=False
    )
    notes: Mapped[str | None] = Column(Text, nullable=True)  # Required for why_not, optional for others
    clicked_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Timestamps
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Relationships
    article: Mapped["Article"] = relationship("Article", back_populates="feedback")
    
    # Indexes
    __table_args__ = (
        Index("ix_feedback_article_id", "article_id"),
        Index("ix_feedback_rating", "rating"),
        Index("ix_feedback_clicked_at", "clicked_at"),
    )
```

**Constraints**:
- `UNIQUE` on `article_id` (enforces one feedback per article)
- Application validation: `notes` required when `rating = 'why_not'`

---

### Entity 4: FilterRule

**Purpose**: Represents an editorial criterion used by AI to evaluate article candidates. Rules evolve over time based on feedback analysis (learned rules) and manual adjustments.

**SQLAlchemy Model**:

```python
class RuleType(enum.Enum):
    MUST_HAVE = "must_have"
    MUST_AVOID = "must_avoid"
    GOOD_TOPIC = "good_topic"
    BORDERLINE = "borderline"

class RuleSource(enum.Enum):
    ORIGINAL = "original"
    LEARNED = "learned"
    MANUAL = "manual"

class FilterRule(Base):
    __tablename__ = "filter_rules"
    
    # Primary Key
    id: Mapped[UUID] = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    
    # Core Fields
    rule_type: Mapped[RuleType] = Column(
        SAEnum(RuleType, native_enum=True),
        nullable=False
    )
    rule_text: Mapped[str] = Column(Text, nullable=False)
    priority: Mapped[int] = Column(Integer, nullable=False)  # Lower = more important
    is_active: Mapped[bool] = Column(Boolean, nullable=False, default=True)
    
    # Origin Tracking
    source: Mapped[RuleSource] = Column(
        SAEnum(RuleSource, native_enum=True),
        nullable=False
    )
    learned_from_count: Mapped[int] = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_filter_rules_is_active", "is_active"),
        Index("ix_filter_rules_priority", "priority"),
    )
```

**Query Pattern** (for AI filtering):
```python
active_rules = session.query(FilterRule)\
    .filter(FilterRule.is_active == True)\
    .order_by(FilterRule.priority.asc())\
    .all()
```

---

### Entity 5: EmailBatch

**Purpose**: Tracks each daily email delivery for debugging and analysis. Records recipient list, article count, and delivery status.

**SQLAlchemy Model**:

```python
from sqlalchemy.dialects.postgresql import ARRAY

class EmailStatus(enum.Enum):
    SENT = "sent"
    FAILED = "failed"

class EmailBatch(Base):
    __tablename__ = "email_batches"
    
    # Primary Key
    id: Mapped[UUID] = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    
    # Core Fields
    sent_at: Mapped[datetime] = Column(DateTime(timezone=True), nullable=False)
    recipient_emails: Mapped[list[str]] = Column(ARRAY(String), nullable=False)
    article_count: Mapped[int] = Column(Integer, nullable=False)
    subject_line: Mapped[str] = Column(String(200), nullable=False)
    status: Mapped[EmailStatus] = Column(
        SAEnum(EmailStatus, native_enum=True),
        nullable=False
    )
    error_message: Mapped[str | None] = Column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Relationships
    articles: Mapped[list["Article"]] = relationship("Article", back_populates="email_batch")
```

---

### Entity 6: DeepDive

**Purpose**: Stores detailed research report generated for approved articles. Includes headline suggestion, key points, additional sources, and Google integration references.

**SQLAlchemy Model**:

```python
from sqlalchemy.dialects.postgresql import JSONB

class DeepDive(Base):
    __tablename__ = "deep_dives"
    
    # Primary Key
    id: Mapped[UUID] = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    
    # Foreign Keys
    article_id: Mapped[UUID] = Column(
        PGUUID(as_uuid=True),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True  # One deep dive per article
    )
    
    # Report Content
    headline_suggestion: Mapped[str] = Column(String(500), nullable=False)
    key_points: Mapped[list[str]] = Column(ARRAY(Text), nullable=False)
    additional_sources: Mapped[dict] = Column(JSONB, nullable=False)
    full_report_text: Mapped[str] = Column(Text, nullable=False)
    
    # Google Integration
    google_doc_id: Mapped[str] = Column(String(100), nullable=False)
    google_doc_url: Mapped[str] = Column(String(500), nullable=False)
    google_sheet_row: Mapped[int | None] = Column(Integer, nullable=True)
    
    # Timestamps
    generated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    email_sent_at: Mapped[datetime | None] = Column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Relationships
    article: Mapped["Article"] = relationship("Article", back_populates="deep_dive")
    
    # Indexes
    __table_args__ = (
        Index("ix_deep_dives_article_id", "article_id"),
    )
```

**JSONB Structure for additional_sources**:
```json
{
  "sources": [
    {
      "url": "https://example.com/background",
      "title": "Background Article Title",
      "description": "Brief description of what this source provides"
    }
  ]
}
```

---

### Entity 7: RefinementLog

**Purpose**: Records weekly feedback analysis results, including suggested rule changes and John's acceptance decisions. Creates audit trail of how filtering criteria evolve.

**SQLAlchemy Model**:

```python
class RefinementLog(Base):
    __tablename__ = "refinement_logs"
    
    # Primary Key
    id: Mapped[UUID] = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    
    # Analysis Period
    week_start: Mapped[date] = Column(Date, nullable=False)
    week_end: Mapped[date] = Column(Date, nullable=False)
    
    # Feedback Summary
    total_articles_reviewed: Mapped[int] = Column(Integer, nullable=False)
    total_good: Mapped[int] = Column(Integer, nullable=False)
    total_no: Mapped[int] = Column(Integer, nullable=False)
    total_why_not: Mapped[int] = Column(Integer, nullable=False)
    
    # Suggestions and Acceptance
    suggestions: Mapped[dict] = Column(JSONB, nullable=False)
    accepted_suggestions: Mapped[dict] = Column(JSONB, nullable=False, default={})
    
    # Timestamps
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_refinement_logs_week_start", "week_start"),
    )
```

**JSONB Structure for suggestions**:
```json
{
  "suggestions": [
    {
      "type": "add_rule",
      "rule_type": "must_avoid",
      "rule_text": "Avoid stories focused on social media influencers",
      "evidence": "3 rejections this week mentioned influencer content",
      "accepted": true
    },
    {
      "type": "adjust_source",
      "source_id": "uuid-here",
      "source_name": "Good News Network",
      "current_trust_score": 0.3,
      "suggested_action": "deprioritize",
      "reason": "8 rejections, 2 approvals this week",
      "accepted": false
    }
  ]
}
```

---

## Relationships Diagram

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   Source    │───────│   Article   │───────│  Feedback   │
│             │ 1:N   │             │ 1:1   │             │
└─────────────┘       └─────────────┘       └─────────────┘
                            │
                            │ 1:1
                            ▼
                      ┌─────────────┐
                      │  DeepDive   │
                      └─────────────┘

┌─────────────┐       ┌─────────────┐
│ EmailBatch  │───────│   Article   │
│             │ 1:N   │             │
└─────────────┘       └─────────────┘

┌─────────────┐
│ FilterRule  │  (standalone, referenced by filtering logic)
└─────────────┘

┌───────────────┐
│ RefinementLog │  (standalone, weekly snapshots)
└───────────────┘
```

---

## Database Initialization SQL

**Initial migration will create these tables** (via Alembic autogenerate). For reference, the equivalent DDL:

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create ENUM types
CREATE TYPE article_status AS ENUM ('pending', 'emailed', 'good', 'rejected', 'passed');
CREATE TYPE source_type AS ENUM ('rss', 'search_query', 'manual');
CREATE TYPE feedback_rating AS ENUM ('good', 'no', 'why_not');
CREATE TYPE rule_type AS ENUM ('must_have', 'must_avoid', 'good_topic', 'borderline');
CREATE TYPE rule_source AS ENUM ('original', 'learned', 'manual');
CREATE TYPE email_status AS ENUM ('sent', 'failed');

-- Create tables (simplified; see SQLAlchemy models for complete definitions)
CREATE TABLE sources (...);
CREATE TABLE email_batches (...);
CREATE TABLE articles (...);
CREATE TABLE feedback (...);
CREATE TABLE filter_rules (...);
CREATE TABLE deep_dives (...);
CREATE TABLE refinement_logs (...);

-- Create indexes
CREATE INDEX ix_articles_daily_email ON articles (status, filter_score DESC, discovered_date DESC);
-- (see model __table_args__ for complete index list)
```

---

## Data Validation Rules

**Application Layer Validations** (not enforced at database level):

1. **Article.filter_score**: Must be between 0.0 and 1.0 (add CHECK constraint in migration)
2. **Feedback.notes**: Required when rating = 'why_not'
3. **Source.url**: Required when type = 'rss'
4. **Source.search_query**: Required when type = 'search_query'
5. **Article.status transitions**: Must follow workflow (pending → emailed → good/rejected/passed)

---

## Testing Requirements

**Contract Tests** (test database constraints):
- Unique constraint on Article.external_url
- One-to-one relationship: Article ↔ Feedback
- One-to-one relationship: Article ↔ DeepDive
- Foreign key cascade: deleting EmailBatch sets Article.email_batch_id to NULL
- Foreign key restrict: deleting Source blocked if articles exist
- Enum validation: invalid status values rejected

**Integration Tests** (test query performance):
- Daily email query (<1 second for 50,000 articles)
- Weekly feedback query (<2 seconds for 7 days)
- Source trust score calculation (<500ms for 50 sources)
- Concurrent feedback writes (10 simultaneous, no data corruption)

---

## Migration Strategy

1. **Initial migration**: `alembic revision --autogenerate -m "Initial schema"`
2. **Review generated SQL**: Check indexes, constraints, CASCADE rules
3. **Add manual steps**: CHECK constraint on filter_score, seed FilterRules from story_criteria.md
4. **Test up/down**: `alembic upgrade head && alembic downgrade -1`
5. **Deploy**: Railway runs `alembic upgrade head` in startup script

---

**Data Model Complete**: Ready for implementation in `app/models.py` and initial Alembic migration.

