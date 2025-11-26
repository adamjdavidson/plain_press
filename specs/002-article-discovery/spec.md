# Feature Specification: Daily Article Discovery

**Feature Branch**: `002-article-discovery`  
**Created**: 2025-11-26  
**Status**: Draft  
**Input**: User description: "Implement daily article discovery using Exa API and RSS feeds, filtering to 40-60 candidates via Claude Haiku against FilterRule criteria"

**Constitution Check**: This feature aligns with `.specify/memory/constitution.md` principles:
- **Volume Over Precision**: Target 40-60 candidates/day (err toward inclusion, not exclusion)
- **Cost Discipline**: Use Claude Haiku ($0.25/million tokens) for filtering, not Sonnet
- **Learning Over Time**: Store filter_score and filter_notes for weekly refinement analysis
- **Reliability Over Performance**: Store articles before filtering, retry on API failures

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fetch Articles from RSS Feeds (Priority: P1)

The system must retrieve articles from configured RSS feeds daily, extracting headline, URL, publication date, and full text content. RSS feeds provide reliable, structured content from proven sources (UPI Odd News, AP Oddities, Reuters, Good News Network). Articles are parsed and stored in raw format before AI filtering.

**Why this priority**: RSS feeds are the most reliable article source with structured data. They provide consistent daily volume (~50-100 articles/day from all feeds) and require no API costs. This is the foundation of article discovery and must work before adding Exa search.

**Independent Test**: Can be fully tested by fetching from a test RSS feed, verifying articles extracted with all fields, stored in database with status="pending", and no duplicates created (URL uniqueness enforced).

**Acceptance Scenarios**:

1. **Given** 5 active RSS feed sources configured, **When** daily job runs, **Then** system fetches from all feeds, extracts 10-30 articles per feed, stores with status="pending", source_id linked correctly
2. **Given** an RSS feed returns an article URL already in database, **When** processing articles, **Then** system skips duplicate (unique constraint prevents re-insertion), logs skip, continues with remaining articles
3. **Given** an RSS feed is temporarily unavailable (HTTP 500 error), **When** fetching fails, **Then** system logs error, continues with other feeds, marks source last_fetched=NULL for retry
4. **Given** RSS feed returns malformed XML, **When** parsing fails, **Then** system logs error with feed URL, skips that feed, continues with remaining feeds without crashing

---

### User Story 2 - Search Articles via Exa API (Priority: P1)

The system must execute configured search queries against Exa API daily, retrieving 10-20 articles per query. Exa provides AI-powered web search optimized for finding relevant content beyond RSS feeds. Each search query targets specific content types (animals, food, community efforts, oddities) per sources.md guidelines.

**Why this priority**: Exa search catches surprising articles from unpredictable sources that RSS feeds miss. Combined with RSS, this achieves the 200-300 raw candidate volume needed for filtering to 40-60. Required for volume over precision principle.

**Independent Test**: Can be fully tested by executing Exa search with test query, verifying 10-20 results returned with URL/headline/content, storing in database with source_type="search_query", no API errors.

**Acceptance Scenarios**:

1. **Given** 10 active search queries configured (animals, food, community, heritage), **When** daily job runs, **Then** system executes all queries, retrieves 10-20 articles per query (100-200 total), stores with source_id linked to search query source
2. **Given** Exa API rate limit exceeded, **When** request fails with 429 error, **Then** system waits exponentially (2s, 4s, 8s), retries up to 3 times, logs failure if exhausted
3. **Given** search query returns articles already in database (from RSS or previous searches), **When** storing results, **Then** system skips duplicates via URL uniqueness, logs duplicate count, continues
4. **Given** Exa API returns 0 results for a query, **When** processing response, **Then** system logs zero-result query, continues with remaining queries, marks query source last_fetched timestamp

---

### User Story 3 - Filter Articles via Claude Haiku (Priority: P1)

The system must evaluate each discovered article (RSS + Exa) against FilterRule criteria using Claude Haiku, generating filter_score (0.0-1.0), AI summary (2-3 sentences), amish_angle explanation, and filter_notes rationale. Articles scoring ≥0.5 are kept as candidates; lower scores discarded. Target: 40-60 candidates per day from 200-300 raw articles.

**Why this priority**: AI filtering is essential for achieving Volume Over Precision while staying within cost limits. Claude Haiku provides fast, cheap filtering ($0.25/million tokens = ~$0.50/day for 300 articles). Without filtering, John would receive 200-300 candidates (overwhelming). This is the core value-add of the system.

**Independent Test**: Can be fully tested by passing test article + FilterRule set to Claude Haiku, verifying response includes filter_score, summary, amish_angle, filter_notes, and articles ≥0.5 are marked for keeping.

