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

from flask import Blueprint, render_template, request, abort, jsonify
from sqlalchemy import func
from werkzeug.exceptions import HTTPException

from app.database import SessionLocal
from app.models import Article, ArticleStatus, Feedback, FeedbackRating, Source, DeepDive

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

@main.route('/admin/articles')
def admin_articles():
    """
    Admin page to view and manage all articles.

    Supports filtering by status, score, source, and search.
    """
    session = SessionLocal()

    try:
        # Get filter parameters
        status_filter = request.args.get('status', '')
        min_score = request.args.get('min_score', '')
        source_filter = request.args.get('source', '')
        search = request.args.get('search', '')
        page = int(request.args.get('page', 1))

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

        # Get articles for current page
        articles = query.order_by(Article.filter_score.desc()).offset(
            (page - 1) * ARTICLES_PER_PAGE
        ).limit(ARTICLES_PER_PAGE).all()

        # Get stats
        stats = {
            'total': session.query(Article).count(),
            'pending': session.query(Article).filter(Article.status == ArticleStatus.PENDING).count(),
            'emailed': session.query(Article).filter(Article.status == ArticleStatus.EMAILED).count(),
            'good': session.query(Article).filter(Article.status == ArticleStatus.GOOD).count(),
            'rejected': session.query(Article).filter(Article.status == ArticleStatus.REJECTED).count(),
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
            # Reset to pending
            session.query(Article).filter(Article.id.in_(uuids)).update(
                {Article.status: ArticleStatus.PENDING, Article.emailed_date: None, Article.email_batch_id: None},
                synchronize_session=False
            )
            session.query(Feedback).filter(Feedback.article_id.in_(uuids)).delete(synchronize_session=False)

        elif action == 'reject':
            session.query(Article).filter(Article.id.in_(uuids)).update(
                {Article.status: ArticleStatus.REJECTED},
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
