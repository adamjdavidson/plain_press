# Implementation Plan: Daily Email Delivery

**Feature Branch**: `003-email-delivery`  
**Planning Date**: 2025-11-26  
**Status**: ✅ Complete (MVP)  
**Spec Reference**: [spec.md](./spec.md)

## Plan Summary

This feature implements the daily email delivery system:
1. **Email Composition** - Build HTML email with 40-60 article candidates
2. **Feedback Buttons** - Good/No/Why Not buttons linking to Flask routes
3. **SendGrid Integration** - Send email via SendGrid API with retry logic
4. **Feedback Routes** - Handle button clicks, update Article status, return confirmation
5. **Email Job** - Daily cron at 9am EST

**Key Technical Decisions**:
- Use `sendgrid 6.11.0` Python SDK for email delivery
- Use Flask routes for feedback handling (no auth required per Single-User Simplicity)
- Use Jinja2 HTML template for responsive email design
- Store feedback URL base in environment (for local vs production)

---

## Constitution Check

| Principle | Compliance | Notes |
|-----------|------------|-------|
| **I. Single-User Simplicity** | ✅ PASS | One email to one recipient (John); no auth on feedback URLs |
| **II. Volume Over Precision** | ✅ PASS | Send all 40-60 candidates; let John decide |
| **III. Learning Over Time** | ✅ PASS | Feedback stored for weekly refinement analysis |
| **IV. Pragmatic Testing** | ✅ PASS | Contract tests for SendGrid API; integration test for email job |
| **V. Cost Discipline** | ✅ PASS | SendGrid free tier (100 emails/day); we send 1 |
| **VI. Reliability Over Performance** | ✅ PASS | Retry logic; EmailBatch tracking; error logging |

---

## Technical Context

### Dependencies (additions to requirements.txt)

```
# Email Delivery
sendgrid==6.11.0
```

### Environment Variables (additions to .env)

```
# SendGrid API
SENDGRID_API_KEY=SG.xxx
SENDGRID_FROM_EMAIL=noreply@yourdomain.com

# Editor (recipient)
EDITOR_EMAIL=john@example.com

# Feedback URL base (for button links)
FEEDBACK_URL_BASE=https://your-app.railway.app
```

### External API Contracts

**SendGrid Mail Send API**:
- Endpoint: POST /v3/mail/send
- Auth: Bearer token (SENDGRID_API_KEY)
- Response: 202 Accepted (success), 400/401/429/500 (errors)
- Rate Limit: 100 emails/day on free tier

---

## Project Structure

```
app/
  routes.py              # Add feedback routes
  services/
    email.py             # Email composition and SendGrid integration
  templates/
    email/
      daily_candidates.html   # Jinja2 email template
    feedback/
      confirmation.html       # Feedback confirmation page
      why_not_form.html       # Why Not text input form

scripts/
  email_job.py           # Cron entry point (9am EST)

tests/
  contract/
    test_sendgrid.py     # SendGrid API contract tests
  integration/
    test_email_job.py    # End-to-end email workflow
```

---

## Phase 0: Research (Complete)

Key technical decisions documented in [research.md](./research.md):

1. **SendGrid Python SDK** - Official SDK with Mail helper class
2. **Jinja2 Templates** - Flask's built-in templating for HTML email
3. **Responsive Email** - Table-based layout for Gmail/Outlook compatibility
4. **Feedback URLs** - Simple pattern: `/feedback/{article_id}/{rating}`
5. **Button Styling** - Inline CSS (email clients strip `<style>` tags)

---

## Phase 1: Design Artifacts

