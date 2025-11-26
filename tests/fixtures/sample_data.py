"""
Test data factories for creating sample database records

Provides factory functions for all entities with sensible defaults
"""
from datetime import datetime, timezone, date
from uuid import uuid4

from app.models import (
    Article, Source, Feedback, FilterRule, EmailBatch, DeepDive, RefinementLog,
    ArticleStatus, SourceType, FeedbackRating, RuleType, RuleSource, EmailStatus
)


def create_article(
    external_url=None,
    headline="Test Article Headline",
    source_name="Test Source",
    source_id=None,
    summary="This is a test article summary with some interesting content.",
    amish_angle="This article relates to Amish values because of community and simplicity.",
    filter_score=0.75,
    status=ArticleStatus.PENDING,
    **kwargs
):
    """
    Create an Article instance with default test values
    
    Args:
        external_url: Article URL (generates unique URL if None)
        source_id: Required foreign key to Source
        **kwargs: Additional field overrides
        
    Returns:
        Article instance (not committed to database)
    """
    if external_url is None:
        external_url = f"https://example.com/article/{uuid4()}"
    
    if source_id is None:
        raise ValueError("source_id is required for Article")
    
    return Article(
        external_url=external_url,
        headline=headline,
        source_name=source_name,
        source_id=source_id,
        summary=summary,
        amish_angle=amish_angle,
        filter_score=filter_score,
        status=status,
        **kwargs
    )


def create_source(
    name=None,
    type=SourceType.RSS,
    url="https://example.com/feed.xml",
    is_active=True,
    trust_score=0.5,
    **kwargs
):
    """
    Create a Source instance with default test values
    
    Args:
        name: Source name (generates unique name if None)
        type: SourceType enum
        **kwargs: Additional field overrides
        
    Returns:
        Source instance (not committed to database)
    """
    if name is None:
        name = f"Test Source {uuid4()}"
    
    return Source(
        name=name,
        type=type,
        url=url,
        is_active=is_active,
        trust_score=trust_score,
        total_surfaced=0,
        total_approved=0,
        total_rejected=0,
        **kwargs
    )


def create_feedback(
    article_id=None,
    rating=FeedbackRating.GOOD,
    notes=None,
    **kwargs
):
    """
    Create a Feedback instance with default test values
    
    Args:
        article_id: Required foreign key to Article
        rating: FeedbackRating enum
        notes: Optional feedback notes
        **kwargs: Additional field overrides
        
    Returns:
        Feedback instance (not committed to database)
    """
    if article_id is None:
        raise ValueError("article_id is required for Feedback")
    
    return Feedback(
        article_id=article_id,
        rating=rating,
        notes=notes,
        **kwargs
    )


def create_filter_rule(
    rule_type=RuleType.MUST_HAVE,
    rule_text="Test rule text",
    priority=1,
    source=RuleSource.ORIGINAL,
    is_active=True,
    **kwargs
):
    """
    Create a FilterRule instance with default test values
    
    Args:
        rule_type: RuleType enum
        rule_text: The rule content
        priority: Rule priority (lower = more important)
        source: RuleSource enum
        **kwargs: Additional field overrides
        
    Returns:
        FilterRule instance (not committed to database)
    """
    return FilterRule(
        rule_type=rule_type,
        rule_text=rule_text,
        priority=priority,
        source=source,
        is_active=is_active,
        learned_from_count=0,
        **kwargs
    )


def create_email_batch(
    sent_at=None,
    recipient_emails=None,
    article_count=50,
    subject_line="Plain News Candidates",
    status=EmailStatus.SENT,
    **kwargs
):
    """
    Create an EmailBatch instance with default test values
    
    Args:
        sent_at: Timestamp (uses current time if None)
        recipient_emails: List of email addresses
        **kwargs: Additional field overrides
        
    Returns:
        EmailBatch instance (not committed to database)
    """
    if sent_at is None:
        sent_at = datetime.now(timezone.utc)
    
    if recipient_emails is None:
        recipient_emails = ["test@example.com"]
    
    return EmailBatch(
        sent_at=sent_at,
        recipient_emails=recipient_emails,
        article_count=article_count,
        subject_line=subject_line,
        status=status,
        **kwargs
    )


def create_deep_dive(
    article_id=None,
    headline_suggestion="Suggested Headline for Story",
    key_points=None,
    additional_sources=None,
    full_report_text="Full report text with detailed research and background.",
    google_doc_id=None,
    google_doc_url=None,
    **kwargs
):
    """
    Create a DeepDive instance with default test values
    
    Args:
        article_id: Required foreign key to Article
        key_points: List of key points (default provided if None)
        additional_sources: JSONB structure (default provided if None)
        google_doc_id: Google Doc ID (generates unique ID if None)
        **kwargs: Additional field overrides
        
    Returns:
        DeepDive instance (not committed to database)
    """
    if article_id is None:
        raise ValueError("article_id is required for DeepDive")
    
    if key_points is None:
        key_points = ["Key point 1", "Key point 2", "Key point 3"]
    
    if additional_sources is None:
        additional_sources = {
            "sources": [
                {
                    "url": "https://example.com/source1",
                    "title": "Background Article",
                    "description": "Provides context"
                }
            ]
        }
    
    if google_doc_id is None:
        google_doc_id = f"doc_{uuid4().hex[:12]}"
    
    if google_doc_url is None:
        google_doc_url = f"https://docs.google.com/document/d/{google_doc_id}"
    
    return DeepDive(
        article_id=article_id,
        headline_suggestion=headline_suggestion,
        key_points=key_points,
        additional_sources=additional_sources,
        full_report_text=full_report_text,
        google_doc_id=google_doc_id,
        google_doc_url=google_doc_url,
        **kwargs
    )


def create_refinement_log(
    week_start=None,
    week_end=None,
    total_articles_reviewed=50,
    total_good=5,
    total_no=30,
    total_why_not=15,
    suggestions=None,
    accepted_suggestions=None,
    **kwargs
):
    """
    Create a RefinementLog instance with default test values
    
    Args:
        week_start: Start date (uses current week if None)
        week_end: End date (uses current week if None)
        suggestions: JSONB structure (default provided if None)
        accepted_suggestions: JSONB structure (default empty if None)
        **kwargs: Additional field overrides
        
    Returns:
        RefinementLog instance (not committed to database)
    """
    if week_start is None:
        week_start = date.today()
    
    if week_end is None:
        week_end = date.today()
    
    if suggestions is None:
        suggestions = {
            "suggestions": [
                {
                    "type": "add_rule",
                    "rule_type": "must_avoid",
                    "rule_text": "Avoid stories about modern technology",
                    "evidence": "3 rejections mentioned technology",
                    "accepted": False
                }
            ]
        }
    
    if accepted_suggestions is None:
        accepted_suggestions = {"suggestions": []}
    
    return RefinementLog(
        week_start=week_start,
        week_end=week_end,
        total_articles_reviewed=total_articles_reviewed,
        total_good=total_good,
        total_no=total_no,
        total_why_not=total_why_not,
        suggestions=suggestions,
        accepted_suggestions=accepted_suggestions,
        **kwargs
    )

