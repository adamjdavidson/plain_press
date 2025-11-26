# Task Breakdown: Daily Article Discovery

**Feature Branch**: `002-article-discovery`  
**Generated**: 2025-11-26  
**Spec Reference**: [spec.md](./spec.md)  
**Plan Reference**: [plan.md](./plan.md)

## Overview

- **Total Tasks**: 72
- **MVP Scope**: Phases 1-6 (48 tasks) - RSS + Exa + Filtering + Storage + Orchestration
- **Full Scope**: All phases including comprehensive tests

## Implementation Status

**Status**: ✅ **MVP COMPLETE** (Phases 1-6)

**Completed**:
- Phase 1: Setup (5 tasks) - dependencies, directories, seed data
- Phase 2: RSS Fetching (12 tasks) - feedparser integration with error handling
- Phase 3: Exa Search (12 tasks) - exa-py SDK integration
- Phase 4: URL Normalization (8 tasks) - deduplication utilities
- Phase 5: Claude Filtering (15 tasks) - Haiku integration with batching
- Phase 6: Job Orchestration (12 tasks) - discovery service + daily_job.py

**Test Results**: ✅ 53 tests passing
- 22 database schema tests (Feature 001)
- 11 RSS fetch contract tests
- 20 URL normalizer unit tests

**Files Created**:
- `app/services/rss_fetcher.py` - RSS feed fetching
- `app/services/exa_searcher.py` - Exa API search
- `app/services/url_normalizer.py` - URL deduplication
- `app/services/claude_filter.py` - Claude Haiku filtering
- `app/services/discovery.py` - Job orchestration
- `scripts/daily_job.py` - Cron entry point
- `scripts/seed_data.py` - Initial data seeding
- `data/sources.json` - 17 initial sources (7 RSS + 10 Exa queries)
- `data/filter_rules.json` - 28 FilterRules from story criteria

---

**Constitution Alignment**:
- Tests REQUIRED for: External API integrations (Anthropic, Exa), daily job workflow
- Tests OPTIONAL for: URL normalization utilities, internal helpers

---

## Dependencies

```
Phase 1 (Setup) → Phase 2 (RSS) → Phase 4 (Normalization) → Phase 5 (Filtering) → Phase 6 (Orchestration)
                  Phase 3 (Exa) ↗
```

- Phase 2 (RSS) and Phase 3 (Exa) can run in parallel [P]
- Phase 4 (Normalization) depends on Phase 2+3 completing
- Phase 5 (Filtering) depends on Phase 4 (needs normalized articles)
- Phase 6 (Orchestration) depends on all prior phases

---

## Phase 1: Setup (5 tasks)

### Task 1.1: Add dependencies to requirements.txt
**File**: `/home/adamd/projects/amish_news/requirements.txt`  
**Action**: Append new dependencies for article discovery

```
# Article Discovery
feedparser==6.0.11
anthropic==0.40.0
exa-py==1.1.0
httpx==0.28.1
```

### Task 1.2: Create services directory structure
**Files**: 
- `/home/adamd/projects/amish_news/app/services/__init__.py`
- `/home/adamd/projects/amish_news/app/services/rss_fetcher.py`
- `/home/adamd/projects/amish_news/app/services/exa_searcher.py`
- `/home/adamd/projects/amish_news/app/services/url_normalizer.py`
- `/home/adamd/projects/amish_news/app/services/claude_filter.py`
- `/home/adamd/projects/amish_news/app/services/discovery.py`

**Action**: Create empty stub files with docstrings

### Task 1.3: Create scripts directory structure
**Files**:
- `/home/adamd/projects/amish_news/scripts/__init__.py`
- `/home/adamd/projects/amish_news/scripts/daily_job.py`
- `/home/adamd/projects/amish_news/scripts/seed_data.py`

**Action**: Create empty stub files with docstrings

### Task 1.4: Create data directory for seed files
**Files**:
- `/home/adamd/projects/amish_news/data/sources.json`
- `/home/adamd/projects/amish_news/data/filter_rules.json`

**Action**: Create JSON files with initial seed data from sources.md and an_story_criteria.md

### Task 1.5: Update .env.example with new variables
**File**: `/home/adamd/projects/amish_news/.env.example`  
**Action**: Add ANTHROPIC_API_KEY, EXA_API_KEY, FILTER_SCORE_THRESHOLD, BATCH_SIZE

**Checkpoint**: ✅ Project structure ready for implementation

---

## Phase 2: RSS Fetching - User Story 1 (12 tasks)

