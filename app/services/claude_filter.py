"""
Claude Filtering Service with Structured Outputs

Evaluates articles against FilterRules using Claude with guaranteed JSON output.
Returns filter_score, summary, amish_angle, and filter_notes.
"""

import json
import logging
import os
import time
from typing import Optional

from anthropic import Anthropic

from app.database import SessionLocal
from app.models import FilterRule, RuleType

logger = logging.getLogger(__name__)

# Configuration
MODEL = "claude-sonnet-4-5"  # Supports structured outputs (Nov 2025)
MAX_TOKENS = 4096
TEMPERATURE = 0  # Deterministic for consistency
BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '10'))
FILTER_THRESHOLD = float(os.environ.get('FILTER_SCORE_THRESHOLD', '0.5'))
MAX_RETRIES = 2
RETRY_BASE_DELAY = 2.0

# Cost estimates (USD per 1M tokens) - Sonnet pricing
INPUT_COST_PER_M = 3.0
OUTPUT_COST_PER_M = 15.0

# JSON Schema for structured output - guarantees valid JSON
ARTICLE_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "filter_score": {"type": "number"},
                    "summary": {"type": "string"},
                    "amish_angle": {"type": "string"},
                    "filter_notes": {"type": "string"}
                },
                "required": ["index", "filter_score", "summary", "amish_angle", "filter_notes"],
                "additionalProperties": False
            }
        }
    },
    "required": ["results"],
    "additionalProperties": False
}


SYSTEM_PROMPT_TEMPLATE = """You are an editorial filter for Plain Press, a publication serving conservative Amish Christian readers. 
Your task is to evaluate article candidates for inclusion in the daily email digest.

EDITORIAL GUIDELINES:

The ideal story is a "delightful oddity" - something surprising, wholesome, and relatable that would make an Amish grandmother smile.

MUST HAVE (all stories need these):
{must_have_rules}

MUST AVOID (automatic rejection if present):
{must_avoid_rules}

GOOD TOPICS (boost score):
{good_topic_rules}

BORDERLINE (use judgment):
{borderline_rules}

For EACH article, provide:
- index: the article index from the input
- filter_score: float 0.0-1.0 (1.0 = perfect fit, 0.0 = completely inappropriate)
- summary: 2-3 sentence summary suitable for Amish readers (simple language, 8th grade level)
- amish_angle: 1 sentence explaining why this story resonates with Amish values
- filter_notes: brief explanation of scoring rationale"""


def get_anthropic_client() -> Anthropic:
    """Get Anthropic client with API key from environment."""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    return Anthropic(api_key=api_key)


def build_system_prompt() -> str:
    """
    Build the system prompt with current FilterRules from database.
    
    Returns:
        Formatted system prompt string
    """
    session = SessionLocal()
    
    try:
        rules = session.query(FilterRule).filter(FilterRule.is_active == True).all()
        
        # Group rules by type
        must_have = []
        must_avoid = []
        good_topics = []
        borderline = []
        
        for rule in rules:
            if rule.rule_type == RuleType.MUST_HAVE:
                must_have.append(f"- {rule.rule_text}")
            elif rule.rule_type == RuleType.MUST_AVOID:
                must_avoid.append(f"- {rule.rule_text}")
            elif rule.rule_type == RuleType.GOOD_TOPIC:
                good_topics.append(f"- {rule.rule_text}")
            elif rule.rule_type == RuleType.BORDERLINE:
                borderline.append(f"- {rule.rule_text}")
        
        return SYSTEM_PROMPT_TEMPLATE.format(
            must_have_rules='\n'.join(must_have) or '- No specific requirements',
            must_avoid_rules='\n'.join(must_avoid) or '- No specific exclusions',
            good_topic_rules='\n'.join(good_topics) or '- No specific preferences',
            borderline_rules='\n'.join(borderline) or '- Use general judgment',
        )
        
    finally:
        session.close()


