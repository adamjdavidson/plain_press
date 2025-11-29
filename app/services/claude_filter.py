"""
Claude Filtering Service with Structured Outputs

Evaluates articles against FilterRules using Claude with guaranteed JSON output.
Returns filter_score, summary, amish_angle, and filter_notes.
"""

import json
import logging
import os
import sys
import time
from typing import Optional

from anthropic import Anthropic

from app.database import SessionLocal
from app.models import FilterRule, RuleType

logger = logging.getLogger(__name__)


def _log_claude(msg: str):
    """Log Claude progress with immediate flush."""
    full_msg = f"CLAUDE: {msg}"
    logger.info(full_msg)
    print(full_msg, file=sys.stdout, flush=True)

# Configuration
# NOTE: Model name is an Anthropic API identifier, not a date.
# Check https://docs.anthropic.com/en/docs/about-claude/models for latest versions.
MODEL = os.environ.get("CLAUDE_FILTER_MODEL", "claude-sonnet-4-5")
MAX_TOKENS = 4096

# Anthropic beta API version identifier
# NOTE: Beta feature versions include dates in their identifiers (e.g., 2025-11-13).
# This is an API version string required by Anthropic, not a runtime date.
# Check Anthropic docs for the latest beta version when updating.
STRUCTURED_OUTPUTS_BETA = os.environ.get("ANTHROPIC_STRUCTURED_OUTPUTS_BETA", "structured-outputs-2025-11-13")
TEMPERATURE = 0  # Deterministic for consistency
BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '10'))
FILTER_THRESHOLD = float(os.environ.get('FILTER_SCORE_THRESHOLD', '0.5'))
WOW_SCORE_THRESHOLD = float(os.environ.get('WOW_SCORE_THRESHOLD', '0.4'))
MAX_RETRIES = 2
RETRY_BASE_DELAY = 2.0

# Cost estimates (USD per 1M tokens) - Sonnet pricing
INPUT_COST_PER_M = 3.0
OUTPUT_COST_PER_M = 15.0

# Topic categories for article classification
TOPIC_CATEGORIES = [
    "animals", "wildlife", "farming", "agriculture",
    "science", "discovery", "history", "archaeology",
    "community", "small_town", "food", "cooking",
    "nature", "weather", "crafts", "traditions",
    "health", "medicine", "technology", "innovation"
]

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
                    "content_type": {
                        "type": "string",
                        "enum": ["news_article", "event_listing", "directory_page", "about_page", "other_non_news"]
                    },
                    "wow_score": {"type": "number"},
                    "wow_notes": {"type": "string"},
                    "topics": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": TOPIC_CATEGORIES
                        }
                        # Note: maxItems not supported by Anthropic structured outputs
                    },
                    "filter_score": {"type": "number"},
                    "summary": {"type": "string"},
                    "amish_angle": {"type": "string"},
                    "filter_notes": {"type": "string"}
                },
                "required": ["index", "content_type", "wow_score", "wow_notes", "topics", "filter_score", "summary", "amish_angle", "filter_notes"],
                "additionalProperties": False
            }
        }
    },
    "required": ["results"],
    "additionalProperties": False
}


