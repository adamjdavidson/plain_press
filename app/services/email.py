"""
Email Delivery Service

Sends daily candidate emails via SendGrid.
Handles retry logic, EmailBatch tracking, and article status updates.
"""

import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To, Subject, HtmlContent

from app.database import SessionLocal
from app.models import Article, ArticleStatus, EmailBatch, EmailStatus
from app.services.email_selector import select_articles_for_email

logger = logging.getLogger(__name__)

# Configuration
MAX_RETRIES = 3
RETRY_DELAYS = [30, 60, 120]  # seconds


def format_date_for_email(dt: Optional[datetime] = None) -> str:
    """
    Format a date for display in emails.

    Args:
        dt: Optional datetime to format (defaults to now)

    Returns:
        Formatted date string like "November 27, 2025"
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime('%B %d, %Y')


def get_sendgrid_client() -> SendGridAPIClient:
    """Get SendGrid client with API key from environment."""
    api_key = os.environ.get('SENDGRID_API_KEY')
    if not api_key:
        raise ValueError("SENDGRID_API_KEY environment variable not set")
    return SendGridAPIClient(api_key=api_key)


def get_template_env() -> Environment:
    """Get Jinja2 environment for email templates."""
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    return Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )


def render_email_html(articles: list[Article], date_str: str) -> str:
    """
    Render the daily candidates email HTML.

    Args:
        articles: List of Article objects to include
        date_str: Formatted date string for display

    Returns:
        Rendered HTML string
    """
    env = get_template_env()
    template = env.get_template('email/daily_candidates.html')

    # Production default - Railway env var is unreliable
    feedback_url_base = os.environ.get('FEEDBACK_URL_BASE') or 'https://plainpress-production.up.railway.app'
    logger.info(f"FEEDBACK_URL_BASE value: '{feedback_url_base}'")

    return template.render(
        articles=articles,
        date=date_str,
        article_count=len(articles),
        feedback_url_base=feedback_url_base,
    )


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    from_email: Optional[str] = None
) -> tuple[bool, Optional[str]]:
    """
    Send an email via SendGrid with retry logic.
    
    Args:
        to_email: Recipient email address (comma-separated for multiple)
        subject: Email subject line
        html_content: HTML body content
        from_email: Sender email (defaults to SENDGRID_FROM_EMAIL)
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    from_email = from_email or os.environ.get('SENDGRID_FROM_EMAIL', 'noreply@example.com')
    
    # Support comma-separated emails
    recipients = [email.strip() for email in to_email.split(',') if email.strip()]
    to_emails = [To(email) for email in recipients]
    
    message = Mail(
        from_email=From(from_email, 'Plain Press'),
        to_emails=to_emails,
        subject=Subject(subject),
        html_content=HtmlContent(html_content)
    )
    
    client = get_sendgrid_client()
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            response = client.send(message)
            
            # 2xx status codes indicate success
            if 200 <= response.status_code < 300:
                logger.info(f"Email sent successfully to {to_email}: {response.status_code}")
                return True, None
            
            # 4xx errors are client errors (don't retry)
            if 400 <= response.status_code < 500:
                error_msg = f"SendGrid client error: {response.status_code} - {response.body}"
                logger.error(error_msg)
                return False, error_msg
            
            # 5xx errors - retry
            last_error = f"SendGrid server error: {response.status_code}"
            logger.warning(f"{last_error} (attempt {attempt + 1}/{MAX_RETRIES})")
            
        except Exception as e:
            last_error = f"SendGrid exception: {str(e)}"
            logger.error(f"{last_error} (attempt {attempt + 1}/{MAX_RETRIES})")
        
        # Wait before retry (if not last attempt)
        if attempt < MAX_RETRIES - 1:
            delay = RETRY_DELAYS[attempt]
            logger.info(f"Retrying in {delay} seconds...")
            time.sleep(delay)
    
    return False, last_error


def create_email_batch(
    session,
    recipient_email: str,
    article_count: int,
    subject: str,
    status: EmailStatus,
    error_message: Optional[str] = None
) -> EmailBatch:
    """
    Create an EmailBatch record for tracking.
    
    Args:
        session: SQLAlchemy session
        recipient_email: Recipient email address
        article_count: Number of articles in email
        subject: Email subject line
        status: Delivery status
        error_message: Error message if failed
        
    Returns:
        Created EmailBatch object
    """
    batch = EmailBatch(
        sent_at=datetime.now(timezone.utc),
        recipient_emails=[recipient_email],
        article_count=article_count,
        subject_line=subject,
        status=status,
        error_message=error_message,
    )
    session.add(batch)
    session.flush()  # Get ID before commit
    return batch


