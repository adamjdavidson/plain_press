# Feature Specification: Database Schema Foundation

**Feature Branch**: `001-database-schema`  
**Created**: 2025-11-26  
**Status**: Draft  
**Input**: User description: "Define SQLAlchemy models for Article, Source, FilterRule, Feedback, EmailBatch, DeepDive, RefinementLog with proper relationships and indexes"

**Constitution Check**: This feature aligns with `.specify/memory/constitution.md` principles:
- **Single-User Simplicity**: Data model supports one editor workflow, no multi-tenancy
- **Reliability Over Performance**: Focus on data integrity, proper relationships, and indexes for essential queries
- **Cost Discipline**: PostgreSQL on Railway stays within budget; proper indexing prevents expensive queries

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Store and Retrieve Article Candidates (Priority: P1)

The system must persistently store every article candidate discovered during the daily search process, including its source information, AI-generated filtering assessment, and current status in the workflow. John's workflow depends on this data being reliably available across multiple interactions (email review, feedback submission, deep dive generation).

**Why this priority**: This is the foundation for all other features. Without persistent article storage, the system cannot track what has been sent to John, what he's rated, or generate historical reports. Blocks all downstream features.

**Independent Test**: Can be fully tested by inserting article records with various statuses and querying them back. Validates data persistence, uniqueness constraints (no duplicate URLs), and status transitions.

**Acceptance Scenarios**:

1. **Given** no existing articles, **When** the system discovers a new article from RSS feed, **Then** it stores the article with status "pending", unique URL constraint, source reference, filter score, and timestamps
2. **Given** an article already exists with a specific URL, **When** the system encounters the same URL again, **Then** it rejects the duplicate and returns the existing record
3. **Given** 100 pending articles, **When** querying for articles to include in daily email, **Then** system returns top 50 by filter score with all required fields populated in under 1 second
4. **Given** an article in "pending" status, **When** it's included in daily email, **Then** status updates to "emailed" and email_batch_id is set correctly

---

### User Story 2 - Track John's Feedback Over Time (Priority: P1)

The system must store every rating decision John makes (Good/No/Why Not), including optional explanatory notes, linked to the specific article. This feedback history enables weekly pattern analysis and long-term learning about John's preferences.

**Why this priority**: Feedback storage is critical for the learning loop (Principle III: Learning Over Time). Without persistent feedback, the system cannot improve filtering rules or analyze rejection patterns. Required for weekly refinement feature.

**Independent Test**: Can be fully tested by creating feedback records linked to articles and querying for patterns (e.g., "all Why Not rejections in the past 7 days with notes containing 'technology'").

**Acceptance Scenarios**:

1. **Given** an article in "emailed" status, **When** John clicks "Good", **Then** system creates feedback record with rating="good", updates article status to "good", and stores timestamp
2. **Given** an article in "emailed" status, **When** John clicks "Why Not" and submits explanation, **Then** system creates feedback with rating="why_not", stores notes text, updates article to "rejected"
3. **Given** feedback exists for an article, **When** attempting to create second feedback for same article, **Then** system prevents duplicate and returns error (one feedback per article rule)
4. **Given** 30 days of feedback history, **When** querying for rejection patterns, **Then** system groups by common phrases in notes and returns counts in under 2 seconds

---

### User Story 3 - Monitor Source Quality and Trust (Priority: P2)

The system must track which sources (RSS feeds, Exa search queries) produce articles, calculate approval rates over time, and support source prioritization decisions. This enables the system to learn which sources consistently produce articles John approves.

**Why this priority**: Source trust scoring is essential for Volume Over Precision (Principle II). By tracking source performance, the system can weight higher-quality sources more heavily, improving the 40-60 candidate mix quality without sacrificing volume.

**Independent Test**: Can be fully tested by creating sources, linking articles to them, adding feedback, and verifying trust score calculations match expected formulas (approved / (approved + rejected), with minimum 10 samples required).

**Acceptance Scenarios**:

