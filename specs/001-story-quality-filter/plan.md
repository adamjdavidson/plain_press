# Implementation Plan: Story Quality Filter

**Branch**: `001-story-quality-filter` | **Date**: 2025-11-29 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-story-quality-filter/spec.md`

## Summary

Enhance the existing Claude filtering service to more aggressively reject non-news content and add explicit "wow factor" evaluation. The current system already classifies content types but doesn't enforce strict quality gating. This feature adds a dedicated `wow_score` field and clearer rejection reasons to filter out boring/mundane news that passes the news-check but lacks the "delightful oddity" quality.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Anthropic Claude API (existing), SQLAlchemy 2.0+ (existing)  
**Storage**: PostgreSQL (existing Article model - minor schema extension)  
**Testing**: pytest (existing contract/integration test structure)  
**Target Platform**: Railway Linux server (existing deployment)
**Project Type**: Single Flask application  
**Performance Goals**: Daily job completes within 30 minutes (existing), no additional latency  
**Constraints**: <$50/month budget, Claude API costs must not significantly increase  
**Scale/Scope**: ~200-300 articles evaluated daily, ~50 candidates retained

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify alignment with `.specify/memory/constitution.md`:

- [x] **Single-User Simplicity**: This feature directly serves John's workflow by reducing junk in his review queue. No new UI, no new user types, no complexity for theoretical users.
- [x] **Volume Over Precision**: This refines the quality floor without aggressive over-filtering. Targets 90% reduction of obvious junk (non-news), 50% reduction of boring news. Still aims for 40-60 candidates/day.
- [x] **Cost Discipline**: No new API calls - enhancements to existing Claude prompt. Marginal token increase (~50 tokens/article for wow_score) is negligible (~$0.50/month increase).
- [x] **Reliability Over Performance**: Changes are to filtering logic, not external API patterns. Existing idempotency and retry patterns remain intact.

**Violations**: None. Feature fully aligned with constitution principles.

## Project Structure

### Documentation (this feature)

```text
specs/001-story-quality-filter/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output - research findings
├── data-model.md        # Phase 1 output - schema changes
├── quickstart.md        # Phase 1 output - implementation guide
├── contracts/           # Phase 1 output - N/A (no new external APIs)
│   └── (none needed)
└── checklists/
    └── requirements.md  # Spec validation checklist
```

### Source Code (repository root)

```text
app/
├── models.py            # Extend Article with content_type, wow_score fields
├── services/
│   └── claude_filter.py # Enhance prompt and schema for wow_score

migrations/
└── versions/
    └── xxx_add_quality_fields.py  # Alembic migration for new columns

tests/
├── contract/
│   └── test_claude_filter.py      # Contract tests for enhanced schema
└── integration/
    └── test_filtering_quality.py  # Integration tests for quality gating
```

**Structure Decision**: Single Flask application (existing structure). Changes confined to `claude_filter.py` service and `models.py` with a single migration.

## Complexity Tracking

> No violations - table not needed.

---

## Phase 0: Research Summary

### Decision 1: Wow Score Implementation Approach

**Decision**: Add `wow_score` as a separate float field (0.0-1.0) in the Claude response schema, evaluated independently from `filter_score`.

**Rationale**: 
- Separating wow_score from filter_score allows independent calibration
- filter_score remains the editorial fit score (topic alignment)
- wow_score captures the "would this make someone say wow?" quality
- Final filtering uses both: must pass news-check AND wow-threshold AND filter-threshold

**Alternatives considered**:
- Single combined score: Rejected because it conflates two different quality dimensions
- Post-filter wow evaluation: Rejected because it would require additional API calls

### Decision 2: Content Type Storage

**Decision**: Add `content_type` as a string column on Article model (already computed but not persisted).

**Rationale**:
- Current system computes content_type but doesn't persist it
- Persisting enables admin filtering, analytics, and debugging
- String enum with constrained values: news_article, event_listing, directory_page, about_page, other_non_news

**Alternatives considered**:
- PostgreSQL enum type: Rejected for migration complexity
- Not storing: Rejected because it prevents admin visibility and debugging

### Decision 3: Wow Factor Threshold

**Decision**: Default wow_score threshold of 0.4 (configurable via environment variable).

**Rationale**:
- Lower than filter_score threshold (0.5) because wow-factor is more subjective
- Allows borderline-interesting stories through while rejecting clearly mundane content
- Configurable allows John to tune based on feedback

**Alternatives considered**:
- Same threshold as filter_score (0.5): Rejected as potentially too aggressive initially
- No threshold (informational only): Rejected because it doesn't solve the "terrible stories" problem

### Decision 4: Prompt Enhancement Strategy

**Decision**: Add "WOW FACTOR EVALUATION" section to existing system prompt template.

**Rationale**:
- Minimal change to existing prompt structure
- Clear separation between news-check, wow-check, and editorial-check
- Explicit criteria for Claude to evaluate: surprising, delightful, unusual

**Alternatives considered**:
- Separate API call for wow evaluation: Rejected for cost
- Rewrite entire prompt: Rejected for risk and unnecessary scope

---

## Phase 1: Design

### Data Model Changes

See [data-model.md](data-model.md) for complete schema.

**Summary**: Two new columns on Article table:
- `content_type`: String, nullable, stores classification result
- `wow_score`: Float, nullable, stores wow-factor score (0.0-1.0)

### API Contract Changes

No external API changes. Internal Claude prompt schema enhanced:

```json
{
  "properties": {
    "results": {
      "items": {
        "properties": {
          "index": {"type": "integer"},
          "content_type": {"type": "string", "enum": [...]},
          "wow_score": {"type": "number"},  // NEW
          "wow_notes": {"type": "string"},  // NEW
          "topics": {"type": "array"},
          "filter_score": {"type": "number"},
          "summary": {"type": "string"},
          "amish_angle": {"type": "string"},
          "filter_notes": {"type": "string"}
        }
      }
    }
  }
}
```

### Implementation Quickstart

See [quickstart.md](quickstart.md) for step-by-step implementation guide.

---

## Phase 2: Tasks

Tasks will be generated by `/speckit.tasks` command. Key work areas:

1. **Schema Migration**: Add content_type and wow_score columns
2. **Prompt Enhancement**: Add WOW FACTOR EVALUATION section to claude_filter.py
3. **Schema Update**: Add wow_score and wow_notes to ARTICLE_RESULT_SCHEMA
4. **Filtering Logic**: Update filter_all_articles to apply wow_score threshold
5. **Filter Notes**: Enhance rejection reason formatting
6. **Testing**: Contract test for new schema, integration test for quality gating