SYSTEM_PROMPT_TEMPLATE = """You are an editorial filter for Plain Press, a publication serving conservative Amish Christian readers.
Your task is to evaluate article candidates for inclusion in the daily email digest.

STEP 1 - CONTENT TYPE CLASSIFICATION (REQUIRED FIRST):
Before evaluating editorial fit, you MUST first determine what type of content this is:

- "news_article": A STORY about something that HAPPENED - has a specific event, when/what/where, narrative structure, journalism
- "event_listing": Calendar events, schedules, "things to do", upcoming festivals, ticket sales, event announcements
- "directory_page": Lists without narrative - "Meet our animals", staff directories, product catalogs, resource lists
- "about_page": Static organizational info - "About Us", "Our Mission", "History of...", FAQ pages
- "other_non_news": Anything else that isn't journalism - recipes, how-to guides, opinion pieces without news, promotional content

CRITICAL RULE: Only content_type="news_article" should receive a filter_score above 0.0.
All other content types MUST receive filter_score: 0.0 and wow_score: 0.0 regardless of how wholesome or relevant the topic seems.

A news article MUST have:
- A specific event or occurrence that happened (not something that WILL happen)
- A narrative structure (not just a list of items)
- Journalistic reporting (not marketing, event promotion, or organizational info)

STEP 2 - WOW FACTOR EVALUATION (apply to news_article only):
Before scoring editorial fit, evaluate if this story would make someone say "wow!"

A story has high wow factor if it is:
- SURPRISING: Unexpected, not routine or predictable news
- DELIGHTFUL: Produces a smile, warmth, sense of wonder
- UNUSUAL: Quirky, odd, uncommon - stands out from typical news

Score wow_score 0.0-1.0:
- 0.8-1.0: Genuinely remarkable - "I have to share this"
- 0.5-0.7: Interesting - "That's nice to know"
- 0.2-0.4: Mildly interesting - "Okay, sure"
- 0.0-0.2: Boring - routine announcement, press release, mundane event

In wow_notes, explain briefly why this story is or isn't "wow-worthy."
A story about a new traffic light is NOT wow-worthy.
A story about a singing traffic light that plays folk tunes IS wow-worthy.

STEP 3 - EDITORIAL GUIDELINES (apply ONLY to news_article content):

The ideal story is a "delightful oddity" - something surprising, wholesome, and relatable that would make an Amish grandmother smile.

MUST HAVE (all stories need these):
{must_have_rules}

MUST AVOID (automatic rejection if present):
{must_avoid_rules}

GOOD TOPICS (boost score):
{good_topic_rules}

BORDERLINE (use judgment):
{borderline_rules}

TOPIC CATEGORIES (select 1-3 that apply):
animals, wildlife, farming, agriculture, science, discovery, history, archaeology,
community, small_town, food, cooking, nature, weather, crafts, traditions, health, medicine, technology, innovation

For EACH article, provide:
- index: the article index from the input
- content_type: one of news_article, event_listing, directory_page, about_page, other_non_news
- wow_score: float 0.0-1.0 for "wow factor" (0.0 = boring, 1.0 = remarkable) - MUST be 0.0 if content_type is not news_article
- wow_notes: brief explanation of wow_score (why surprising/delightful/unusual, or why boring/mundane)
- topics: array of 1-3 topic categories that apply (from the list above)
- filter_score: float 0.0-1.0 (1.0 = perfect fit, 0.0 = reject) - MUST be 0.0 if content_type is not news_article
- summary: 2-3 sentence summary suitable for Amish readers (simple language, 8th grade level)
- amish_angle: 1 sentence explaining why this story resonates with Amish values (or why it doesn't if rejected)
- filter_notes: brief explanation of scoring rationale including content_type decision"""


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
    _log_claude("Building system prompt - getting DB session...")
    session = SessionLocal()
    _log_claude("DB session acquired, querying FilterRules...")
    
    try:
        rules = session.query(FilterRule).filter(FilterRule.is_active == True).all()
        _log_claude(f"Found {len(rules)} active FilterRules")

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
    _log_claude(f"Getting Anthropic client for batch of {len(articles)} articles...")
    client = get_anthropic_client()
    _log_claude("Anthropic client ready")

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
            _log_claude(f"Calling Claude API (attempt {attempt + 1}/{MAX_RETRIES})...")
            api_start = time.time()
            # Use structured outputs beta for guaranteed valid JSON
            response = client.beta.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                betas=[STRUCTURED_OUTPUTS_BETA],
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                output_format={
                    "type": "json_schema",
                    "schema": ARTICLE_RESULT_SCHEMA
                }
            )
            api_time = time.time() - api_start
            _log_claude(f"Claude API responded in {api_time:.1f}s")

            # Extract and parse response - guaranteed valid JSON
            response_text = response.content[0].text
            parsed = json.loads(response_text)
            results = parsed.get("results", [])

            # Log cost estimate
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = (input_tokens * INPUT_COST_PER_M / 1_000_000) + (output_tokens * OUTPUT_COST_PER_M / 1_000_000)
            _log_claude(f"Batch complete: {len(articles)} articles, {input_tokens}+{output_tokens} tokens, ~${cost:.4f}")

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
    _log_claude(f"Starting filter_all_articles with {len(articles)} articles")
    _log_claude("Building system prompt...")
    system_prompt = build_system_prompt()
    _log_claude("System prompt built")

    kept = []
    discarded = []
    stats = {
        'total_evaluated': len(articles),
        'total_kept': 0,
        'total_discarded': 0,
        'cost_estimate': 0.0,
    }

    total_batches = (len(articles) + BATCH_SIZE - 1) // BATCH_SIZE
    _log_claude(f"Will process {total_batches} batches of up to {BATCH_SIZE} articles each")

    # Process in batches
    for i in range(0, len(articles), BATCH_SIZE):
        batch = articles[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        _log_claude(f"[BATCH {batch_num}/{total_batches}] Starting {len(batch)} articles...")

        batch_start = time.time()
        results = filter_article_batch(batch, system_prompt)
        batch_time = time.time() - batch_start
        _log_claude(f"[BATCH {batch_num}/{total_batches}] Complete in {batch_time:.1f}s")
        
        # Build index map from results
        results_by_index = {r.get('index', idx): r for idx, r in enumerate(results)}
        
        # Merge results and categorize
        for j, article in enumerate(batch):
            result = results_by_index.get(j, {})
            content_type = result.get('content_type', 'other_non_news')
            wow_score = result.get('wow_score', 0.0)
            wow_notes = result.get('wow_notes', '')
            
            article['content_type'] = content_type
            article['wow_score'] = wow_score
            article['topics'] = result.get('topics', [])
            article['filter_score'] = result.get('filter_score', 0.0)
            article['summary'] = result.get('summary', '')
            article['amish_angle'] = result.get('amish_angle', '')
            article['filter_notes'] = result.get('filter_notes', 'No result')

            # Gate 1: Content type check - non-news content MUST be rejected
            if content_type != 'news_article':
                article['filter_score'] = 0.0
                article['filter_notes'] = f"Rejected: content_type={content_type} | {article['filter_notes']}"
                discarded.append(article)
                stats['total_discarded'] += 1
                continue
            
            # Gate 2: Wow score check - boring news MUST be rejected
            if wow_score < WOW_SCORE_THRESHOLD:
                article['filter_score'] = 0.0
                article['filter_notes'] = f"Rejected: wow_score={wow_score:.2f} (threshold: {WOW_SCORE_THRESHOLD}) | {wow_notes}"
                discarded.append(article)
                stats['total_discarded'] += 1
                continue

            # Gate 3: Editorial filter score threshold
            if article['filter_score'] >= FILTER_THRESHOLD:
                kept.append(article)
                stats['total_kept'] += 1
            else:
                article['filter_notes'] = f"Rejected: filter_score={article['filter_score']:.2f} (threshold: {FILTER_THRESHOLD}) | {article['filter_notes']}"
                discarded.append(article)
                stats['total_discarded'] += 1
        
        # Sonnet pricing estimate
        batch_cost = len(batch) * (500 * INPUT_COST_PER_M / 1_000_000 + 150 * OUTPUT_COST_PER_M / 1_000_000)
        stats['cost_estimate'] += batch_cost
    
    logger.info(f"Filtering complete: {stats['total_kept']} kept, {stats['total_discarded']} discarded (~${stats['cost_estimate']:.2f})")
    return kept, discarded, stats