1. **Given** a new source is added, **When** querying source list, **Then** it has trust_score=0.5 (default for insufficient data), total_surfaced=0, is_active=true
2. **Given** a source has 5 approved and 15 rejected articles, **When** calculating trust score, **Then** trust_score = 5/(5+15) = 0.25
3. **Given** a source has 3 approved and 2 rejected articles (total < 10), **When** calculating trust score, **Then** trust_score remains 0.5 (insufficient data for reliable score)
4. **Given** 20 active sources, **When** querying for daily search sources, **Then** system returns only is_active=true sources ordered by trust_score DESC in under 500ms

---

### User Story 4 - Maintain and Query Filter Rules (Priority: P2)

The system must store the current editorial criteria (must_have, must_avoid, good_topic, borderline) used by AI to evaluate article candidates. Rules must be queryable, updatable, and track their origin (original criteria, learned from feedback, or manually added by John).

**Why this priority**: Filter rules are the heart of article selection. They must be persistent, transparent (Principle V: Transparency in Filtering), and evolvable based on feedback. Without proper rule storage, the system cannot learn or allow John to customize filtering.

**Independent Test**: Can be fully tested by creating filter rules of different types, querying active rules for AI filtering, updating rules, and verifying rule priority ordering.

**Acceptance Scenarios**:

1. **Given** initial system setup, **When** loading filter rules, **Then** system has all rules from story_criteria.md stored with source="original", is_active=true, and proper priority ordering
2. **Given** weekly refinement suggests new rule, **When** rule is added, **Then** it's stored with source="learned", learned_from_count>0, unique priority, and is_active=true
3. **Given** John manually adds a rule via interface, **When** rule is created, **Then** it's stored with source="manual", highest priority, and is_active=true
4. **Given** 30 filter rules exist, **When** querying for active rules to pass to AI, **Then** system returns only is_active=true rules ordered by priority ASC in under 200ms

---

### User Story 5 - Log Email Deliveries and Deep Dive Reports (Priority: P3)

The system must maintain records of daily emails sent (batch tracking) and deep dive reports generated for approved articles, including Google Doc IDs and Sheet row references. This enables debugging email delivery issues and tracking the complete article lifecycle.

**Why this priority**: Email batch and deep dive logging are important for reliability (Principle VI: Reliability Over Performance) and debugging, but not blocking for MVP. System can function without historical email logs, but logging enables troubleshooting failed sends and tracking which reports were generated.

**Independent Test**: Can be fully tested by creating email batch records and deep dive records, verifying links to articles, and querying delivery history.

**Acceptance Scenarios**:

1. **Given** daily job completes successfully, **When** email is sent, **Then** EmailBatch record created with sent_at timestamp, recipient list, article_count=50, status="sent"
2. **Given** daily job fails to send email, **When** SendGrid returns error, **Then** EmailBatch record created with status="failed", error_message populated with details
3. **Given** John approves an article, **When** deep dive is generated, **Then** DeepDive record created with full_report_text, google_doc_id, google_doc_url, generated_at timestamp
4. **Given** past 30 days of email batches, **When** querying for delivery success rate, **Then** system calculates (sent / (sent + failed)) in under 1 second

---

### User Story 6 - Store Weekly Refinement Analysis (Priority: P3)

The system must persist weekly refinement analysis results, including suggested rule changes and John's acceptance decisions. This creates an audit trail of how filtering criteria evolve over time based on feedback patterns.

**Why this priority**: Refinement logging is valuable for transparency and understanding system evolution, but not critical for MVP functionality. The weekly refinement job can run without storing historical logs, but persistence enables John to review past suggestions and understand why rules changed.

**Independent Test**: Can be fully tested by creating RefinementLog records with suggestion structures, querying by week range, and verifying JSON structure matches expected format.

**Acceptance Scenarios**:

