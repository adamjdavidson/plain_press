# Data Model: Multi-Stage Filtering Pipeline

## New Entities

### PipelineRun

Represents a single execution of the filtering pipeline. Groups all filter traces for one run.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | Unique identifier |
| started_at | DateTime(tz) | NOT NULL, default now() | When pipeline execution began |
| completed_at | DateTime(tz) | NULL | When pipeline finished (null if still running) |
| status | Enum | NOT NULL, default 'running' | running, completed, failed |
| input_count | Integer | NOT NULL | Total articles entering pipeline |
| filter1_pass_count | Integer | NULL | Articles passing News Check |
| filter2_pass_count | Integer | NULL | Articles passing Wow Factor |
| filter3_pass_count | Integer | NULL | Articles passing Values Fit |
| error_message | Text | NULL | Error details if status=failed |
| created_at | DateTime(tz) | NOT NULL, default now() | Record creation time |

**Indexes**:
- `ix_pipeline_runs_started_at` on `started_at` (for listing recent runs)
- `ix_pipeline_runs_status` on `status` (for finding incomplete runs)

**Relationships**:
- Has many `FilterTrace` (one-to-many via `run_id`)

---

### FilterTrace

Records one filter's evaluation of one article. Core tracing entity.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | Unique identifier |
| run_id | UUID | FK → pipeline_runs.id, NOT NULL | Which pipeline run |
| article_url | String(500) | NOT NULL | Article being evaluated |
| article_title | String(500) | NOT NULL | Article headline |
| filter_name | String(50) | NOT NULL | 'news_check', 'wow_factor', 'values_fit' |
| filter_order | Integer | NOT NULL | 1, 2, or 3 |
| decision | String(20) | NOT NULL | 'pass' or 'reject' |
| score | Float | NULL | Numeric score (0.0-1.0) if applicable |
| reasoning | Text | NOT NULL | Claude's explanation |
| input_tokens | Integer | NULL | Tokens sent to Claude |
| output_tokens | Integer | NULL | Tokens received |
| latency_ms | Integer | NULL | API call duration in milliseconds |
| created_at | DateTime(tz) | NOT NULL, default now() | Record creation time |

**Indexes**:
- `ix_filter_traces_run_id` on `run_id` (for grouping by run)
- `ix_filter_traces_filter_name` on `filter_name` (for filtering by stage)
- `ix_filter_traces_decision` on `decision` (for rejection analysis)
- `ix_filter_traces_created_at` on `created_at` (for retention cleanup)

**Relationships**:
- Belongs to `PipelineRun` (many-to-one via `run_id`)

---

## Modified Entities

### Article (existing)

Add fields to store final filter results:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| content_type | String(50) | NULL | Already exists - news_article, event_listing, etc. |
| wow_score | Float | NULL | Already exists - wow factor score |
| filter_score | Float | NOT NULL | Already exists - values fit score (renamed semantically) |
| last_run_id | UUID | FK → pipeline_runs.id, NULL | NEW: Which pipeline run last evaluated this article |

**Note**: `content_type` and `wow_score` columns already exist from previous feature. Only `last_run_id` is new.

---

## Enums

### PipelineRunStatus

```python
class PipelineRunStatus(enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
```

---

## Migration Notes

1. Create `pipeline_runs` table first (parent)
2. Create `filter_traces` table with FK to `pipeline_runs`
3. Add `last_run_id` column to `articles` table
4. Add index on `filter_traces.created_at` for retention cleanup queries

---

## Retention Policy

FilterTrace records older than 7 days are automatically deleted:

```sql
DELETE FROM filter_traces 
WHERE created_at < NOW() - INTERVAL '7 days';
```

PipelineRun records are deleted when all their traces are deleted (cascade or cleanup job).

---

## Query Patterns

### Funnel for a Run

```sql
SELECT 
    filter_name,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE decision = 'pass') as passed,
    COUNT(*) FILTER (WHERE decision = 'reject') as rejected
FROM filter_traces
WHERE run_id = :run_id
GROUP BY filter_name
ORDER BY MIN(filter_order);
```

### Article Journey

```sql
SELECT filter_name, filter_order, decision, score, reasoning
FROM filter_traces
WHERE run_id = :run_id AND article_url = :url
ORDER BY filter_order;
```

### Rejection Patterns for Filter

```sql
SELECT 
    reasoning,
    COUNT(*) as count
FROM filter_traces
WHERE run_id = :run_id 
  AND filter_name = :filter_name
  AND decision = 'reject'
GROUP BY reasoning
ORDER BY count DESC
LIMIT 20;
```

