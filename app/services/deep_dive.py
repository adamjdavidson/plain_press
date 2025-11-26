"""
Deep Dive Report Generation Service

Orchestrates the creation of comprehensive reports for approved articles.
Uses Claude Sonnet for AI generation, saves to Google Docs, and sends via email.
"""

import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID

from anthropic import Anthropic

from app.database import SessionLocal
from app.models import Article, DeepDive
from app.services.content_fetcher import fetch_article_content, extract_from_html
from app.services.google_docs import create_doc, share_doc_with_user

logger = logging.getLogger(__name__)

# Claude model for deep dives (Sonnet for quality)
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Generation settings
MAX_RETRIES = 3
GENERATION_TIMEOUT = 90  # seconds

# Report prompt template
REPORT_PROMPT = """You are helping write stories for Plain News, an Amish newspaper.

Given this article, create a deep-dive report with these sections:

# SUMMARY
Write 2-3 sentences summarizing the story at an 8th grade reading level. Focus on what happened and why it matters.

# KEY FACTS
List 5-7 bullet points with the most important facts from the story. Include:
- Who is involved
- What happened
- Where and when
- Any numbers or specific details

# AMISH ANGLE
Explain in 2-3 sentences why this story would interest Plain community readers. Connect it to values like:
- Community and mutual aid
- Simple living and traditional ways
- Nature and farming
- Family and faith
- Honest work and craftsmanship

# STORY LEADS
Suggest 2-3 follow-up angles a reporter could explore to expand this into a longer piece.

# SOURCES
List the original source URL and any other sources mentioned in the article.

---

Article Headline: {headline}
Source: {source_name}
Original URL: {url}

Article Content:
{content}

---

Keep the total report under 1000 words. Write in clear, simple language suitable for an 8th grade reading level. Avoid complex words and long sentences."""


def get_anthropic_client() -> Anthropic:
    """Get Anthropic client."""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    return Anthropic(api_key=api_key)


def generate_report_content(
    headline: str,
    source_name: str,
    url: str,
    content: str
) -> Tuple[str, dict]:
    """
    Generate a deep dive report using Claude Sonnet.
    
    Args:
        headline: Article headline
        source_name: Source name
        url: Original article URL
        content: Extracted article content
        
    Returns:
        Tuple of (report_text, metadata_dict)
    """
    client = get_anthropic_client()
    
    prompt = REPORT_PROMPT.format(
        headline=headline,
        source_name=source_name,
        url=url,
        content=content
    )
    
    start_time = time.time()
    
    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            generation_time = time.time() - start_time
            
            report_text = response.content[0].text
            
            metadata = {
                'model': CLAUDE_MODEL,
                'generation_time_seconds': round(generation_time, 2),
                'prompt_tokens': response.usage.input_tokens,
                'completion_tokens': response.usage.output_tokens,
            }
            
            logger.info(
                f"Generated report: {metadata['completion_tokens']} tokens "
                f"in {metadata['generation_time_seconds']}s"
            )
            
            return report_text, metadata
            
        except Exception as e:
            logger.error(f"Claude API error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
    
    raise RuntimeError(f"Failed to generate report after {MAX_RETRIES} attempts")


def extract_key_points(report_text: str) -> list[str]:
    """
    Extract key points from the report for the DeepDive model.
    """
    key_points = []
    in_key_facts = False
    
    for line in report_text.split('\n'):
        line = line.strip()
        
        if 'KEY FACTS' in line.upper():
            in_key_facts = True
            continue
        elif line.startswith('#'):
            in_key_facts = False
            continue
        
        if in_key_facts and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
            # Remove bullet character
            point = line.lstrip('-•* ').strip()
            if point:
                key_points.append(point)
    
    return key_points[:7]  # Max 7 points


def extract_headline_suggestion(report_text: str, original_headline: str) -> str:
    """
    Extract or generate a headline suggestion from the report.
    For now, we'll clean up the original headline.
    """
    # Remove common prefixes/suffixes
    headline = original_headline.strip()
    
    # Truncate if too long
    if len(headline) > 500:
        headline = headline[:497] + '...'
    
    return headline


def generate_deep_dive_for_article(article_id: UUID) -> Optional[DeepDive]:
    """
    Generate a complete deep dive for an article.
    
    This is the main orchestration function that:
    1. Fetches article content
    2. Generates report via Claude
    3. Creates Google Doc
    4. Creates DeepDive record
    
    Args:
        article_id: UUID of the article
        
    Returns:
        DeepDive record if successful, None if failed
    """
    session = SessionLocal()
    
    try:
        # Get article
        article = session.query(Article).filter(Article.id == article_id).first()
        if not article:
            logger.error(f"Article not found: {article_id}")
            return None
        
        # Check if deep dive already exists
        existing = session.query(DeepDive).filter(DeepDive.article_id == article_id).first()
        if existing:
            logger.info(f"Deep dive already exists for article {article_id}")
            return existing
        
        logger.info(f"Generating deep dive for: {article.headline}")
        
        # Step 1: Fetch content
        content = fetch_article_content(
            article.external_url,
            fallback_content=article.raw_content
        )
        
        if not content:
            content = extract_from_html(article.raw_content or '') or article.summary or ''
        
        if not content:
            logger.error(f"No content available for article {article_id}")
            raise ValueError("No content available for deep dive")
        
        # Step 2: Generate report
        report_text, metadata = generate_report_content(
            headline=article.headline,
            source_name=article.source_name,
            url=article.external_url,
            content=content
        )
        
        # Step 3: Create Google Doc (optional - skip if not configured)
        doc_id = None
        doc_url = None
        
        if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') and os.environ.get('GOOGLE_DRIVE_FOLDER_ID'):
            doc_title = f"{datetime.now().strftime('%Y-%m-%d')} - {article.headline[:80]}"
            
            try:
                doc_id, doc_url = create_doc(doc_title, report_text)
                
                # Share with editor
                editor_email = os.environ.get('EDITOR_EMAIL')
                if editor_email:
                    share_doc_with_user(doc_id, editor_email, 'writer')
                    
            except Exception as e:
                logger.warning(f"Google Docs error (continuing without): {e}")
                doc_id = None
                doc_url = None
        else:
            logger.info("Google Docs not configured - skipping doc creation")
        
        # Step 4: Create DeepDive record
        key_points = extract_key_points(report_text)
        headline_suggestion = extract_headline_suggestion(report_text, article.headline)
        
        deep_dive = DeepDive(
            article_id=article_id,
            headline_suggestion=headline_suggestion,
            key_points=key_points if key_points else ["See full report"],
            additional_sources={
                'original_url': article.external_url,
                'generation_metadata': metadata,
            },
            full_report_text=report_text,
            google_doc_id=doc_id,
            google_doc_url=doc_url,
            generated_at=datetime.now(timezone.utc),
        )
        
        session.add(deep_dive)
        
        # Update article with Google Doc info
        if doc_url:
            article.google_doc_id = doc_id
            article.google_doc_url = doc_url
        
        session.commit()
        
        logger.info(f"Deep dive created: {deep_dive.id}")
        return deep_dive
        
    except Exception as e:
        logger.error(f"Failed to generate deep dive for {article_id}: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def get_deep_dive_for_article(article_id: UUID) -> Optional[DeepDive]:
    """
    Get existing deep dive for an article.
    """
    session = SessionLocal()
    try:
        return session.query(DeepDive).filter(DeepDive.article_id == article_id).first()
    finally:
        session.close()

