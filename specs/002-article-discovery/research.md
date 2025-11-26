# Research Documentation: Article Discovery

**Feature**: 002-article-discovery  
**Date**: 2025-11-26

## Key Technical Decisions

### 1. RSS Parsing Library: feedparser 6.0.11

**Decision**: Use `feedparser` for all RSS/Atom/JSON feed parsing.

**Rationale**:
- Universal parser handles RSS 1.0, RSS 2.0, Atom 1.0, and JSON Feed 1.0 formats
- Proven stability (20+ years of development)
- Graceful handling of malformed feeds (doesn't crash on bad XML)
- Normalizes all formats to consistent Python dictionary structure
- Extracts publication dates, authors, content in multiple formats

**Usage Pattern**:
```python
import feedparser

result = feedparser.parse('https://example.com/feed.xml')

# Check for errors
if result.bozo:
    # Feed had issues but may still have usable entries
    logger.warning(f"Feed parsing issue: {result.bozo_exception}")

# Access entries uniformly across formats
for entry in result.entries:
    title = entry.get('title', '')
    link = entry.get('link', '')
    summary = entry.get('summary', entry.get('description', ''))
    published = entry.get('published_parsed')  # time.struct_time
```

**Key Fields Available**:
- `result.version` - Feed format detected (rss20, atom10, json1)
- `result.feed.title` - Feed title
- `result.entries` - List of articles
- `entry.title`, `entry.link`, `entry.summary`, `entry.published_parsed`
- `result.status` - HTTP status code (200, 301, 404, etc.)

---

### 2. Anthropic SDK: anthropic 0.40+

**Decision**: Use official Anthropic Python SDK with synchronous client for batch filtering.

**Rationale**:
- Official SDK with full API coverage
- Type hints for IDE support
- Built-in retry logic for transient errors
- Simple JSON response handling

**Model Selection**: `claude-3-haiku-20240307`
- Fastest Claude model (~0.5s response time)
- Cheapest ($0.25/1M input, $1.25/1M output)
- Sufficient intelligence for classification tasks
- Reserve Sonnet for deep dive generation (Feature 005)

**Usage Pattern**:
```python
from anthropic import Anthropic

client = Anthropic()

response = client.messages.create(
    model="claude-3-haiku-20240307",
    max_tokens=1024,
    temperature=0,  # Deterministic for consistency
    system=FILTER_SYSTEM_PROMPT,
    messages=[
        {"role": "user", "content": articles_json}
    ]
)

# Parse JSON from response
result_text = response.content[0].text
filter_results = json.loads(result_text)
```

**Batching Strategy**:
- 15 articles per API call (balances latency vs. cost)
- ~20 API calls for 300 articles
- Total latency: ~30 seconds (parallelizable if needed)

---

### 3. Exa Search API: exa-py 1.1.0+

**Decision**: Use Exa's Python SDK for AI-powered web search.

**Rationale**:
- Neural search optimized for semantic relevance (not just keywords)
- Returns content snippets (avoids scraping)
- Cost-effective (~$0.03/query)
- Date filtering to get recent content
- Auto-prompt improves query relevance

**Usage Pattern**:
```python
from exa_py import Exa

exa = Exa(api_key=os.environ["EXA_API_KEY"])

results = exa.search_and_contents(
    query="community helps neighbors unusual heartwarming story",
    num_results=15,
    type="neural",
    use_autoprompt=True,
    start_published_date="2024-01-01",
    text={"max_characters": 2000}
)

for result in results.results:
    url = result.url
    title = result.title
    published = result.published_date
    content = result.text  # Snippet for filtering
```

**Query Strategy**:
- Store queries in Source table (type=SEARCH_QUERY)
- Execute all active queries daily
- Categories: animals, food, community, heritage, oddities (per sources.md)
- 10-15 queries × 15 results = 150-225 articles from search

---

### 4. URL Normalization Strategy

**Decision**: Custom URL normalization using urllib.parse with parameter stripping.

**Rationale**:
- Same article often appears with different URL variations
- Tracking parameters (utm_*, fbclid, etc.) create false duplicates
- Protocol/domain variations (http/https, www/non-www) must be unified
- Database unique constraint on normalized URL ensures deduplication

**Normalization Rules**:
1. Convert to lowercase
2. Remove scheme (http/https) for comparison, store as https
3. Remove 'www.' prefix
4. Remove trailing slashes
5. Remove query parameters (except essential ones like article ID)
6. Remove fragments (#...)

**Implementation**:
```python
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

def normalize_url(url: str) -> str:
    """Normalize URL for deduplication."""
    parsed = urlparse(url.lower())
    
    # Standardize domain
    netloc = parsed.netloc.replace('www.', '')
    
    # Remove most query params (keep article IDs)
    query_params = parse_qs(parsed.query)
    essential_params = {k: v for k, v in query_params.items() 
                       if k in ('id', 'article', 'p', 'story')}
    
    # Reconstruct URL
    normalized = urlunparse((
        'https',                          # Always https
        netloc,                           # Cleaned domain
        parsed.path.rstrip('/'),          # No trailing slash
        '',                               # No params
        urlencode(essential_params, doseq=True) if essential_params else '',
        ''                                # No fragment
    ))
    
    return normalized
```

**Storage Strategy**:
- Store normalized URL in `Article.external_url` (unique constraint)
- Store original URL in `Article.raw_content` metadata (JSON field) if needed
- Log duplicates for debugging (which source had the duplicate)

---

### 5. Error Handling and Retry Strategy

**Decision**: Exponential backoff with jitter for all external API calls.

**Rationale**:
- Network issues are transient; retrying usually succeeds
- Rate limits require waiting; exponential backoff respects limits
- Jitter prevents thundering herd when multiple retries align

**Retry Configuration**:
```python
RETRY_CONFIG = {
    'max_retries': 3,
    'base_delay': 2,        # seconds
    'max_delay': 60,        # seconds
    'exponential_base': 2,  # 2s, 4s, 8s
    'jitter': 0.5           # ±50% randomization
}
```

**Error Categories**:
1. **Transient** (retry): Connection timeout, 429 rate limit, 500 server error
2. **Permanent** (log & skip): 404 not found, 401 unauthorized, invalid content
3. **Critical** (fail job): All retries exhausted, API key invalid

**Implementation**:
```python
import time
import random

def retry_with_backoff(func, *args, **kwargs):
    for attempt in range(RETRY_CONFIG['max_retries']):
        try:
            return func(*args, **kwargs)
        except RetryableError as e:
            if attempt == RETRY_CONFIG['max_retries'] - 1:
                raise
            delay = min(
                RETRY_CONFIG['base_delay'] * (RETRY_CONFIG['exponential_base'] ** attempt),
                RETRY_CONFIG['max_delay']
            )
            delay *= (1 + random.uniform(-RETRY_CONFIG['jitter'], RETRY_CONFIG['jitter']))
            logger.warning(f"Retry {attempt + 1}/{RETRY_CONFIG['max_retries']} after {delay:.1f}s: {e}")
            time.sleep(delay)
```

---

### 6. Claude Filtering Prompt Engineering

**Decision**: Use structured JSON prompt with explicit FilterRule injection.

**Rationale**:
- FilterRules from database must be dynamic (weekly refinement adds rules)
- JSON output enables programmatic parsing
- Explicit scoring criteria improve consistency
- Temperature=0 ensures deterministic responses

**Prompt Structure**:
```
SYSTEM: You are an editorial filter for Amish News...
        FILTER RULES: {rules from database}
        Respond with valid JSON array.

USER:   ARTICLES TO EVALUATE:
        [{"id": "...", "headline": "...", "content": "..."}]
```

**FilterRule Format in Prompt**:
```json
{
  "must_have": [
    "A surprising or unusual angle",
    "Completely wholesome content",
    "Simple, clear language (8th grade level)"
  ],
  "must_avoid": [
    "Death, fatal accidents, or tragedies",
    "Modern technology (smartphones, AI, social media)",
    "Individual hero or record-breaking stories"
  ],
  "good_topics": [
    "Animals - unusual behavior, friendships",
    "Food - bizarre products, unusual flavors",
    "Community efforts - neighbors helping neighbors"
  ],
  "borderline": [
    "Individual craftsmanship (lean toward include if craft is focus)",
    "Heritage railways and steam trains (generally safe)"
  ]
}
```

---

### 7. Database Interaction Patterns

**Decision**: Use SQLAlchemy session per job, bulk operations where possible.

**Rationale**:
- Single daily job = single session scope
- Bulk inserts faster than individual commits
- Unique constraint handles duplicates at DB level

**Patterns**:
```python
from sqlalchemy.dialects.postgresql import insert

def bulk_insert_articles(session, articles: list[dict]):
    """Insert articles, skip duplicates via ON CONFLICT DO NOTHING."""
    stmt = insert(Article).values(articles)
    stmt = stmt.on_conflict_do_nothing(index_elements=['external_url'])
    result = session.execute(stmt)
    session.commit()
    return result.rowcount  # Number actually inserted (excludes duplicates)
```

**Session Management**:
```python
from app.database import SessionLocal

def run_discovery_job():
    session = SessionLocal()
    try:
        # ... discovery logic
        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()
```

---

### 8. Logging Strategy

**Decision**: Structured logging with job context for debugging.

**Rationale**:
- Daily job runs unattended; logs are primary debugging tool
- Job summary enables monitoring (candidates found, costs, errors)
- Per-source metrics help identify problematic sources

**Log Format**:
```python
import logging
import json

logger = logging.getLogger('discovery')

# Job start
logger.info(json.dumps({
    "event": "job_start",
    "timestamp": datetime.utcnow().isoformat(),
    "sources_active": 15,
    "queries_active": 12
}))

# Per-source result
logger.info(json.dumps({
    "event": "source_complete",
    "source_name": "UPI Odd News",
    "articles_found": 23,
    "duration_seconds": 1.5
}))

# Job summary
logger.info(json.dumps({
    "event": "job_complete",
    "total_discovered": 280,
    "total_filtered": 52,
    "total_stored": 48,
    "total_duplicates": 32,
    "sources_succeeded": 14,
    "sources_failed": 1,
    "cost_estimate_usd": 0.82,
    "duration_seconds": 185
}))
```

---

### 9. Railway Cron Configuration

**Decision**: Use Railway cron jobs with UTC scheduling.

**Rationale**:
- Railway supports cron syntax natively
- Job runs in same environment as web app (DATABASE_URL available)
- UTC scheduling avoids DST issues

**Configuration** (railway.toml):
```toml
[deploy]
startCommand = "python -m gunicorn app:create_app() --bind 0.0.0.0:$PORT"

[[crons]]
name = "daily-discovery"
schedule = "0 13 * * *"  # 8am EST = 1pm UTC
command = "python scripts/daily_job.py"
```

**Job Entry Point** (scripts/daily_job.py):
```python
#!/usr/bin/env python
"""Daily article discovery job - runs at 8am EST via Railway cron."""

import sys
import logging
from app.services.discovery import run_discovery_job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('daily_job')

if __name__ == '__main__':
    try:
        result = run_discovery_job()
        logger.info(f"Job complete: {result['total_stored']} candidates stored")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Job failed: {e}")
        # TODO: Send alert email (Feature 003)
        sys.exit(1)
```

---

### 10. Test Data Seeding

**Decision**: Create initial Sources (RSS feeds + Exa queries) and FilterRules on first run.

**Rationale**:
- Database starts empty; discovery job needs sources to query
- FilterRules from an_story_criteria.md must be seeded
- Idempotent seeding allows re-running without duplicates

**Seed Data Files**:
- `data/sources.json` - Initial RSS feeds and Exa queries from sources.md
- `data/filter_rules.json` - Initial rules from an_story_criteria.md

**Seeding Script** (scripts/seed_data.py):
```python
def seed_sources(session):
    """Insert initial sources if not exists."""
    sources = load_json('data/sources.json')
    for source in sources:
        existing = session.query(Source).filter_by(name=source['name']).first()
        if not existing:
            session.add(Source(**source))
    session.commit()

def seed_filter_rules(session):
    """Insert initial filter rules if not exists."""
    rules = load_json('data/filter_rules.json')
    for rule in rules:
        existing = session.query(FilterRule).filter_by(rule_text=rule['rule_text']).first()
        if not existing:
            session.add(FilterRule(**rule))
    session.commit()
```

---

## References

- [feedparser documentation](https://feedparser.readthedocs.io/)
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [Exa Python SDK](https://docs.exa.ai/sdks/python-sdk)
- [an_story_criteria.md](../../an_story_criteria.md) - Editorial guidelines
- [sources.md](../../sources.md) - Source configuration

