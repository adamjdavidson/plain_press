<!--
  Constitution Sync Impact Report
  ===============================
  Version: 1.0.0 (Initial ratification)
  Changed Principles: N/A (initial version)
  Added Sections: All sections (initial constitution)
  Removed Sections: None
  
  Templates Requiring Updates:
  ✅ plan-template.md - Constitution Check placeholder already present
  ✅ spec-template.md - User story format aligns with single-user principle
  ✅ tasks-template.md - Test-optional approach aligns with pragmatism principle
  ✅ agent-file-template.md - Compatible with constitution principles
  
  Follow-up TODOs: None
-->

# Amish News Finder Constitution

## Core Principles

### I. Single-User Simplicity (NON-NEGOTIABLE)

This system serves **one person: John Lapp**. Every decision must pass the single-user test: does this help John's workflow, or does it add complexity for theoretical future users?

**Rules**:
- No multi-tenancy, no user management, no permissions system beyond basic auth
- No dashboards, analytics, or complex UIs—John needs one email per day and three buttons per article
- No feature exists unless John explicitly needs it for his current workflow
- All interfaces designed for editor productivity, not end-reader experience

**Rationale**: Premature abstraction for hypothetical users wastes resources and obscures the real problem. Build exactly what John needs, nothing more.

### II. Volume Over Precision

John wants **50 article candidates per day** (~1,500/month) to select his final **20 articles per month** (1.3% selection rate). The system optimizes for recall over precision—better to surface borderline candidates than to hide potentially good stories.

**Rules**:
- AI filtering must err toward inclusion; false positives are acceptable, false negatives are costly
- No aggressive filtering that might eliminate surprising-but-valid content
- Target: 40-60 candidates per day (tolerance band to avoid overwhelming or underwhelming John)
- Candidate quality measured by John's "Good" rate over time, not by confidence scores

**Rationale**: John can quickly reject poor candidates (seconds per article), but he cannot review stories the system never showed him. Abundance creates choice.

### III. Learning Over Time, Not Real-Time

John's feedback improves the system through **weekly refinement**, not instant adjustments. This prevents chasing noise from individual bad days and focuses on durable patterns.

**Rules**:
- Feedback analysis runs weekly (Sunday cron job)
- Refinements require pattern detection (3+ similar rejections before rule adjustment)
- All rule changes logged with rationale in `RefinementLog` table
- John can manually override rules at any time via simple interface

**Rationale**: Real-time learning risks overfitting to outliers. Weekly batching filters noise, surfaces real trends, and keeps the system predictable.

### IV. Pragmatic Testing

Tests exist to **prevent regressions and validate contracts**, not to achieve coverage metrics. Test what breaks, not what's obvious.

**Rules**:
- Contract tests REQUIRED for all API integrations (Exa, Claude, SendGrid, Google APIs)
- Integration tests REQUIRED for core workflows (daily job, feedback processing, deep dive generation)
- Unit tests OPTIONAL—write only when complexity justifies (e.g., criteria parsing, scoring logic)
- No test-first dogma: prototype freely, add tests once patterns stabilize

**Rationale**: This is a single-user productivity tool with clear workflows. Over-testing slows development without meaningful safety gains. Test the boundaries where things break (external APIs, data transforms, scheduled jobs), not trivial getters.

### V. Cost Discipline

Monthly operational costs MUST stay **under $50**. This constraint drives architectural decisions toward simplicity and away from expensive abstractions.

**Budget Breakdown** (estimated):
- Railway hosting: $10-15/month
- Claude API (Haiku filtering + Sonnet deep dives): $15-25/month
- Exa API: $5-10/month
- SendGrid: Free tier (sufficient for <1 email/day)
- Google APIs: Free tier

**Rules**:
- Use Haiku for filtering (cheap, fast), reserve Sonnet for deep dives only
- No unnecessary database queries; cache aggressively where appropriate
- Monitor API costs weekly; alert if approaching $50
- No premium services or add-ons without explicit cost justification

**Rationale**: John's budget is fixed. If a feature costs money, it must deliver proportional value. Cost discipline prevents feature creep.

### VI. Reliability Over Performance

A **delayed email is acceptable**; a **lost email is not**. The system prioritizes durability and correctness over speed.

### VII. Temporal Accuracy (NON-NEGOTIABLE)

This is a **live production system** that runs daily. All date-dependent logic must use **current dates dynamically**.

**Rules**:
- Never hardcode years in search queries, filters, or any time-based logic
- Search queries must dynamically calculate the current year at runtime
- All development sessions must verify date references are current
- Sources/queries in config files should NOT include year strings—year is injected at runtime