1. **Given** weekly refinement job analyzes feedback, **When** analysis completes, **Then** RefinementLog created with week_start, week_end, article counts (total_good, total_no, total_why_not), suggestions JSON array
2. **Given** refinement log has 3 suggestions (2 accepted, 1 rejected), **When** John reviews and accepts some, **Then** accepted_suggestions JSON updated with accepted items
3. **Given** past 12 weeks of refinement logs, **When** querying for trend analysis, **Then** system returns all logs ordered by week_start DESC in under 1 second
4. **Given** refinement log with suggestion type="add_rule", **When** John accepts suggestion, **Then** new FilterRule created referencing the refinement log that generated it

---

### Edge Cases

- **What happens when an article URL changes slightly** (e.g., tracking parameters added)? URL normalization should occur before uniqueness check to prevent functional duplicates
- **What happens when a source is deactivated but has existing articles**? Articles remain in database with source_id reference intact; source.is_active=false prevents future searches but preserves historical data
- **What happens when feedback notes contain very long text** (>10,000 characters)? System should accept but log warning; database field TEXT type has no practical limit in PostgreSQL
- **What happens when deep dive generation fails but article is already marked "good"**? Article status remains "good", but DeepDive record not created; retry mechanism should attempt regeneration
- **What happens when two emails are sent on same day** (manual re-run)? Each creates separate EmailBatch record; articles can reference only one batch (most recent), no uniqueness constraint on date
- **What happens when calculating trust score for source with 0 total interactions**? Division by zero prevented by checking (total_approved + total_rejected) >= 10 threshold; default to 0.5
- **What happens when querying articles with NULL filter_score**? Should not occur (filter_score required during discovery), but queries should treat NULL as 0.0 for sorting safety

## Requirements *(mandatory)*

### Functional Requirements

**Data Persistence**

- **FR-001**: System MUST persist all article candidates discovered, including URL, headline, source reference, summary, filter score, and status
- **FR-002**: System MUST enforce unique constraint on article.external_url to prevent duplicate processing
- **FR-003**: System MUST automatically set created_at and updated_at timestamps for all entities on creation and modification
- **FR-004**: System MUST support article status transitions: pending → emailed → (good | rejected | passed)

**Data Relationships**

- **FR-005**: System MUST link each article to its originating source via foreign key relationship
- **FR-006**: System MUST link each article to its email batch (if emailed) via foreign key relationship
- **FR-007**: System MUST enforce one-to-one relationship between article and feedback (one feedback record per article maximum)
- **FR-008**: System MUST enforce one-to-one relationship between article and deep dive report (if article status is "good")

**Data Integrity**

- **FR-009**: System MUST prevent deletion of source records that have associated articles (maintain referential integrity)
- **FR-010**: System MUST cascade article status updates when feedback is created (feedback creation updates article.status atomically)
- **FR-011**: System MUST validate enum values for article.status, feedback.rating, source.type, filterrule.rule_type, filterrule.source
- **FR-012**: System MUST validate that filter_score is between 0.0 and 1.0 inclusive

**Data Retrieval Performance**

- **FR-013**: System MUST provide index on articles.external_url for O(log n) uniqueness checks during discovery
- **FR-014**: System MUST provide index on articles.status for efficient filtering of pending/emailed articles
- **FR-015**: System MUST provide composite index on (articles.status, articles.filter_score DESC, articles.discovered_date DESC) for daily email candidate queries
- **FR-016**: System MUST provide index on feedback.clicked_at for weekly refinement queries over date ranges
- **FR-017**: System MUST provide index on sources.is_active for daily job source filtering

**Data Calculations**

- **FR-018**: System MUST support calculation of source.trust_score = total_approved / (total_approved + total_rejected) when total >= 10, else default to 0.5
- **FR-019**: System MUST support querying feedback patterns grouped by common phrases in notes field
- **FR-020**: System MUST support counting articles by status, source, and date ranges for reporting

**Data Structures**

- **FR-021**: System MUST store DeepDive.additional_sources as structured data (array of objects with url, title, description)
- **FR-022**: System MUST store RefinementLog.suggestions as structured data (array of suggestion objects with type, rule_text, evidence, accepted fields)
- **FR-023**: System MUST store EmailBatch.recipient_emails as array of email address strings

