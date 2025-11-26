# Implementation Plan: Daily Article Discovery

**Feature Branch**: `002-article-discovery`  
**Planning Date**: 2025-11-26  
**Spec Reference**: [spec.md](./spec.md)

## Plan Summary

This feature implements the daily article discovery pipeline:
1. **RSS Fetching** via `feedparser` library - fetch articles from 10+ curated RSS sources
2. **Exa Search** via `exa-py` SDK - execute AI-powered web searches for broader discovery
3. **URL Normalization** - deduplicate across sources via URL cleaning
4. **Claude Haiku Filtering** via `anthropic` SDK - evaluate 200-300 articles against FilterRules
5. **Candidate Storage** - persist 40-60 filtered articles with status="pending"
6. **Job Orchestration** - daily cron at 8am EST with retry logic

**Key Technical Decisions**:
- Use `feedparser 6.0.11` for RSS/Atom/JSON feed parsing (proven, stable)
- Use `anthropic 0.40+` SDK with Claude Haiku (`claude-3-haiku-20240307`)
- Use `exa-py 1.1.0+` for Exa search API
- Batch Claude API calls (15 articles/request) to minimize cost
- Store filter_score/filter_notes for ALL articles (kept and discarded) to enable learning

---

## Constitution Check

| Principle | Compliance | Notes |
|-----------|------------|-------|
| **I. Single-User Simplicity** | ✅ PASS | No multi-user features; job runs once daily for John |
| **II. Volume Over Precision** | ✅ PASS | Target 40-60 candidates; filter_score ≥0.5 threshold errs toward inclusion |
| **III. Learning Over Time** | ✅ PASS | filter_score + filter_notes stored for weekly refinement analysis |
| **IV. Pragmatic Testing** | ✅ PASS | Contract tests for APIs; integration test for daily job workflow |
| **V. Cost Discipline** | ✅ PASS | Claude Haiku ~$0.50/day; Exa ~$0.30/day; total <$2/day |
| **VI. Reliability Over Performance** | ✅ PASS | Retry logic with exponential backoff; partial failures don't crash job |

---

## Technical Context

### Dependencies (additions to requirements.txt)

```
# Article Discovery
feedparser==6.0.11           # RSS/Atom/JSON feed parsing
anthropic==0.40.0            # Claude API SDK
exa-py==1.1.0                # Exa search API
httpx==0.28.1                # HTTP client for Exa (dependency)

# URL Processing
urllib3==2.3.0               # URL parsing utilities (often already installed)
```

### Environment Variables (additions to .env)

```
# Anthropic API (Claude Haiku filtering)
ANTHROPIC_API_KEY=sk-ant-...

# Exa API (AI-powered web search)
EXA_API_KEY=...

# Job configuration
DAILY_JOB_HOUR=8             # EST time for daily job
FILTER_SCORE_THRESHOLD=0.5   # Minimum score to keep article
BATCH_SIZE=15                # Articles per Claude API call
```

### External API Contracts

**Anthropic Claude API** (Messages endpoint):
- Model: `claude-3-haiku-20240307`
- Max tokens: 1024 (sufficient for structured response)
- Temperature: 0 (consistent, deterministic filtering)
- Input: Article content + FilterRules as system prompt
- Output: JSON with filter_score, summary, amish_angle, filter_notes

**Exa Search API** (Search endpoint):
- Queries: 10-15 per day (from sources.search_query)
- Results per query: 10-20 (configurable)
- Fields: url, title, publishedDate, text (snippet), highlights
- Cost: ~$0.03/query = $0.30-0.45/day

---

## Project Structure

```
app/
  services/
    discovery.py           # Orchestrates RSS + Exa + filtering workflow
    rss_fetcher.py         # RSS feed fetching with feedparser
    exa_searcher.py        # Exa API integration
    url_normalizer.py      # URL deduplication utilities
    claude_filter.py       # Claude Haiku filtering with batching

scripts/
  daily_job.py             # Cron entry point (8am EST)

tests/
  contract/
    test_rss_fetch.py      # RSS parsing contract tests
    test_exa_api.py        # Exa API contract tests
    test_claude_filter.py  # Claude API contract tests
  integration/
    test_daily_job.py      # End-to-end discovery workflow
```

---

## Phase 0: Research (Complete)

Key technical decisions documented in [research.md](./research.md):

1. **feedparser** - Universal RSS/Atom/JSON parser; handles malformed feeds gracefully
2. **Anthropic SDK** - Sync client preferred for batch processing; no streaming needed
3. **Exa API** - Neural search optimized for finding relevant content; cost-effective
4. **URL normalization** - Standard urllib.parse + custom parameter stripping
5. **Batch filtering** - 15 articles/request balances cost and latency
6. **Error handling** - Exponential backoff with jitter for API retries

---

## Phase 1: Design Artifacts

### Data Model Extensions

No schema changes required - existing models support all discovery fields:

- `Article.external_url` - Normalized URL (unique constraint)
- `Article.headline`, `summary`, `amish_angle` - AI-generated content
- `Article.filter_score`, `filter_notes` - Filtering metadata
- `Article.raw_content` - Original article text for filtering
- `Article.source_id` - Links to RSS feed or search query Source
- `Article.status` - Default "pending" for candidates

