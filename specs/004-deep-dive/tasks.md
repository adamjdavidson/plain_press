# Task Breakdown: Deep Dive Generation

**Feature Branch**: `004-deep-dive`  
**Generated**: 2025-11-26  
**Status**: ✅ Complete (MVP)  
**Spec Reference**: [spec.md](./spec.md)  
**Plan Reference**: [plan.md](./plan.md)

## Overview

- **Total Tasks**: 42
- **MVP Scope**: Phases 1-5 (34 tasks)
- **Full Scope**: All phases including Google Sheets

**Constitution Alignment**:
- Tests REQUIRED for: Claude API integration, Google Docs API
- Tests OPTIONAL for: Content fetching (low risk)

---

## Dependencies

```
Phase 1 (Setup) → Phase 2 (Content Fetch) → Phase 3 (Claude) → Phase 4 (Google Docs) → Phase 5 (Email) → Phase 6 (Integration)
                                                              ↘ Phase 4b (Google Sheets - Optional)
```

---

## Phase 1: Setup & Dependencies

### 1.1 Add Dependencies [P]
- [ ] **Task 1.1.1**: Add `google-api-python-client==2.154.0` to requirements.txt
- [ ] **Task 1.1.2**: Add `google-auth-httplib2==0.2.0` to requirements.txt
- [ ] **Task 1.1.3**: Add `google-auth-oauthlib==1.2.1` to requirements.txt
- [ ] **Task 1.1.4**: Add `beautifulsoup4==4.12.3` to requirements.txt
- [ ] **Task 1.1.5**: Run `pip install -r requirements.txt`

### 1.2 Environment Setup
- [ ] **Task 1.2.1**: Document required env vars in README
- [ ] **Task 1.2.2**: Add placeholder env vars to .env.example

**Files**: `requirements.txt`

---

## Phase 2: Content Fetcher Service

### 2.1 Create Content Fetcher [P]
- [ ] **Task 2.1.1**: Create `app/services/content_fetcher.py`
- [ ] **Task 2.1.2**: Implement `fetch_article_content(url)` function
- [ ] **Task 2.1.3**: Use `httpx` for HTTP requests with timeout
- [ ] **Task 2.1.4**: Use BeautifulSoup to extract article text
- [ ] **Task 2.1.5**: Implement fallback to `article.raw_content` on failure
- [ ] **Task 2.1.6**: Strip HTML tags, normalize whitespace
- [ ] **Task 2.1.7**: Truncate to 10,000 chars max

### 2.2 Content Fetcher Tests
- [ ] **Task 2.2.1**: Create `tests/unit/test_content_fetcher.py`
- [ ] **Task 2.2.2**: Test HTML extraction
- [ ] **Task 2.2.3**: Test fallback behavior
- [ ] **Task 2.2.4**: Test truncation

**Files**: `app/services/content_fetcher.py`, `tests/unit/test_content_fetcher.py`

---

## Phase 3: Claude Report Generation

### 3.1 Create Deep Dive Service [P]
- [ ] **Task 3.1.1**: Create `app/services/deep_dive.py`
- [ ] **Task 3.1.2**: Implement `generate_report(article)` function
- [ ] **Task 3.1.3**: Build report prompt with sections
- [ ] **Task 3.1.4**: Call Claude Sonnet API
- [ ] **Task 3.1.5**: Parse response and validate sections
- [ ] **Task 3.1.6**: Create/update DeepDive record
- [ ] **Task 3.1.7**: Implement retry logic (3 attempts)
- [ ] **Task 3.1.8**: Track token usage and generation time

### 3.2 Report Generation Tests
- [ ] **Task 3.2.1**: Create `tests/contract/test_deep_dive.py`
- [ ] **Task 3.2.2**: Test successful generation (mocked)
- [ ] **Task 3.2.3**: Test retry on API failure
- [ ] **Task 3.2.4**: Test DeepDive record creation

**Files**: `app/services/deep_dive.py`, `tests/contract/test_deep_dive.py`

---

## Phase 4: Google Docs Integration

### 4.1 Create Google Docs Service [P]
- [ ] **Task 4.1.1**: Create `app/services/google_docs.py`
- [ ] **Task 4.1.2**: Implement `get_google_credentials()` from service account
- [ ] **Task 4.1.3**: Implement `create_doc(title, content, folder_id)` function
- [ ] **Task 4.1.4**: Format Markdown content as Doc (headings, paragraphs)
- [ ] **Task 4.1.5**: Return doc_id and doc_url
- [ ] **Task 4.1.6**: Implement retry logic for API calls

### 4.2 Google Docs Tests
- [ ] **Task 4.2.1**: Create `tests/integration/test_google_api.py`
- [ ] **Task 4.2.2**: Test doc creation (requires credentials)
- [ ] **Task 4.2.3**: Test credential loading

**Files**: `app/services/google_docs.py`, `tests/integration/test_google_api.py`

---

## Phase 5: Email & Route Integration

### 5.1 Report Email Template
- [ ] **Task 5.1.1**: Create `app/templates/email/deep_dive_report.html`
- [ ] **Task 5.1.2**: Include report sections with formatting
- [ ] **Task 5.1.3**: Add Google Doc link prominently
- [ ] **Task 5.1.4**: Add original article link

### 5.2 Email Delivery
- [ ] **Task 5.2.1**: Add `send_deep_dive_email(article, report, doc_url)` to `email.py`
- [ ] **Task 5.2.2**: Set subject line format

### 5.3 Route Integration
- [ ] **Task 5.3.1**: Update `/feedback/<id>/good` route in `routes.py`
- [ ] **Task 5.3.2**: Check for existing DeepDive, skip if completed
- [ ] **Task 5.3.3**: Trigger deep dive generation
- [ ] **Task 5.3.4**: Update confirmation page with Doc link

**Files**: `app/templates/email/deep_dive_report.html`, `app/services/email.py`, `app/routes.py`

---

## Phase 6: End-to-End Integration

### 6.1 Orchestration
- [ ] **Task 6.1.1**: Create `generate_deep_dive_for_article(article_id)` orchestrator
- [ ] **Task 6.1.2**: Wire up: content → claude → docs → email
- [ ] **Task 6.1.3**: Handle all error cases gracefully
- [ ] **Task 6.1.4**: Update Article with google_doc_id, google_doc_url

### 6.2 Integration Tests
- [ ] **Task 6.2.1**: Test full flow with mocked services
- [ ] **Task 6.2.2**: Test error handling (Claude fail, Google fail)

**Files**: `app/services/deep_dive.py`, `app/routes.py`

---

## Phase 7: Google Sheets (Optional/Deferred)

### 7.1 Google Sheets Service
- [ ] **Task 7.1.1**: Create `app/services/google_sheets.py`
- [ ] **Task 7.1.2**: Implement `append_article_row(article, doc_url)`
- [ ] **Task 7.1.3**: Configure sheet columns

**Files**: `app/services/google_sheets.py`

---

## MVP Completion Checklist

- [ ] Content fetcher extracts article text
- [ ] Claude generates structured report
- [ ] Google Doc created with report
- [ ] Email sent with report and Doc link
- [ ] Good feedback triggers full flow
- [ ] Errors handled gracefully
- [ ] All tests passing

