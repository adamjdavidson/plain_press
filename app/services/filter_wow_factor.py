"""
Filter 2: Wow Factor

Evaluates if a news story would make someone say "wow" - is it surprising, 
delightful, or unusual?

This filter asks ONE question: "Would this make someone go wow?"
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

from anthropic import Anthropic

logger = logging.getLogger(__name__)

# Configuration
MODEL = os.environ.get("FILTER_WOW_FACTOR_MODEL", "claude-sonnet-4-5")
MAX_TOKENS = 1024
TEMPERATURE = 0
CONTENT_LIMIT = 8000  # Truncate articles to 8,000 characters
WOW_THRESHOLD = float(os.environ.get("FILTER_WOW_THRESHOLD", "0.5"))

# Anthropic beta API version for structured outputs
STRUCTURED_OUTPUTS_BETA = os.environ.get(
    "ANTHROPIC_STRUCTURED_OUTPUTS_BETA", 
    "structured-outputs-2025-11-13"
)

# JSON Schema for structured output
WOW_FACTOR_SCHEMA = {
    "type": "object",
    "properties": {
        "wow_score": {
            "type": "number",
            "description": "Score from 0.0 to 1.0 indicating how 'wow-worthy' this story is"
        },
        "reasoning": {
            "type": "string",
            "description": "Brief explanation of why this story is or isn't wow-worthy"
        }
    },
    "required": ["wow_score", "reasoning"],
    "additionalProperties": False
}

WOW_FACTOR_PROMPT = """You are evaluating news stories for their "wow factor" - would this story make someone say "wow!"?

A story has HIGH wow factor if it is:
- SURPRISING: Unexpected, not routine or predictable news
- DELIGHTFUL: Produces a smile, warmth, sense of wonder
- UNUSUAL: Quirky, odd, uncommon - stands out from typical news

Score the wow factor from 0.0 to 1.0:
- 0.8-1.0: Genuinely remarkable - "I have to share this!"
- 0.5-0.7: Interesting - "That's nice to know"
- 0.2-0.4: Mildly interesting - "Okay, sure"
- 0.0-0.2: Boring - routine announcement, mundane event, standard press release

Examples of HIGH wow factor:
- A 200-year-old barn restored using only hand tools
- A rare albino deer spotted in farmland
- A community raises $50,000 in one day for a neighbor's medical bills
- A 95-year-old grandmother wins a pie-baking contest for the 50th year in a row

Examples of LOW wow factor:
- City council approves routine budget
- New traffic light installed at intersection
- Business announces quarterly earnings
- School board meeting scheduled for next week

DO NOT consider whether the story fits any particular values or audience - ONLY evaluate if it's surprising, delightful, or unusual.

Evaluate this story:

TITLE: {title}

CONTENT:
{content}

Score the wow factor. Be honest - most news is NOT wow-worthy."""


@dataclass
class WowFactorResult:
    """Result from the wow factor filter."""
    passed: bool
    score: float
    reasoning: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: Optional[int] = None


def truncate_content(content: str, limit: int = CONTENT_LIMIT) -> str:
    """Truncate content to specified character limit."""
    if len(content) <= limit:
        return content
    return content[:limit] + "\n\n[Content truncated...]"


def filter_wow_factor(article: dict) -> WowFactorResult:
    """
    Evaluate if an article has high wow factor.
    
    Args:
        article: Dict with 'title', 'content' keys
        
    Returns:
        WowFactorResult with passed status, score, reasoning, and metrics
    """
    client = Anthropic()
    
    # Prepare content
    title = article.get('title', 'Untitled')
    content = truncate_content(article.get('content', ''))
    
    # Format prompt
    prompt = WOW_FACTOR_PROMPT.format(
        title=title,
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
                "schema": WOW_FACTOR_SCHEMA
            }
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Parse response
        import json
        result = json.loads(response.content[0].text)
        
        # Clamp score to 0.0-1.0 range
        score = max(0.0, min(1.0, result["wow_score"]))
        passed = score >= WOW_THRESHOLD
        
        return WowFactorResult(
            passed=passed,
            score=score,
            reasoning=result["reasoning"],
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=latency_ms
        )
        
    except Exception as e:
        logger.error(f"Wow factor filter error for '{title}': {e}")
        latency_ms = int((time.time() - start_time) * 1000)
        return WowFactorResult(
            passed=False,
            score=0.0,
            reasoning=f"Filter error: {str(e)}",
            input_tokens=0,
            output_tokens=0,
            latency_ms=latency_ms
        )

