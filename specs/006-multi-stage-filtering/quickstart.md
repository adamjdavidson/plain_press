# Quickstart: Multi-Stage Filtering Pipeline

## Overview

This feature replaces the single-pass Claude filter with three sequential focused filters:

1. **News Check** (Haiku): Is this actual news?
2. **Wow Factor** (Sonnet): Would this make someone say wow?
3. **Values Fit** (Sonnet): Does this fit Amish values?

Each filter evaluates ONE criterion and records its decision in a trace table.

## Implementation Order

### Phase 1: Database & Models

1. Create migration for `pipeline_runs` and `filter_traces` tables
2. Add `PipelineRun` and `FilterTrace` models to `app/models.py`
3. Add `PipelineRunStatus` enum
4. Run migration

### Phase 2: Individual Filters

Build and test each filter in isolation:

1. **filter_news_check.py**
   - Haiku model
   - Binary is_news + category classification
   - Structured output schema

2. **filter_wow_factor.py**
   - Sonnet model
   - 0.0-1.0 wow_score
   - Structured output schema

3. **filter_values_fit.py**
   - Sonnet model
   - 0.0-1.0 values_score
   - Loads rules from FilterRule table
   - Structured output schema

### Phase 3: Pipeline Orchestrator

1. **filter_pipeline.py**
   - Creates PipelineRun at start
   - Runs filters sequentially
   - Records FilterTrace after each evaluation
   - Updates PipelineRun counts at end
   - Handles errors gracefully (continue on individual failures)

### Phase 4: Integration

1. Update `discovery.py` to use new pipeline
2. Add environment flag for rollout: `USE_MULTI_STAGE_FILTER=true`
3. Keep old `claude_filter.py` for fallback

### Phase 5: Admin Views

1. **filter_runs.html** - List of pipeline runs
2. **filter_run_detail.html** - Funnel view
3. **article_journey.html** - Single article path
4. Add routes to `routes.py`
5. Add CSV export endpoint

### Phase 6: Cleanup & Validation

1. Create `scripts/cleanup_traces.py` for 7-day retention
2. Add cleanup to cron or Railway scheduled job
3. Manual testing with real data
4. Remove old filter code after validation

## Environment Variables

```bash
# Filter thresholds (defaults shown)
FILTER_WOW_THRESHOLD=0.5
FILTER_VALUES_THRESHOLD=0.5

# Model selection (defaults shown)  
FILTER_NEWS_CHECK_MODEL=claude-haiku-4-5
FILTER_WOW_FACTOR_MODEL=claude-sonnet-4-5
FILTER_VALUES_FIT_MODEL=claude-sonnet-4-5

# Feature flag
USE_MULTI_STAGE_FILTER=true

# Tracing
FILTER_TRACING_ENABLED=true
```

## Key Files to Create

```
app/services/filter_news_check.py    # ~100 lines
app/services/filter_wow_factor.py    # ~100 lines
app/services/filter_values_fit.py    # ~120 lines
app/services/filter_pipeline.py      # ~200 lines
templates/admin/filter_runs.html     # ~100 lines
templates/admin/filter_run_detail.html # ~150 lines
templates/admin/article_journey.html # ~80 lines
scripts/cleanup_traces.py            # ~50 lines
```

## Testing Strategy

1. **Unit tests** for each filter function (mocked Claude responses)
2. **Integration test** for full pipeline with real Claude calls (limited batch)
3. **Manual validation** comparing old vs new filter results
4. **Admin UI** walkthrough with John

## Rollback Plan

If issues arise after deployment:

1. Set `USE_MULTI_STAGE_FILTER=false`
2. System reverts to old single-pass filter
3. Trace data remains for analysis
4. Fix issues and re-enable

