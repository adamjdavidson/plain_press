# Feature Specification: Story Quality Filter

**Feature Branch**: `001-story-quality-filter`  
**Created**: 2025-11-29  
**Status**: Draft  
**Input**: User description: "Most of the stories are terrible. I want a very simple filter. Is this a news story? Meaning, is it news, an event that happened in the world, rather than a calendar listing or random website? Would it make someone go 'wow?' Is it surprising? Is it delightful? Is it unusual?"

**Constitution Check**: Aligned with Volume Over Precision (II) - but rebalancing toward higher quality floor. Aligned with Single-User Simplicity (I) - John needs fewer terrible stories to review. Aligned with Cost Discipline (V) - simple binary check is cheaper than complex evaluation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Filter Out Non-News Content (Priority: P1)

John receives too many "stories" that aren't actually news - they're calendar listings ("Holiday Festival starts Saturday"), website pages ("About Our Farm"), or resource directories ("Meet Our Therapy Animals"). These waste his time scrolling past obvious junk.

**Why this priority**: The highest-volume problem. Non-news content has zero chance of becoming a published story, so filtering it early saves the most review time.

**Independent Test**: Can be tested by running the filter on a batch of known non-news URLs (event pages, about pages, directories) and verifying they're rejected before editorial evaluation.

**Acceptance Scenarios**:

1. **Given** an article sourced from a URL that is an event listing (e.g., "Fall Festival 2025 - Tickets Available"), **When** the filter evaluates it, **Then** it is rejected with content_type="event_listing" and filter_score=0.0 before any editorial evaluation.

2. **Given** an article sourced from an "About Us" or organizational page, **When** the filter evaluates it, **Then** it is rejected with content_type="about_page" and filter_score=0.0.

3. **Given** an article sourced from a directory or resource list page (e.g., "Meet Our Animals", "Staff Directory"), **When** the filter evaluates it, **Then** it is rejected with content_type="directory_page" and filter_score=0.0.

4. **Given** an article that IS actual news (a story about something that happened), **When** the filter evaluates it, **Then** it passes the news-check and proceeds to editorial evaluation.

---

### User Story 2 - Reject Boring/Mundane News (Priority: P2)

Even among actual news stories, many are mundane ("New traffic light installed at Main Street") or generic press releases that wouldn't make anyone say "wow." John wants stories that are surprising, delightful, or unusual.

**Why this priority**: Second-highest volume problem. Boring news is harder to filter than non-news, but represents significant review time waste.

**Independent Test**: Can be tested by presenting the filter with known-boring headlines vs known-delightful headlines and measuring separation accuracy.

**Acceptance Scenarios**:

1. **Given** a news story with a mundane topic (routine government announcement, standard business news, unremarkable local event), **When** the filter evaluates it for "wow factor," **Then** it receives a low wow_score and is flagged for potential rejection.

2. **Given** a news story that is surprising, unusual, or delightful (unexpected animal behavior, quirky community event, strange food product), **When** the filter evaluates it, **Then** it receives a high wow_score and is retained for editorial review.

3. **Given** a story that is technically news but reads like a press release or marketing copy, **When** the filter evaluates it, **Then** it is penalized and likely rejected.

---

### User Story 3 - See Clear Rejection Reasons (Priority: P3)

When John reviews the admin panel, he should be able to quickly understand why stories were rejected. Clear rejection reasons help him trust the filter and identify if it's making mistakes.

**Why this priority**: Supports feedback loop and system calibration. Without clear reasons, John can't tell if the filter is working correctly.

**Independent Test**: Can be verified by reviewing filter_notes for rejected articles and confirming they contain specific, actionable rejection reasons.

**Acceptance Scenarios**:

1. **Given** an article rejected for being non-news, **When** John views it in the admin panel, **Then** the filter_notes clearly state the content type detected (e.g., "Rejected: event_listing - This is a calendar event, not a news story").

2. **Given** an article rejected for low wow factor, **When** John views it in the admin panel, **Then** the filter_notes explain why it failed the quality check (e.g., "Rejected: Low wow factor - Routine announcement with no surprising or unusual element").

---

### Edge Cases

- **Borderline content types**: An article that describes a past event but is framed as a future event ("The festival, which ran last weekend...") should be treated as news, not an event listing.
- **News about boring topics written interestingly**: A story about a traffic light that has an unusual angle ("Town installs singing traffic light that plays folk tunes") should pass the wow-factor check.
- **Press releases disguised as news**: Corporate announcements rephrased as news stories should be detected and rejected.
- **Empty or minimal content**: Articles with too little content to evaluate should be rejected with a clear reason.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST classify every incoming article into one of these content types before editorial evaluation: news_article, event_listing, directory_page, about_page, other_non_news.

- **FR-002**: System MUST automatically reject (score 0.0) any article that is not classified as "news_article" - no exceptions.

- **FR-003**: System MUST evaluate news_article content for "wow factor" using these criteria:
  - Is it surprising? (unexpected, not routine)
  - Is it delightful? (produces smile, warmth, wonder)
  - Is it unusual? (quirky, odd, uncommon)

- **FR-004**: System MUST provide a wow_score (0.0-1.0) indicating how strongly the story meets the wow-factor criteria.

- **FR-005**: System MUST record clear rejection reasons in filter_notes that specify:
  - For non-news: the detected content type
  - For low wow-factor: which criteria it failed and why

- **FR-006**: System MUST apply the quality filter BEFORE applying editorial topic filters (must_have, must_avoid rules), so obviously bad content is rejected cheaply.

- **FR-007**: Articles with wow_score below threshold MUST be rejected regardless of how well they match good topics.

### Key Entities

- **Article**: Extended with content_type (news_article|event_listing|directory_page|about_page|other_non_news) and wow_score (float 0.0-1.0) fields.
- **FilterResult**: Contains content_type, wow_score, and quality_notes explaining the evaluation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Reduction in non-news content reaching John's review queue by 90% (event listings, directory pages, about pages should almost never appear).

- **SC-002**: Reduction in "obviously boring" stories by 50% - measured by John's rejection rate (if fewer stories are rejected with "Why Not" feedback citing boringness, the filter is working).

- **SC-003**: John spends less than 5 seconds per rejected story understanding why it was filtered (clear filter_notes enable quick trust verification).

- **SC-004**: Overall daily candidate quality improves such that John's "Good" rate increases from baseline (fewer wasted review cycles on junk).

- **SC-005**: No increase in false negatives - surprising/delightful stories that would have passed before should still pass (measured by monitoring for "rescued" stories John manually includes).

## Assumptions

- The existing Claude filtering infrastructure can be extended to add content type and wow-factor evaluation without significant architectural changes.
- The current content_type classification in claude_filter.py provides a foundation but needs stricter enforcement and clearer separation.
- "Wow factor" can be reliably evaluated by Claude given clear criteria - this is a qualitative judgment that benefits from AI evaluation.
- The 0.5 filter_score threshold remains appropriate; wow_score is an additional gate, not a replacement.
