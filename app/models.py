"""
SQLAlchemy Models for Amish News Finder Database Schema

All models use UUID primary keys, proper relationships, indexes, and constraints
per specs/001-database-schema/data-model.md
"""
import enum
from datetime import datetime, date
from uuid import UUID
from typing import Optional

from sqlalchemy import (
    Column, String, Text, Float, DateTime, Date, Integer, Boolean,
    Enum as SAEnum, ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.sql import func

from app.database import Base


# ============================================================================
# Enum Definitions
# ============================================================================

class ArticleStatus(enum.Enum):
    """Article workflow status"""
    PENDING = "pending"
    EMAILED = "emailed"
    GOOD = "good"
    REJECTED = "rejected"
    PASSED = "passed"
    PUBLISHED = "published"


class SourceType(enum.Enum):
    """Source type for article discovery"""
    RSS = "rss"
    SEARCH_QUERY = "search_query"
    MANUAL = "manual"


class FeedbackRating(enum.Enum):
    """John's rating on an article"""
    GOOD = "good"
    NO = "no"
    WHY_NOT = "why_not"


class RuleType(enum.Enum):
    """Filter rule category"""
    MUST_HAVE = "must_have"
    MUST_AVOID = "must_avoid"
    GOOD_TOPIC = "good_topic"
    BORDERLINE = "borderline"


class RuleSource(enum.Enum):
    """Origin of filter rule"""
    ORIGINAL = "original"
    LEARNED = "learned"
    MANUAL = "manual"


class EmailStatus(enum.Enum):
    """Email batch delivery status"""
    SENT = "sent"
    FAILED = "failed"


class PipelineRunStatus(enum.Enum):
    """Filter pipeline execution status"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# Entity Models
# ============================================================================

class Article(Base):
    """
    News story candidate with lifecycle tracking
    
    Workflow: pending → emailed → (good | rejected | passed)
    """
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
    published_date: Mapped[Optional[datetime]] = Column(DateTime(timezone=True), nullable=True)
    discovered_date: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # AI-Generated Content
    summary: Mapped[str] = Column(Text, nullable=False)
    amish_angle: Mapped[str] = Column(Text, nullable=False)
    filter_score: Mapped[float] = Column(Float, nullable=False)
    filter_notes: Mapped[Optional[str]] = Column(Text, nullable=True)
    raw_content: Mapped[Optional[str]] = Column(Text, nullable=True)
    
    # Quality Filter Fields
    content_type: Mapped[Optional[str]] = Column(String(50), nullable=True)
    wow_score: Mapped[Optional[float]] = Column(Float, nullable=True)
    
    # Workflow State
    emailed_date: Mapped[Optional[datetime]] = Column(DateTime(timezone=True), nullable=True)
    status: Mapped[ArticleStatus] = Column(
        SAEnum(ArticleStatus, native_enum=True, name="article_status"),
        nullable=False,
        default=ArticleStatus.PENDING
    )
    
    # Google Integration (for approved articles)
    google_doc_id: Mapped[Optional[str]] = Column(String(100), nullable=True)
    google_doc_url: Mapped[Optional[str]] = Column(String(500), nullable=True)

    # Article Management (for web UI workflow)
    is_published: Mapped[bool] = Column(Boolean, nullable=False, default=False)
    is_rejected: Mapped[bool] = Column(Boolean, nullable=False, default=False)
    topics: Mapped[list[str]] = Column(ARRAY(String), nullable=False, default=[])

    # Foreign Keys
    source_id: Mapped[UUID] = Column(
        PGUUID(as_uuid=True),
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=False
    )
    email_batch_id: Mapped[Optional[UUID]] = Column(
        PGUUID(as_uuid=True),
        ForeignKey("email_batches.id", ondelete="SET NULL"),
        nullable=True
    )
    last_run_id: Mapped[Optional[UUID]] = Column(
        PGUUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="SET NULL"),
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
    email_batch: Mapped[Optional["EmailBatch"]] = relationship("EmailBatch", back_populates="articles")
    feedback: Mapped[Optional["Feedback"]] = relationship("Feedback", back_populates="article", uselist=False)
    deep_dive: Mapped[Optional["DeepDive"]] = relationship("DeepDive", back_populates="article", uselist=False)
    
    # Indexes
    __table_args__ = (
        Index("ix_articles_daily_email", "status", "filter_score", "discovered_date",
              postgresql_using="btree"),
        Index("ix_articles_status", "status"),
        Index("ix_articles_discovered_date", "discovered_date"),
        Index("ix_articles_source_id", "source_id"),
        Index("ix_articles_is_published", "is_published"),
        Index("ix_articles_is_rejected", "is_rejected"),
    )


class Source(Base):
    """
    RSS feed or Exa search query that produces articles
    
    Tracks source performance for trust scoring and prioritization
    """
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
        SAEnum(SourceType, native_enum=True, name="source_type"),
        nullable=False
    )
    url: Mapped[Optional[str]] = Column(String(500), nullable=True)
    search_query: Mapped[Optional[str]] = Column(String(500), nullable=True)
    is_active: Mapped[bool] = Column(Boolean, nullable=False, default=True)
    
    # Performance Metrics
    trust_score: Mapped[float] = Column(Float, nullable=False, default=0.5)
    total_surfaced: Mapped[int] = Column(Integer, nullable=False, default=0)
    total_approved: Mapped[int] = Column(Integer, nullable=False, default=0)
    total_rejected: Mapped[int] = Column(Integer, nullable=False, default=0)
    last_fetched: Mapped[Optional[datetime]] = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    notes: Mapped[Optional[str]] = Column(Text, nullable=True)
    
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


class Feedback(Base):
    """
    John's rating decision on an emailed article
    
    One-to-one relationship with Article
    """
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
        SAEnum(FeedbackRating, native_enum=True, name="feedback_rating"),
        nullable=False
    )
    notes: Mapped[Optional[str]] = Column(Text, nullable=True)
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


class FilterRule(Base):
    """
    Editorial criterion used by AI to evaluate article candidates
    
    Rules evolve over time based on feedback analysis
    """
    __tablename__ = "filter_rules"
    
    # Primary Key
    id: Mapped[UUID] = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    
    # Core Fields
    rule_type: Mapped[RuleType] = Column(
        SAEnum(RuleType, native_enum=True, name="rule_type"),
        nullable=False
    )
    rule_text: Mapped[str] = Column(Text, nullable=False)
    priority: Mapped[int] = Column(Integer, nullable=False)
    is_active: Mapped[bool] = Column(Boolean, nullable=False, default=True)
    
    # Origin Tracking
    source: Mapped[RuleSource] = Column(
        SAEnum(RuleSource, native_enum=True, name="rule_source"),
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


class EmailBatch(Base):
    """
    Daily email delivery tracking
    
    Records recipient list, article count, and delivery status
    """
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
        SAEnum(EmailStatus, native_enum=True, name="email_status"),
        nullable=False
    )
    error_message: Mapped[Optional[str]] = Column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Relationships
    articles: Mapped[list["Article"]] = relationship("Article", back_populates="email_batch")


class DeepDive(Base):
    """
    Detailed research report generated for approved articles
    
    One-to-one relationship with Article. Includes Google Doc references.
    """
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
    
    # Google Integration (optional - may be empty if not configured)
    google_doc_id: Mapped[Optional[str]] = Column(String(100), nullable=True)
    google_doc_url: Mapped[Optional[str]] = Column(String(500), nullable=True)
    google_sheet_row: Mapped[Optional[int]] = Column(Integer, nullable=True)
    
    # Timestamps
    generated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    email_sent_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True), nullable=True)
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


class RefinementLog(Base):
    """
    Weekly feedback analysis results
    
    Tracks suggested rule changes and John's acceptance decisions
    """
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
    
    # Suggestions and Acceptance (JSONB structure)
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


class EmailSettings(Base):
    """
    User preferences for daily email generation.

    Single row table - only one configuration active at a time.
    """
    __tablename__ = "email_settings"

    # Primary Key
    id: Mapped[UUID] = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )

    # Volume settings
    target_article_count: Mapped[int] = Column(Integer, nullable=False, default=50)
    min_article_count: Mapped[int] = Column(Integer, nullable=False, default=30)
    max_article_count: Mapped[int] = Column(Integer, nullable=False, default=70)

    # Variety settings
    max_per_source: Mapped[int] = Column(Integer, nullable=False, default=5)
    max_per_topic: Mapped[int] = Column(Integer, nullable=False, default=10)

    # Score thresholds
    min_filter_score: Mapped[float] = Column(Float, nullable=False, default=0.5)

    # Recipient
    recipient_email: Mapped[Optional[str]] = Column(String(255), nullable=True)

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


# ============================================================================
# Pipeline Tracing Models
# ============================================================================

class PipelineRun(Base):
    """
    A single execution of the multi-stage filtering pipeline.
    
    Groups all filter traces for one pipeline run and tracks aggregate statistics.
    """
    __tablename__ = "pipeline_runs"
    
    # Primary Key
    id: Mapped[UUID] = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    
    # Timing
    started_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True), nullable=True)
    
    # Status
    status: Mapped[PipelineRunStatus] = Column(
        SAEnum(PipelineRunStatus, native_enum=True, name="pipeline_run_status"),
        nullable=False,
        default=PipelineRunStatus.RUNNING
    )
    
    # Counts
    input_count: Mapped[int] = Column(Integer, nullable=False, default=0)
    filter1_pass_count: Mapped[Optional[int]] = Column(Integer, nullable=True)
    filter2_pass_count: Mapped[Optional[int]] = Column(Integer, nullable=True)
    filter3_pass_count: Mapped[Optional[int]] = Column(Integer, nullable=True)
    
    # Error info
    error_message: Mapped[Optional[str]] = Column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Relationships
    traces: Mapped[list["FilterTrace"]] = relationship(
        "FilterTrace",
        back_populates="pipeline_run",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_pipeline_runs_started_at", "started_at"),
        Index("ix_pipeline_runs_status", "status"),
    )


class FilterTrace(Base):
    """
    Record of one filter evaluating one article.
    
    Core tracing entity for understanding filter decisions.
    """
    __tablename__ = "filter_traces"
    
    # Primary Key
    id: Mapped[UUID] = Column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid()
    )
    
    # Foreign Keys
    run_id: Mapped[UUID] = Column(
        PGUUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Article identification (not FK - articles may not exist yet)
    article_url: Mapped[str] = Column(String(500), nullable=False)
    article_title: Mapped[str] = Column(String(500), nullable=False)
    
    # Filter identification
    filter_name: Mapped[str] = Column(String(50), nullable=False)  # news_check, wow_factor, values_fit
    filter_order: Mapped[int] = Column(Integer, nullable=False)  # 1, 2, or 3
    
    # Decision
    decision: Mapped[str] = Column(String(20), nullable=False)  # pass, reject
    score: Mapped[Optional[float]] = Column(Float, nullable=True)
    reasoning: Mapped[str] = Column(Text, nullable=False)
    
    # Metrics
    input_tokens: Mapped[Optional[int]] = Column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = Column(Integer, nullable=True)
    latency_ms: Mapped[Optional[int]] = Column(Integer, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    # Relationships
    pipeline_run: Mapped["PipelineRun"] = relationship("PipelineRun", back_populates="traces")
    
    # Indexes
    __table_args__ = (
        Index("ix_filter_traces_run_id", "run_id"),
        Index("ix_filter_traces_filter_name", "filter_name"),
        Index("ix_filter_traces_decision", "decision"),
        Index("ix_filter_traces_created_at", "created_at"),
    )


# ============================================================================
# Helper Functions
# ============================================================================

def calculate_trust_score(source: Source) -> float:
    """
    Calculate source trust score based on approval rate
    
    Formula: total_approved / (total_approved + total_rejected)
    Minimum 10 samples required, otherwise default to 0.5
    
    Args:
        source: Source instance
        
    Returns:
        Trust score between 0.0 and 1.0
    """
    total_rated = source.total_approved + source.total_rejected
    
    if total_rated < 10:
        return 0.5  # Insufficient data, use default
    
    return source.total_approved / total_rated