def update_articles_to_emailed(session, articles: list[Article], batch_id) -> int:
    """
    Update article status to 'emailed' and link to batch.
    
    Args:
        session: SQLAlchemy session
        articles: List of Article objects
        batch_id: EmailBatch ID to link
        
    Returns:
        Number of articles updated
    """
    now = datetime.now(timezone.utc)
    count = 0
    
    for article in articles:
        article.status = ArticleStatus.EMAILED
        article.email_batch_id = batch_id
        article.emailed_date = now
        count += 1
    
    return count


def render_deep_dive_email(
    headline: str,
    source_name: str,
    report_text: str,
    doc_url: str,
    original_url: str
) -> str:
    """
    Render the deep dive report email HTML.
    
    Parses the report text to extract sections.
    """
    env = get_template_env()
    template = env.get_template('email/deep_dive_report.html')
    
    # Parse report sections
    sections = _parse_report_sections(report_text)
    
    return template.render(
        headline=headline,
        source_name=source_name,
        generated_date=datetime.now().strftime('%B %d, %Y'),
        doc_url=doc_url,
        original_url=original_url,
        summary=sections.get('summary', ''),
        key_points=sections.get('key_points', []),
        amish_angle=sections.get('amish_angle', ''),
        story_leads=sections.get('story_leads', ''),
    )


def _parse_report_sections(report_text: str) -> dict:
    """
    Parse report text into sections.
    """
    sections = {
        'summary': '',
        'key_points': [],
        'amish_angle': '',
        'story_leads': '',
    }
    
    current_section = None
    current_content = []
    
    for line in report_text.split('\n'):
        line_upper = line.upper().strip()
        
        # Detect section headers
        if 'SUMMARY' in line_upper and line.strip().startswith('#'):
            if current_section and current_content:
                _save_section(sections, current_section, current_content)
            current_section = 'summary'
            current_content = []
        elif 'KEY FACTS' in line_upper and line.strip().startswith('#'):
            if current_section and current_content:
                _save_section(sections, current_section, current_content)
            current_section = 'key_points'
            current_content = []
        elif 'AMISH ANGLE' in line_upper and line.strip().startswith('#'):
            if current_section and current_content:
                _save_section(sections, current_section, current_content)
            current_section = 'amish_angle'
            current_content = []
        elif 'STORY LEADS' in line_upper and line.strip().startswith('#'):
            if current_section and current_content:
                _save_section(sections, current_section, current_content)
            current_section = 'story_leads'
            current_content = []
        elif 'SOURCES' in line_upper and line.strip().startswith('#'):
            if current_section and current_content:
                _save_section(sections, current_section, current_content)
            current_section = 'sources'
            current_content = []
        elif current_section:
            current_content.append(line)
    
    # Save last section
    if current_section and current_content:
        _save_section(sections, current_section, current_content)
    
    return sections


def _save_section(sections: dict, section_name: str, content: list):
    """Save parsed content to the appropriate section."""
    if section_name == 'key_points':
        # Extract bullet points
        points = []
        for line in content:
            line = line.strip()
            if line.startswith(('-', '•', '*')):
                point = line.lstrip('-•* ').strip()
                if point:
                    points.append(point)
        sections['key_points'] = points[:7]
    else:
        # Join as paragraph
        text = '\n'.join(content).strip()
        sections[section_name] = text


def send_deep_dive_email(
    to_email: str,
    headline: str,
    source_name: str,
    report_text: str,
    doc_url: str,
    original_url: str
) -> tuple[bool, Optional[str]]:
    """
    Send a deep dive report email.
    
    Args:
        to_email: Recipient email
        headline: Article headline
        source_name: Source name
        report_text: Full report text
        doc_url: Google Doc URL
        original_url: Original article URL
        
    Returns:
        Tuple of (success, error_message)
    """
    subject = f"Deep Dive: {headline[:60]}{'...' if len(headline) > 60 else ''} - Plain Press"
    
    html_content = render_deep_dive_email(
        headline=headline,
        source_name=source_name,
        report_text=report_text,
        doc_url=doc_url,
        original_url=original_url
    )
    
    success, error = send_email(to_email, subject, html_content)
    
    if success:
        logger.info(f"Deep dive email sent for: {headline[:50]}...")
    else:
        logger.error(f"Deep dive email failed for: {headline[:50]}... - {error}")
    
    return success, error


