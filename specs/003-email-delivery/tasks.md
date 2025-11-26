# Task Breakdown: Daily Email Delivery

**Feature Branch**: `003-email-delivery`  
**Generated**: 2025-11-26  
**Status**: ✅ Complete (MVP)  
**Spec Reference**: [spec.md](./spec.md)  
**Plan Reference**: [plan.md](./plan.md)

## Overview

- **Total Tasks**: 48
- **MVP Scope**: Phases 1-5 (38 tasks) - Email + Feedback + Job
- **Full Scope**: All phases including comprehensive tests

**Constitution Alignment**:
- Tests REQUIRED for: SendGrid API integration, feedback routes
- Tests OPTIONAL for: HTML template rendering

---

## Dependencies

```
Phase 1 (Setup) → Phase 2 (Template) → Phase 3 (SendGrid) → Phase 5 (Job)
                                    → Phase 4 (Feedback Routes)
```

- Phase 2 (Template) and Phase 4 (Feedback) can run in parallel after Phase 1
- Phase 5 (Job) depends on Phase 3 (SendGrid) completing

---

## Phase 1: Setup (4 tasks)

### Task 1.1: Add sendgrid dependency
**File**: `/home/adamd/projects/amish_news/requirements.txt`  
**Action**: Add `sendgrid==6.11.0`

### Task 1.2: Create email service file
**File**: `/home/adamd/projects/amish_news/app/services/email.py`  
**Action**: Create stub with docstring

### Task 1.3: Create templates directory structure
**Files**:
- `/home/adamd/projects/amish_news/app/templates/email/daily_candidates.html`
- `/home/adamd/projects/amish_news/app/templates/feedback/confirmation.html`
- `/home/adamd/projects/amish_news/app/templates/feedback/why_not_form.html`

**Action**: Create empty template files

### Task 1.4: Create email job script
**File**: `/home/adamd/projects/amish_news/scripts/email_job.py`  
**Action**: Create stub with docstring

**Checkpoint**: ✅ Project structure ready for implementation

---

## Phase 2: Email Template (6 tasks) - User Story 1

### Task 2.1: Create base HTML email template
**File**: `/home/adamd/projects/amish_news/app/templates/email/daily_candidates.html`  
**Action**: Create responsive HTML structure with inline CSS
**Spec**: FR-003, FR-006

### Task 2.2: Add article card section
**File**: `/home/adamd/projects/amish_news/app/templates/email/daily_candidates.html`  
**Action**: Add Jinja2 loop for articles with headline, summary, amish_angle, source
**Spec**: FR-003

### Task 2.3: Add feedback buttons to template
**File**: `/home/adamd/projects/amish_news/app/templates/email/daily_candidates.html`  
**Action**: Add Good (green), No (red), Why Not (yellow) buttons with URLs
**Spec**: FR-004, FR-008

### Task 2.4: Add Read More link
**File**: `/home/adamd/projects/amish_news/app/templates/email/daily_candidates.html`  
**Action**: Add link to original article URL
**Spec**: FR-005

### Task 2.5: Add email header and footer
**File**: `/home/adamd/projects/amish_news/app/templates/email/daily_candidates.html`  
**Action**: Add subject-like header with date/count, footer with generation info
**Spec**: FR-002

### Task 2.6: Test template rendering with sample data
**Action**: Manual test - render template with test articles, verify HTML output

**Checkpoint**: ✅ Email template complete - ready for SendGrid integration

---

## Phase 3: SendGrid Integration (8 tasks) - User Story 3

### Task 3.1: Implement SendGrid client initialization
**File**: `/home/adamd/projects/amish_news/app/services/email.py`  
**Action**: Create `get_sendgrid_client()` function using SENDGRID_API_KEY
**Spec**: FR-014

### Task 3.2: Implement render_email_html function
**File**: `/home/adamd/projects/amish_news/app/services/email.py`  
**Action**: Load Jinja2 template, render with articles and feedback URL base

### Task 3.3: Implement send_email function
**File**: `/home/adamd/projects/amish_news/app/services/email.py`  
**Action**: Use SendGrid Mail helper to compose and send email
**Spec**: FR-014

### Task 3.4: Add retry logic with exponential backoff
**File**: `/home/adamd/projects/amish_news/app/services/email.py`  
**Action**: Retry on 5xx errors, wait 30s/60s/120s between attempts
**Spec**: FR-015