**Rationale**: Hardcoded dates cause the system to search for stale content, resulting in low-quality or zero results. A news finder that searches for "2024" news in 2025 is fundamentally broken.

**Rules**:
- Daily job retries on failure (3 attempts with exponential backoff)
- All state persisted to database before external actions (email, Google Docs)
- Idempotency keys for all external API calls
- Error notifications sent to John's email when critical jobs fail

**Performance Standards** (adequate, not aggressive):
- Daily job completes within 30 minutes (no hard requirement for sub-second responses)
- Button clicks (Good/No/Why Not) respond within 5 seconds
- Deep dive report generation completes within 2 minutes

**Rationale**: John checks email once per morning. A 10-minute delay is invisible; missing an email or losing a "Good" click wastes hours of work. Build for correctness first.

## Development Workflow

### Code Organization

**Structure**:
```
app/
  models.py            # SQLAlchemy models
  routes.py            # Flask routes
  services/
    search.py          # Exa + RSS fetching
    filter.py          # Claude filtering
    email.py           # SendGrid integration
    deep_dive.py       # Report generation
    google.py          # Drive/Sheets/Docs
    refinement.py      # Weekly feedback analysis

scripts/
  daily_job.py         # 8am EST cron
  weekly_refinement.py # Sunday cron

tests/
  contract/            # API integration tests
  integration/         # Workflow tests
```

**Rules**:
- Services remain stateless and testable in isolation
- Models contain only data definitions (no business logic)
- Routes remain thin adapters (delegate to services)
- Scripts orchestrate services but contain no core logic

### Feature Development Process

1. **Spec Phase**: Document user need in `/specs/###-feature/spec.md` using `/speckit.spec`
2. **Plan Phase**: Technical design in `plan.md` using `/speckit.plan`
3. **Constitution Check**: Verify feature aligns with principles (especially Single-User Simplicity, Cost Discipline)
4. **Implementation**: Follow tasks from `/speckit.tasks` if needed, or proceed directly for small changes
5. **Manual Testing**: Validate with John's real workflow (send test email, click buttons, check Google Docs)
6. **Deploy**: Railway auto-deploys from main branch

### Testing Requirements

**REQUIRED**:
- Contract tests for external APIs (detect breaking changes early)
- Integration tests for daily job, feedback loop, deep dive generation
- Manual validation with John before deploying changes to email templates or filtering logic

**OPTIONAL**:
- Unit tests (add only when logic complexity justifies)
- Performance tests (not needed unless job times exceed 30 minutes)

## Editorial Alignment

### Story Criteria

The system filters for stories that are **wholesome, surprising, and relatable** at an 8th-grade reading level.

**Must Include**:
- Animals, food oddities, community efforts, nature, small-town traditions
- Positive, uplifting, or humorous content
- Stories that provoke "well, I'll be!" reactions

**Must Avoid**:
- Individual hero/achievement stories (conflicts with Amish humility values)
- Modern technology, death/tragedy, violence, politics, military
- Content requiring context beyond Plain News readers' experience

**Reference**: See `an_story_criteria.md` for full editorial guidelines. FilterRule table mirrors these criteria.

**Constitution Rule**: Any changes to editorial criteria MUST be validated with John before deploying. AI models follow John's judgment, not vice versa.

## Governance

### Amendment Process

1. **Proposal**: Document proposed change with rationale (why current principle blocks progress)
2. **Impact Analysis**: Identify affected code, tests, and workflows
3. **Version Bump**:
   - **MAJOR**: Removing or fundamentally redefining a principle (e.g., dropping Single-User Simplicity to add multi-tenancy)
   - **MINOR**: Adding new principle or expanding guidance (e.g., new security requirements)
   - **PATCH**: Clarifications, wording fixes, non-semantic updates
4. **Propagation**: Update related templates, docs, and agent guidance files
5. **Approval**: Document amendment in this file with updated version and date

### Compliance

- All `/speckit.plan` outputs include **Constitution Check** section
- Plan phase MUST document any principle violations with explicit justification
- Code reviews verify alignment with Single-User Simplicity and Cost Discipline
- Weekly cost review ensures budget remains under $50/month

### Development Guidance

For runtime development context, see:
- `CLAUDE.md` - Project overview, tech stack, architecture, data flow
- `an_story_criteria.md` - Editorial guidelines for filtering logic
- `/specs/###-feature/` - Feature-specific design docs

**Version**: 1.0.0 | **Ratified**: 2025-11-26 | **Last Amended**: 2025-11-26
