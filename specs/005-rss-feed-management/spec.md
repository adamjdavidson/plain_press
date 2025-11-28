# Feature Specification: RSS Feed Management

**Feature Branch**: `005-rss-feed-management`  
**Created**: 2025-11-28  
**Status**: Draft  
**Input**: User description: "I want to be able to easily add RSS feeds through the admin page or through some other page. Is there a way to create a simple site where you can paste in an RSS feed and it's automatically added to sources? Similarly, I'd like to be able to see all the existing RSS feeds and delete or pause them one by one."

**Constitution Check**: This feature aligns with Single-User Simplicity (provides a straightforward interface for the editor to manage feeds) and Cost Discipline (no external service dependencies required).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add New RSS Feed (Priority: P1)

The editor discovers a new website with interesting content and wants to add it as a source. They navigate to the RSS feed management page, paste the RSS feed URL, give it a name, and submit. The system validates the URL is a valid RSS feed and adds it to the active sources.

**Why this priority**: Adding new content sources is the core function that enables the discovery pipeline to find new articles. Without this, the system cannot grow its source base.

**Independent Test**: Can be fully tested by adding a single new RSS feed URL and verifying it appears in the sources list and is fetched in the next pipeline run.

**Acceptance Scenarios**:

1. **Given** the editor is on the RSS feed management page, **When** they enter a valid RSS feed URL and name and click "Add Feed", **Then** the feed is saved to the database as an active source
2. **Given** the editor enters a URL that is not a valid RSS feed, **When** they click "Add Feed", **Then** an error message explains the URL is not a valid RSS feed
3. **Given** the editor enters a feed URL that already exists, **When** they click "Add Feed", **Then** an error message indicates the feed already exists

---

### User Story 2 - View All RSS Feeds (Priority: P1)

The editor wants to see all configured RSS feeds to understand what sources are being monitored. They navigate to the RSS feed management page and see a list of all feeds with their status, performance metrics, and last fetch time.

**Why this priority**: Visibility into existing feeds is essential for managing the source ecosystem and understanding where articles come from.

**Independent Test**: Can be fully tested by loading the RSS management page and verifying all database sources are displayed with their key information.

**Acceptance Scenarios**:

1. **Given** there are RSS sources in the database, **When** the editor visits the feed management page, **Then** all RSS feeds are displayed in a list
2. **Given** the editor is viewing the feed list, **When** they look at any feed, **Then** they can see the feed name, URL, active/paused status, trust score, total articles surfaced, and last fetch time

---

### User Story 3 - Pause/Resume RSS Feed (Priority: P2)

The editor notices a source is producing low-quality articles and wants to temporarily disable it without losing its configuration and history. They click "Pause" next to the feed, and it stops being fetched. Later, they can resume it.

**Why this priority**: Pausing provides a non-destructive way to manage problematic sources while preserving the option to re-enable them.

**Independent Test**: Can be fully tested by pausing a feed, running the pipeline, verifying the feed is skipped, then resuming and verifying it is fetched again.

**Acceptance Scenarios**:

1. **Given** an active RSS feed in the list, **When** the editor clicks "Pause", **Then** the feed status changes to paused and shows as inactive
2. **Given** a paused RSS feed, **When** the daily pipeline runs, **Then** the paused feed is not fetched
3. **Given** a paused RSS feed in the list, **When** the editor clicks "Resume", **Then** the feed becomes active again

---

### User Story 4 - Delete RSS Feed (Priority: P3)

The editor determines a source is permanently unsuitable and wants to remove it entirely. They click "Delete" next to the feed and confirm the action. The feed is removed from the system.

**Why this priority**: Deletion is lower priority because pausing achieves most use cases. Deletion is needed for cleanup and removing test sources.

**Independent Test**: Can be fully tested by deleting a feed and verifying it no longer appears in the list or database.

**Acceptance Scenarios**:

1. **Given** an RSS feed in the list, **When** the editor clicks "Delete", **Then** a confirmation dialog appears asking for confirmation
2. **Given** the confirmation dialog is shown, **When** the editor confirms deletion, **Then** the feed is removed from the database
3. **Given** a deleted feed, **When** the feed list is viewed, **Then** the deleted feed no longer appears

---

### Edge Cases

- What happens when an RSS feed URL becomes invalid after being added? (Feed remains in system, marked with fetch errors)
- How does system handle feeds with no articles? (Display shows 0 articles surfaced, no special handling needed)
- What happens to articles already fetched from a deleted source? (Articles remain in database with source_name preserved; source_id becomes orphaned but articles are not deleted)
- What if the user tries to add a URL that redirects to an RSS feed? (System follows redirects and validates the final content)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a dedicated page for managing RSS feed sources
- **FR-002**: System MUST allow adding a new RSS feed by providing a URL and name
- **FR-003**: System MUST validate that submitted URLs are valid RSS/Atom feeds before saving
- **FR-004**: System MUST display all RSS sources in a list with: name, URL, active status, trust score, articles surfaced, last fetch time
- **FR-005**: System MUST allow pausing an active feed (sets is_active to false)
- **FR-006**: System MUST allow resuming a paused feed (sets is_active to true)
- **FR-007**: System MUST allow deleting a feed with confirmation
- **FR-008**: System MUST prevent duplicate feeds (same URL cannot be added twice)
- **FR-009**: System MUST show error messages for invalid inputs (bad URL, duplicate, validation failure)
- **FR-010**: New feeds MUST be created with default trust_score of 0.5 and is_active set to true

### Key Entities *(include if feature involves data)*

- **Source**: Existing entity - RSS feeds are stored as Source records with type=RSS. Key fields: id, name, type, url, is_active, trust_score, total_surfaced, total_approved, total_rejected, last_fetched, notes

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Editor can add a new RSS feed in under 30 seconds
- **SC-002**: Editor can locate and pause/resume any feed in under 10 seconds
- **SC-003**: Feed list loads and displays all sources within 2 seconds
- **SC-004**: 100% of invalid RSS URLs are rejected with clear error messages
- **SC-005**: No accidental deletions occur (confirmation required for destructive actions)
- **SC-006**: All feed management operations persist correctly to the database

## Assumptions

- The existing Source model and database schema supports all needed fields (confirmed: name, type, url, is_active, trust_score, etc.)
- RSS feed validation can be performed by attempting to parse the feed using the existing feedparser library
- The page will be accessible via the existing admin route structure (e.g., /admin/sources)
- No authentication is required beyond what exists (single-user system)
- Default trust_score for new sources is 0.5 (matches existing behavior)
- Articles from deleted sources are retained (source_name is stored on articles)
