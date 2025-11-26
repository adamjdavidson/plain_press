# Feature Specification: Daily Email Delivery

**Feature Branch**: `003-email-delivery`  
**Created**: 2025-11-26  
**Status**: Draft  
**Input**: User description: "Send daily email at 9am EST with 40-60 pending article candidates to John, including Good/No/Why Not feedback buttons for each article"

**Constitution Check**: This feature aligns with `.specify/memory/constitution.md` principles:
- **Single-User Simplicity**: One email to one recipient (John) - no multi-user complexity
- **Volume Over Precision**: Display all 40-60 candidates; let John decide what's good
- **Reliability Over Performance**: Retry on failure, log delivery status, alert on errors
- **Cost Discipline**: Use SendGrid free tier (sufficient for 1 email/day)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Receive Daily Candidate Email (Priority: P1)

John must receive one email per day at 9am EST containing all pending article candidates (40-60 articles). The email displays each article with headline, AI summary, Amish angle, and source. Email is formatted for easy scanning on desktop or mobile. Subject line includes date and candidate count.

**Why this priority**: This is the primary interface between the system and John. Without email delivery, John cannot review candidates. The email replaces his manual RSS checking workflow. Must work reliably every day.

**Independent Test**: Can be fully tested by creating test articles with status="pending", triggering email send, verifying email received with correct content and formatting.

**Acceptance Scenarios**:

1. **Given** 52 articles with status="pending" exist, **When** 9am EST job runs, **Then** John receives email with subject "Plain News Candidates - Nov 26 (52 articles)", body contains all 52 articles formatted with headline, summary, amish_angle
2. **Given** email sent successfully, **When** delivery confirmed, **Then** all included articles updated to status="emailed", EmailBatch record created with article_count=52, status="sent"
3. **Given** 0 articles with status="pending", **When** 9am job runs, **Then** NO email sent, warning logged "No pending candidates for daily email", no EmailBatch created
4. **Given** articles include special characters (quotes, ampersands), **When** email rendered, **Then** HTML properly escaped, no rendering issues in Gmail/Outlook

---

### User Story 2 - Click Feedback Buttons (Priority: P1)

Each article in the email includes three feedback buttons: Good, No, and Why Not. When John clicks a button, it opens a URL that records his feedback and shows a confirmation page. Good marks the article for deep dive generation; No rejects it; Why Not prompts for a text explanation.

**Why this priority**: Feedback buttons are how John communicates with the system. Without them, there's no learning loop. Buttons must be prominent, easy to click on mobile, and work reliably with one click.

**Independent Test**: Can be fully tested by generating feedback URLs, clicking each button type, verifying Feedback record created with correct rating, Article status updated appropriately.

**Acceptance Scenarios**:

1. **Given** article in email with Good button, **When** John clicks Good button, **Then** browser opens feedback URL, Feedback record created with rating="good", Article status updated to "good", confirmation page shows "Marked as Good!"
2. **Given** article in email with No button, **When** John clicks No button, **Then** Feedback record created with rating="no", Article status updated to "rejected", confirmation page shows "Marked as No"
3. **Given** article in email with Why Not button, **When** John clicks Why Not button, **Then** browser shows text input form, John enters reason, Feedback record created with rating="why_not" and notes containing reason, Article status updated to "rejected"
4. **Given** John clicks same button twice (double-click), **When** second request arrives, **Then** system detects existing Feedback for article, returns "Already recorded" message, no duplicate created

---

### User Story 3 - Track Email Delivery Status (Priority: P2)

System must track email delivery success/failure in EmailBatch table. Failed deliveries trigger retry with exponential backoff. Persistent failures send alert to John via backup method (could be same email to alternate address). Delivery stats available for debugging.

**Why this priority**: Reliability is critical - a missed email means John loses a day of candidates. Tracking enables debugging and ensures no silent failures. Lower priority than core delivery because SendGrid is generally reliable.