**Data Retention**

- **FR-024**: System MUST retain all articles indefinitely (no automatic deletion)
- **FR-025**: System MUST retain all feedback records indefinitely (essential for learning)
- **FR-026**: System MUST retain filter rules with is_active=false (preserve rule history even when deactivated)

### Key Entities *(include if feature involves data)*

- **Article**: Represents a news story candidate with lifecycle tracking (pending → emailed → rated). Includes URL, headline, source reference, AI-generated summary/angle, filter score, email batch reference, Google Doc ID (if approved), status, and timestamps.

- **Source**: Represents an RSS feed or Exa search query that produces articles. Tracks source type (rss/search_query/manual), trust score based on approval rate, cumulative statistics (total surfaced/approved/rejected), active status, and last fetch timestamp.

- **Feedback**: Represents John's rating decision on an emailed article. One-to-one with Article. Includes rating (good/no/why_not), optional explanatory notes (required for why_not), and clicked timestamp.

- **FilterRule**: Represents an editorial criterion used by AI to evaluate articles. Includes rule type (must_have/must_avoid/good_topic/borderline), rule text, priority ordering, active status, origin (original/learned/manual), and count of feedback items that informed the rule.

- **EmailBatch**: Represents a single daily email delivery. Tracks sent timestamp, recipient list, article count, subject line, delivery status (sent/failed), and error details if failed.

- **DeepDive**: Represents a detailed research report generated for an approved article. One-to-one with Article. Includes headline suggestion, key points, additional sources (structured), full report text, Google Doc ID/URL, Sheet row reference, generation timestamp, and email send timestamp.

- **RefinementLog**: Represents weekly feedback analysis results. Tracks week range, article rating counts, structured suggestions array (proposed rule changes with evidence), and accepted suggestions subset. Creates audit trail of rule evolution.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System can store and retrieve 10,000 articles with all relationships intact in under 5 seconds for any filtered query
- **SC-002**: Daily email candidate query (top 50 pending articles by filter score) completes in under 1 second even with 50,000 articles in database
- **SC-003**: Weekly refinement analysis queries (all feedback from past 7 days) complete in under 2 seconds
- **SC-004**: Source trust score calculations for 50 sources complete in under 500 milliseconds
- **SC-005**: Database enforces 100% of uniqueness constraints (zero duplicate article URLs stored)
- **SC-006**: Database enforces 100% of referential integrity constraints (no orphaned records, no dangling foreign keys)
- **SC-007**: All enum field validations reject invalid values with clear error messages
- **SC-008**: System supports concurrent writes for feedback submission (10 simultaneous clicks) without data corruption
- **SC-009**: Database schema supports all queries needed for daily job, feedback processing, and weekly refinement without requiring schema changes
- **SC-010**: Data model can be fully restored from backups and validated for integrity in under 10 minutes

## Assumptions

- **Database Technology**: PostgreSQL is used as the underlying database (specified in CLAUDE.md tech stack)
- **Database Hosting**: Database runs on Railway alongside application (single hosting platform for simplicity and cost)
- **Connection Pooling**: Application uses connection pooling to manage database connections efficiently
- **Migration Strategy**: Schema changes handled via Alembic migrations (standard SQLAlchemy migration tool)
- **Backup Strategy**: Railway provides automated daily backups; no custom backup implementation needed for MVP
- **UUID Primary Keys**: All entities use UUID primary keys (better for distributed systems, no sequence contention)
- **Timestamp Timezone**: All timestamps stored in UTC; conversion to EST handled at application layer
- **Text Field Sizing**: TEXT type used for unlimited length fields (notes, reports); VARCHAR(500) for constrained fields (headlines, URLs)
- **JSON Storage**: JSONB type used for structured data (additional_sources, suggestions) enabling efficient querying
- **Default Values**: Boolean fields default to appropriate values (is_active=true, status="pending") reducing application logic