- `Source.type` - RSS vs SEARCH_QUERY enum
- `Source.url` - RSS feed URL (if type=RSS)
- `Source.search_query` - Exa query text (if type=SEARCH_QUERY)
- `Source.total_surfaced`, `last_fetched` - Performance metrics

### API Contracts

**Claude Haiku Filtering Prompt** (system message):

```
You are an editorial filter for Amish News, a publication serving conservative Amish Christian readers. 
Your task is to evaluate article candidates for inclusion in the daily email digest.

FILTER RULES:
{filter_rules_json}

For each article, provide a JSON response with:
- filter_score: float 0.0-1.0 (1.0 = perfect fit, 0.0 = completely inappropriate)
- summary: 2-3 sentence summary suitable for Amish readers
- amish_angle: 1 sentence explaining why this story resonates with Amish values
- filter_notes: brief explanation of scoring rationale, noting any rule violations

ARTICLES TO EVALUATE:
{articles_json}

Respond with valid JSON array matching the input article order.
```

**Claude Haiku Response Schema**:

```json
[
  {
    "filter_score": 0.75,
    "summary": "A community in rural Ohio formed a human chain to move 9,000 books to their new library building, completing the task in just three hours.",
    "amish_angle": "Demonstrates the power of neighbors working together toward a common good, embodying Gemeinschaft values.",
    "filter_notes": "Strong community cooperation story. No individual hero. Wholesome. Score boosted by good_topic:community."
  }
]
```

**Exa Search Parameters**:

```python
{
    "query": "community helps neighbors unusual heartwarming story",
    "num_results": 15,
    "type": "neural",
    "use_autoprompt": True,
    "start_published_date": "2024-01-01",  # Recent content only
    "contents": {
        "text": {"max_characters": 2000}  # Sufficient for filtering
    }
}
```

### Service Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        daily_job.py                             │
│                    (Cron entry point)                           │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     discovery.py                                │
│                  (Orchestration service)                        │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────┐ │
│  │ rss_fetch  │ │ exa_search │ │ url_normal │ │ claude_filter│ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PostgreSQL (Railway)                        │
│          articles, sources, filter_rules tables                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Setup (Tasks 1-5)
- Add dependencies to requirements.txt
- Add environment variables
- Create service file stubs

### Phase 2: RSS Fetching (Tasks 6-15) - User Story 1
- Implement `rss_fetcher.py` with feedparser
- Handle fetch errors gracefully
- Parse RSS/Atom formats uniformly
- Update Source.last_fetched metrics

### Phase 3: Exa Search (Tasks 16-25) - User Story 2
- Implement `exa_searcher.py` with exa-py SDK
- Execute configured search queries
- Handle rate limits and errors
- Track API costs for budget monitoring

### Phase 4: URL Normalization (Tasks 26-32) - User Story 4
- Implement `url_normalizer.py`
- Remove tracking parameters
- Standardize protocols and domains
- Preserve original URL in metadata

### Phase 5: Claude Filtering (Tasks 33-45) - User Story 3
- Implement `claude_filter.py` with anthropic SDK
- Build filter prompt from FilterRules
- Batch articles for efficiency
- Parse structured JSON responses
- Store filter_score/notes for all articles

### Phase 6: Source Metrics (Tasks 46-52) - User Story 5
- Update total_surfaced on discovery
- Update last_fetched after each source
- Log fetch errors with details

### Phase 7: Job Orchestration (Tasks 53-65) - User Story 6
- Implement `discovery.py` orchestration
- Implement `daily_job.py` cron entry
- Add retry logic with exponential backoff
- Log job summary statistics
- Configure Railway cron

### Phase 8: Testing (Tasks 66-77)
- Contract tests for RSS parsing
- Contract tests for Exa API
- Contract tests for Claude API
- Integration test for full workflow

---

## Cost Projections

| Component | Daily Usage | Cost/Unit | Daily Cost | Monthly Cost |
|-----------|------------|-----------|------------|--------------|
| Claude Haiku | ~300 articles × 500 tokens | $0.25/1M input | ~$0.15 | ~$4.50 |
| Claude Haiku | ~300 responses × 200 tokens | $1.25/1M output | ~$0.35 | ~$10.50 |
| Exa Search | ~12 queries × 15 results | $0.03/query | ~$0.36 | ~$11.00 |
| **Total** | | | **~$0.86** | **~$26.00** |

✅ Well under $50/month budget (Cost Discipline principle)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| RSS feed format changes | feedparser handles most edge cases; log parsing errors |
| Exa API rate limits | Exponential backoff; spread queries over job duration |
| Claude API failures | Retry 3× with backoff; store failed articles for manual review |
| Low candidate volume (<40) | Log warning but don't lower threshold; maintain quality |
| High candidate volume (>60) | Log warning but accept all ≥0.5; per Volume Over Precision |
| Duplicate articles across sources | URL normalization + unique constraint = guaranteed dedup |

---

## Ready For

**Next Step**: Task generation (`/speckit.tasks`) and implementation.

---

**Command `/speckit.plan` execution complete.**