**Independent Test**: Can be fully tested by mocking SendGrid API responses (success, failure, rate limit), verifying EmailBatch status updated correctly, retry logic triggered on failures.

**Acceptance Scenarios**:

1. **Given** SendGrid returns success (202 status), **When** email sent, **Then** EmailBatch created with status="sent", sent_at timestamp recorded
2. **Given** SendGrid returns temporary failure (500 error), **When** first attempt fails, **Then** system retries after 30 seconds, up to 3 attempts, EmailBatch created only after final success/failure
3. **Given** all retry attempts fail, **When** giving up, **Then** EmailBatch created with status="failed", error_message contains SendGrid error, warning email sent to backup address (if configured)
4. **Given** rate limit exceeded (429 error), **When** request fails, **Then** system waits for Retry-After header duration, retries, logs rate limit event

---

### User Story 4 - View Article in Email (Priority: P2)

Each article in the email includes a "Read More" link to the original article URL. Clicking opens the source website in a new browser tab. Original URL preserved (not normalized version) for user convenience.

**Why this priority**: John needs to read full articles before deciding Good/No. Link must work and go to the actual article. Lower priority because this is standard email link functionality.

**Independent Test**: Can be fully tested by verifying email HTML contains correct href attributes pointing to original article URLs, links open in new tab.

**Acceptance Scenarios**:

1. **Given** article with external_url "https://example.com/story/123", **When** email rendered, **Then** "Read More" link href equals original URL, target="_blank" for new tab
2. **Given** article URL contains special characters, **When** email rendered, **Then** URL properly encoded in href attribute
3. **Given** John clicks Read More link, **When** browser opens, **Then** original article page loads (system does not track this click)

---

### Edge Cases

- **What happens if discovery job runs late (after 9am)?** Email job checks for pending articles regardless of when they were discovered. If discovery finishes at 9:30am and email job already ran at 9am with 0 articles, no email sent. Next day's email includes all pending articles. Consider adding dependency: email job waits for discovery or runs after discovery completes.
- **What happens if John doesn't click any buttons?** Articles remain status="emailed" indefinitely. Weekly refinement job (Feature 006) can analyze unclicked articles as "ignored" for learning purposes.
- **What happens if email is very long (100+ articles)?** System sends all articles regardless of count (per Volume Over Precision). Email client may truncate; consider adding "View in browser" link for full list. Log warning if >80 articles.
- **What happens if SendGrid free tier limit exceeded?** SendGrid free tier is 100 emails/day - we send 1. If somehow exceeded, system logs error and retries next day. Alert John via application logs (Railway).
- **What happens if feedback URL expires or is bookmarked?** Feedback URLs contain article ID and are permanent - John can click days later. No expiration. Duplicate clicks handled gracefully.
- **What happens if email contains duplicate articles?** Should never happen (articles have unique URLs), but if it does, each article gets its own feedback buttons. Database constraint prevents duplicate feedback per article.

## Requirements *(mandatory)*

### Functional Requirements

**Email Composition**

- **FR-001**: System MUST send one email per day at 9am EST containing all articles with status="pending"
- **FR-002**: Email subject MUST follow format: "Plain News Candidates - {Month} {Day} ({count} articles)"
- **FR-003**: Email body MUST display each article with: headline, AI summary (2-3 sentences), amish_angle, source name
- **FR-004**: Each article MUST include three feedback buttons: Good (green), No (red), Why Not (yellow/orange)
- **FR-005**: Each article MUST include "Read More" link to original article URL
- **FR-006**: Email MUST be mobile-responsive (readable on phone without horizontal scrolling)
- **FR-007**: System MUST NOT send email if 0 pending articles exist (log warning instead)

**Feedback Buttons**

