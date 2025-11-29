# Filter API Contracts

## Claude API Contracts

Each filter uses Anthropic's structured outputs beta to guarantee valid JSON responses.

### Filter 1: News Check

**Model**: `claude-haiku-4-5`

**Input Schema**:
```json
{
  "title": "string",
  "url": "string", 
  "content": "string (max 8000 chars)"
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "is_news": { "type": "boolean" },
    "category": { 
      "type": "string",
      "enum": ["news_article", "event_listing", "directory_page", "about_page", "product_page", "other_non_news"]
    },
    "reasoning": { "type": "string" }
  },
  "required": ["is_news", "category", "reasoning"],
  "additionalProperties": false
}
```

**Example Response**:
```json
{
  "is_news": false,
  "category": "event_listing",
  "reasoning": "This is a community calendar listing upcoming church events, not a news story about something that happened."
}
```

---

### Filter 2: Wow Factor

**Model**: `claude-sonnet-4-5`

**Input Schema**:
```json
{
  "title": "string",
  "content": "string (max 8000 chars)"
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "wow_score": { "type": "number", "minimum": 0, "maximum": 1 },
    "reasoning": { "type": "string" }
  },
  "required": ["wow_score", "reasoning"],
  "additionalProperties": false
}
```

**Example Response**:
```json
{
  "wow_score": 0.85,
  "reasoning": "A 200-year-old barn being restored entirely by hand using traditional methods is genuinely remarkable. The community effort and preservation of heritage makes this story surprising and delightful."
}
```

---

### Filter 3: Values Fit

**Model**: `claude-sonnet-4-5`

**Input Schema**:
```json
{
  "title": "string",
  "content": "string (max 8000 chars)",
  "must_have_rules": ["string"],
  "must_avoid_rules": ["string"]
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "values_score": { "type": "number", "minimum": 0, "maximum": 1 },
    "reasoning": { "type": "string" }
  },
  "required": ["values_score", "reasoning"],
  "additionalProperties": false
}
```

**Example Response**:
```json
{
  "values_score": 0.92,
  "reasoning": "This story about a community barn raising aligns strongly with Amish values of mutual aid, craftsmanship, and community. No forbidden topics present."
}
```

---

## Internal Service Contracts

### FilterPipeline.run()

**Input**:
```python
articles: list[dict]  # Each dict has: url, title, content (raw_content from scrape)
```

**Output**:
```python
PipelineResult:
  run_id: UUID
  passed_articles: list[dict]  # Articles that passed all 3 filters
  traces: list[FilterTrace]    # All trace records created
  stats: dict                  # Counts per stage
```

### Individual Filter Functions

**Signature**:
```python
def filter_news_check(article: dict) -> FilterResult:
    """
    Args:
        article: {url, title, content}
    Returns:
        FilterResult(passed=bool, score=float|None, category=str, reasoning=str, tokens_in=int, tokens_out=int, latency_ms=int)
    """

def filter_wow_factor(article: dict) -> FilterResult:
    """
    Args:
        article: {url, title, content}
    Returns:
        FilterResult(passed=bool, score=float, reasoning=str, tokens_in=int, tokens_out=int, latency_ms=int)
    """

def filter_values_fit(article: dict, rules: dict) -> FilterResult:
    """
    Args:
        article: {url, title, content}
        rules: {must_have: list[str], must_avoid: list[str]}
    Returns:
        FilterResult(passed=bool, score=float, reasoning=str, tokens_in=int, tokens_out=int, latency_ms=int)
    """
```

