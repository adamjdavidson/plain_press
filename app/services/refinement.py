"""
Weekly Refinement Service

Analyzes editor feedback to:
1. Calculate source trust scores
2. Identify patterns in rejected articles
3. Suggest filter rule changes
4. Update the RefinementLog table
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from collections import defaultdict

from anthropic import Anthropic

from app.database import SessionLocal
from app.models import (
    Article, Feedback, FeedbackRating, FilterRule, RuleType, RuleSource,
    Source, RefinementLog, calculate_trust_score
)

logger = logging.getLogger(__name__)

# Configuration
MODEL = os.environ.get("CLAUDE_REFINEMENT_MODEL", "claude-sonnet-4-5")
MAX_TOKENS = 4096


def get_anthropic_client() -> Anthropic:
    """Get Anthropic client with API key from environment."""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    return Anthropic(api_key=api_key)


def get_feedback_since(days: int = 7) -> dict:
    """
    Get all feedback from the last N days.

    Returns:
        Dict with feedback statistics and details
    """
    session = SessionLocal()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    try:
        feedbacks = session.query(Feedback).filter(
            Feedback.clicked_at >= cutoff
        ).all()

        result = {
            'total': len(feedbacks),
            'good': [],
            'no': [],
            'why_not': [],
            'by_source': defaultdict(lambda: {'good': 0, 'no': 0, 'why_not': 0}),
        }

        for fb in feedbacks:
            article = fb.article
            fb_data = {
                'article_id': str(fb.article_id),
                'headline': article.headline if article else 'Unknown',
                'source_name': article.source_name if article else 'Unknown',
                'filter_score': article.filter_score if article else 0.0,
                'notes': fb.notes,
                'clicked_at': fb.clicked_at.isoformat(),
            }

            if fb.rating == FeedbackRating.GOOD:
                result['good'].append(fb_data)
                if article:
                    result['by_source'][article.source_name]['good'] += 1
            elif fb.rating == FeedbackRating.NO:
                result['no'].append(fb_data)
                if article:
                    result['by_source'][article.source_name]['no'] += 1
            elif fb.rating == FeedbackRating.WHY_NOT:
                result['why_not'].append(fb_data)
                if article:
                    result['by_source'][article.source_name]['why_not'] += 1

        # Convert defaultdict to regular dict
        result['by_source'] = dict(result['by_source'])

        return result

    finally:
        session.close()


def update_source_trust_scores() -> dict:
    """
    Recalculate and update trust scores for all sources based on feedback.

    Returns:
        Dict mapping source names to their new trust scores
    """
    session = SessionLocal()
    updates = {}

    try:
        sources = session.query(Source).filter(Source.is_active == True).all()

        for source in sources:
            old_score = source.trust_score
            new_score = calculate_trust_score(source)

            if old_score != new_score:
                source.trust_score = new_score
                updates[source.name] = {
                    'old': old_score,
                    'new': new_score,
                    'approved': source.total_approved,
                    'rejected': source.total_rejected,
                }

        session.commit()
        logger.info(f"Updated trust scores for {len(updates)} sources")

    except Exception as e:
        logger.error(f"Error updating trust scores: {e}")
        session.rollback()
        raise
    finally:
        session.close()

    return updates


def analyze_feedback_patterns(feedback_data: dict) -> dict:
    """
    Use Claude to analyze feedback patterns and suggest improvements.

    Args:
        feedback_data: Dict from get_feedback_since()

    Returns:
        Dict with analysis results and suggestions
    """
    if feedback_data['total'] == 0:
        return {
            'analysis': 'No feedback data to analyze',
            'suggestions': [],
            'patterns': [],
        }

    client = get_anthropic_client()

    # Prepare the prompt
    why_not_notes = [
        f"- {fb['headline']}: {fb['notes'] or 'No explanation provided'}"
        for fb in feedback_data['why_not'][:20]  # Limit to 20 most recent
    ]

    source_stats = "\n".join([
        f"- {name}: {stats['good']} good, {stats['no']} no, {stats['why_not']} why_not"
        for name, stats in feedback_data['by_source'].items()
    ])

    prompt = f"""Analyze the following editor feedback data for a news curation system for Plain Press (an Amish newspaper).

FEEDBACK SUMMARY (last 7 days):
- Total feedback: {feedback_data['total']}
- Marked Good: {len(feedback_data['good'])}
- Marked No: {len(feedback_data['no'])}
- Marked Why Not (with explanation): {len(feedback_data['why_not'])}

SOURCE PERFORMANCE:
{source_stats}

REJECTION EXPLANATIONS (Why Not responses):
{chr(10).join(why_not_notes) if why_not_notes else 'None provided'}