### Task 3.5: Implement create_email_batch function
**File**: `/home/adamd/projects/amish_news/app/services/email.py`  
**Action**: Create EmailBatch record with status, article_count, sent_at
**Spec**: FR-016

### Task 3.6: Implement update_articles_to_emailed function
**File**: `/home/adamd/projects/amish_news/app/services/email.py`  
**Action**: Update article status to "emailed", set email_batch_id
**Spec**: FR-017, FR-019, FR-022

### Task 3.7: Implement send_daily_candidates function
**File**: `/home/adamd/projects/amish_news/app/services/email.py`  
**Action**: Main function that queries pending articles, renders, sends, updates
**Spec**: FR-001

### Task 3.8: Add logging for delivery status
**File**: `/home/adamd/projects/amish_news/app/services/email.py`  
**Action**: Log success/failure with SendGrid response details
**Spec**: FR-018

**Checkpoint**: ✅ SendGrid integration complete - can send emails

---

## Phase 4: Feedback Routes (12 tasks) - User Story 2

### Task 4.1: Create feedback confirmation template
**File**: `/home/adamd/projects/amish_news/app/templates/feedback/confirmation.html`  
**Action**: Simple HTML page showing "Marked as Good!" / "Marked as No" / "Feedback recorded"
**Spec**: FR-013

### Task 4.2: Create Why Not form template
**File**: `/home/adamd/projects/amish_news/app/templates/feedback/why_not_form.html`  
**Action**: HTML form with text input for reason, submit button
**Spec**: FR-011

### Task 4.3: Add feedback routes to Flask app
**File**: `/home/adamd/projects/amish_news/app/routes.py`  
**Action**: Add routes for /feedback/<article_id>/<rating>
**Spec**: FR-008

### Task 4.4: Implement Good feedback handler
**File**: `/home/adamd/projects/amish_news/app/routes.py`  
**Action**: Create Feedback(rating="good"), update Article status to "good"
**Spec**: FR-009, FR-020

### Task 4.5: Implement No feedback handler
**File**: `/home/adamd/projects/amish_news/app/routes.py`  
**Action**: Create Feedback(rating="no"), update Article status to "rejected"
**Spec**: FR-010, FR-021

### Task 4.6: Implement Why Not GET handler (show form)
**File**: `/home/adamd/projects/amish_news/app/routes.py`  
**Action**: Render why_not_form.html template
**Spec**: FR-011

### Task 4.7: Implement Why Not POST handler (submit form)
**File**: `/home/adamd/projects/amish_news/app/routes.py`  
**Action**: Create Feedback(rating="why_not", notes=form_input), update status
**Spec**: FR-011, FR-021

### Task 4.8: Handle duplicate feedback clicks
**File**: `/home/adamd/projects/amish_news/app/routes.py`  
**Action**: Check if Feedback exists for article, return "Already recorded" if so
**Spec**: FR-012

### Task 4.9: Handle invalid article ID
**File**: `/home/adamd/projects/amish_news/app/routes.py`  
**Action**: Return 404 if article not found

### Task 4.10: Update Source metrics on feedback
**File**: `/home/adamd/projects/amish_news/app/routes.py`  
**Action**: Increment Source.total_approved (Good) or total_rejected (No/Why Not)

### Task 4.11: Style confirmation pages
**File**: `/home/adamd/projects/amish_news/app/templates/feedback/confirmation.html`  
**Action**: Add simple CSS for pleasant display

### Task 4.12: Style Why Not form
**File**: `/home/adamd/projects/amish_news/app/templates/feedback/why_not_form.html`  
**Action**: Add CSS for form, show article headline for context

**Checkpoint**: ✅ Feedback routes complete - buttons work

---

## Phase 5: Email Job (8 tasks) - User Story 1

### Task 5.1: Implement email job entry point
**File**: `/home/adamd/projects/amish_news/scripts/email_job.py`  
**Action**: Main function that calls send_daily_candidates()
**Spec**: FR-023

### Task 5.2: Query pending articles
**File**: `/home/adamd/projects/amish_news/scripts/email_job.py`  
**Action**: Get all articles with status="pending", ordered by filter_score desc

### Task 5.3: Skip if no pending articles
**File**: `/home/adamd/projects/amish_news/scripts/email_job.py`  
**Action**: Log warning "No pending candidates", exit without sending
**Spec**: FR-007