### Task 2.1: Implement RSS feed fetcher base function
**File**: `/home/adamd/projects/amish_news/app/services/rss_fetcher.py`  
**Action**: Create `fetch_rss_feed(url: str) -> list[dict]` function using feedparser
**Spec**: FR-001, FR-002

### Task 2.2: Add error handling for fetch failures
**File**: `/home/adamd/projects/amish_news/app/services/rss_fetcher.py`  
**Action**: Handle HTTP errors (404, 500, timeout) gracefully, return empty list with error logged
**Spec**: FR-003

### Task 2.3: Parse article metadata from RSS entries
**File**: `/home/adamd/projects/amish_news/app/services/rss_fetcher.py`  
**Action**: Extract title, link, published_date, summary/description, content from feedparser entries
**Spec**: FR-002

### Task 2.4: Handle malformed feed XML gracefully
**File**: `/home/adamd/projects/amish_news/app/services/rss_fetcher.py`  
**Action**: Check `result.bozo` flag, log warning but continue if entries available
**Spec**: FR-003

### Task 2.5: Implement fetch_all_rss_sources function
**File**: `/home/adamd/projects/amish_news/app/services/rss_fetcher.py`  
**Action**: Query active RSS sources from database, fetch each, aggregate results
**Spec**: FR-001

### Task 2.6: Update source.last_fetched after each fetch
**File**: `/home/adamd/projects/amish_news/app/services/rss_fetcher.py`  
**Action**: Set last_fetched = now() after fetch attempt (success or failure)
**Spec**: FR-004

### Task 2.7: Implement rate limiting for RSS fetches
**File**: `/home/adamd/projects/amish_news/app/services/rss_fetcher.py`  
**Action**: Add configurable delay between fetches (default 1s) to avoid hammering sources
**Spec**: FR-005

### Task 2.8: Add retry logic for transient RSS errors
**File**: `/home/adamd/projects/amish_news/app/services/rss_fetcher.py`  
**Action**: Implement exponential backoff for connection errors and timeouts (max 3 retries)

### Task 2.9: Log fetch results per source
**File**: `/home/adamd/projects/amish_news/app/services/rss_fetcher.py`  
**Action**: Log source_name, articles_found, duration_seconds, any errors

### Task 2.10: Contract test - RSS parsing with valid feed [P]
**File**: `/home/adamd/projects/amish_news/tests/contract/test_rss_fetch.py`  
**Action**: Test parsing sample RSS feed, verify title/link/date extracted correctly

### Task 2.11: Contract test - RSS parsing with malformed feed [P]
**File**: `/home/adamd/projects/amish_news/tests/contract/test_rss_fetch.py`  
**Action**: Test graceful handling of malformed XML, verify no crash, partial results returned

### Task 2.12: Contract test - RSS fetch with network error [P]
**File**: `/home/adamd/projects/amish_news/tests/contract/test_rss_fetch.py`  
**Action**: Mock HTTP 500 error, verify retry logic triggered, empty result returned after retries

**Checkpoint**: ✅ RSS fetching complete - can fetch from all configured RSS sources

---

## Phase 3: Exa Search - User Story 2 (12 tasks) [P]

### Task 3.1: Implement Exa client initialization
**File**: `/home/adamd/projects/amish_news/app/services/exa_searcher.py`  
**Action**: Create Exa client from EXA_API_KEY environment variable
**Spec**: FR-006

### Task 3.2: Implement search_articles function
**File**: `/home/adamd/projects/amish_news/app/services/exa_searcher.py`  
**Action**: Create `search_articles(query: str, num_results: int = 15) -> list[dict]`
**Spec**: FR-007

### Task 3.3: Configure Exa search parameters
**File**: `/home/adamd/projects/amish_news/app/services/exa_searcher.py`  
**Action**: Set type="neural", use_autoprompt=True, date filter for recent content, text max_characters=2000
**Spec**: FR-010

### Task 3.4: Parse Exa results to article dict
**File**: `/home/adamd/projects/amish_news/app/services/exa_searcher.py`  
**Action**: Extract url, title, published_date, text from Exa results

### Task 3.5: Implement rate limit handling
**File**: `/home/adamd/projects/amish_news/app/services/exa_searcher.py`  
**Action**: Handle 429 errors with exponential backoff (2s, 4s, 8s delays)
**Spec**: FR-008

### Task 3.6: Implement search_all_queries function
**File**: `/home/adamd/projects/amish_news/app/services/exa_searcher.py`  
**Action**: Query active SEARCH_QUERY sources from database, execute each, aggregate results
**Spec**: FR-006