def filter_article_batch(articles: list[dict], system_prompt: str) -> list[dict]:
    """
    Filter a batch of articles through Claude with structured outputs.
    
    Uses the structured outputs beta to guarantee valid JSON responses.
    
    Args:
        articles: List of article dicts with headline and content
        system_prompt: Pre-built system prompt with FilterRules
        
    Returns:
        List of filter result dicts with filter_score, summary, amish_angle, filter_notes
    """
    client = get_anthropic_client()
    
    # Prepare articles for prompt
    articles_for_prompt = []
    for i, article in enumerate(articles):
        articles_for_prompt.append({
            'index': i,
            'headline': article.get('headline', ''),
            'content': article.get('content', '')[:1500],  # Truncate long content
        })
    
    user_message = f"ARTICLES TO EVALUATE:\n{json.dumps(articles_for_prompt, indent=2)}"
    
    for attempt in range(MAX_RETRIES):
        try:
            # Use structured outputs beta for guaranteed valid JSON
            response = client.beta.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                betas=["structured-outputs-2025-11-13"],
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                output_format={
                    "type": "json_schema",
                    "schema": ARTICLE_RESULT_SCHEMA
                }
            )
            
            # Extract and parse response - guaranteed valid JSON
            response_text = response.content[0].text
            parsed = json.loads(response_text)
            results = parsed.get("results", [])
            
            # Log cost estimate
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = (input_tokens * INPUT_COST_PER_M / 1_000_000) + (output_tokens * OUTPUT_COST_PER_M / 1_000_000)
            logger.info(f"Claude batch: {len(articles)} articles, {input_tokens}+{output_tokens} tokens, ~${cost:.4f}")
            
            return results
                
        except Exception as e:
            error_str = str(e).lower()
            
            if '429' in error_str or 'rate limit' in error_str:
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(f"Claude rate limit, waiting {delay}s (attempt {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(delay)
                    continue
            
            logger.error(f"Claude API error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BASE_DELAY * (2 ** attempt))
            else:
                return [{'index': i, 'filter_score': 0.0, 'summary': '', 'amish_angle': '', 'filter_notes': f'Claude API error: {e}'} for i in range(len(articles))]
    
    return []


def filter_articles(articles: list[dict]) -> list[dict]:
    """
    Filter a single batch of articles (for testing).
    
    Args:
        articles: List of article dicts
        
    Returns:
        List of articles with filter results merged in
    """
    system_prompt = build_system_prompt()
    results = filter_article_batch(articles, system_prompt)
    
    # Merge results into articles
    for i, article in enumerate(articles):
        if i < len(results):
            article.update(results[i])
        else:
            article['filter_score'] = 0.0
            article['filter_notes'] = 'No result from Claude'
    
    return articles


def filter_all_articles(articles: list[dict]) -> tuple[list[dict], list[dict], dict]:
    """
    Filter all articles through Claude with structured outputs in batches.
    
    Args:
        articles: List of article dicts
        
    Returns:
        Tuple of (kept articles, discarded articles, stats dict)
    """
    system_prompt = build_system_prompt()
    
    kept = []
    discarded = []
    stats = {
        'total_evaluated': len(articles),
        'total_kept': 0,
        'total_discarded': 0,
        'cost_estimate': 0.0,
    }
    
    total_batches = (len(articles) + BATCH_SIZE - 1) // BATCH_SIZE
    logger.info(f"Starting Claude filtering: {len(articles)} articles in {total_batches} batches (using structured outputs)")
    
    # Process in batches
    for i in range(0, len(articles), BATCH_SIZE):
        batch = articles[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        logger.info(f"[BATCH {batch_num}/{total_batches}] Processing {len(batch)} articles...")
        
        batch_start = time.time()
        results = filter_article_batch(batch, system_prompt)
        batch_time = time.time() - batch_start
        logger.info(f"[BATCH {batch_num}/{total_batches}] Complete in {batch_time:.1f}s")
        
        # Build index map from results
        results_by_index = {r.get('index', idx): r for idx, r in enumerate(results)}
        
        # Merge results and categorize
        for j, article in enumerate(batch):
            result = results_by_index.get(j, {})
            article['filter_score'] = result.get('filter_score', 0.0)
            article['summary'] = result.get('summary', '')
            article['amish_angle'] = result.get('amish_angle', '')
            article['filter_notes'] = result.get('filter_notes', 'No result')
            
            # Apply threshold
            if article['filter_score'] >= FILTER_THRESHOLD:
                kept.append(article)
                stats['total_kept'] += 1
            else:
                discarded.append(article)
                stats['total_discarded'] += 1
        
        # Sonnet pricing estimate
        batch_cost = len(batch) * (500 * INPUT_COST_PER_M / 1_000_000 + 150 * OUTPUT_COST_PER_M / 1_000_000)
        stats['cost_estimate'] += batch_cost
    
    logger.info(f"Filtering complete: {stats['total_kept']} kept, {stats['total_discarded']} discarded (~${stats['cost_estimate']:.2f})")
    return kept, discarded, stats

