"""
Flask Routes for Plain Press Finder

Includes:
- Feedback routes for Good/No/Why Not buttons
- Deep dive trigger on Good
- Health check endpoint
- Admin interface for viewing/managing articles
"""

import logging
import os
from datetime import datetime, timezone
from uuid import UUID

import feedparser
import httpx
from flask import Blueprint, render_template, request, abort, jsonify, flash, redirect, url_for
from sqlalchemy import func
from werkzeug.exceptions import HTTPException

from app.database import SessionLocal
from app.models import (
    Article, ArticleStatus, Feedback, FeedbackRating, Source, SourceType, DeepDive,
    PipelineRun, FilterTrace, PipelineRunStatus, FilterStatus
)

logger = logging.getLogger(__name__)

# Create blueprint
main = Blueprint('main', __name__)

# Number of articles per page in admin
ARTICLES_PER_PAGE = 100


@main.route('/health')
def health_check():
    """Health check endpoint for Railway."""
    return {'status': 'healthy', 'timestamp': datetime.now(timezone.utc).isoformat()}


@main.route('/run-pipeline')
def run_pipeline():
    """
    Manually trigger the daily pipeline.
    Visit: https://your-app.up.railway.app/run-pipeline
    """
    import subprocess
    import sys
    
    try:
        result = subprocess.run(
            [sys.executable, 'scripts/run_daily_pipeline.py'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        return {
            'status': 'completed',
            'stdout': result.stdout[-2000:] if result.stdout else '',  # Last 2000 chars
            'stderr': result.stderr[-1000:] if result.stderr else '',
            'return_code': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {'status': 'timeout', 'message': 'Pipeline took longer than 5 minutes'}, 504
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500


@main.route('/feedback/<article_id>/good')
def feedback_good(article_id: str):
    """
    Handle Good feedback button click.
    
    Creates Feedback record with rating="good" and updates Article status.
    """
    return _handle_feedback(article_id, FeedbackRating.GOOD, ArticleStatus.GOOD)


@main.route('/feedback/<article_id>/no')
def feedback_no(article_id: str):
    """
    Handle No feedback button click.
    
    Creates Feedback record with rating="no" and updates Article status to rejected.
    """
    return _handle_feedback(article_id, FeedbackRating.NO, ArticleStatus.REJECTED)


@main.route('/feedback/<article_id>/why_not', methods=['GET', 'POST'])
def feedback_why_not(article_id: str):
    """
    Handle Why Not feedback button click.
    
    GET: Shows form for text input
    POST: Creates Feedback record with rating="why_not" and notes
    """
    session = SessionLocal()
    
    try:
        # Validate article ID
        try:
            article_uuid = UUID(article_id)
        except ValueError:
            abort(404, description="Invalid article ID")
        
        # Get article
        article = session.query(Article).filter(Article.id == article_uuid).first()
        if not article:
            abort(404, description="Article not found")
        
        if request.method == 'GET':
            # Show form
            return render_template('feedback/why_not_form.html', article=article)
        
        # POST - handle form submission
        notes = request.form.get('notes', '').strip()
        
        # Check for existing feedback
        existing = session.query(Feedback).filter(Feedback.article_id == article_uuid).first()
        if existing:
            return render_template('feedback/confirmation.html',
                                 message="Feedback already recorded",
                                 article=article,
                                 already_recorded=True)
        
        # Create feedback record
        feedback = Feedback(
            article_id=article_uuid,
            rating=FeedbackRating.WHY_NOT,
            notes=notes if notes else None,
            clicked_at=datetime.now(timezone.utc),
        )
        session.add(feedback)
        
        # Update article status
        article.status = ArticleStatus.REJECTED
        
        # Update source metrics
        if article.source_id:
            source = session.query(Source).filter(Source.id == article.source_id).first()
            if source:
                source.total_rejected += 1
        
        session.commit()
        
        logger.info(f"Feedback recorded: article={article_id}, rating=why_not, notes={notes[:50] if notes else 'none'}...")
        
        return render_template('feedback/confirmation.html',
                             message="Thanks for the feedback!",
                             article=article,
                             rating='why_not')
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except Exception as e:
        logger.error(f"Error handling why_not feedback for {article_id}: {e}")
        session.rollback()
        abort(500, description="Error recording feedback")
    finally:
        session.close()


def _handle_feedback(article_id: str, rating: FeedbackRating, new_status: ArticleStatus):
    """
    Generic feedback handler for Good and No buttons.
    
    Args:
        article_id: UUID string of article
        rating: FeedbackRating enum value
        new_status: ArticleStatus to set
        
    Returns:
        Rendered confirmation template
    """
    session = SessionLocal()
    
    try:
        # Validate article ID
        try:
            article_uuid = UUID(article_id)
        except ValueError:
            abort(404, description="Invalid article ID")
        
        # Get article
        article = session.query(Article).filter(Article.id == article_uuid).first()
        if not article:
            abort(404, description="Article not found")
        
        # Check for existing feedback
        existing = session.query(Feedback).filter(Feedback.article_id == article_uuid).first()
        if existing:
            return render_template('feedback/confirmation.html',
                                 message="Feedback already recorded",
                                 article=article,
                                 already_recorded=True)
        
        # Create feedback record
        feedback = Feedback(
            article_id=article_uuid,
            rating=rating,
            clicked_at=datetime.now(timezone.utc),
        )
        session.add(feedback)
        
        # Update article status
        article.status = new_status
        
        # Update source metrics
        if article.source_id:
            source = session.query(Source).filter(Source.id == article.source_id).first()
            if source:
                if rating == FeedbackRating.GOOD:
                    source.total_approved += 1
                else:
                    source.total_rejected += 1
        
        session.commit()
        
        # Trigger deep dive for Good ratings
        doc_url = None
        deep_dive_error = None
        
        if rating == FeedbackRating.GOOD:
            try:
                from app.services.deep_dive import generate_deep_dive_for_article
                from app.services.email import send_deep_dive_email
                
                logger.info(f"Triggering deep dive for article {article_id}")
                
                # Generate deep dive report
                deep_dive = generate_deep_dive_for_article(article_uuid)
                
                if deep_dive:
                    doc_url = deep_dive.google_doc_url  # May be None if Google not configured

                    # Send report email (even if no Google Doc)
                    editor_email = os.environ.get('EDITOR_EMAIL')
                    if editor_email:
                        send_deep_dive_email(
                            to_email=editor_email,
                            headline=article.headline,
                            source_name=article.source_name,
                            report_text=deep_dive.full_report_text,
                            doc_url=deep_dive.google_doc_url or '',
                            original_url=article.external_url
                        )

                    logger.info(f"Deep dive completed: {deep_dive.id}")
                    
            except Exception as e:
                logger.error(f"Deep dive generation failed for {article_id}: {e}")
                deep_dive_error = str(e)
        
        # Format message based on rating
        if rating == FeedbackRating.GOOD:
            if doc_url:
                message = "Marked as Good! ✓ Deep dive report generated."
            elif deep_dive_error:
                message = f"Marked as Good! ✓ (Report generation failed: {deep_dive_error[:50]})"
            else:
                message = "Marked as Good! ✓"
        else:
            message = "Marked as No"
        
        logger.info(f"Feedback recorded: article={article_id}, rating={rating.value}")

        return render_template('feedback/confirmation.html',
                             message=message,
                             article=article,
                             rating=rating.value,
                             doc_url=doc_url)

    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except Exception as e:
        logger.error(f"Error handling {rating.value} feedback for {article_id}: {e}")
        session.rollback()
        abort(500, description="Error recording feedback")
    finally:
        session.close()


# =============================================================================
# Admin Routes
# =============================================================================

# Sort column mapping for admin articles
SORT_COLUMNS = {
    'date': Article.discovered_date,
    'score': Article.filter_score,
    'status': Article.status,
    'source': Article.source_name,
    'headline': Article.headline,
}

DEFAULT_SORT_DIRECTIONS = {
    'date': 'desc',      # Newest first
    'score': 'desc',     # Highest first
    'status': 'asc',     # Alphabetical
    'source': 'asc',     # Alphabetical
    'headline': 'asc',   # Alphabetical
}


@main.route('/admin/articles')
def admin_articles():
    """
    Admin page to view and manage all articles.

    Supports filtering by status, score, source, search, and sorting.
    """
    from sqlalchemy import nullslast
    
    session = SessionLocal()

    try:
        # Get filter parameters
        status_filter = request.args.get('status', '')
        min_score = request.args.get('min_score', '')
        source_filter = request.args.get('source', '')
        search = request.args.get('search', '')
        page = int(request.args.get('page', 1))
        
        # Get sort parameters
        sort_column = request.args.get('sort', 'date')
        sort_dir = request.args.get('dir', '')
        
        # Validate sort column
        if sort_column not in SORT_COLUMNS:
            sort_column = 'date'
        
        # Use default direction if not specified or invalid
        if sort_dir not in ('asc', 'desc'):
            sort_dir = DEFAULT_SORT_DIRECTIONS.get(sort_column, 'desc')

        # Build query
        query = session.query(Article)

        if status_filter:
            try:
                status_enum = ArticleStatus(status_filter)
                query = query.filter(Article.status == status_enum)
            except ValueError:
                pass

        if min_score:
            try:
                query = query.filter(Article.filter_score >= float(min_score))
            except ValueError:
                pass

        if source_filter:
            query = query.filter(Article.source_name == source_filter)

        if search:
            query = query.filter(Article.headline.ilike(f'%{search}%'))

        # Get total count for pagination
        total_count = query.count()
        total_pages = (total_count + ARTICLES_PER_PAGE - 1) // ARTICLES_PER_PAGE

        # Build sort order with nulls last
        sort_attr = SORT_COLUMNS[sort_column]
        if sort_dir == 'desc':
            order = nullslast(sort_attr.desc())
        else:
            order = nullslast(sort_attr.asc())

        # Get articles for current page with sorting
        articles = query.order_by(order).offset(
            (page - 1) * ARTICLES_PER_PAGE
        ).limit(ARTICLES_PER_PAGE).all()

        # Get stats
        stats = {
            'total': session.query(Article).count(),
            'pending': session.query(Article).filter(Article.status == ArticleStatus.PENDING).count(),
            'emailed': session.query(Article).filter(Article.status == ArticleStatus.EMAILED).count(),
            'good': session.query(Article).filter(Article.status == ArticleStatus.GOOD).count(),
            'rejected': session.query(Article).filter(Article.status == ArticleStatus.REJECTED).count(),
            'published': session.query(Article).filter(Article.status == ArticleStatus.PUBLISHED).count(),
            'high_score': session.query(Article).filter(Article.filter_score >= 0.5).count(),
        }

        # Get unique sources for dropdown
        sources = [r[0] for r in session.query(Article.source_name).distinct().order_by(Article.source_name).all()]

        return render_template('admin/articles.html',
                             articles=articles,
                             stats=stats,
                             sources=sources,
                             filters={
                                 'status': status_filter,
                                 'min_score': min_score,
                                 'source': source_filter,
                                 'search': search,
                             },
                             sort=sort_column,
                             dir=sort_dir,
                             page=page,
                             total_pages=total_pages)
    finally:
        session.close()


@main.route('/admin/articles/<article_id>/pending', methods=['POST'])
def admin_set_pending(article_id: str):
    """Reset an article to pending status."""
    session = SessionLocal()
    try:
        article_uuid = UUID(article_id)
        article = session.query(Article).filter(Article.id == article_uuid).first()
        if not article:
            return jsonify({'error': 'Article not found'}), 404

        article.status = ArticleStatus.PENDING
        article.emailed_date = None
        article.email_batch_id = None

        # Boost score to 0.5 if below threshold so it qualifies for email
        if article.filter_score < 0.5:
            article.filter_score = 0.5
            article.filter_notes = (article.filter_notes or '') + ' [Manually included by editor]'

        # Remove any feedback
        feedback = session.query(Feedback).filter(Feedback.article_id == article_uuid).first()
        if feedback:
            session.delete(feedback)

        session.commit()
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@main.route('/admin/articles/<article_id>/reject', methods=['POST'])
def admin_set_rejected(article_id: str):
    """Mark an article as rejected."""
    session = SessionLocal()
    try:
        article_uuid = UUID(article_id)
        article = session.query(Article).filter(Article.id == article_uuid).first()
        if not article:
            return jsonify({'error': 'Article not found'}), 404

        article.status = ArticleStatus.REJECTED
        session.commit()
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@main.route('/admin/articles/<article_id>/published', methods=['POST'])
def admin_set_published(article_id: str):
    """Mark an article as published."""
    session = SessionLocal()
    try:
        article_uuid = UUID(article_id)
        article = session.query(Article).filter(Article.id == article_uuid).first()
        if not article:
            return jsonify({'error': 'Article not found'}), 404

        article.status = ArticleStatus.PUBLISHED
        session.commit()
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@main.route('/admin/articles/<article_id>/why_not', methods=['POST'])
def admin_why_not(article_id: str):
    """Mark article as rejected with feedback notes."""
    session = SessionLocal()
    try:
        article_uuid = UUID(article_id)
        article = session.query(Article).filter(Article.id == article_uuid).first()
        if not article:
            return jsonify({'error': 'Article not found'}), 404

        data = request.get_json()
        notes = data.get('notes', '').strip() if data else ''

        # Create feedback record
        existing = session.query(Feedback).filter(Feedback.article_id == article_uuid).first()
        if existing:
            existing.rating = FeedbackRating.WHY_NOT
            existing.notes = notes if notes else None
            existing.clicked_at = datetime.now(timezone.utc)
        else:
            feedback = Feedback(
                article_id=article_uuid,
                rating=FeedbackRating.WHY_NOT,
                notes=notes if notes else None,
                clicked_at=datetime.now(timezone.utc),
            )
            session.add(feedback)

        # Update article status
        article.status = ArticleStatus.REJECTED

        # Update source metrics
        if article.source_id:
            source = session.query(Source).filter(Source.id == article.source_id).first()
            if source:
                source.total_rejected += 1

        session.commit()
        logger.info(f"Why Not feedback from admin: article={article_id}, notes={notes[:50] if notes else 'none'}...")
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@main.route('/admin/articles/<article_id>/delete', methods=['POST'])
def admin_delete_article(article_id: str):
    """Delete an article."""
    session = SessionLocal()
    try:
        article_uuid = UUID(article_id)
        article = session.query(Article).filter(Article.id == article_uuid).first()
        if not article:
            return jsonify({'error': 'Article not found'}), 404

        # Delete related records first
        session.query(Feedback).filter(Feedback.article_id == article_uuid).delete()
        session.query(DeepDive).filter(DeepDive.article_id == article_uuid).delete()

        session.delete(article)
        session.commit()
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@main.route('/admin/articles/bulk', methods=['POST'])
def admin_bulk_action():
    """Handle bulk actions on multiple articles."""
    session = SessionLocal()
    try:
        data = request.get_json()
        ids = data.get('ids', [])
        action = data.get('action', '')

        if not ids:
            return jsonify({'error': 'No articles selected'}), 400

        uuids = [UUID(id_str) for id_str in ids]

        if action == 'pending':
            # Reset to pending and boost low scores to 0.5
            articles = session.query(Article).filter(Article.id.in_(uuids)).all()
            for article in articles:
                article.status = ArticleStatus.PENDING
                article.emailed_date = None
                article.email_batch_id = None
                if article.filter_score < 0.5:
                    article.filter_score = 0.5
                    article.filter_notes = (article.filter_notes or '') + ' [Manually included by editor]'
            session.query(Feedback).filter(Feedback.article_id.in_(uuids)).delete(synchronize_session=False)

        elif action == 'reject':
            session.query(Article).filter(Article.id.in_(uuids)).update(
                {Article.status: ArticleStatus.REJECTED},
                synchronize_session=False
            )

        elif action == 'published':
            session.query(Article).filter(Article.id.in_(uuids)).update(
                {Article.status: ArticleStatus.PUBLISHED},
                synchronize_session=False
            )

        elif action == 'delete':
            session.query(Feedback).filter(Feedback.article_id.in_(uuids)).delete(synchronize_session=False)
            session.query(DeepDive).filter(DeepDive.article_id.in_(uuids)).delete(synchronize_session=False)
            session.query(Article).filter(Article.id.in_(uuids)).delete(synchronize_session=False)

        else:
            return jsonify({'error': 'Invalid action'}), 400

        session.commit()
        return jsonify({'success': True, 'count': len(ids)})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


# =============================================================================
# RSS Source Management Routes
# =============================================================================

# RSS validation configuration
RSS_VALIDATION_TIMEOUT = 10  # seconds
RSS_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'


def validate_rss_url(url: str) -> tuple[bool, str]:
    """
    Validate that a URL points to a valid RSS/Atom feed.
    
    Uses httpx to fetch with timeout, then feedparser to validate content.
    
    Args:
        url: URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Fetch with timeout using httpx (feedparser doesn't support timeout directly)
        response = httpx.get(
            url,
            timeout=RSS_VALIDATION_TIMEOUT,
            follow_redirects=True,
            headers={
                'User-Agent': RSS_USER_AGENT,
                'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml',
            }
        )
        response.raise_for_status()
        
        # Parse the fetched content
        result = feedparser.parse(response.content)
        
        # Check for parsing errors
        if result.bozo:
            bozo_exception = getattr(result, 'bozo_exception', None)
            # Some bozo exceptions are recoverable
            if not result.entries:
                return False, f"Invalid RSS/Atom feed: {bozo_exception}"
        
        # Must have at least the feed structure (entries can be empty for new feeds)
        if not hasattr(result, 'feed') or not result.feed:
            return False, "URL does not contain a valid RSS/Atom feed"
        
        return True, ""
    
    except httpx.TimeoutException:
        return False, f"Timeout: feed took longer than {RSS_VALIDATION_TIMEOUT} seconds to respond"
    except httpx.HTTPStatusError as e:
        return False, f"URL returned HTTP {e.response.status_code}"
    except httpx.RequestError as e:
        return False, f"Error fetching URL: {str(e)}"
    except Exception as e:
        return False, f"Error validating feed: {str(e)}"


@main.route('/admin/sources')
def admin_sources():
    """
    Admin page to view and manage RSS feed sources.
    
    Supports filtering by status (active/paused) and sorting.
    """
    session = SessionLocal()
    
    try:
        # Get filter parameters
        status_filter = request.args.get('status', '')
        sort_by = request.args.get('sort', 'name')
        
        # Build query for RSS sources only
        query = session.query(Source).filter(Source.type == SourceType.RSS)
        
        # Apply status filter
        if status_filter == 'active':
            query = query.filter(Source.is_active == True)
        elif status_filter == 'paused':
            query = query.filter(Source.is_active == False)
        
        # Apply sorting
        if sort_by == 'trust_score':
            query = query.order_by(Source.trust_score.desc())
        elif sort_by == 'last_fetched':
            query = query.order_by(Source.last_fetched.desc().nullslast())
        elif sort_by == 'total_surfaced':
            query = query.order_by(Source.total_surfaced.desc())
        else:  # default: name
            query = query.order_by(Source.name)
        
        sources = query.all()
        
        # Calculate stats
        total_rss = session.query(Source).filter(Source.type == SourceType.RSS).count()
        active_count = session.query(Source).filter(
            Source.type == SourceType.RSS,
            Source.is_active == True
        ).count()
        paused_count = total_rss - active_count
        
        stats = {
            'total': total_rss,
            'active': active_count,
            'paused': paused_count,
        }
        
        return render_template('admin/sources.html',
                             sources=sources,
                             stats=stats,
                             filters={
                                 'status': status_filter,
                                 'sort': sort_by,
                             })
    finally:
        session.close()


@main.route('/admin/sources', methods=['POST'])
def admin_add_source():
    """
    Add a new RSS feed source.
    
    Validates the URL is a valid RSS/Atom feed before saving.
    """
    session = SessionLocal()
    
    try:
        # Get form data
        name = request.form.get('name', '').strip()
        url = request.form.get('url', '').strip()
        notes = request.form.get('notes', '').strip()
        
        # Validate required fields
        if not name:
            flash('Feed name is required', 'error')
            return redirect(url_for('main.admin_sources'))
        
        if not url:
            flash('Feed URL is required', 'error')
            return redirect(url_for('main.admin_sources'))
        
        # Check for duplicate name
        existing_name = session.query(Source).filter(Source.name == name).first()
        if existing_name:
            flash('A source with this name already exists', 'error')
            return redirect(url_for('main.admin_sources'))
        
        # Check for duplicate URL (RSS sources only)
        existing_url = session.query(Source).filter(
            Source.url == url,
            Source.type == SourceType.RSS
        ).first()
        if existing_url:
            flash(f'This feed URL already exists as "{existing_url.name}"', 'error')
            return redirect(url_for('main.admin_sources'))
        
        # Validate RSS feed
        is_valid, error_msg = validate_rss_url(url)
        if not is_valid:
            flash(f'Invalid RSS feed: {error_msg}', 'error')
            return redirect(url_for('main.admin_sources'))
        
        # Create new source
        source = Source(
            name=name,
            type=SourceType.RSS,
            url=url,
            is_active=True,
            trust_score=0.5,
            notes=notes if notes else None,
        )
        session.add(source)
        session.commit()
        
        logger.info(f"New RSS source added: {name} ({url})")
        flash(f'RSS feed "{name}" added successfully', 'success')
        return redirect(url_for('main.admin_sources'))
        
    except Exception as e:
        logger.error(f"Error adding RSS source: {e}")
        session.rollback()
        flash('Error adding RSS feed', 'error')
        return redirect(url_for('main.admin_sources'))
    finally:
        session.close()


@main.route('/admin/sources/<source_id>/pause', methods=['POST'])
def admin_pause_source(source_id: str):
    """Pause an active RSS feed source."""
    session = SessionLocal()
    try:
        source_uuid = UUID(source_id)
        source = session.query(Source).filter(
            Source.id == source_uuid,
            Source.type == SourceType.RSS
        ).first()
        if not source:
            return jsonify({'error': 'Source not found'}), 404
        
        source.is_active = False
        session.commit()
        
        logger.info(f"RSS source paused: {source.name}")
        return jsonify({'success': True, 'is_active': False})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@main.route('/admin/sources/<source_id>/resume', methods=['POST'])
def admin_resume_source(source_id: str):
    """Resume a paused RSS feed source."""
    session = SessionLocal()
    try:
        source_uuid = UUID(source_id)
        source = session.query(Source).filter(
            Source.id == source_uuid,
            Source.type == SourceType.RSS
        ).first()
        if not source:
            return jsonify({'error': 'Source not found'}), 404
        
        source.is_active = True
        session.commit()
        
        logger.info(f"RSS source resumed: {source.name}")
        return jsonify({'success': True, 'is_active': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@main.route('/admin/sources/<source_id>/delete', methods=['POST'])
def admin_delete_source(source_id: str):
    """
    Delete an RSS feed source.
    
    Fails if source has associated articles (FK constraint).
    """
    session = SessionLocal()
    try:
        source_uuid = UUID(source_id)
        source = session.query(Source).filter(
            Source.id == source_uuid,
            Source.type == SourceType.RSS
        ).first()
        if not source:
            return jsonify({'error': 'Source not found'}), 404
        
        # Check for associated articles
        article_count = session.query(Article).filter(Article.source_id == source_uuid).count()
        if article_count > 0:
            return jsonify({
                'error': f'Cannot delete source with {article_count} existing articles. Pause it instead.'
            }), 400
        
        source_name = source.name
        session.delete(source)
        session.commit()
        
        logger.info(f"RSS source deleted: {source_name}")
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


# ============================================================================
# Filter Pipeline Admin Routes
# ============================================================================

@main.route('/admin/filter-runs')
def admin_filter_runs():
    """
    List all pipeline runs with summary statistics.
    
    Shows funnel data: input → filter1 → filter2 → filter3 → output
    """
    session = SessionLocal()
    try:
        # Get recent pipeline runs (last 7 days worth)
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        
        runs = session.query(PipelineRun).filter(
            PipelineRun.started_at >= cutoff
        ).order_by(PipelineRun.started_at.desc()).all()
        
        # Calculate aggregate stats
        total_processed = sum(r.input_count for r in runs)
        total_passed = sum(r.filter3_pass_count or 0 for r in runs)
        avg_pass_rate = total_passed / total_processed if total_processed > 0 else 0
        
        stats = {
            'total_runs': len(runs),
            'total_processed': total_processed,
            'total_passed': total_passed,
            'avg_pass_rate': avg_pass_rate
        }
        
        return render_template('admin/filter_runs.html', runs=runs, stats=stats)
    finally:
        session.close()


@main.route('/admin/filter-runs/<run_id>')
def admin_filter_run_detail(run_id: str):
    """
    Show detailed funnel view for a single pipeline run.
    
    Displays each filter stage with passed/rejected articles and reasoning.
    """
    session = SessionLocal()
    try:
        run_uuid = UUID(run_id)
        run = session.query(PipelineRun).filter(PipelineRun.id == run_uuid).first()
        if not run:
            abort(404)
        
        # Get all traces for this run
        traces_list = session.query(FilterTrace).filter(
            FilterTrace.run_id == run_uuid
        ).order_by(FilterTrace.filter_order, FilterTrace.created_at).all()
        
        # Group traces by filter
        traces = {
            'news_check': [t for t in traces_list if t.filter_name == 'news_check'],
            'wow_factor': [t for t in traces_list if t.filter_name == 'wow_factor'],
            'values_fit': [t for t in traces_list if t.filter_name == 'values_fit']
        }
        
        # Calculate funnel stats
        funnel = {
            'news_check': {
                'passed': len([t for t in traces['news_check'] if t.decision == 'pass']),
                'rejected': len([t for t in traces['news_check'] if t.decision == 'reject'])
            },
            'wow_factor': {
                'passed': len([t for t in traces['wow_factor'] if t.decision == 'pass']),
                'rejected': len([t for t in traces['wow_factor'] if t.decision == 'reject'])
            },
            'values_fit': {
                'passed': len([t for t in traces['values_fit'] if t.decision == 'pass']),
                'rejected': len([t for t in traces['values_fit'] if t.decision == 'reject'])
            }
        }
        
        return render_template(
            'admin/filter_run_detail.html',
            run=run,
            traces=traces,
            funnel=funnel
        )
    except ValueError:
        abort(400, "Invalid run ID")
    finally:
        session.close()


@main.route('/admin/filter-runs/<run_id>/article/<path:article_url>')
def admin_article_journey(run_id: str, article_url: str):
    """
    Show the complete filter journey for a single article.
    
    Displays each filter's decision, score, and reasoning.
    """
    from urllib.parse import unquote
    
    session = SessionLocal()
    try:
        run_uuid = UUID(run_id)
        run = session.query(PipelineRun).filter(PipelineRun.id == run_uuid).first()
        if not run:
            abort(404)
        
        # URL decode the article URL
        decoded_url = unquote(article_url)
        
        # Get all traces for this article in this run
        traces = session.query(FilterTrace).filter(
            FilterTrace.run_id == run_uuid,
            FilterTrace.article_url == decoded_url
        ).order_by(FilterTrace.filter_order).all()
        
        if not traces:
            abort(404, "Article not found in this run")
        
        # Build journey dict
        journey = {}
        article_title = traces[0].article_title if traces else "Unknown"
        
        for trace in traces:
            journey[trace.filter_name] = {
                'decision': trace.decision,
                'score': trace.score,
                'reasoning': trace.reasoning,
                'input_tokens': trace.input_tokens,
                'output_tokens': trace.output_tokens,
                'latency_ms': trace.latency_ms
            }
        
        # Determine final outcome
        final_outcome = 'passed'
        rejected_at = None
        for filter_name in ['news_check', 'wow_factor', 'values_fit']:
            if filter_name in journey and journey[filter_name]['decision'] == 'reject':
                final_outcome = 'rejected'
                rejected_at = filter_name
                break
        
        return render_template(
            'admin/article_journey.html',
            run=run,
            article_url=decoded_url,
            article_title=article_title,
            journey=journey,
            final_outcome=final_outcome,
            rejected_at=rejected_at
        )
    except ValueError:
        abort(400, "Invalid run ID")
    finally:
        session.close()


@main.route('/admin/filter-runs/<run_id>/rejections/<filter_name>')
def admin_rejection_analysis(run_id: str, filter_name: str):
    """
    Show aggregated rejection patterns for a specific filter.
    
    Groups rejections by reasoning to identify systematic issues.
    """
    session = SessionLocal()
    try:
        run_uuid = UUID(run_id)
        run = session.query(PipelineRun).filter(PipelineRun.id == run_uuid).first()
        if not run:
            abort(404)
        
        # Validate filter name
        if filter_name not in ['news_check', 'wow_factor', 'values_fit']:
            abort(400, "Invalid filter name")
        
        # Get all rejections for this filter
        rejections = session.query(FilterTrace).filter(
            FilterTrace.run_id == run_uuid,
            FilterTrace.filter_name == filter_name,
            FilterTrace.decision == 'reject'
        ).all()
        
        total_rejected = len(rejections)
        
        # Group by reasoning pattern (truncated to first 100 chars for grouping)
        from collections import defaultdict
        pattern_groups = defaultdict(list)
        
        for r in rejections:
            # Use first line or first 100 chars as pattern key
            reason_key = r.reasoning.split('\n')[0][:100] if r.reasoning else "No reason provided"
            pattern_groups[reason_key].append({
                'url': r.article_url,
                'title': r.article_title,
                'score': r.score,
                'full_reasoning': r.reasoning
            })
        
        # Build patterns list sorted by count
        patterns = []
        for reason, examples in sorted(pattern_groups.items(), key=lambda x: -len(x[1])):
            patterns.append({
                'reason_summary': reason,
                'count': len(examples),
                'examples': examples
            })
        
        return render_template(
            'admin/rejection_analysis.html',
            run=run,
            filter_name=filter_name,
            patterns=patterns,
            total_rejected=total_rejected
        )
    except ValueError:
        abort(400, "Invalid run ID")
    finally:
        session.close()


@main.route('/admin/filter-runs/<run_id>/rejections/<filter_name>/export')
def admin_rejection_export(run_id: str, filter_name: str):
    """
    Export rejected articles for a filter as CSV.
    """
    from flask import Response
    import csv
    from io import StringIO
    
    session = SessionLocal()
    try:
        run_uuid = UUID(run_id)
        run = session.query(PipelineRun).filter(PipelineRun.id == run_uuid).first()
        if not run:
            abort(404)
        
        # Validate filter name
        if filter_name not in ['news_check', 'wow_factor', 'values_fit']:
            abort(400, "Invalid filter name")
        
        # Get all rejections for this filter
        rejections = session.query(FilterTrace).filter(
            FilterTrace.run_id == run_uuid,
            FilterTrace.filter_name == filter_name,
            FilterTrace.decision == 'reject'
        ).order_by(FilterTrace.created_at).all()
        
        # Build CSV
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Title', 'URL', 'Score', 'Reasoning'])
        
        for r in rejections:
            writer.writerow([
                r.article_title,
                r.article_url,
                f"{r.score:.2f}" if r.score is not None else "",
                r.reasoning
            ])
        
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=rejections_{filter_name}_{run_id[:8]}.csv'
            }
        )
    except ValueError:
        abort(400, "Invalid run ID")
    finally:
        session.close()


@main.route('/admin/unreject-article', methods=['POST'])
def unreject_article():
    """
    Unreject an article, changing its status from rejected to pending.
    
    This allows John to rescue articles that were incorrectly rejected by
    the filtering pipeline.
    """
    article_url = request.form.get('article_url')
    
    if not article_url:
        flash('No article URL provided', 'error')
        return redirect(request.referrer or url_for('main.admin_filter_runs'))
    
    session = SessionLocal()
    try:
        article = session.query(Article).filter(
            Article.external_url == article_url
        ).first()
        
        if not article:
            flash('Article not found', 'error')
            return redirect(request.referrer or url_for('main.admin_filter_runs'))
        
        if article.status == ArticleStatus.PENDING and article.filter_status == FilterStatus.PASSED:
            flash('Article is already pending', 'info')
            return redirect(request.referrer or url_for('main.admin_filter_runs'))
        
        # Update status to make it a candidate
        article.status = ArticleStatus.PENDING
        article.filter_status = FilterStatus.PASSED
        session.commit()
        
        flash(f'Article unrejected: {article.headline[:50]}...', 'success')
        return redirect(request.referrer or url_for('main.admin_filter_runs'))
        
    except Exception as e:
        logger.error(f"Error unrejecting article: {e}")
        flash(f'Error unrejecting article: {str(e)}', 'error')
        return redirect(request.referrer or url_for('main.admin_filter_runs'))
    finally:
        session.close()