### Task 3.7: Log Exa API costs per request
**File**: `/home/adamd/projects/amish_news/app/services/exa_searcher.py`  
**Action**: Estimate cost (~$0.03/query) and log for budget tracking
**Spec**: FR-009

### Task 3.8: Update source metrics after search
**File**: `/home/adamd/projects/amish_news/app/services/exa_searcher.py`  
**Action**: Update last_fetched, increment total_surfaced for search query source
**Spec**: FR-024, FR-025

### Task 3.9: Handle zero-result queries
**File**: `/home/adamd/projects/amish_news/app/services/exa_searcher.py`  
**Action**: Log zero-result query, continue with other queries, update last_fetched

### Task 3.10: Contract test - Exa search returns results [P]
**File**: `/home/adamd/projects/amish_news/tests/contract/test_exa_api.py`  
**Action**: Test actual Exa API call with simple query, verify results structure

### Task 3.11: Contract test - Exa search rate limit handling [P]
**File**: `/home/adamd/projects/amish_news/tests/contract/test_exa_api.py`  
**Action**: Mock 429 response, verify exponential backoff triggered

### Task 3.12: Contract test - Exa search error handling [P]
**File**: `/home/adamd/projects/amish_news/tests/contract/test_exa_api.py`  
**Action**: Mock API error, verify graceful failure with logged error

**Checkpoint**: ✅ Exa search complete - can execute all configured search queries

---

## Phase 4: URL Normalization - User Story 4 (8 tasks)

### Task 4.1: Implement URL normalization function
**File**: `/home/adamd/projects/amish_news/app/services/url_normalizer.py`  
**Action**: Create `normalize_url(url: str) -> str` with lowercase, protocol standardization
**Spec**: FR-011

### Task 4.2: Remove tracking parameters from URLs
**File**: `/home/adamd/projects/amish_news/app/services/url_normalizer.py`  
**Action**: Strip utm_*, fbclid, ref, source and other tracking params
**Spec**: FR-011

### Task 4.3: Standardize domain variations
**File**: `/home/adamd/projects/amish_news/app/services/url_normalizer.py`  
**Action**: Remove www. prefix, standardize to https://
**Spec**: FR-011

### Task 4.4: Handle trailing slashes consistently
**File**: `/home/adamd/projects/amish_news/app/services/url_normalizer.py`  
**Action**: Remove trailing slashes from path
**Spec**: FR-011

### Task 4.5: Preserve original URL in article metadata
**File**: `/home/adamd/projects/amish_news/app/services/url_normalizer.py`  
**Action**: Return both normalized and original URL for storage
**Spec**: FR-012

### Task 4.6: Handle URL edge cases
**File**: `/home/adamd/projects/amish_news/app/services/url_normalizer.py`  
**Action**: Handle relative URLs, invalid URLs (log and skip), fragments
**Spec**: FR-013

### Task 4.7: Implement deduplicate_articles function
**File**: `/home/adamd/projects/amish_news/app/services/url_normalizer.py`  
**Action**: Takes list of articles, returns deduplicated list with normalized URLs

### Task 4.8: Unit tests for URL normalization
**File**: `/home/adamd/projects/amish_news/tests/unit/test_url_normalizer.py`  
**Action**: Test all normalization rules: tracking params, www, https, trailing slash, edge cases

**Checkpoint**: ✅ URL normalization complete - duplicates prevented across sources

---

## Phase 5: Claude Filtering - User Story 3 (15 tasks)

### Task 5.1: Implement Anthropic client initialization
**File**: `/home/adamd/projects/amish_news/app/services/claude_filter.py`  
**Action**: Create Anthropic client from ANTHROPIC_API_KEY environment variable
**Spec**: FR-017

### Task 5.2: Build filter rules prompt from database
**File**: `/home/adamd/projects/amish_news/app/services/claude_filter.py`  
**Action**: Load active FilterRules, format as JSON for system prompt
**Spec**: FR-014

### Task 5.3: Create system prompt template
**File**: `/home/adamd/projects/amish_news/app/services/claude_filter.py`  
**Action**: Define FILTER_SYSTEM_PROMPT with filter rules injection and JSON output format
**Spec**: FR-015

### Task 5.4: Implement filter_article_batch function
**File**: `/home/adamd/projects/amish_news/app/services/claude_filter.py`  
**Action**: Send batch of articles to Claude Haiku, parse JSON response
**Spec**: FR-014, FR-015, FR-016

