# Quickstart: Story Quality Filter Implementation

**Feature**: 001-story-quality-filter  
**Date**: 2025-11-29

## Prerequisites

- Python 3.11+ environment active
- PostgreSQL database accessible
- Anthropic API key configured
- Existing codebase with `claude_filter.py` and `models.py`

## Implementation Steps

### Step 1: Create Database Migration

```bash
cd /home/adamd/projects/amish_news
source venv/bin/activate
alembic revision -m "add_quality_filter_fields"
```

Edit the generated migration file:

```python
def upgrade():
    op.add_column('articles', sa.Column('content_type', sa.String(50), nullable=True))
    op.add_column('articles', sa.Column('wow_score', sa.Float(), nullable=True))

def downgrade():
    op.drop_column('articles', 'wow_score')
    op.drop_column('articles', 'content_type')
```

Run migration:

```bash
alembic upgrade head
```

### Step 2: Update Article Model

In `app/models.py`, add to Article class:

```python
# After existing AI-Generated Content fields
content_type: Mapped[Optional[str]] = Column(String(50), nullable=True)
wow_score: Mapped[Optional[float]] = Column(Float, nullable=True)
```

### Step 3: Update Claude Filter Schema

In `app/services/claude_filter.py`, update `ARTICLE_RESULT_SCHEMA`:

```python
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
                    "wow_score": {"type": "number"},  # NEW
                    "wow_notes": {"type": "string"},  # NEW
                    "topics": {
                        "type": "array",
                        "items": {"type": "string", "enum": TOPIC_CATEGORIES}
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
```

### Step 4: Add Wow Factor Prompt Section

In `app/services/claude_filter.py`, add to `SYSTEM_PROMPT_TEMPLATE` after CONTENT TYPE section:

```python
WOW FACTOR EVALUATION (apply to news_article only):

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
```

### Step 5: Add Configuration

At top of `app/services/claude_filter.py`:

```python
WOW_SCORE_THRESHOLD = float(os.environ.get('WOW_SCORE_THRESHOLD', '0.4'))
```

### Step 6: Update Filtering Logic

In `filter_all_articles()`, update the merge/categorize loop:

```python
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

    # Gate 1: Content type check
    if content_type != 'news_article':
        article['filter_score'] = 0.0
        article['filter_notes'] = f"Rejected: content_type={content_type} | {article['filter_notes']}"
        discarded.append(article)
        stats['total_discarded'] += 1
        continue
    
    # Gate 2: Wow score check
    if wow_score < WOW_SCORE_THRESHOLD:
        article['filter_score'] = 0.0
        article['filter_notes'] = f"Rejected: wow_score={wow_score:.2f} (threshold: {WOW_SCORE_THRESHOLD}) | {wow_notes}"
        discarded.append(article)
        stats['total_discarded'] += 1
        continue

    # Gate 3: Filter score threshold (existing)
    if article['filter_score'] >= FILTER_THRESHOLD:
        kept.append(article)
        stats['total_kept'] += 1
    else:
        discarded.append(article)
        stats['total_discarded'] += 1
```

### Step 7: Update Discovery to Persist New Fields

In `app/services/discovery.py` (or wherever articles are saved), ensure new fields are persisted:

```python
article = Article(
    # ... existing fields ...
    content_type=filter_result.get('content_type'),
    wow_score=filter_result.get('wow_score'),
)
```

## Testing

### Manual Test

```bash
# Run the daily job in test mode
python scripts/run_daily_pipeline.py --dry-run
```

Verify in logs:
- Content type classifications appear
- Wow scores appear in output
- Rejections show clear reasons with content_type or wow_score

### Integration Test

```python
# tests/integration/test_filtering_quality.py

def test_non_news_rejected():
    """Event listings should be rejected with content_type reason."""
    articles = [{"headline": "Fall Festival 2025 - Buy Tickets Now!", "content": "Join us for..."}]
    kept, discarded, stats = filter_all_articles(articles)
    assert len(discarded) == 1
    assert "content_type=event_listing" in discarded[0]['filter_notes']

def test_boring_news_rejected():
    """Mundane news should be rejected with low wow_score."""
    articles = [{"headline": "City Council Approves Budget", "content": "The council met..."}]
    kept, discarded, stats = filter_all_articles(articles)
    assert len(discarded) == 1
    assert "wow_score=" in discarded[0]['filter_notes']

def test_wow_news_passes():
    """Surprising/delightful news should pass wow check."""
    articles = [{"headline": "Giant Pumpkin Floats Across Lake", "content": "A local farmer..."}]
    kept, discarded, stats = filter_all_articles(articles)
    # Should pass content_type and wow checks, may pass or fail editorial
    assert discarded[0].get('content_type') == 'news_article' if discarded else True
```

## Rollback

If issues arise:

```bash
# Revert migration
alembic downgrade -1

# Revert code changes
git checkout app/models.py app/services/claude_filter.py
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `WOW_SCORE_THRESHOLD` | `0.4` | Minimum wow_score to pass quality check |
| `FILTER_SCORE_THRESHOLD` | `0.5` | Existing editorial fit threshold |

To make filtering more strict, increase `WOW_SCORE_THRESHOLD`:

```bash
export WOW_SCORE_THRESHOLD=0.5
```

