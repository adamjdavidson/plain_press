"""
Filter 1: News Check

Determines if content is actual news (an event that happened) versus non-news content
like event listings, directories, or about pages.

This filter asks ONE question: "Is this news?"
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

from anthropic import Anthropic

logger = logging.getLogger(__name__)

# Configuration
# Note: Using Sonnet because Haiku doesn't support structured outputs
MODEL = os.environ.get("FILTER_NEWS_CHECK_MODEL", "claude-sonnet-4-5")
MAX_TOKENS = 1024
TEMPERATURE = 0
CONTENT_LIMIT = 8000  # Truncate articles to 8,000 characters

# Anthropic beta API version for structured outputs
STRUCTURED_OUTPUTS_BETA = os.environ.get(
    "ANTHROPIC_STRUCTURED_OUTPUTS_BETA", 
    "structured-outputs-2025-11-13"
)

# JSON Schema for structured output
NEWS_CHECK_SCHEMA = {
    "type": "object",
    "properties": {
        "is_news": {
            "type": "boolean",
            "description": "True if this is an actual news story about an event that happened"
        },
        "category": {
            "type": "string",
            "enum": [
                "news_article",
                "event_listing", 
                "directory_page",
                "about_page",
                "product_page",
                "other_non_news"
            ],
            "description": "Classification of the content type"
        },
        "reasoning": {
            "type": "string",
            "description": "Brief explanation of the classification decision"
        }
    },
    "required": ["is_news", "category", "reasoning"],
    "additionalProperties": False
}

NEWS_CHECK_PROMPT = """You are a news classifier. Your ONLY job is to determine if this content is an actual NEWS STORY or something else.

A NEWS STORY is:
- A report about an EVENT that HAPPENED (past tense)
- Something newsworthy that occurred in the world
- A story someone would read to learn "what happened"

NOT a news story (classify as non-news):
- EVENT LISTING: Calendar of upcoming events, "join us on Saturday", schedule of activities
- DIRECTORY PAGE: List of businesses, churches, organizations with addresses/phone numbers
- ABOUT PAGE: "About us", company history, mission statement, team bios
- PRODUCT PAGE: Items for sale, services offered, pricing information
- OTHER NON-NEWS: Recipes, how-to guides, opinion pieces without news hook, press releases that don't report events

Evaluate this content:

TITLE: {title}
URL: {url}

CONTENT:
{content}

Classify this content. Be strict - if it's NOT clearly reporting on something that happened, mark it as non-news."""


@dataclass
class NewsCheckResult:
    """Result from the news check filter."""
    passed: bool
    category: str
    reasoning: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: Optional[int] = None


def truncate_content(content: str, limit: int = CONTENT_LIMIT) -> str:
    """Truncate content to specified character limit."""
    if len(content) <= limit:
        return content
    return content[:limit] + "\n\n[Content truncated...]"


def filter_news_check(article: dict) -> NewsCheckResult:
    """
    Evaluate if an article is actual news content.
    
    Args:
        article: Dict with 'url', 'title', 'content' keys
        
    Returns:
        NewsCheckResult with passed status, category, reasoning, and metrics
    """
    client = Anthropic()
    
    # Prepare content
    title = article.get('title', 'Untitled')
    url = article.get('url', '')
    content = truncate_content(article.get('content', ''))
    
    # Handle empty content
    if not content or len(content.strip()) < 50:
        return NewsCheckResult(
            passed=False,
            category="other_non_news",
            reasoning="Insufficient content to evaluate - article appears empty or failed to scrape",
            input_tokens=0,
            output_tokens=0,
            latency_ms=0
        )
    
    # Format prompt
    prompt = NEWS_CHECK_PROMPT.format(
        title=title,
        url=url,
        content=content
    )
    
    start_time = time.time()
    
    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            betas=[STRUCTURED_OUTPUTS_BETA],
            messages=[
                {"role": "user", "content": prompt}
            ],
            output_format={
                "type": "json_schema",
                "schema": NEWS_CHECK_SCHEMA
            }
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Parse response
        import json
        result = json.loads(response.content[0].text)
        
        return NewsCheckResult(
            passed=result["is_news"],
            category=result["category"],
            reasoning=result["reasoning"],
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=latency_ms
        )
        
    except Exception as e:
        logger.error(f"News check filter error for {url}: {e}")
        latency_ms = int((time.time() - start_time) * 1000)
        return NewsCheckResult(
            passed=False,
            category="other_non_news",
            reasoning=f"Filter error: {str(e)}",
            input_tokens=0,
            output_tokens=0,
            latency_ms=latency_ms
        )