**Acceptance Scenarios**:

1. **Given** 250 discovered articles and 30 active FilterRules loaded, **When** filtering runs, **Then** Claude Haiku evaluates all articles, generates filter_score for each, stores summary/amish_angle for scores ≥0.5, discards articles <0.5
2. **Given** FilterRules include must_avoid "death/tragedy", **When** article contains "family mourns loss", **Then** filter_score <0.3, filter_notes explain "contains death/tragedy (must_avoid rule violated)", article discarded
3. **Given** FilterRules include good_topic "animals", **When** article about "dog befriends duck", **Then** filter_score >0.7, amish_angle explains "heartwarming animal friendship aligns with wholesome values", article kept
4. **Given** Claude Haiku API fails (timeout or error), **When** filtering article batch, **Then** system retries with exponential backoff (5s, 10s, 20s), logs failure, marks articles as failed_filter if retries exhausted

---

### User Story 4 - Deduplicate Across Discovery Methods (Priority: P2)

The system must prevent the same article from being discovered via both RSS and Exa (or multiple Exa queries). URL normalization occurs before uniqueness check to catch variations (http/https, www/non-www, trailing slashes, tracking parameters). Duplicate detection happens at insertion time via database unique constraint.

**Why this priority**: Without deduplication, John sees the same article multiple times in daily email. URL normalization is critical because same article often has different URLs across sources. Improves user experience but not blocking for MVP (database enforces uniqueness even without normalization).

**Independent Test**: Can be fully tested by discovering same article via RSS and Exa with URL variations, verifying only one record created after normalization, duplicate logged.

**Acceptance Scenarios**:

