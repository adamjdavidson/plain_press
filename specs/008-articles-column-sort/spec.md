# Feature Specification: Sortable Article Columns

**Feature Branch**: `008-articles-column-sort`  
**Created**: 2025-11-29  
**Status**: Draft  
**Input**: User description: "On the /admin/articles page I want to be able to sort by column heading, especially 'date' to identify more recent or older articles."

**Constitution Check**: Aligns with Single-User Simplicity (helps John quickly find articles by date or other criteria) and pragmatic approach (standard table sorting pattern).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sort by Date (Priority: P1)

John wants to find the most recently added articles to review what came in today, or find older articles that may have been missed. He clicks on the "Added" column header to sort articles by date.

**Why this priority**: This is the explicitly requested use case - date sorting is the primary need.

**Independent Test**: Visit `/admin/articles`, click "Added" column header, verify articles reorder by date (newest first), click again to reverse (oldest first).

**Acceptance Scenarios**:

1. **Given** John is viewing the articles page, **When** he clicks the "Added" column header, **Then** articles are sorted by date with newest first, and a visual indicator shows the sort direction.

2. **Given** articles are sorted by date (newest first), **When** John clicks the "Added" header again, **Then** articles are sorted with oldest first, and the indicator updates to show descending order.

---

### User Story 2 - Sort by Score (Priority: P2)

John wants to review articles by filter score to focus on high-scoring candidates or investigate low-scoring rejections.

**Why this priority**: Score is a key metric for understanding filter quality and finding good candidates.

**Independent Test**: Click "Score" header, verify articles sort by score (highest first), click again to reverse.

**Acceptance Scenarios**:

1. **Given** John is viewing the articles page, **When** he clicks the "Score" column header, **Then** articles are sorted by filter score with highest first.

---

### User Story 3 - Sort by Status (Priority: P3)

John wants to group articles by status to focus on pending items or review rejected ones.

**Why this priority**: Status grouping helps focus workflow on actionable items.

**Independent Test**: Click "Status" header, verify articles group by status alphabetically.

**Acceptance Scenarios**:

1. **Given** John is viewing the articles page, **When** he clicks the "Status" column header, **Then** articles are sorted alphabetically by status.

---

### User Story 4 - Sort by Source (Priority: P4)

John wants to see which sources are producing the most articles or review articles from a specific source.

**Why this priority**: Convenience feature for source analysis.

**Independent Test**: Click "Source" header, verify articles sort alphabetically by source name.

**Acceptance Scenarios**:

1. **Given** John is viewing the articles page, **When** he clicks the "Source" column header, **Then** articles are sorted alphabetically by source name.

---

### Edge Cases

- What happens when sorting with filters applied? Sort should work within filtered results.
- What happens when sorting with pagination? Sort applies to full dataset, pagination shows sorted results.
- What happens when column has null/empty values? Empty values should sort to the end.
- What happens when clicking a different column? Previous sort is replaced with new sort.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow sorting by clicking column headers for: Added (date), Score, Status, Source, Headline.
- **FR-002**: System MUST display a visual indicator (arrow or similar) showing current sort column and direction.
- **FR-003**: Clicking a sorted column header MUST toggle between ascending and descending order.
- **FR-004**: Clicking a different column header MUST sort by that column (defaulting to a sensible direction for that data type).
- **FR-005**: Sorting MUST work in combination with existing filters (status filter, search).
- **FR-006**: Sorting MUST persist across pagination (all pages show sorted results).
- **FR-007**: Default sort on page load MUST be by date (newest first) to show recent articles.

### Non-Sortable Columns

The following columns should NOT be sortable:
- Checkbox column (selection)
- Topics (array values, not meaningful to sort)
- Filter Notes (long text, not meaningful to sort)
- Actions (buttons)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: John can sort articles by date in under 1 second (single click, immediate visual feedback).
- **SC-002**: Sort direction is visually clear at all times (indicator visible on sorted column).
- **SC-003**: Sorting works correctly with any combination of filters applied.
- **SC-004**: Page load defaults to showing newest articles first.

## Assumptions

- Sorting is performed server-side for consistency with pagination.
- Sort state is maintained via URL parameters (e.g., `?sort=discovered_date&dir=desc`).
- No client-side JavaScript sorting required - standard page reload pattern is acceptable.
- Only single-column sorting is needed (not multi-column).
- Reasonable performance expected (under 1 second) for the typical article volume (~1,000-2,000 articles).