### Task 5.4: Log job summary
**File**: `/home/adamd/projects/amish_news/scripts/email_job.py`  
**Action**: Log articles sent, delivery status, any errors
**Spec**: FR-025

### Task 5.5: Add error handling and exit codes
**File**: `/home/adamd/projects/amish_news/scripts/email_job.py`  
**Action**: Return exit code 0 on success, 1 on failure

### Task 5.6: Log warning for high article count
**File**: `/home/adamd/projects/amish_news/scripts/email_job.py`  
**Action**: Log warning if >80 articles (per Volume Over Precision, still send all)

### Task 5.7: Configure environment loading
**File**: `/home/adamd/projects/amish_news/scripts/email_job.py`  
**Action**: Load .env, set up logging

### Task 5.8: Add Railway cron configuration note
**File**: `/home/adamd/projects/amish_news/scripts/email_job.py`  
**Action**: Add comment with Railway cron config (9am EST = 2pm UTC)
**Spec**: FR-023

**Checkpoint**: ✅ Email job complete - daily pipeline ready

---

## Phase 6: Testing (10 tasks)

### Task 6.1: Contract test - SendGrid send success [P]
**File**: `/home/adamd/projects/amish_news/tests/contract/test_sendgrid.py`  
**Action**: Mock SendGrid API 202 response, verify email sent

### Task 6.2: Contract test - SendGrid retry on 500 [P]
**File**: `/home/adamd/projects/amish_news/tests/contract/test_sendgrid.py`  
**Action**: Mock 500 then 202, verify retry logic works

### Task 6.3: Contract test - SendGrid failure handling [P]
**File**: `/home/adamd/projects/amish_news/tests/contract/test_sendgrid.py`  
**Action**: Mock persistent 500, verify EmailBatch created with status="failed"

### Task 6.4: Integration test - feedback Good button [P]
**File**: `/home/adamd/projects/amish_news/tests/integration/test_feedback.py`  
**Action**: Click Good URL, verify Feedback created, Article status updated

### Task 6.5: Integration test - feedback No button [P]
**File**: `/home/adamd/projects/amish_news/tests/integration/test_feedback.py`  
**Action**: Click No URL, verify Feedback created, Article status updated

### Task 6.6: Integration test - feedback Why Not flow [P]
**File**: `/home/adamd/projects/amish_news/tests/integration/test_feedback.py`  
**Action**: GET form, POST with text, verify Feedback with notes

### Task 6.7: Integration test - duplicate feedback rejected [P]
**File**: `/home/adamd/projects/amish_news/tests/integration/test_feedback.py`  
**Action**: Click same button twice, verify no duplicate Feedback

### Task 6.8: Integration test - email job with pending articles
**File**: `/home/adamd/projects/amish_news/tests/integration/test_email_job.py`  
**Action**: Create pending articles, run job, verify email sent, status updated

### Task 6.9: Integration test - email job with no articles
**File**: `/home/adamd/projects/amish_news/tests/integration/test_email_job.py`  
**Action**: Run job with 0 pending, verify no email sent, warning logged

### Task 6.10: Integration test - article status transitions
**File**: `/home/adamd/projects/amish_news/tests/integration/test_email_job.py`  
**Action**: Verify pending → emailed → good/rejected transitions

**Checkpoint**: ✅ Testing complete - all workflows validated

---

## MVP Completion Summary

**MVP = Phases 1-5** (38 tasks)

After completing MVP:
- ✅ Daily email sent at 9am EST with all pending articles
- ✅ Good/No/Why Not buttons work with single click
- ✅ Feedback stored in database for learning
- ✅ Article status transitions tracked
- ✅ EmailBatch records for delivery tracking

**Remaining for Full Completion**:
- Phase 6: Testing (10 tasks)

---

## Test Summary

| Category | Count | Files |
|----------|-------|-------|
| Contract Tests (SendGrid) | 3 | `tests/contract/test_sendgrid.py` |
| Integration Tests (Feedback) | 4 | `tests/integration/test_feedback.py` |
| Integration Tests (Email Job) | 3 | `tests/integration/test_email_job.py` |
| **Total** | **10** | |

---

**Command `/speckit.tasks` execution complete.**

Ready for implementation with `/speckit.implement`.

