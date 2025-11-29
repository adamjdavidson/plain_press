# Research: Story Quality Filter

**Feature**: 001-story-quality-filter  
**Date**: 2025-11-29

## Research Questions

### Q1: How should wow_score interact with existing filter_score?

**Decision**: Separate evaluation with independent thresholds

**Rationale**:
- `filter_score` measures editorial fit (topic alignment, must_have/must_avoid compliance)
- `wow_score` measures quality/interestingness (surprising, delightful, unusual)
- A story can have high editorial fit but be boring (routine local news about farming)
- A story can be "wow" but not fit editorially (amazing tech story)
- Both gates must pass for inclusion

**Implementation**:
```
Final inclusion = news_check AND (wow_score >= wow_threshold) AND (filter_score >= filter_threshold)
```

**Alternatives Rejected**:
- Combined single score: Loses the ability to diagnose WHY something was rejected
- Multiplicative combination: Over-penalizes borderline stories

---

### Q2: What prompt structure best captures "wow factor"?

**Decision**: Dedicated WOW FACTOR EVALUATION section in system prompt

**Rationale**:
- Current prompt is already structured with clear sections (CONTENT TYPE, EDITORIAL GUIDELINES)
- Adding a parallel WOW FACTOR section maintains consistency
- Explicit criteria give Claude clear guidance on what "wow" means

**Prompt Addition**:
```
WOW FACTOR EVALUATION (apply to news_article only):

Before scoring editorial fit, evaluate if this story would make someone say "wow!"

A story has high wow factor if it is:
- SURPRISING: Unexpected, not routine or predictable news
- DELIGHTFUL: Produces a smile, warmth, sense of wonder
- UNUSUAL: Quirky, odd, uncommon - stands out from typical news

Score wow_factor 0.0-1.0:
- 0.8-1.0: Genuinely remarkable - "I have to share this"
- 0.5-0.7: Interesting - "That's nice to know"
- 0.2-0.4: Mildly interesting - "Okay, sure"
- 0.0-0.2: Boring - routine announcement, press release, mundane event

In wow_notes, briefly explain why this story is or isn't "wow-worthy."
```

**Alternatives Rejected**:
- Rewriting entire prompt: Too risky, existing prompt works well for content type and editorial checks
- Inline wow criteria in existing sections: Muddies the evaluation flow

---

### Q3: Should content_type be persisted to database?

**Decision**: Yes, add content_type column to Article model

**Rationale**:
- Currently computed by Claude but not stored
- Persisting enables:
  - Admin filtering by content type (see all event_listing rejections)
  - Analytics on source quality (which sources produce most non-news?)
  - Debugging filter decisions
  - Weekly refinement analysis

**Schema**:
```python
content_type: Mapped[Optional[str]] = Column(String(50), nullable=True)
```

**Alternatives Rejected**:
- PostgreSQL enum: Harder to migrate, less flexible for future categories
- JSONB field: Overkill for single string value
- Not storing: Loses valuable diagnostic information

---

### Q4: What default threshold for wow_score?

**Decision**: 0.4 default, configurable via WOW_SCORE_THRESHOLD env var

**Rationale**:
- Lower than filter_score threshold (0.5) because:
  - Wow factor is more subjective
  - Want to err toward inclusion per constitution (Volume Over Precision)
  - John can tune up if too many boring stories still pass
- Configurable allows iteration without code changes

**Threshold Behavior**:
| wow_score | Result |
|-----------|--------|
| 0.0-0.39  | Rejected - boring/mundane |
| 0.4-1.0   | Passes wow check, proceeds to editorial check |

**Alternatives Rejected**:
- 0.5 threshold: Too aggressive initially, risks false negatives
- 0.3 threshold: Too permissive, might not solve the problem
- No threshold: Doesn't address the core issue of terrible stories

---

### Q5: How to format enhanced rejection reasons?

**Decision**: Structured format with clear categorization

**Rationale**:
- John needs to quickly understand WHY a story was rejected
- Categories: content_type rejection vs wow_score rejection vs editorial rejection
- Specific details enable trust calibration

**Format Examples**:

Non-news rejection:
```
Rejected: content_type=event_listing | This is a calendar event announcing a festival, not a news story about something that happened.
```

Low wow rejection:
```
Rejected: wow_score=0.25 (threshold: 0.40) | Routine announcement about road construction - mundane local news with no surprising or unusual element.
```

Editorial rejection:
```
Rejected: filter_score=0.35 | Story involves modern technology (electric vehicles) which conflicts with Amish values.
```

**Alternatives Rejected**:
- Unstructured prose: Harder to parse at a glance
- Codes only: Not human-readable enough

---

## Cost Impact Analysis

**Current cost per article**: ~$0.003 (500 input + 150 output tokens)

**With wow_score additions**:
- Additional prompt text: ~100 tokens
- Additional output fields: ~30 tokens per article
- New cost per article: ~$0.0035

**Monthly impact**:
- 300 articles/day × 30 days = 9,000 articles
- Additional cost: 9,000 × $0.0005 = ~$4.50/month
- Still well within $50 budget

**Conclusion**: Cost impact is negligible and acceptable.

---

## Technical Risks

### Risk 1: Claude consistency on wow_score

**Risk**: Claude may not consistently apply wow criteria

**Mitigation**: 
- Clear, specific criteria in prompt
- Temperature 0 for deterministic outputs
- Example thresholds in prompt help calibration

### Risk 2: Over-aggressive filtering reduces candidates below target

**Risk**: With wow threshold + filter threshold, might reject too many stories

**Mitigation**:
- Start with low wow threshold (0.4)
- Monitor daily candidate counts
- Threshold is configurable for quick adjustment

### Risk 3: Migration on production data

**Risk**: Adding nullable columns to Article table with existing data

**Mitigation**:
- New columns are nullable, no default required
- Existing articles get NULL for content_type/wow_score
- Only newly filtered articles populate fields

---

## Dependencies

No new external dependencies required. All changes use existing:
- Anthropic Claude API (structured outputs beta)
- SQLAlchemy/Alembic for schema migration
- Existing test infrastructure