1. **Given** article URL with tracking params "?utm_source=rss&id=123", **When** normalizing URL, **Then** system removes query parameters, stores clean URL "https://example.com/article/story"
2. **Given** same article discovered from RSS (http://www) and Exa (https://non-www), **When** normalizing both URLs, **Then** system produces identical normalized URL, second insertion rejected by unique constraint
3. **Given** two genuinely different articles with similar URLs, **When** normalizing, **Then** system preserves uniqueness (e.g., /article/123 vs /article/124 remain distinct)
4. **Given** article URL has trailing slash variation, **When** normalizing, **Then** system treats "https://example.com/article" and "https://example.com/article/" as identical

---

### User Story 5 - Track Source Performance Metrics (Priority: P2)

The system must update Source entity statistics after each discovery run: increment total_surfaced for all articles found, update last_fetched timestamp, log fetch errors. This data enables trust scoring in future refinement cycles.

**Why this priority**: Source metrics feed the learning loop (constitution principle III). Without tracking which sources produce articles, weekly refinement cannot identify high/low-quality sources. Important for long-term quality but not blocking for daily job functionality.

**Independent Test**: Can be fully tested by running discovery for one source, verifying total_surfaced incremented by article count, last_fetched updated to current timestamp, fetch errors logged.

**Acceptance Scenarios**:

1. **Given** source with total_surfaced=100, **When** daily job fetches 15 new articles from that source, **Then** total_surfaced updated to 115, last_fetched set to job completion timestamp
2. **Given** source fetch succeeds, **When** articles stored, **Then** last_fetched timestamp set to current time, no error_message recorded
3. **Given** source fetch fails (timeout or 404), **When** error occurs, **Then** last_fetched remains previous value (or NULL if first fetch), error logged to application logs with source name and error type
4. **Given** source returns 0 articles (valid response, no results), **When** processing, **Then** last_fetched updated (successful fetch), total_surfaced unchanged, logged as zero-result fetch

---

### User Story 6 - Implement Daily Job Orchestration (Priority: P1)

The system must orchestrate the complete discovery workflow in a single scheduled job: (1) fetch RSS feeds, (2) execute Exa searches, (3) deduplicate via URL normalization, (4) filter batch through Claude Haiku, (5) store candidates ≥0.5 score, (6) update source metrics, (7) log job summary. Job runs daily at 8am EST via Railway cron.

**Why this priority**: The daily job is the system's primary function. Without orchestration, individual components cannot work together. This creates the end-to-end workflow from discovery to candidate storage. Blocks Feature 003 (email delivery) which depends on pending articles existing.

**Independent Test**: Can be fully tested by running daily job with test sources/queries, verifying workflow completes, 40-60 articles stored with status="pending", all source metrics updated, job summary logged.

**Acceptance Scenarios**:

1. **Given** daily job scheduled for 8am EST, **When** Railway cron triggers, **Then** job executes RSS fetch → Exa search → filtering → storage in sequence, completes within 30 minutes, logs start/end timestamps
2. **Given** job discovers 280 raw articles (180 RSS + 100 Exa), **When** filtering completes, **Then** 45-55 articles have filter_score ≥0.5, stored as candidates, 225-235 discarded (logged with filter_scores <0.5)
3. **Given** job encounters partial failures (1 RSS feed down, 1 Exa query times out), **When** job continues, **Then** successful sources processed, failures logged, job completes with partial results, summary indicates 9/10 sources succeeded
4. **Given** job runs twice in same day (manual trigger), **When** processing articles, **Then** duplicate detection prevents re-insertion, job summary shows "X new articles, Y duplicates skipped"

---

### Edge Cases

- **What happens when RSS feed migrates to new URL**? Old feed returns 404, new feed has same article URLs. System logs fetch failure for old feed, discovers articles from new feed, URL uniqueness prevents duplicates, source metrics continue correctly (may need manual source URL update)
- **What happens when Exa API returns article without accessible content**? System stores article with raw_content=NULL, filters based on headline/summary only (Exa provides preview text), logs content-unavailable warning, includes in candidates if headline passes filtering
- **What happens when Claude Haiku rate limit exceeded**? System waits with exponential backoff (10s, 20s, 40s, 80s), retries entire batch, logs rate limit event, fails job if retries exhausted (notifies John via email)
- **What happens when filtering produces only 20 candidates (below 40 target)**? System stores all ≥0.5 score articles regardless of count, logs low-volume warning, does NOT lower threshold to compensate (maintain quality standards)
- **What happens when filtering produces 80 candidates (above 60 target)**? System stores all ≥0.5 articles, logs high-volume warning, does NOT raise threshold (Volume Over Precision principle - better to give John 80 options than filter too aggressively)
- **What happens when article headline or content contains non-English characters**? System stores as UTF-8, Claude Haiku processes correctly (supports multilingual), English-language filtering rules still applied, non-English articles likely score low and filtered out naturally
- **What happens when same article appears in multiple RSS feeds**? First feed processed stores article successfully, subsequent feeds encounter duplicate URL, system logs "duplicate from [source]", increments all relevant source total_surfaced counters

## Requirements *(mandatory)*

### Functional Requirements

**RSS Feed Fetching**

- **FR-001**: System MUST fetch articles from all sources where type="rss" and is_active=true daily
- **FR-002**: System MUST parse RSS/Atom feed formats using feedparser library, extracting title, link, published date, description, content
- **FR-003**: System MUST handle fetch failures gracefully (timeouts, 404, 500 errors) without crashing entire job
- **FR-004**: System MUST update source.last_fetched timestamp after each fetch attempt (success or failure)
- **FR-005**: System MUST respect RSS feed update frequency (no more than once per hour to avoid hammering sources)

**Exa API Search**

- **FR-006**: System MUST execute all sources where type="search_query" and is_active=true daily
- **FR-007**: System MUST retrieve 10-20 articles per Exa search query with content snippets
- **FR-008**: System MUST handle Exa API rate limits with exponential backoff retry (2s, 4s, 8s delays)
- **FR-009**: System MUST log Exa API costs per request for monthly budget tracking (<$10/month target)
- **FR-010**: System MUST store Exa search parameters (query text, filters) with source record for reproducibility

**URL Normalization**

- **FR-011**: System MUST normalize URLs before uniqueness check: remove query parameters, convert to lowercase, remove trailing slashes, standardize http/https
- **FR-012**: System MUST preserve original URL in metadata while using normalized URL for uniqueness
- **FR-013**: System MUST handle URL edge cases: relative URLs (convert to absolute), redirects (follow once), invalid URLs (log and skip)

**AI Filtering with Claude Haiku**

- **FR-014**: System MUST send article (headline + content + metadata) + all active FilterRules to Claude Haiku for evaluation
- **FR-015**: System MUST request structured response: filter_score (float 0.0-1.0), summary (2-3 sentences), amish_angle (1 sentence), filter_notes (rationale)
- **FR-016**: System MUST batch articles for filtering (10-20 articles per Claude request) to minimize API calls
- **FR-017**: System MUST use Claude Haiku model (cheap, fast) not Sonnet (expensive) for filtering
- **FR-018**: System MUST keep articles with filter_score ≥0.5, discard articles <0.5
- **FR-019**: System MUST store filter_score and filter_notes for all articles (kept and discarded) to enable analysis

**Candidate Storage**

- **FR-020**: System MUST store articles with filter_score ≥0.5 as candidates (status="pending") in articles table
- **FR-021**: System MUST link each article to originating source via source_id foreign key
- **FR-022**: System MUST preserve discovered_date timestamp (when article found by system, not published_date from source)
- **FR-023**: System MUST store AI-generated summary and amish_angle for later use in email template

**Source Performance Tracking**

- **FR-024**: System MUST increment source.total_surfaced for every article discovered from that source (before filtering)
- **FR-025**: System MUST update source.last_fetched after each fetch attempt with current timestamp
- **FR-026**: System MUST log fetch errors (timeouts, HTTP errors, parse errors) with source name for debugging

**Daily Job Orchestration**

- **FR-027**: System MUST run complete discovery workflow daily at 8am EST via Railway cron
- **FR-028**: System MUST complete job within 30 minutes maximum (allow generous time for retries)
- **FR-029**: System MUST log job summary: total raw articles, total filtered, total kept, total discarded, sources succeeded/failed, API costs
- **FR-030**: System MUST send alert email to John if job fails completely (no candidates produced)

**Volume Targets**

- **FR-031**: System MUST target 40-60 candidate articles per day after filtering
- **FR-032**: System MUST log warning if candidates <40 (insufficient volume) or >80 (excessive volume)
- **FR-033**: System MUST NOT automatically adjust filtering threshold based on volume (maintain consistent standards)

### Key Entities *(include if feature involves data)*

- **Discovery Service**: Orchestrates RSS fetch + Exa search + Claude filtering workflow. Handles retries, error logging, source metrics updates. Returns list of candidate articles ready for storage.

- **RSS Fetcher**: Fetches and parses RSS/Atom feeds using feedparser. Extracts article metadata (headline, URL, date, content). Handles fetch failures and malformed feeds gracefully.

- **Exa Searcher**: Executes Exa API queries, retrieves article results with content snippets. Manages rate limits and API costs. Returns structured article data.

- **URL Normalizer**: Normalizes article URLs for deduplication. Removes tracking parameters, standardizes protocol/domain, handles edge cases (relative URLs, redirects).

- **Claude Filter**: Sends article + FilterRules to Claude Haiku, parses structured response (filter_score, summary, amish_angle, filter_notes). Batches articles for efficiency.

- **Article Candidate (extended)**: Articles table records enhanced with AI-generated fields (summary, amish_angle, filter_score, filter_notes) after filtering. Source linkage via source_id.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Daily job discovers 200-300 raw articles from RSS feeds + Exa searches combined in under 20 minutes
- **SC-002**: URL deduplication prevents >95% of duplicate articles from being stored (tested across RSS/Exa overlap)
- **SC-003**: Claude Haiku filtering evaluates all discovered articles in under 10 minutes (batched efficiently)
- **SC-004**: System produces 40-60 candidate articles per day after filtering (target range) for 90% of days
- **SC-005**: Daily job cost stays under $2/day (Exa API ~$0.30, Claude Haiku ~$0.50, buffer for retries)
- **SC-006**: Job completion rate >95% (fewer than 1-2 failures per month requiring manual intervention)
- **SC-007**: Partial failures (1-2 sources down) do not block job completion (continues with available sources)
- **SC-008**: Zero duplicate articles delivered to John (URL uniqueness + normalization achieves 100% deduplication at database level)
- **SC-009**: Filter score distribution: 15-20% of raw articles pass filtering (e.g., 50 kept from 250-300 discovered)
- **SC-010**: Source fetch errors logged with sufficient detail for debugging (source name, error type, timestamp, retry count)

## Assumptions

- **RSS Feeds**: All configured RSS sources return standard RSS 2.0 or Atom format parseable by feedparser library
- **Exa API**: Exa account provisioned, API key available, free/low-cost tier sufficient for ~10 queries/day × 10-20 results each
- **Claude Haiku**: Anthropic API key available, Haiku model accessed via Anthropic Python SDK, structured output via prompt engineering (no function calling required)
- **Article Content**: Most discovered articles include full text or substantial preview (minimum 100 characters for filtering)
- **Duplicate Rate**: Expect 10-20% overlap between RSS and Exa results (e.g., 50 duplicates from 300 discovered)
- **Filtering Selectivity**: Expect 80-85% of articles filtered out (only 15-20% pass criteria) based on strict Amish appropriateness standards
- **Job Timing**: 8am EST chosen to have candidates ready when John checks email morning (8:30-9am typical)
- **Railway Cron**: Railway supports cron jobs, DATABASE_URL available in cron environment, same Python environment as web app
- **Error Recovery**: Transient failures (timeouts, rate limits) resolve on retry; persistent failures (feed removed, API key invalid) require manual intervention
- **Character Encoding**: All sources provide UTF-8 encoded content; non-English articles naturally filtered out by English-language filtering rules
