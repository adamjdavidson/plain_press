# Feature Specification: Multi-Stage Filtering Pipeline with Tracing

**Feature Branch**: `006-multi-stage-filtering`  
**Created**: 2025-11-29  
**Status**: Draft  
**Input**: User description: "Multi-Stage Filtering Pipeline with Tracing: Replace single-pass filtering with three sequential focused filters (news check, wow factor, values fit) and add comprehensive tracing for review and tuning"

**Constitution Check**: Ensure feature aligns with `.specify/memory/constitution.md` principles (especially Single-User Simplicity).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Pipeline Funnel (Priority: P1)

John wants to understand how many articles pass through each filtering stage so he can identify where candidates are being lost and whether his quality targets are achievable.

**Why this priority**: Without visibility into the funnel, John cannot diagnose why he's not getting 50+ quality stories per day. This is the foundational observability needed before any tuning can happen.

**Independent Test**: Can be fully tested by running a pipeline and viewing the funnel summary. Delivers immediate insight into filtering effectiveness.

**Acceptance Scenarios**:

1. **Given** a completed pipeline run, **When** John views the run summary, **Then** he sees the count of articles entering and passing each filter stage (e.g., "523 → 198 → 87 → 62")
2. **Given** multiple pipeline runs, **When** John views the runs list, **Then** he sees each run with its date, input count, final count, and overall pass rate
3. **Given** a pipeline run, **When** John clicks on a filter stage, **Then** he sees the list of articles that passed and failed at that stage

---

### User Story 2 - Review Individual Article Decisions (Priority: P2)

John wants to see why a specific article was accepted or rejected so he can understand the filter logic and identify prompt improvements.

**Why this priority**: Once John sees the funnel, he'll want to drill into specific decisions. This enables prompt tuning by revealing exactly what the AI is thinking at each stage.

**Independent Test**: Can be fully tested by selecting any article from a run and viewing its complete journey through all filters.

**Acceptance Scenarios**:

1. **Given** a completed pipeline run, **When** John clicks on an article, **Then** he sees the article's title, URL, and the decision/reasoning from each filter it passed through
2. **Given** an article rejected at Filter 2, **When** John views its journey, **Then** he sees Filter 1 pass decision and Filter 2 reject decision with reasoning (no Filter 3 entry since it never reached that stage)
3. **Given** an article that passed all filters, **When** John views its journey, **Then** he sees all three filter decisions with scores and reasoning

---

### User Story 3 - Focused News Check Filter (Priority: P1)

The system needs to determine if content is actual news (an event that happened) versus non-news content like event listings, directories, or about pages. This filter asks ONE question: "Is this news?"

**Why this priority**: This is the first gate - filtering out non-news content is essential and was the original pain point. Without this, garbage content pollutes subsequent filters.

**Independent Test**: Can be fully tested by running a batch of URLs through Filter 1 alone and verifying binary pass/reject decisions with reasoning.

**Acceptance Scenarios**:

1. **Given** an article about a barn fire that occurred yesterday, **When** processed by Filter 1, **Then** it passes with reasoning indicating it's an actual news event
2. **Given** a community calendar listing upcoming events, **When** processed by Filter 1, **Then** it's rejected with reasoning indicating it's an event listing, not news
3. **Given** a church directory page, **When** processed by Filter 1, **Then** it's rejected with reasoning indicating it's a directory, not news
4. **Given** a "About Us" page from a local newspaper, **When** processed by Filter 1, **Then** it's rejected with reasoning indicating it's an about page, not news

---

### User Story 4 - Focused Wow Factor Filter (Priority: P1)

The system needs to evaluate if a news story would make someone say "wow" - is it surprising, delightful, or unusual? This filter asks ONE question: "Would this make someone go wow?"

**Why this priority**: This is the core quality gate that separates interesting stories from mundane announcements. It directly addresses the "terrible stories" problem.

**Independent Test**: Can be fully tested by running confirmed news articles through Filter 2 alone and verifying wow scores with reasoning.

**Acceptance Scenarios**:

1. **Given** a story about a 200-year-old barn being restored by community volunteers using only hand tools, **When** processed by Filter 2, **Then** it scores high (0.7+) with reasoning about community, tradition, and unusual methods
2. **Given** a story about a city council approving a routine budget, **When** processed by Filter 2, **Then** it scores low (under 0.3) with reasoning indicating it's routine and not surprising
3. **Given** a story about a rare albino deer spotted in Amish country, **When** processed by Filter 2, **Then** it scores high with reasoning about rarity and wonder

---

### User Story 5 - Focused Values Fit Filter (Priority: P1)

The system needs to evaluate if a news story aligns with Amish/conservative values and avoids forbidden topics. This filter asks ONE question: "Does this fit our values?"

**Why this priority**: This ensures stories are appropriate for the Plain News audience. Must be separate from wow factor to avoid confusion between "interesting" and "appropriate."

**Independent Test**: Can be fully tested by running wow-worthy articles through Filter 3 alone and verifying values scores with reasoning.

**Acceptance Scenarios**:

1. **Given** a wholesome story about a community barn raising, **When** processed by Filter 3, **Then** it scores high with reasoning about community values and tradition
2. **Given** an interesting story that involves alcohol or drugs, **When** processed by Filter 3, **Then** it scores low with reasoning citing the forbidden topic
3. **Given** an interesting story focused on an individual hero/achievement, **When** processed by Filter 3, **Then** it scores low with reasoning about Amish humility values

---

### User Story 6 - Analyze Rejection Patterns (Priority: P2)

John wants to see aggregated rejection reasons for each filter so he can identify systematic issues and improve prompts.

**Why this priority**: Individual decisions are useful, but pattern analysis reveals systemic issues. This enables bulk prompt improvements.