### Email Template Structure

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Plain News Candidates</title>
</head>
<body style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h1 style="color: #333;">Plain News Candidates</h1>
  <p style="color: #666;">{{ date }} • {{ article_count }} articles</p>
  
  {% for article in articles %}
  <div style="border-bottom: 1px solid #eee; padding: 20px 0;">
    <h2 style="font-size: 18px; margin: 0 0 10px;">{{ article.headline }}</h2>
    <p style="color: #666; font-size: 14px; margin: 0 0 10px;">{{ article.source_name }}</p>
    <p style="margin: 0 0 10px;">{{ article.summary }}</p>
    <p style="font-style: italic; color: #666; margin: 0 0 15px;">{{ article.amish_angle }}</p>
    
    <div style="margin: 15px 0;">
      <a href="{{ feedback_url_base }}/feedback/{{ article.id }}/good" 
         style="display: inline-block; padding: 10px 20px; background: #28a745; color: white; text-decoration: none; border-radius: 4px; margin-right: 10px;">Good</a>
      <a href="{{ feedback_url_base }}/feedback/{{ article.id }}/no" 
         style="display: inline-block; padding: 10px 20px; background: #dc3545; color: white; text-decoration: none; border-radius: 4px; margin-right: 10px;">No</a>
      <a href="{{ feedback_url_base }}/feedback/{{ article.id }}/why_not" 
         style="display: inline-block; padding: 10px 20px; background: #ffc107; color: #333; text-decoration: none; border-radius: 4px;">Why Not?</a>
    </div>
    
    <a href="{{ article.external_url }}" target="_blank" style="color: #007bff;">Read More →</a>
  </div>
  {% endfor %}
  
  <footer style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #999; font-size: 12px;">
    Generated by Amish News Finder • {{ date }}
  </footer>
</body>
</html>
```

### Feedback Routes

```python
# GET /feedback/<article_id>/good
# GET /feedback/<article_id>/no
# GET /feedback/<article_id>/why_not (shows form)
# POST /feedback/<article_id>/why_not (submits form)
```

### Database Interactions

```sql
-- Query pending articles for email
SELECT * FROM articles 
WHERE status = 'pending' 
ORDER BY filter_score DESC, discovered_date DESC;

-- Update articles after email sent
UPDATE articles 
SET status = 'emailed', email_batch_id = :batch_id, emailed_date = NOW()
WHERE id IN (:article_ids);

-- Create feedback record
INSERT INTO feedback (article_id, rating, notes, clicked_at)
VALUES (:article_id, :rating, :notes, NOW())
ON CONFLICT (article_id) DO NOTHING;

-- Update article status on feedback
UPDATE articles SET status = :new_status WHERE id = :article_id;
```

---

## Implementation Phases

### Phase 1: Setup (Tasks 1-4)
- Add sendgrid to requirements.txt
- Create email service directory
- Create templates directory
- Add environment variables

### Phase 2: Email Template (Tasks 5-10) - User Story 1
- Create Jinja2 HTML template
- Style for mobile responsiveness
- Add feedback button placeholders
- Test rendering with sample data

### Phase 3: SendGrid Integration (Tasks 11-18) - User Story 3
- Implement SendGrid client wrapper
- Implement send_daily_email function
- Add retry logic with exponential backoff
- Create EmailBatch records
- Update article status after send

### Phase 4: Feedback Routes (Tasks 19-30) - User Story 2
- Add Flask routes for Good/No/Why Not
- Create Feedback records on click
- Update Article status
- Create confirmation HTML pages
- Handle duplicate clicks gracefully

### Phase 5: Email Job (Tasks 31-38) - User Story 1
- Implement email_job.py cron script
- Query pending articles
- Compose and send email
- Log job summary
- Configure Railway cron

### Phase 6: Testing (Tasks 39-48)
- Contract tests for SendGrid API
- Integration test for full workflow
- Test feedback button clicks
- Test error handling and retries

---

## Cost Projections

| Component | Monthly Cost |
|-----------|--------------|
| SendGrid Free Tier | $0 (100 emails/day, we use 1) |
| **Total** | **$0** |

✅ Well under $50/month budget per constitution

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| SendGrid API failure | Retry 3x with exponential backoff; log errors |
| Email lands in spam | Use authenticated sender domain; test deliverability |
| Feedback URL doesn't work | Test URLs manually; ensure Flask routes accessible |
| Email too long (truncated) | Gmail truncates at ~102KB; our emails ~50KB typically |
| Double-click creates duplicates | Database unique constraint on Feedback.article_id |

---

## Ready For

**Next Step**: Task generation (`/speckit.tasks`) and implementation.

---

**Command `/speckit.plan` execution complete.**

