"""
Filter 3: Values Fit

Evaluates if a news story aligns with Amish/conservative values and avoids 
forbidden topics.

This filter asks ONE question: "Does this fit our values?"
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

from anthropic import Anthropic

from app.database import SessionLocal
from app.models import FilterRule, RuleType

logger = logging.getLogger(__name__)

# Configuration
MODEL = os.environ.get("FILTER_VALUES_FIT_MODEL", "claude-sonnet-4-5")
MAX_TOKENS = 1024
TEMPERATURE = 0
CONTENT_LIMIT = 8000  # Truncate articles to 8,000 characters
VALUES_THRESHOLD = float(os.environ.get("FILTER_VALUES_THRESHOLD", "0.5"))

# Anthropic beta API version for structured outputs
STRUCTURED_OUTPUTS_BETA = os.environ.get(
    "ANTHROPIC_STRUCTURED_OUTPUTS_BETA", 
    "structured-outputs-2025-11-13"
)

# JSON Schema for structured output
VALUES_FIT_SCHEMA = {
    "type": "object",
    "properties": {
        "values_score": {
            "type": "number",
            "description": "Score from 0.0 to 1.0 indicating how well this story fits Amish values"
        },
        "reasoning": {
            "type": "string",
            "description": "Brief explanation of why this story does or doesn't fit the values criteria"
        }
    },
    "required": ["values_score", "reasoning"],
    "additionalProperties": False
}

VALUES_FIT_PROMPT_TEMPLATE = """You are evaluating news stories for alignment with Amish/conservative Christian values.

This publication serves Plain News readers - Amish and conservative Mennonite communities. Stories should be wholesome, relatable, and written at an 8th-grade reading level.

MUST INCLUDE (stories should have at least one):
{must_have_rules}

MUST AVOID (stories with these should be rejected):
{must_avoid_rules}

Score the values fit from 0.0 to 1.0:
- 0.8-1.0: Perfect fit - wholesome, community-focused, appropriate
- 0.5-0.7: Good fit - mostly appropriate with minor concerns
- 0.2-0.4: Poor fit - some inappropriate elements or conflicts with values
- 0.0-0.2: Reject - contains forbidden topics or conflicts with core values

DO NOT consider if the story is interesting or surprising - ONLY evaluate if it fits the values criteria above.

Evaluate this story:

TITLE: {title}

CONTENT:
{content}

Score the values fit. Be strict about the MUST AVOID topics."""


@dataclass
class ValuesFitResult:
    """Result from the values fit filter."""
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


def load_filter_rules() -> dict:
    """
    Load must_have and must_avoid rules from the FilterRule table.
    
    Returns:
        Dict with 'must_have' and 'must_avoid' lists of rule texts
    """
    session = SessionLocal()
    try:
        rules = session.query(FilterRule).filter(FilterRule.is_active == True).all()
        
        must_have = []
        must_avoid = []
        
        for rule in rules:
            if rule.rule_type == RuleType.MUST_HAVE:
                must_have.append(f"- {rule.rule_text}")
            elif rule.rule_type == RuleType.MUST_AVOID:
                must_avoid.append(f"- {rule.rule_text}")
        
        # Default rules if none configured
        if not must_have:
            must_have = [
                "- Animals, wildlife, farming stories",
                "- Community efforts and barn raisings",
                "- Small-town traditions and events",
                "- Nature, weather, and seasonal stories",
                "- Food, cooking, and recipes",
                "- Crafts and traditional skills"
            ]
        
        if not must_avoid:
            must_avoid = [
                "- Politics, elections, government controversy",
                "- Violence, crime, death, tragedy",
                "- Alcohol, drugs, gambling",
                "- Sexual content or immodesty",
                "- Modern technology focus (smartphones, internet, AI)",
                "- Individual hero worship or celebrity focus",
                "- Military, war, international conflict"
            ]
        
        return {
            "must_have": must_have,
            "must_avoid": must_avoid
        }
    finally:
        session.close()


def filter_values_fit(article: dict, rules: Optional[dict] = None) -> ValuesFitResult:
    """
    Evaluate if an article fits Amish/conservative values.
    
    Args:
        article: Dict with 'title', 'content' keys
        rules: Optional dict with 'must_have' and 'must_avoid' lists.
               If not provided, loads from database.
        
    Returns:
        ValuesFitResult with passed status, score, reasoning, and metrics
    """
    client = Anthropic()
    
    # Load rules if not provided
    if rules is None:
        rules = load_filter_rules()
    
    # Prepare content
    title = article.get('title', 'Untitled')
    content = truncate_content(article.get('content', ''))
    
    # Format rules as bullet lists
    must_have_text = "\n".join(rules.get("must_have", []))
    must_avoid_text = "\n".join(rules.get("must_avoid", []))
    
    # Format prompt
    prompt = VALUES_FIT_PROMPT_TEMPLATE.format(
        must_have_rules=must_have_text,
        must_avoid_rules=must_avoid_text,
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
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "values_fit_result",
                    "schema": VALUES_FIT_SCHEMA,
                    "strict": True
                }
            }
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Parse response
        import json
        result = json.loads(response.content[0].text)
        
        # Clamp score to 0.0-1.0 range
        score = max(0.0, min(1.0, result["values_score"]))
        passed = score >= VALUES_THRESHOLD
        
        return ValuesFitResult(
            passed=passed,
            score=score,
            reasoning=result["reasoning"],
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=latency_ms
        )
        
    except Exception as e:
        logger.error(f"Values fit filter error for '{title}': {e}")
        latency_ms = int((time.time() - start_time) * 1000)
        return ValuesFitResult(
            passed=False,
            score=0.0,
            reasoning=f"Filter error: {str(e)}",
            input_tokens=0,
            output_tokens=0,
            latency_ms=latency_ms
        )