**Independent Test**: Can be fully tested by viewing rejection analysis for any filter from a completed run.

**Acceptance Scenarios**:

1. **Given** a pipeline run with 300 Filter 1 rejections, **When** John views rejection analysis, **Then** he sees rejections grouped by type (e.g., "Event listing: 150, Directory: 80, About page: 45, Other: 25")
2. **Given** rejection analysis for Filter 2, **When** John views the data, **Then** he can export the rejected articles to a file for deeper analysis
3. **Given** rejection patterns over multiple runs, **When** John compares them, **Then** he can see if rejection rates are improving or degrading over time

---

### Edge Cases

- What happens when an article has no content (empty or failed scrape)?
  - Article is rejected at Filter 1 with reasoning "insufficient content to evaluate"
- How does the system handle API failures mid-pipeline?
  - Failed articles are logged with error state and can be retried; pipeline continues with remaining articles
- What happens when a filter returns invalid scores?
  - Invalid responses are logged, article marked as "filter_error", excluded from final results
- How does the system handle very long articles?
  - Articles are truncated to 8,000 characters for evaluation; truncation noted in trace

## Requirements *(mandatory)*

### Functional Requirements

**Pipeline Architecture**:
- **FR-001**: System MUST run three sequential filters: News Check → Wow Factor → Values Fit
- **FR-002**: Each filter MUST evaluate ONE criterion only (no multi-criteria evaluation in a single filter)
- **FR-003**: Articles rejected at any stage MUST NOT proceed to subsequent filters
- **FR-004**: Each filter MUST produce a decision (pass/reject), optional score, and reasoning text

**Filter 1 - News Check**:
- **FR-005**: Filter 1 MUST classify content as either "news" or "non-news"
- **FR-006**: Non-news categories MUST include: event listing, directory, about page, product page, and other non-news
- **FR-007**: Filter 1 MUST provide reasoning explaining the classification decision

**Filter 2 - Wow Factor**:
- **FR-008**: Filter 2 MUST score articles on a 0.0-1.0 scale for "wow factor"
- **FR-009**: Filter 2 MUST evaluate ONLY interestingness (surprising, delightful, unusual) - NOT values fit
- **FR-010**: Filter 2 threshold MUST be configurable (default: 0.5)
- **FR-011**: Filter 2 MUST provide reasoning explaining the wow score

**Filter 3 - Values Fit**:
- **FR-012**: Filter 3 MUST score articles on a 0.0-1.0 scale for values alignment
- **FR-013**: Filter 3 MUST evaluate ONLY appropriateness and values fit - NOT interestingness
- **FR-014**: Filter 3 MUST apply must_have and must_avoid rules from existing filter configuration
- **FR-015**: Filter 3 threshold MUST be configurable (default: 0.5)
- **FR-016**: Filter 3 MUST provide reasoning explaining the values score

**Tracing**:
- **FR-017**: System MUST record a trace entry for every article entering every filter
- **FR-018**: Trace entries MUST include: run identifier, article identifier, filter name, decision, score (if applicable), and reasoning
- **FR-019**: System MUST assign a unique run identifier to each pipeline execution
- **FR-020**: Traces MUST be queryable by run, by filter, and by article

**Admin Views**:
- **FR-021**: System MUST provide a view listing all pipeline runs with summary statistics
- **FR-022**: System MUST provide a funnel view for each run showing counts at each stage
- **FR-023**: System MUST provide article journey view showing all filter decisions for a single article
- **FR-024**: System MUST provide rejection analysis view grouping rejections by reasoning patterns

**Configuration**:
- **FR-025**: Filter thresholds MUST be configurable via environment variables
- **FR-026**: Tracing MUST be toggleable via environment variable (enabled by default)
- **FR-027**: System MUST automatically delete trace records older than 7 days

### Key Entities

- **PipelineRun**: A single execution of the filtering pipeline; has a unique ID, start time, and references to all traces from that run
- **FilterTrace**: A record of one filter evaluating one article; includes filter name, decision, score, reasoning, and timing metrics
- **Article**: Existing entity; extended with fields for content_type, wow_score, and filter_score from the pipeline

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Pipeline delivers 50+ quality story candidates per day (measured by John's acceptance rate improving)
- **SC-002**: John can identify why any article was rejected within 30 seconds of viewing its journey
- **SC-003**: Funnel view loads within 3 seconds for runs with up to 1,000 articles
- **SC-004**: Each filter's reasoning clearly explains the single criterion it evaluated (no mixed criteria in explanations)
- **SC-005**: Rejection analysis correctly groups 90%+ of rejections into identifiable patterns
- **SC-006**: John can adjust filter thresholds and see immediate impact on subsequent runs

## Clarifications

### Session 2025-11-29

- Q: What is the article content truncation limit for filter evaluation? → A: 8,000 characters (~2 pages of text)
- Q: How long should trace data be retained before automatic cleanup? → A: 7 days
- Q: Where should article enrichment (summary, topics, amish_angle) happen? → A: Out of scope - enrichment is triggered by John's "Good" feedback click, not the filtering pipeline

## Out of Scope

- **Article enrichment** (summary, topics, amish_angle generation) - handled by existing feedback-triggered workflow when John clicks "Good"
- **Discovery/scraping changes** - this feature assumes sufficient input candidates already exist
- **Email template changes** - filtering happens before email generation

## Assumptions

- The existing scraping/discovery pipeline provides sufficient article candidates (500+) as input
- Claude AI models can reliably make focused single-criterion judgments when given clear, narrow prompts
- Filter prompts can be independently tuned without affecting other filters
- John will review pipeline results at least weekly to identify improvement opportunities