- **FR-008**: Each feedback button MUST link to unique URL: `/feedback/{article_id}/{rating}` where rating is good|no|why_not
- **FR-009**: Good button click MUST create Feedback record with rating="good", update Article status to "good"
- **FR-010**: No button click MUST create Feedback record with rating="no", update Article status to "rejected"
- **FR-011**: Why Not button click MUST show form for text input, then create Feedback with rating="why_not" and notes
- **FR-012**: Feedback endpoint MUST handle duplicate clicks gracefully (return success, no duplicate record)
- **FR-013**: Feedback endpoint MUST return HTML confirmation page (not JSON) for browser display

**Email Delivery**

- **FR-014**: System MUST use SendGrid API for email delivery
- **FR-015**: System MUST retry failed deliveries with exponential backoff (30s, 60s, 120s)
- **FR-016**: System MUST create EmailBatch record for each delivery attempt with status, timestamp, article count
- **FR-017**: System MUST update all included articles to status="emailed" after successful delivery
- **FR-018**: System MUST log delivery failures with SendGrid error details

**Article Status Updates**

- **FR-019**: Articles transition from "pending" → "emailed" when included in sent email
- **FR-020**: Articles transition from "emailed" → "good" when Good button clicked
- **FR-021**: Articles transition from "emailed" → "rejected" when No or Why Not button clicked
- **FR-022**: Article email_batch_id MUST be set to link article to its delivery batch

**Job Scheduling**

- **FR-023**: Email job MUST run daily at 9am EST via Railway cron
- **FR-024**: Email job MUST complete within 5 minutes (allow time for retries)
- **FR-025**: Email job MUST log summary: articles sent, delivery status, any errors

### Key Entities *(include if feature involves data)*

- **Email Service**: Composes and sends daily candidate email via SendGrid. Builds HTML template with articles and feedback buttons. Handles delivery status tracking.

- **Feedback Routes**: Flask routes that handle feedback button clicks. Create Feedback records, update Article status, return confirmation pages.

- **Email Template**: HTML template for daily email. Responsive design, clear typography, prominent buttons. Renders article data into scannable format.

- **EmailBatch (existing)**: Records each email delivery with sent_at, recipient_emails, article_count, status, error_message. Links to articles via Article.email_batch_id.

- **Feedback (existing)**: Records John's rating on each article with rating enum, notes field, clicked_at timestamp. One-to-one with Article.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Daily email delivered to John's inbox by 9:05am EST 95% of days (allowing 5 min for job execution)
- **SC-002**: Email renders correctly in Gmail and Outlook (tested manually during development)
- **SC-003**: Feedback buttons work with single click, <3 second response time for confirmation page
- **SC-004**: Zero duplicate Feedback records created (constraint enforced at database level)
- **SC-005**: EmailBatch records created for 100% of delivery attempts (success and failure)
- **SC-006**: Article status transitions logged and queryable for debugging
- **SC-007**: Email job cost is $0/month (SendGrid free tier)
- **SC-008**: Retry logic successfully recovers from transient SendGrid failures (tested with mock)
- **SC-009**: Why Not form captures text input and stores in Feedback.notes
- **SC-010**: Email contains all pending articles with no omissions (count matches EmailBatch.article_count)

## Assumptions

- **SendGrid Account**: SendGrid account created, API key available, sender email verified (e.g., noreply@amish-news.example.com or via SendGrid sender authentication)
- **John's Email**: John's email address configured in environment variable (EDITOR_EMAIL)
- **Gmail Rendering**: John uses Gmail; email template tested primarily for Gmail compatibility
- **Button Click Behavior**: John clicks buttons from email client; buttons open in default browser
- **Single Recipient**: Only John receives the email; no CC/BCC or multiple recipients
- **EST Timezone**: 9am EST hardcoded; no timezone configuration needed for single user
- **Discovery Complete**: Discovery job (Feature 002) completes before 9am, providing pending articles
- **Feedback URL Access**: Feedback URLs are publicly accessible (no authentication required for simplicity)
- **Mobile Reading**: John may read email on mobile; responsive design is important
- **Article Limit**: No maximum articles per email; system sends all pending (typically 40-60)