Based on this data, provide:

1. PATTERNS: What types of stories are consistently rejected? What types are approved?

2. SUGGESTIONS: Specific, actionable changes to improve article selection. These could be:
   - New MUST_AVOID rules (e.g., "Avoid stories about X")
   - New MUST_HAVE rules (e.g., "Stories must include Y")
   - Adjustments to GOOD_TOPIC weights
   - Sources to consider disabling (if consistently rejected)
   - Sources performing well that should be prioritized

3. INSIGHTS: Any other observations about editorial preferences.

Format your response as JSON with keys: patterns, suggestions, insights"""

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text

        # Try to parse as JSON, fall back to raw text
        try:
            # Find JSON in response (it might be wrapped in markdown)
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                analysis = json.loads(json_match.group())
            else:
                analysis = {
                    'patterns': response_text,
                    'suggestions': [],
                    'insights': '',
                }
        except json.JSONDecodeError:
            analysis = {
                'patterns': response_text,
                'suggestions': [],
                'insights': '',
            }

        return analysis

    except Exception as e:
        logger.error(f"Error analyzing feedback: {e}")
        return {
            'analysis': f'Error: {e}',
            'suggestions': [],
            'patterns': [],
        }


def create_refinement_log(
    week_start: datetime,
    week_end: datetime,
    feedback_data: dict,
    analysis: dict,
) -> RefinementLog:
    """
    Create a RefinementLog record with the weekly analysis.

    Args:
        week_start: Start of analysis period
        week_end: End of analysis period
        feedback_data: Raw feedback data
        analysis: Claude's analysis results

    Returns:
        Created RefinementLog instance
    """
    session = SessionLocal()

    try:
        log = RefinementLog(
            week_start=week_start.date(),
            week_end=week_end.date(),
            total_articles_reviewed=feedback_data['total'],
            total_good=len(feedback_data['good']),
            total_no=len(feedback_data['no']),
            total_why_not=len(feedback_data['why_not']),
            suggestions=analysis,
            accepted_suggestions={},  # To be updated when editor reviews
        )

        session.add(log)
        session.commit()
        session.refresh(log)

        logger.info(f"Created RefinementLog {log.id} for week {week_start.date()} to {week_end.date()}")
        return log

    except Exception as e:
        logger.error(f"Error creating refinement log: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def run_weekly_refinement() -> dict:
    """
    Run the complete weekly refinement job.

    Returns:
        Dict with job results
    """
    job_start = datetime.now(timezone.utc)
    week_end = job_start
    week_start = job_start - timedelta(days=7)

    logger.info(f"Starting weekly refinement for {week_start.date()} to {week_end.date()}")

    results = {
        'week_start': week_start.isoformat(),
        'week_end': week_end.isoformat(),
        'feedback_collected': 0,
        'trust_scores_updated': 0,
        'suggestions': [],
        'errors': [],
    }

    try:
        # Step 1: Collect feedback
        logger.info("Step 1: Collecting feedback...")
        feedback_data = get_feedback_since(days=7)
        results['feedback_collected'] = feedback_data['total']
        logger.info(f"Collected {feedback_data['total']} feedback items")

        # Step 2: Update trust scores
        logger.info("Step 2: Updating source trust scores...")
        trust_updates = update_source_trust_scores()
        results['trust_scores_updated'] = len(trust_updates)
        results['trust_score_changes'] = trust_updates
        logger.info(f"Updated {len(trust_updates)} trust scores")

        # Step 3: Analyze patterns (if we have enough feedback)
        if feedback_data['total'] >= 5:
            logger.info("Step 3: Analyzing feedback patterns with Claude...")
            analysis = analyze_feedback_patterns(feedback_data)
            results['analysis'] = analysis
            results['suggestions'] = analysis.get('suggestions', [])
            logger.info(f"Generated {len(results['suggestions'])} suggestions")
        else:
            logger.info("Step 3: Skipping analysis (fewer than 5 feedback items)")
            analysis = {
                'patterns': 'Insufficient feedback for pattern analysis',
                'suggestions': [],
                'insights': '',
            }
            results['analysis'] = analysis

        # Step 4: Create refinement log
        logger.info("Step 4: Creating refinement log...")
        log = create_refinement_log(week_start, week_end, feedback_data, analysis)
        results['refinement_log_id'] = str(log.id)
        logger.info(f"Created refinement log {log.id}")

    except Exception as e:
        logger.error(f"Weekly refinement failed: {e}")
        results['errors'].append(str(e))

    results['duration_seconds'] = (datetime.now(timezone.utc) - job_start).total_seconds()
    logger.info(f"Weekly refinement complete in {results['duration_seconds']:.1f}s")

    return results
