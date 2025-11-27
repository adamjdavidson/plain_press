"""
Smart Email Article Selector

Selects articles for the daily email with variety algorithm to ensure
diverse content from multiple sources and topics.
"""

import logging
import random
from collections import defaultdict
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Article, ArticleStatus, EmailSettings

logger = logging.getLogger(__name__)


def get_email_settings(session: Optional[Session] = None) -> EmailSettings:
    """
    Get the current email settings (single row table).

    Args:
        session: Optional database session. If not provided, creates one.

    Returns:
        EmailSettings instance with current configuration
    """
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True

    try:
        settings = session.query(EmailSettings).first()
        if settings is None:
            # Create default settings if none exist
            settings = EmailSettings(
                target_article_count=50,
                min_article_count=30,
                max_article_count=70,
                max_per_source=5,
                max_per_topic=10,
                min_filter_score=0.5,
            )
            session.add(settings)
            session.commit()
            logger.info("Created default email settings")
        return settings
    finally:
        if close_session:
            session.close()


def select_articles_for_email(session: Optional[Session] = None) -> list[Article]:
    """
    Select articles for daily email with variety algorithm.

    Algorithm:
    1. Get all candidates (status=PENDING, filter_score >= min, not published, not rejected)
    2. Group by source and track topics
    3. Round-robin select to ensure variety:
       - No more than max_per_source from any source
       - No more than max_per_topic from any topic
       - Prioritize higher scores within constraints
    4. Shuffle final selection for varied reading experience
    5. Return target_article_count articles

    Args:
        session: Optional database session. If not provided, creates one.

    Returns:
        List of Article instances selected for the email
    """
    close_session = False
    if session is None:
        session = SessionLocal()
        close_session = True

    try:
        settings = get_email_settings(session)

        # Get all candidate articles
        candidates = session.query(Article).filter(
            and_(
                Article.status == ArticleStatus.PENDING,
                Article.filter_score >= settings.min_filter_score,
                Article.is_published == False,
                Article.is_rejected == False,
            )
        ).order_by(Article.filter_score.desc()).all()

        logger.info(f"Found {len(candidates)} candidate articles")

        if not candidates:
            return []

        # Track selection constraints
        selected: list[Article] = []
        source_counts: dict[str, int] = defaultdict(int)
        topic_counts: dict[str, int] = defaultdict(int)

        # First pass: select articles respecting variety constraints
        for article in candidates:
            if len(selected) >= settings.max_article_count:
                break

            # Check source limit
            if source_counts[article.source_name] >= settings.max_per_source:
                continue

            # Check topic limits (article may have multiple topics)
            topics = article.topics or []
            if topics:
                # Skip if any topic is already at max
                topic_maxed = any(
                    topic_counts[topic] >= settings.max_per_topic
                    for topic in topics
                )
                if topic_maxed:
                    continue

            # Article passes all constraints - select it
            selected.append(article)
            source_counts[article.source_name] += 1
            for topic in topics:
                topic_counts[topic] += 1

        logger.info(f"Selected {len(selected)} articles with variety constraints")

        # If we don't have enough, relax constraints and add more
        if len(selected) < settings.min_article_count:
            already_selected_ids = {a.id for a in selected}

            # Second pass: relax topic constraints but keep source limits
            for article in candidates:
                if len(selected) >= settings.target_article_count:
                    break
                if article.id in already_selected_ids:
                    continue

                # Only enforce source limit in relaxed mode
                if source_counts[article.source_name] >= settings.max_per_source:
                    continue

                selected.append(article)
                source_counts[article.source_name] += 1

            logger.info(f"After relaxing topic constraints: {len(selected)} articles")

        # If still not enough, fully relax constraints
        if len(selected) < settings.min_article_count:
            already_selected_ids = {a.id for a in selected}

            for article in candidates:
                if len(selected) >= settings.target_article_count:
                    break
                if article.id in already_selected_ids:
                    continue

                selected.append(article)

            logger.info(f"After fully relaxing constraints: {len(selected)} articles")

        # Trim to target if we have too many
        if len(selected) > settings.target_article_count:
            selected = selected[:settings.target_article_count]

        # Shuffle for varied reading experience (not just by score)
        random.shuffle(selected)

        # Log summary
        _log_selection_summary(selected, source_counts, topic_counts)

        return selected

    finally:
        if close_session:
            session.close()


def _log_selection_summary(
    articles: list[Article],
    source_counts: dict[str, int],
    topic_counts: dict[str, int]
) -> None:
    """Log a summary of the selection for debugging."""
    if not articles:
        logger.info("No articles selected")
        return

    # Score stats
    scores = [a.filter_score for a in articles]
    avg_score = sum(scores) / len(scores)
    min_score = min(scores)
    max_score = max(scores)

    logger.info(f"Selection summary:")
    logger.info(f"  Total articles: {len(articles)}")
    logger.info(f"  Score range: {min_score:.2f} - {max_score:.2f} (avg: {avg_score:.2f})")

    # Source distribution
    sources_with_articles = {k: v for k, v in source_counts.items() if v > 0}
    logger.info(f"  Sources: {len(sources_with_articles)}")
    for source, count in sorted(sources_with_articles.items(), key=lambda x: -x[1])[:5]:
        logger.info(f"    {source}: {count}")

    # Topic distribution
    topics_with_articles = {k: v for k, v in topic_counts.items() if v > 0}
    if topics_with_articles:
        logger.info(f"  Topics: {len(topics_with_articles)}")
        for topic, count in sorted(topics_with_articles.items(), key=lambda x: -x[1])[:5]:
            logger.info(f"    {topic}: {count}")


def preview_email_selection() -> dict:
    """
    Preview what would be selected for the next email without making changes.

    Returns:
        Dict with selection statistics and article summaries
    """
    session = SessionLocal()
    try:
        settings = get_email_settings(session)
        articles = select_articles_for_email(session)

        # Group by source
        by_source: dict[str, list[dict]] = defaultdict(list)
        for article in articles:
            by_source[article.source_name].append({
                'headline': article.headline,
                'score': article.filter_score,
                'topics': article.topics or [],
            })

        return {
            'total_selected': len(articles),
            'settings': {
                'target': settings.target_article_count,
                'min': settings.min_article_count,
                'max': settings.max_article_count,
                'max_per_source': settings.max_per_source,
                'max_per_topic': settings.max_per_topic,
                'min_score': settings.min_filter_score,
            },
            'by_source': dict(by_source),
            'source_counts': {source: len(arts) for source, arts in by_source.items()},
        }
    finally:
        session.close()
