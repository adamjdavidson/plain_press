"""
Filter Pipeline Orchestrator

Runs three sequential filters (News Check → Wow Factor → Values Fit) with tracing.
Records all filter decisions to enable funnel analysis and prompt tuning.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.database import SessionLocal
from app.models import PipelineRun, FilterTrace, PipelineRunStatus
from app.services.filter_news_check import filter_news_check, NewsCheckResult
from app.services.filter_wow_factor import filter_wow_factor, WowFactorResult
from app.services.filter_values_fit import filter_values_fit, load_filter_rules, ValuesFitResult

logger = logging.getLogger(__name__)

# Configuration
TRACING_ENABLED = os.environ.get("FILTER_TRACING_ENABLED", "true").lower() == "true"


@dataclass
class FilterResult:
    """Unified result structure for pipeline output."""
    url: str
    title: str
    passed: bool
    content_type: Optional[str] = None  # From Filter 1
    wow_score: Optional[float] = None   # From Filter 2
    values_score: Optional[float] = None  # From Filter 3
    rejection_stage: Optional[str] = None  # Which filter rejected it
    rejection_reason: Optional[str] = None  # Why it was rejected


@dataclass
class PipelineResult:
    """Result from running the full pipeline."""
    run_id: UUID
    passed_articles: list[FilterResult]
    failed_articles: list[FilterResult]
    stats: dict


def create_pipeline_run(session, input_count: int) -> PipelineRun:
    """
    Create a new PipelineRun record at the start of a pipeline execution.
    
    Args:
        session: Database session
        input_count: Number of articles entering the pipeline
        
    Returns:
        Created PipelineRun instance
    """
    run = PipelineRun(
        status=PipelineRunStatus.RUNNING,
        input_count=input_count
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    logger.info(f"Created pipeline run {run.id} with {input_count} input articles")
    return run


def record_trace(
    session,
    run_id: UUID,
    article_url: str,
    article_title: str,
    filter_name: str,
    filter_order: int,
    decision: str,
    reasoning: str,
    score: Optional[float] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    latency_ms: Optional[int] = None
) -> FilterTrace:
    """
    Record a filter decision trace.
    
    Args:
        session: Database session
        run_id: Pipeline run UUID
        article_url: URL of the article being evaluated
        article_title: Title of the article
        filter_name: Name of the filter (news_check, wow_factor, values_fit)
        filter_order: Order in pipeline (1, 2, or 3)
        decision: 'pass' or 'reject'
        reasoning: Claude's explanation
        score: Numeric score if applicable
        input_tokens: Tokens sent to Claude
        output_tokens: Tokens received
        latency_ms: API call duration
        
    Returns:
        Created FilterTrace instance
    """
    if not TRACING_ENABLED:
        return None
        
    trace = FilterTrace(
        run_id=run_id,
        article_url=article_url,
        article_title=article_title[:500],  # Truncate title to fit column
        filter_name=filter_name,
        filter_order=filter_order,
        decision=decision,
        score=score,
        reasoning=reasoning,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms
    )
    session.add(trace)
    session.commit()
    return trace


def update_pipeline_run(
    session,
    run: PipelineRun,
    status: PipelineRunStatus,
    filter1_pass: Optional[int] = None,
    filter2_pass: Optional[int] = None,
    filter3_pass: Optional[int] = None,
    error_message: Optional[str] = None
):
    """
    Update a PipelineRun with final counts and status.
    
    Args:
        session: Database session
        run: PipelineRun to update
        status: Final status
        filter1_pass: Articles passing Filter 1
        filter2_pass: Articles passing Filter 2
        filter3_pass: Articles passing Filter 3
        error_message: Error details if failed
    """
    run.status = status
    run.completed_at = datetime.utcnow()
    run.filter1_pass_count = filter1_pass
    run.filter2_pass_count = filter2_pass
    run.filter3_pass_count = filter3_pass
    run.error_message = error_message
    session.commit()
    logger.info(f"Pipeline run {run.id} completed: {status.value}")


def run_pipeline(articles: list[dict]) -> PipelineResult:
    """
    Run the multi-stage filtering pipeline on a batch of articles.
    
    Pipeline stages:
    1. News Check - Is this actual news?
    2. Wow Factor - Would this make someone say wow?
    3. Values Fit - Does this fit Amish values?
    
    Articles rejected at any stage do not proceed to subsequent stages.
    All decisions are traced for analysis.
    
    Args:
        articles: List of dicts with 'url', 'title', 'content' keys
        
    Returns:
        PipelineResult with passed/failed articles and statistics
    """
    session = SessionLocal()
    
    try:
        # Create pipeline run
        run = create_pipeline_run(session, len(articles))
        run_id = run.id
        
        # Load filter rules once for all articles
        rules = load_filter_rules()
        
        # Track results at each stage
        passed_articles = []
        failed_articles = []
        
        # Stage counters
        filter1_pass_count = 0
        filter2_pass_count = 0
        filter3_pass_count = 0
        
        # Process each article through the pipeline
        for article in articles:
            url = article.get('url', '')
            title = article.get('title', 'Untitled')
            
            try:
                # =========================================
                # FILTER 1: News Check
                # =========================================
                result1 = filter_news_check(article)
                
                record_trace(
                    session=session,
                    run_id=run_id,
                    article_url=url,
                    article_title=title,
                    filter_name="news_check",
                    filter_order=1,
                    decision="pass" if result1.passed else "reject",
                    reasoning=result1.reasoning,
                    score=None,
                    input_tokens=result1.input_tokens,
                    output_tokens=result1.output_tokens,
                    latency_ms=result1.latency_ms
                )
                
                if not result1.passed:
                    # Rejected at Filter 1 - record and skip remaining filters
                    failed_articles.append(FilterResult(
                        url=url,
                        title=title,
                        passed=False,
                        content_type=result1.category,
                        rejection_stage="news_check",
                        rejection_reason=result1.reasoning
                    ))
                    continue
                
                filter1_pass_count += 1
                
                # =========================================
                # FILTER 2: Wow Factor
                # =========================================
                result2 = filter_wow_factor(article)
                
                record_trace(
                    session=session,
                    run_id=run_id,
                    article_url=url,
                    article_title=title,
                    filter_name="wow_factor",
                    filter_order=2,
                    decision="pass" if result2.passed else "reject",
                    reasoning=result2.reasoning,
                    score=result2.score,
                    input_tokens=result2.input_tokens,
                    output_tokens=result2.output_tokens,
                    latency_ms=result2.latency_ms
                )
                
                if not result2.passed:
                    # Rejected at Filter 2 - record and skip remaining filter
                    failed_articles.append(FilterResult(
                        url=url,
                        title=title,
                        passed=False,
                        content_type="news_article",
                        wow_score=result2.score,
                        rejection_stage="wow_factor",
                        rejection_reason=result2.reasoning
                    ))
                    continue
                
                filter2_pass_count += 1
                
                # =========================================
                # FILTER 3: Values Fit
                # =========================================
                result3 = filter_values_fit(article, rules)
                
                record_trace(
                    session=session,
                    run_id=run_id,
                    article_url=url,
                    article_title=title,
                    filter_name="values_fit",
                    filter_order=3,
                    decision="pass" if result3.passed else "reject",
                    reasoning=result3.reasoning,
                    score=result3.score,
                    input_tokens=result3.input_tokens,
                    output_tokens=result3.output_tokens,
                    latency_ms=result3.latency_ms
                )
                
                if not result3.passed:
                    # Rejected at Filter 3
                    failed_articles.append(FilterResult(
                        url=url,
                        title=title,
                        passed=False,
                        content_type="news_article",
                        wow_score=result2.score,
                        values_score=result3.score,
                        rejection_stage="values_fit",
                        rejection_reason=result3.reasoning
                    ))
                    continue
                
                filter3_pass_count += 1
                
                # =========================================
                # PASSED ALL FILTERS
                # =========================================
                passed_articles.append(FilterResult(
                    url=url,
                    title=title,
                    passed=True,
                    content_type="news_article",
                    wow_score=result2.score,
                    values_score=result3.score
                ))
                
            except Exception as e:
                # Error processing this article - log and continue
                logger.error(f"Error processing article {url}: {e}")
                failed_articles.append(FilterResult(
                    url=url,
                    title=title,
                    passed=False,
                    rejection_stage="error",
                    rejection_reason=str(e)
                ))
        
        # Update pipeline run with final counts
        update_pipeline_run(
            session=session,
            run=run,
            status=PipelineRunStatus.COMPLETED,
            filter1_pass=filter1_pass_count,
            filter2_pass=filter2_pass_count,
            filter3_pass=filter3_pass_count
        )
        
        # Build statistics
        stats = {
            "input_count": len(articles),
            "filter1_pass": filter1_pass_count,
            "filter2_pass": filter2_pass_count,
            "filter3_pass": filter3_pass_count,
            "final_pass": len(passed_articles),
            "final_reject": len(failed_articles)
        }
        
        logger.info(
            f"Pipeline complete: {len(articles)} in → "
            f"{filter1_pass_count} (F1) → {filter2_pass_count} (F2) → "
            f"{filter3_pass_count} (F3) = {len(passed_articles)} passed"
        )
        
        return PipelineResult(
            run_id=run_id,
            passed_articles=passed_articles,
            failed_articles=failed_articles,
            stats=stats
        )
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        if 'run' in locals():
            update_pipeline_run(
                session=session,
                run=run,
                status=PipelineRunStatus.FAILED,
                error_message=str(e)
            )
        raise
    finally:
        session.close()


@dataclass
class SingleArticleResult:
    """Result from filtering a single article."""
    passed: bool
    filter_score: float
    filter_notes: str
    summary: str
    amish_angle: str
    content_type: Optional[str] = None
    wow_score: Optional[float] = None


def run_pipeline_for_article(article) -> SingleArticleResult:
    """
    Run the multi-stage filtering pipeline on a single Article object.
    
    Used by the background filter worker to process one article at a time.
    Does NOT update the article in the database - caller is responsible for that.
    
    Args:
        article: SQLAlchemy Article object with external_url, headline, raw_content
        
    Returns:
        SingleArticleResult with filter decisions and generated content
    """
    # Prepare article data dict for filters
    article_data = {
        'url': article.external_url,
        'title': article.headline,
        'content': article.raw_content or ''
    }
    
    # Load filter rules
    rules = load_filter_rules()
    
    # =========================================
    # FILTER 1: News Check
    # =========================================
    try:
        result1 = filter_news_check(article_data)
    except Exception as e:
        logger.error(f"News check failed for {article.external_url}: {e}")
        return SingleArticleResult(
            passed=False,
            filter_score=0.0,
            filter_notes=f"Error in news_check: {e}",
            summary="",
            amish_angle="",
            content_type="error"
        )
    
    if not result1.passed:
        return SingleArticleResult(
            passed=False,
            filter_score=0.0,
            filter_notes=f"Rejected at news_check: {result1.reasoning}",
            summary="",
            amish_angle="",
            content_type=result1.category
        )
    
    # =========================================
    # FILTER 2: Wow Factor
    # =========================================
    try:
        result2 = filter_wow_factor(article_data)
    except Exception as e:
        logger.error(f"Wow factor failed for {article.external_url}: {e}")
        return SingleArticleResult(
            passed=False,
            filter_score=0.0,
            filter_notes=f"Error in wow_factor: {e}",
            summary="",
            amish_angle="",
            content_type="news_article"
        )
    
    if not result2.passed:
        return SingleArticleResult(
            passed=False,
            filter_score=0.0,
            filter_notes=f"Rejected at wow_factor: {result2.reasoning}",
            summary="",
            amish_angle="",
            content_type="news_article",
            wow_score=result2.score
        )
    
    # =========================================
    # FILTER 3: Values Fit
    # =========================================
    try:
        result3 = filter_values_fit(article_data, rules)
    except Exception as e:
        logger.error(f"Values fit failed for {article.external_url}: {e}")
        return SingleArticleResult(
            passed=False,
            filter_score=0.0,
            filter_notes=f"Error in values_fit: {e}",
            summary="",
            amish_angle="",
            content_type="news_article",
            wow_score=result2.score
        )
    
    if not result3.passed:
        return SingleArticleResult(
            passed=False,
            filter_score=result3.score or 0.0,
            filter_notes=f"Rejected at values_fit: {result3.reasoning}",
            summary="",
            amish_angle="",
            content_type="news_article",
            wow_score=result2.score
        )
    
    # =========================================
    # PASSED ALL FILTERS
    # =========================================
    # Summary and amish_angle will be generated by a separate process
    # after John approves an article
    return SingleArticleResult(
        passed=True,
        filter_score=result3.score or 0.7,
        filter_notes=f"Passed all filters. Wow: {result2.reasoning}. Values: {result3.reasoning}",
        summary="",  # Generated on approval
        amish_angle="",  # Generated on approval
        content_type="news_article",
        wow_score=result2.score
    )

