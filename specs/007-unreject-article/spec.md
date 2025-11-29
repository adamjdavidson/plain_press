# Feature Specification: Unreject Article Button

**Feature Branch**: `007-unreject-article`  
**Created**: 2025-11-29  
**Status**: Draft  
**Input**: User description: "on the /admin/filter-runs site I'd like buttons that allow me to un-reject something from any of the filters. It should be a simple button that automatically turns the article into pending. And can be attached to any news item."

**Constitution Check**: Aligns with Single-User Simplicity (John can quickly override filter decisions) and Volume Over Precision (catch false negatives by allowing manual overrides).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Override Filter Rejection from Rejection Analysis (Priority: P1)

John is reviewing the rejection analysis page for a pipeline run and notices an article that was incorrectly rejected. He wants to quickly rescue this article and add it back to the candidate pool without navigating elsewhere.

**Why this priority**: This is the primary use case - John will be reviewing rejections to tune filters and will frequently spot false negatives that need rescuing.

**Independent Test**: Visit `/admin/filter-runs/<run_id>/rejections/<filter_name>`, click "Unreject" on any article, verify article status changes to pending.

**Acceptance Scenarios**:

1. **Given** John is viewing the rejection analysis page for "news_check" filter, **When** he clicks the "Unreject" button next to a rejected article, **Then** the article's status changes to "pending" and filter_status changes to "passed", and the button changes to indicate success.

2. **Given** John has clicked "Unreject" on an article, **When** he navigates to `/admin/articles`, **Then** the article appears with status "pending" and is available for email selection.

---

### User Story 2 - Override Filter Rejection from Article Journey (Priority: P2)

John is examining an individual article's journey through the filters and realizes it was incorrectly rejected at one stage. He wants to override the decision from this detailed view.

**Why this priority**: Article journey view provides full context about why an article was rejected, making it a natural place to make override decisions.

**Independent Test**: Visit `/admin/filter-runs/<run_id>/article/<url>`, click "Unreject" button, verify article becomes pending.

**Acceptance Scenarios**:

1. **Given** John is viewing an article's journey that shows rejection at "wow_factor", **When** he clicks the "Unreject" button, **Then** the article becomes a candidate (status=pending, filter_status=passed).

---

### User Story 3 - Override from Pipeline Run Detail (Priority: P3)

John is viewing the pipeline run funnel and wants to quickly unreject an article listed in the summary without drilling into detailed views.

**Why this priority**: Convenience feature for when John spots an article to rescue without needing the full rejection context.

**Independent Test**: From run detail page, if rejected articles are shown, click "Unreject" and verify status change.

**Acceptance Scenarios**:

1. **Given** John is viewing a pipeline run detail page, **When** rejected articles are displayed with unreject buttons and he clicks one, **Then** the article status changes to pending.

---

### Edge Cases

- What happens when John unrejets an article that was already manually unrejected? System should handle gracefully (no error, possibly show "Already pending" state).
- What happens if the article was rejected due to a processing error? Unrejecting should still work, setting it to pending for manual review.
- What happens if the database update fails? Show user-friendly error message and keep button enabled for retry.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display an "Unreject" button next to each rejected article in the rejection analysis view.
- **FR-002**: System MUST display an "Unreject" button on the article journey page for articles with rejected status.
- **FR-003**: When the "Unreject" button is clicked, system MUST update the article's `status` to "pending" and `filter_status` to "passed".
- **FR-004**: System MUST provide visual feedback when unreject action succeeds (button text change, color change, or checkmark).
- **FR-005**: System MUST handle errors gracefully and display user-friendly error messages if the update fails.
- **FR-006**: The unreject action MUST work without requiring a full page reload (inline update preferred).

### Key Entities

- **Article**: Existing entity. Unreject action modifies `status` (to PENDING) and `filter_status` (to PASSED).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: John can unreject an article in under 2 seconds (single click, immediate feedback).
- **SC-002**: Unrejected articles appear in the pending candidates list immediately.
- **SC-003**: 100% of unreject actions either succeed with visual confirmation or fail with clear error message.
- **SC-004**: Feature works across all views where rejected articles are displayed (rejection analysis, article journey).

## Assumptions

- The unreject button uses a simple form POST or AJAX call - no complex frontend framework needed.
- Unrejected articles follow the normal candidate workflow (appear in next email batch if score qualifies).
- No audit trail is needed for unreject actions beyond the standard database timestamps.
- Only John (single user) needs access; no permission system required.