def send_daily_candidates() -> dict:
    """
    Main function to send daily candidate email.

    Uses smart selector to pick articles with variety (max per source,
    max per topic), composes email, sends via SendGrid,
    updates article status, and creates EmailBatch record.

    Returns:
        Stats dict with results
    """
    session = SessionLocal()
    stats = {
        'articles_found': 0,
        'articles_sent': 0,
        'email_sent': False,
        'error': None,
    }

    try:
        # Use smart selector with variety algorithm
        articles = select_articles_for_email(session)

        stats['articles_found'] = len(articles)

        # Check if we have articles to send
        if not articles:
            logger.warning("No pending candidates for daily email")
            return stats

        logger.info(f"Selected {len(articles)} articles with variety algorithm")
        
        # Compose email
        date_str = datetime.now().strftime('%B %d, %Y')
        subject = f"Plain Press Candidates - {datetime.now().strftime('%b %d')} ({len(articles)} articles)"
        html_content = render_email_html(articles, date_str)
        
        # Get recipient
        recipient = os.environ.get('EDITOR_EMAIL')
        if not recipient:
            raise ValueError("EDITOR_EMAIL environment variable not set")
        
        # Send email
        success, error = send_email(recipient, subject, html_content)
        
        if success:
            # Create successful batch record
            batch = create_email_batch(
                session=session,
                recipient_email=recipient,
                article_count=len(articles),
                subject=subject,
                status=EmailStatus.SENT,
            )
            
            # Update article status
            updated = update_articles_to_emailed(session, articles, batch.id)
            
            session.commit()
            
            stats['articles_sent'] = updated
            stats['email_sent'] = True
            
            logger.info(f"Daily email sent: {updated} articles to {recipient}")
            
        else:
            # Create failed batch record
            batch = create_email_batch(
                session=session,
                recipient_email=recipient,
                article_count=len(articles),
                subject=subject,
                status=EmailStatus.FAILED,
                error_message=error,
            )
            session.commit()
            
            stats['error'] = error
            logger.error(f"Daily email failed: {error}")
        
    except Exception as e:
        logger.error(f"Error in send_daily_candidates: {e}")
        session.rollback()
        stats['error'] = str(e)
        raise
    finally:
        session.close()

    return stats


def send_refinement_report(to_email: str, results: dict) -> bool:
    """
    Send weekly refinement report email to editor.

    Args:
        to_email: Editor's email address
        results: Results dict from run_weekly_refinement()

    Returns:
        True if sent successfully, False otherwise
    """
    subject = f"Plain Press - Weekly Refinement Report ({format_date_for_email()})"

    # Build HTML content
    suggestions = results.get('suggestions', [])
    analysis = results.get('analysis', {})
    trust_changes = results.get('trust_score_changes', {})

    html_parts = [
        "<html><body>",
        "<h1>Weekly Refinement Report</h1>",
        f"<p>Period: {results.get('week_start', 'Unknown')[:10]} to {results.get('week_end', 'Unknown')[:10]}</p>",

        "<h2>Feedback Summary</h2>",
        f"<ul>",
        f"<li>Total feedback: {results.get('feedback_collected', 0)}</li>",
        f"<li>Trust scores updated: {results.get('trust_scores_updated', 0)}</li>",
        f"</ul>",
    ]

    # Source trust score changes
    if trust_changes:
        html_parts.append("<h2>Source Trust Score Changes</h2>")
        html_parts.append("<table border='1' cellpadding='5'>")
        html_parts.append("<tr><th>Source</th><th>Old Score</th><th>New Score</th><th>Approved</th><th>Rejected</th></tr>")
        for source, data in trust_changes.items():
            html_parts.append(
                f"<tr><td>{source}</td><td>{data['old']:.2f}</td><td>{data['new']:.2f}</td>"
                f"<td>{data['approved']}</td><td>{data['rejected']}</td></tr>"
            )
        html_parts.append("</table>")

    # Patterns identified
    if analysis.get('patterns'):
        html_parts.append("<h2>Patterns Identified</h2>")
        patterns = analysis['patterns']
        if isinstance(patterns, list):
            html_parts.append("<ul>")
            for p in patterns:
                html_parts.append(f"<li>{p}</li>")
            html_parts.append("</ul>")
        else:
            html_parts.append(f"<p>{patterns}</p>")

    # Suggestions
    if suggestions:
        html_parts.append("<h2>Suggestions for Improvement</h2>")
        html_parts.append("<ul>")
        for s in suggestions:
            if isinstance(s, dict):
                html_parts.append(f"<li><strong>{s.get('type', 'Suggestion')}:</strong> {s.get('description', str(s))}</li>")
            else:
                html_parts.append(f"<li>{s}</li>")
        html_parts.append("</ul>")

    # Insights
    if analysis.get('insights'):
        html_parts.append("<h2>Additional Insights</h2>")
        html_parts.append(f"<p>{analysis['insights']}</p>")

    # Errors
    if results.get('errors'):
        html_parts.append("<h2>Errors</h2>")
        html_parts.append("<ul style='color: red;'>")
        for e in results['errors']:
            html_parts.append(f"<li>{e}</li>")
        html_parts.append("</ul>")

    html_parts.append("</body></html>")
    html_content = "\n".join(html_parts)

    success, error = send_email(to_email, subject, html_content)

    if success:
        logger.info(f"Refinement report sent to {to_email}")
    else:
        logger.error(f"Failed to send refinement report: {error}")

    return success

