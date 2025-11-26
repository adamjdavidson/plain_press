# Implementation Plan: Deep Dive Generation

**Feature Branch**: `004-deep-dive`  
**Planning Date**: 2025-11-26  
**Status**: ✅ Complete (MVP)  
**Spec Reference**: [spec.md](./spec.md)

## Plan Summary

This feature generates comprehensive reports when John clicks "Good" on an article:

1. **Content Fetching** - Fetch full article from source URL
2. **Report Generation** - Claude Sonnet creates 500-1000 word report
3. **Google Docs** - Save report to Drive folder
4. **Google Sheets** - Log approved article (optional)
5. **Email Delivery** - Send report with Doc link

**Key Technical Decisions**:
- Use `google-api-python-client` for Google integration
- Use `httpx` for article fetching (already installed)
- Background processing triggered by Good feedback route
- Synchronous flow (report before confirmation) for simplicity

---

## Constitution Check

| Principle | Check | Notes |
|-----------|-------|-------|
| Single-User Simplicity | ✅ | No auth complexity, direct to John |
| Cost Discipline | ✅ | ~$0.03/report, well under budget |
| Pragmatic Testing | ✅ | Test API integrations, mock external calls |
| Reliability | ✅ | 3 retries, graceful failure |

---

## Technical Context

### Existing Infrastructure
- Python 3.13 + SQLAlchemy 2.0+
- PostgreSQL on Railway
- SendGrid for email
- Anthropic SDK installed
- Flask routes for feedback

### New Dependencies
```
google-api-python-client==2.154.0
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.2.1
beautifulsoup4==4.12.3
```

### Environment Variables Required
```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_DRIVE_FOLDER_ID=your-folder-id
GOOGLE_SHEET_ID=your-sheet-id  # Optional
```

---

## Project Structure

```
app/
├── services/
│   ├── deep_dive.py      # NEW - Report orchestration
│   ├── content_fetcher.py # NEW - Fetch article content
│   ├── google_docs.py    # NEW - Google Docs/Drive API
│   ├── google_sheets.py  # NEW - Google Sheets API (optional)
│   └── email.py          # UPDATE - Add report email template
├── templates/
│   └── email/
│       └── deep_dive_report.html  # NEW - Report email template
└── routes.py             # UPDATE - Trigger deep dive on Good

tests/
├── contract/
│   └── test_deep_dive.py # NEW - Claude API contract tests
├── integration/
│   └── test_google_api.py # NEW - Google API integration tests
└── unit/
    └── test_content_fetcher.py # NEW - Content extraction tests
```

---

## Phase 0: Research (Complete)

### Technical Decisions

1. **Google Auth Strategy**: Service account (no OAuth flow needed for single user)
2. **Content Extraction**: BeautifulSoup for HTML parsing, fallback to raw_content
3. **Claude Model**: claude-sonnet-4-20250514 (best quality/cost balance)
4. **Report Format**: Markdown in Claude response, convert to Doc formatting
5. **Error Handling**: Fail fast, notify John, log for debugging

---

## Phase 1: Design

### Report Prompt Structure
```
You are helping write stories for Plain News, an Amish newspaper.

Given this article, create a deep-dive report with these sections:
1. SUMMARY (2-3 sentences, 8th grade reading level)
2. KEY FACTS (5-7 bullet points)
3. AMISH ANGLE (why this matters to Plain community)
4. STORY LEADS (2-3 follow-up angles to explore)
5. SOURCES (original URL + any mentioned sources)

Article: {headline}
Source: {source_name}
Content: {content}

Keep total report under 1000 words. Write in clear, simple language.
```

### Flow Diagram
```
Good Click → Check DeepDive exists? 
           ↓ No
     Create DeepDive (PENDING)
           ↓
     Fetch Article Content
           ↓
     Generate Report (Claude)
           ↓
     Create Google Doc
           ↓
     Update Article (doc_id, doc_url)
           ↓
     Log to Google Sheet (optional)
           ↓
     Send Email with Report
           ↓
     Update DeepDive (COMPLETED)
           ↓
     Show Confirmation Page
```

---

## MVP Scope

**In MVP**:
- Content fetching from URL
- Claude Sonnet report generation
- Google Docs creation
- Email delivery with report
- Basic error handling

**Deferred**:
- Google Sheets logging (nice-to-have)
- Retry queue for failed reports
- Report regeneration

---

## Cost Projection

| Item | Per Report | Daily (5) | Monthly |
|------|------------|-----------|---------|
| Claude Sonnet (~2K in, 1K out) | $0.024 | $0.12 | $3.60 |
| Google APIs | Free | Free | Free |
| SendGrid | Free | Free | Free |
| **Total** | $0.024 | $0.12 | $3.60 |

Well within $50/month budget.