### Task 5.5: Configure Claude Haiku model settings
**File**: `/home/adamd/projects/amish_news/app/services/claude_filter.py`  
**Action**: Set model="claude-3-haiku-20240307", max_tokens=1024, temperature=0
**Spec**: FR-017

### Task 5.6: Parse structured JSON response
**File**: `/home/adamd/projects/amish_news/app/services/claude_filter.py`  
**Action**: Extract filter_score, summary, amish_angle, filter_notes from response
**Spec**: FR-015

### Task 5.7: Implement batching logic
**File**: `/home/adamd/projects/amish_news/app/services/claude_filter.py`  
**Action**: Split articles into batches of BATCH_SIZE (default 15), process sequentially
**Spec**: FR-016

### Task 5.8: Implement filter_all_articles function
**File**: `/home/adamd/projects/amish_news/app/services/claude_filter.py`  
**Action**: Process all discovered articles through batched filtering

### Task 5.9: Store filter results for all articles
**File**: `/home/adamd/projects/amish_news/app/services/claude_filter.py`  
**Action**: Store filter_score and filter_notes for ALL articles (kept and discarded)
**Spec**: FR-019

### Task 5.10: Apply threshold for candidate selection
**File**: `/home/adamd/projects/amish_news/app/services/claude_filter.py`  
**Action**: Keep articles with filter_score >= FILTER_SCORE_THRESHOLD (0.5)
**Spec**: FR-018

### Task 5.11: Handle Claude API errors with retry
**File**: `/home/adamd/projects/amish_news/app/services/claude_filter.py`  
**Action**: Implement exponential backoff for API errors (5s, 10s, 20s)

### Task 5.12: Log filtering costs and statistics
**File**: `/home/adamd/projects/amish_news/app/services/claude_filter.py`  
**Action**: Estimate token usage and cost, log per batch and total

### Task 5.13: Contract test - Claude filter returns valid JSON [P]
**File**: `/home/adamd/projects/amish_news/tests/contract/test_claude_filter.py`  
**Action**: Test actual Claude API call with sample article, verify JSON structure

### Task 5.14: Contract test - Claude filter handles batch [P]
**File**: `/home/adamd/projects/amish_news/tests/contract/test_claude_filter.py`  
**Action**: Test batch of 15 articles, verify all receive scores

### Task 5.15: Contract test - Claude filter error handling [P]
**File**: `/home/adamd/projects/amish_news/tests/contract/test_claude_filter.py`  
**Action**: Mock API error, verify retry logic and graceful failure

**Checkpoint**: ✅ Claude filtering complete - can evaluate articles against FilterRules

---

## Phase 6: Job Orchestration - User Story 6 (12 tasks)

### Task 6.1: Implement discovery service orchestration
**File**: `/home/adamd/projects/amish_news/app/services/discovery.py`  
**Action**: Create `run_discovery_job()` that orchestrates RSS → Exa → Normalize → Filter → Store
**Spec**: FR-027

### Task 6.2: Fetch RSS articles in discovery job
**File**: `/home/adamd/projects/amish_news/app/services/discovery.py`  
**Action**: Call fetch_all_rss_sources(), collect results

### Task 6.3: Execute Exa searches in discovery job
**File**: `/home/adamd/projects/amish_news/app/services/discovery.py`  
**Action**: Call search_all_queries(), collect results

### Task 6.4: Deduplicate discovered articles
**File**: `/home/adamd/projects/amish_news/app/services/discovery.py`  
**Action**: Combine RSS + Exa results, call deduplicate_articles()
**Spec**: FR-011

### Task 6.5: Filter articles through Claude
**File**: `/home/adamd/projects/amish_news/app/services/discovery.py`  
**Action**: Call filter_all_articles() with deduplicated list

### Task 6.6: Store candidate articles
**File**: `/home/adamd/projects/amish_news/app/services/discovery.py`  
**Action**: Bulk insert articles with filter_score >= 0.5, status="pending"
**Spec**: FR-020, FR-021, FR-022, FR-023

### Task 6.7: Handle partial failures gracefully
**File**: `/home/adamd/projects/amish_news/app/services/discovery.py`  
**Action**: Continue job even if some sources fail, log failures, report in summary
**Spec**: FR-028

### Task 6.8: Log job summary
**File**: `/home/adamd/projects/amish_news/app/services/discovery.py`  
**Action**: Log total discovered, filtered, stored, duplicates, cost estimate, duration
**Spec**: FR-029

### Task 6.9: Implement daily job entry point
**File**: `/home/adamd/projects/amish_news/scripts/daily_job.py`  
**Action**: CLI entry point that calls run_discovery_job(), handles exit codes
**Spec**: FR-027

