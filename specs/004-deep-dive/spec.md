# Feature Specification: Deep Dive Report Generation

**Feature ID**: 004-deep-dive  
**Created**: 2025-11-26  
**Status**: Draft  
**Constitution Check**: ✅ Aligns with Single-User Simplicity, Cost Discipline, Reliability

## Overview

When John clicks "Good" on an article, the system automatically generates a comprehensive deep-dive report using Claude Sonnet. The report is delivered via email and saved to Google Docs for easy access and archival.

---

## User Stories

### US-1: Trigger Deep Dive on Good Click (P1)
**As** John (editor)  
**I want** a deep dive report generated when I click "Good"  
**So that** I get the full story context without manual research

**Acceptance Criteria**:
- Clicking "Good" triggers background report generation
- Report generation completes within 60 seconds
- John receives email notification when report is ready
- Article status updates to "GOOD" immediately, DeepDive record created

### US-2: Receive Report via Email (P1)
**As** John  
**I want** the deep dive report emailed to me  
**So that** I can read it on any device without logging in

**Acceptance Criteria**:
- Email contains the full report inline (not just a link)
- Email includes link to Google Doc for editing/archival
- Email sent within 2 minutes of clicking "Good"
- Subject line identifies the article clearly

### US-3: Access Report in Google Docs (P1)
**As** John  
**I want** each report saved to Google Docs  
**So that** I can edit, annotate, and archive stories

**Acceptance Criteria**:
- Google Doc created in designated folder
- Doc title includes article headline and date
- Doc is shareable/editable by John
- Link stored in Article.google_doc_url

### US-4: Track Report in Google Sheets (P2)
**As** John  
**I want** approved articles logged to a Google Sheet  
**So that** I can track which stories I've approved over time

**Acceptance Criteria**:
- New row added for each approved article
- Columns: Date, Headline, Source, Score, Doc Link
- Sheet ID configurable via environment variable

### US-5: Handle Generation Failures Gracefully (P1)
**As** John  
**I want** to be notified if report generation fails  
**So that** I know to manually research the story

**Acceptance Criteria**:
- Failed generation sends error email to John
- DeepDive record marked as failed with error message
- Retry mechanism for transient failures (3 attempts)
- Article remains "GOOD" even if report fails

---

## Functional Requirements

### Report Generation
- FR-1: Use Claude Sonnet (claude-sonnet-4-20250514) for report generation
- FR-2: Fetch full article content from source URL before generation
- FR-3: Generate report with sections: Summary, Key Facts, Amish Angle, Story Leads, Sources
- FR-4: Report length: 500-1000 words
- FR-5: Include original article URL in report
- FR-6: Timeout after 90 seconds, mark as failed

### Email Delivery
- FR-7: Send report email via SendGrid
- FR-8: HTML email with clean, readable formatting
- FR-9: Include Google Doc link at top of email
- FR-10: Subject: "Deep Dive: {headline} - Plain News"

### Google Docs Integration
- FR-11: Create Doc in configured Drive folder (GOOGLE_DRIVE_FOLDER_ID)
- FR-12: Doc title format: "{YYYY-MM-DD} - {headline}"
- FR-13: Apply standard formatting (headings, paragraphs)
- FR-14: Store doc_id and doc_url in Article record

### Google Sheets Integration (Optional)
- FR-15: Append row to configured Sheet (GOOGLE_SHEET_ID)
- FR-16: Row data: discovered_date, headline, source_name, filter_score, google_doc_url
- FR-17: Graceful failure (don't block report delivery)

### Error Handling
- FR-18: Retry failed API calls (Claude, Google) up to 3 times
- FR-19: Log all generation attempts with timing
- FR-20: DeepDive.status enum: PENDING, GENERATING, COMPLETED, FAILED
- FR-21: Store error_message on failure

---

## Key Entities

### DeepDive (existing model)
```
id: UUID (PK)
article_id: UUID (FK to articles, unique)
report_content: TEXT (generated report)
generated_at: TIMESTAMP
generation_time_seconds: FLOAT
model_used: VARCHAR(100)
prompt_tokens: INTEGER
completion_tokens: INTEGER
status: ENUM (pending, generating, completed, failed)
error_message: TEXT (nullable)
```

### Article (updates)
- google_doc_id: VARCHAR(100)
- google_doc_url: VARCHAR(500)

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Report generation success rate | ≥95% |
| Average generation time | <45 seconds |
| Email delivery success | ≥99% |
| Google Doc creation success | ≥95% |
| Cost per report | <$0.05 |

---

## Edge Cases

1. **Article URL returns 404**: Generate report from cached raw_content only
2. **Claude API timeout**: Retry with exponential backoff, fail after 3 attempts
3. **Google API quota exceeded**: Queue report, retry in 1 hour
4. **Duplicate "Good" click**: Check if DeepDive exists, skip if completed
5. **Very long article**: Truncate content to 10,000 chars before sending to Claude

---

## Out of Scope

- Real-time progress indicator (too complex for single-user)
- Report editing within app (use Google Docs)
- Multiple report templates (one format for all)
- Batch report generation (one at a time)

---

## Dependencies

- Feature 001: Database Schema (DeepDive model) ✅
- Feature 003: Email Delivery (SendGrid integration) ✅
- Google Cloud service account with Drive/Docs/Sheets API access
- `GOOGLE_DRIVE_FOLDER_ID`, `GOOGLE_SHEET_ID` environment variables

---

## Cost Estimate

| Service | Per Report | Daily (5 reports) | Monthly |
|---------|------------|-------------------|---------|
| Claude Sonnet | ~$0.03 | $0.15 | $4.50 |
| SendGrid | Free tier | Free | Free |
| Google APIs | Free tier | Free | Free |
| **Total** | ~$0.03 | $0.15 | $4.50 |

Within budget constraints (<$50/month total).

