# Research Decisions: Multi-Stage Filtering Pipeline

## R1: Filter Architecture - Sequential vs Parallel

**Decision**: Sequential pipeline with early exit

**Rationale**: 
- Articles rejected at Filter 1 (non-news) never reach Filter 2 or 3
- Saves API costs by avoiding unnecessary Claude calls
- Simplifies tracing - each article has a clear "furthest stage reached"
- Matches user's insight: "LLMs get confused when balancing multiple criteria"

**Alternatives Considered**:
- Parallel evaluation (all 3 filters at once): Faster but wastes API calls on junk content
- Single mega-filter with internal stages: Current approach, proven to produce confused results

---

## R2: Model Selection per Filter

**Decision**: 
- Filter 1 (News Check): `claude-haiku-4-5` - Binary decision, fast and cheap
- Filter 2 (Wow Factor): `claude-sonnet-4-5` - Nuanced judgment required
- Filter 3 (Values Fit): `claude-sonnet-4-5` - Nuanced judgment required

**Rationale**:
- Filter 1 is a classification task (news vs not-news) - Haiku handles this well
- Filters 2 and 3 require subjective evaluation - Sonnet's quality matters
- Constitution v2.0.0 removed Cost Discipline - prioritize effectiveness over cost

**Alternatives Considered**:
- Haiku for all filters: Risked poor quality on nuanced judgments
- Sonnet for all filters: Unnecessarily expensive for simple Filter 1 task
- Opus for Filter 2/3: Overkill for this use case

---

## R3: Trace Storage Strategy

**Decision**: Database table (`filter_traces`) with 7-day retention

**Rationale**:
- Database storage enables SQL queries for funnel analytics
- 7-day retention balances analysis needs vs storage growth
- ~500 articles × 3 filters × 7 days = ~10,500 rows max - trivial for PostgreSQL
- Cleanup via scheduled script or database trigger

**Alternatives Considered**:
- File-based logging: Harder to query, aggregate, and display in admin UI
- External observability (Langfuse): Additional dependency, overkill for single user
- Indefinite retention: Unnecessary storage growth

---

## R4: Prompt Structure for Focused Filters

**Decision**: Each filter gets a minimal, single-purpose prompt with structured JSON output

**Rationale**:
- User insight: "LLMs get confused when asked to balance multiple things"
- Each prompt asks ONE question and expects ONE answer type
- Structured outputs guarantee valid JSON (using Anthropic beta feature)
- Short prompts = faster responses, lower token costs

**Prompt Patterns**:

**Filter 1 (News Check)**:
```
Is this an actual news story about an event that happened, or is it non-news content?

Categories: news_article, event_listing, directory_page, about_page, product_page, other_non_news

Output: { "is_news": boolean, "category": string, "reasoning": string }
```

**Filter 2 (Wow Factor)**:
```
Would this news story make someone say "wow"? Is it surprising, delightful, or unusual?

Score 0.0-1.0 where:
- 0.8-1.0: Remarkable, must share
- 0.5-0.7: Interesting, worth knowing
- 0.2-0.4: Mildly interesting
- 0.0-0.2: Routine, mundane

Output: { "wow_score": number, "reasoning": string }
```

**Filter 3 (Values Fit)**:
```
Does this story align with Amish/conservative values? Does it avoid forbidden topics?

[Insert must_have and must_avoid rules from FilterRule table]

Score 0.0-1.0 for values alignment.

Output: { "values_score": number, "reasoning": string }
```

**Alternatives Considered**:
- Long detailed prompts: Risked confusion, slower responses
- Free-form text output: Required parsing, risked invalid responses

---

## R5: Admin View Implementation

**Decision**: Server-rendered HTML templates (Jinja2) with existing Flask patterns

**Rationale**:
- Matches existing admin UI patterns (`/admin/articles`, `/admin/sources`)
- Single-user tool doesn't need SPA complexity
- Jinja2 templates are fast to implement and maintain
- No additional frontend dependencies

**Alternatives Considered**:
- React/Vue SPA: Overkill for admin views, adds build complexity
- HTMX: Could enhance interactivity but not needed for MVP

---

## R6: Pipeline Run Identity

**Decision**: UUID-based `run_id` generated at pipeline start, stored in `PipelineRun` table

**Rationale**:
- UUID ensures uniqueness across restarts and distributed runs
- `PipelineRun` table stores metadata (start time, article count, status)
- All `FilterTrace` records reference `run_id` for grouping
- Enables funnel queries: `SELECT filter_name, COUNT(*) FROM filter_traces WHERE run_id = X GROUP BY filter_name`

**Alternatives Considered**:
- Timestamp-based ID: Risk of collisions in rapid succession
- Auto-increment: Requires database roundtrip before pipeline starts

---

## R7: Handling Existing `claude_filter.py`

**Decision**: Deprecate and replace, not modify

**Rationale**:
- Current single-pass architecture is fundamentally different from multi-stage
- Clean separation allows A/B testing during rollout
- Old code can be deleted after validation
- New modules (`filter_news_check.py`, etc.) are easier to test in isolation

**Migration Path**:
1. Build new pipeline alongside existing code
2. Add environment flag `USE_MULTI_STAGE_FILTER=true`
3. Test with real data, compare results
4. Remove old code once validated

**Alternatives Considered**:
- In-place modification: Riskier, harder to rollback, harder to test