### Task 6.10: Log volume warnings
**File**: `/home/adamd/projects/amish_news/app/services/discovery.py`  
**Action**: Log warning if candidates < 40 or > 80
**Spec**: FR-031, FR-032

### Task 6.11: Integration test - full discovery workflow
**File**: `/home/adamd/projects/amish_news/tests/integration/test_daily_job.py`  
**Action**: Test complete workflow with mocked APIs, verify articles stored correctly

### Task 6.12: Integration test - partial failure handling
**File**: `/home/adamd/projects/amish_news/tests/integration/test_daily_job.py`  
**Action**: Mock one source failure, verify job continues and completes

**Checkpoint**: ✅ Job orchestration complete - daily discovery pipeline functional

---

## Phase 7: Source Metrics - User Story 5 (4 tasks)

### Task 7.1: Update total_surfaced on discovery
**File**: `/home/adamd/projects/amish_news/app/services/discovery.py`  
**Action**: Increment source.total_surfaced for each article discovered
**Spec**: FR-024

### Task 7.2: Update last_fetched after source processing
**File**: `/home/adamd/projects/amish_news/app/services/rss_fetcher.py`, `/home/adamd/projects/amish_news/app/services/exa_searcher.py`  
**Action**: Set source.last_fetched = now() after each source processed
**Spec**: FR-025

### Task 7.3: Log fetch errors with details
**File**: `/home/adamd/projects/amish_news/app/services/rss_fetcher.py`, `/home/adamd/projects/amish_news/app/services/exa_searcher.py`  
**Action**: Log source_name, error_type, timestamp, retry_count for all errors
**Spec**: FR-026

### Task 7.4: Integration test - source metrics updated
**File**: `/home/adamd/projects/amish_news/tests/integration/test_daily_job.py`  
**Action**: Verify total_surfaced and last_fetched updated after job run

**Checkpoint**: ✅ Source metrics complete - can track source performance

---

## Phase 8: Data Seeding (4 tasks)

### Task 8.1: Create sources.json seed file
**File**: `/home/adamd/projects/amish_news/data/sources.json`  
**Action**: Define initial RSS sources (UPI, AP, Reuters, Good News Network, etc.) and Exa queries from sources.md

### Task 8.2: Create filter_rules.json seed file
**File**: `/home/adamd/projects/amish_news/data/filter_rules.json`  
**Action**: Define initial FilterRules from an_story_criteria.md (must_have, must_avoid, good_topics, borderline)

### Task 8.3: Implement seed_data.py script
**File**: `/home/adamd/projects/amish_news/scripts/seed_data.py`  
**Action**: CLI script to seed sources and/or filter_rules, idempotent (skip existing)

### Task 8.4: Test seed script
**File**: `/home/adamd/projects/amish_news/tests/integration/test_seed_data.py`  
**Action**: Verify seeding creates expected records, re-run is idempotent

**Checkpoint**: ✅ Seeding complete - database has initial sources and rules

---

## MVP Completion Summary

**MVP = Phases 1-6** (48 tasks)

After completing MVP:
- ✅ RSS feeds fetched daily
- ✅ Exa searches executed daily  
- ✅ URLs deduplicated across sources
- ✅ Articles filtered via Claude Haiku
- ✅ 40-60 candidates stored with status="pending"
- ✅ Job runs at 8am EST via scripts/daily_job.py

**Remaining for Full Completion**:
- Phase 7: Source metrics tracking (4 tasks)
- Phase 8: Data seeding (4 tasks)

---

## Parallel Execution Notes

Tasks marked with [P] can run in parallel:
- Phase 2 (RSS) and Phase 3 (Exa) - independent data sources
- All contract tests within a phase - independent test files
- Tasks 2.10-2.12, 3.10-3.12, 5.13-5.15 - parallel test execution

---

## Test Summary

| Category | Count | Files |
|----------|-------|-------|
| Contract Tests (RSS) | 3 | `tests/contract/test_rss_fetch.py` |
| Contract Tests (Exa) | 3 | `tests/contract/test_exa_api.py` |
| Contract Tests (Claude) | 3 | `tests/contract/test_claude_filter.py` |
| Unit Tests | 1 | `tests/unit/test_url_normalizer.py` |
| Integration Tests | 4 | `tests/integration/test_daily_job.py`, `test_seed_data.py` |
| **Total** | **14** | |

---

**Command `/speckit.tasks` execution complete.**

Ready for implementation with `/speckit.implement`.

