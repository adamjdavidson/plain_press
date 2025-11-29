# Admin Routes Contract

## Routes

### GET /admin/filter-runs

**Purpose**: List all pipeline runs with summary statistics

**Response**: HTML page with table of runs

**Template Data**:
```python
{
  "runs": [
    {
      "id": UUID,
      "started_at": datetime,
      "status": "completed" | "running" | "failed",
      "input_count": int,
      "filter1_pass_count": int,
      "filter2_pass_count": int,
      "filter3_pass_count": int,
      "pass_rate": float  # filter3_pass_count / input_count
    }
  ]
}
```

**Sorting**: Most recent first (`started_at DESC`)

**Pagination**: Show last 50 runs (7 days retention means ~7-14 runs typical)

---

### GET /admin/filter-runs/<run_id>

**Purpose**: Funnel view for a single pipeline run

**Response**: HTML page with funnel visualization and article tables

**Template Data**:
```python
{
  "run": {
    "id": UUID,
    "started_at": datetime,
    "completed_at": datetime | None,
    "status": str,
    "input_count": int,
    "error_message": str | None
  },
  "funnel": [
    {"name": "Input", "count": 523},
    {"name": "News Check", "passed": 198, "rejected": 325},
    {"name": "Wow Factor", "passed": 87, "rejected": 111},
    {"name": "Values Fit", "passed": 62, "rejected": 25}
  ],
  "articles_by_stage": {
    "news_check": {"passed": [...], "rejected": [...]},
    "wow_factor": {"passed": [...], "rejected": [...]},
    "values_fit": {"passed": [...], "rejected": [...]}
  }
}
```

**Article Summary** (in lists):
```python
{
  "url": str,
  "title": str,
  "decision": "pass" | "reject",
  "score": float | None,
  "reasoning": str (truncated to 100 chars for list view)
}
```

---

### GET /admin/filter-runs/<run_id>/article/<url_hash>

**Purpose**: Show single article's journey through all filters

**URL Hash**: MD5 of article URL (for URL-safe routing)

**Response**: HTML page with article details and filter decisions

**Template Data**:
```python
{
  "run_id": UUID,
  "article": {
    "url": str,
    "title": str
  },
  "journey": [
    {
      "filter_name": "news_check",
      "filter_order": 1,
      "decision": "pass",
      "score": None,
      "category": "news_article",  # Only for Filter 1
      "reasoning": str (full text),
      "latency_ms": int,
      "tokens_in": int,
      "tokens_out": int
    },
    {
      "filter_name": "wow_factor",
      "filter_order": 2,
      "decision": "pass",
      "score": 0.72,
      "reasoning": str,
      "latency_ms": int,
      "tokens_in": int,
      "tokens_out": int
    },
    # ... Filter 3 if reached
  ],
  "final_outcome": "accepted" | "rejected_at_news_check" | "rejected_at_wow_factor" | "rejected_at_values_fit"
}
```

---

### GET /admin/filter-runs/<run_id>/rejections/<filter_name>

**Purpose**: Rejection analysis for a specific filter

**Response**: HTML page with rejection patterns and export option

**Template Data**:
```python
{
  "run_id": UUID,
  "filter_name": str,
  "total_rejections": int,
  "patterns": [
    {
      "reasoning_summary": str (grouped/clustered),
      "count": int,
      "percentage": float,
      "example_articles": [
        {"url": str, "title": str}
      ]
    }
  ]
}
```

---

### GET /admin/filter-runs/<run_id>/rejections/<filter_name>/export

**Purpose**: Export rejected articles as CSV

**Response**: CSV file download

**CSV Columns**:
```
url,title,reasoning,score
```

**Filename**: `{filter_name}_rejections_{run_id[:8]}.csv`

---

## Error Handling

- **404**: Run not found, article not found in run
- **400**: Invalid filter_name (must be news_check, wow_factor, or values_fit)

All errors render error template with message, not JSON.

