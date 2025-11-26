# Specification: Amish News Finder

## Overview

A daily automated system that discovers news articles potentially suitable for an Amish newspaper, filters them against editorial criteria, presents them to the editor for review, and generates detailed reports on selected articles.

---

## User Stories

### Daily Discovery Flow

**US-1: Receive Daily Candidates**
As the editor, I want to receive an email at 8am EST each day containing approximately 50 article candidates, so that I have fresh material to review each morning.

**US-2: Quick Rating**
As the editor, I want each article in the email to have three clickable buttons (Good / No / Why Not), so that I can rate articles quickly without leaving my email client.

**US-3: Instant Rejection**
As the editor, when I click "No" on an article, I want it logged as rejected and removed from consideration, so that I don't see it again.

**US-4: Rejection with Feedback**
As the editor, when I click "Why Not" on an article, I want to be taken to a simple web form where I can type a few sentences explaining why this article didn't work, so that the system can learn from my feedback.

**US-5: Approval Triggers Deep Dive**
As the editor, when I click "Good" on an article, I want the system to immediately generate a detailed report and deliver it to me, so that I can begin working on the story.

### Deep Dive Reports

**US-6: Report Contents**
As the editor, when I approve an article, I want to receive a report containing:
- A suggested headline
- Link to the original article
- Outline of key points and themes worth exploring
- Additional sources (related articles, background information, official sources) that would help in research

**US-7: Report Delivery - Email**
As the editor, I want the deep dive report emailed to me immediately after I click "Good," so that I can access it from anywhere.

**US-8: Report Delivery - Google Doc**
As the editor, I want the deep dive report saved as a Google Doc in a "Not Yet Used" folder in my Google Drive, so that I have a persistent, editable copy.

**US-9: Report Delivery - Spreadsheet Log**
As the editor, I want each approved article added as a row in a Google Sheet, so that I have a running log of all potential stories.

### Article Lifecycle Management

**US-10: Track Article Status**
As the editor, I want the Google Sheet to have a checkbox for each article indicating whether I've used it or not, so that I can track my progress.

**US-11: Archive Used Articles**
As the editor, when I mark an article as "used" in the spreadsheet, I want the corresponding Google Doc moved to a "Used" folder, so that my workspace stays organized.

**US-12: Archive Passed Articles**
As the editor, when I mark an article as "not used" in the spreadsheet, I want the corresponding Google Doc moved to a "Passed" folder, so that unused research doesn't clutter my active workspace.

### Feedback and Learning

**US-13: Weekly Refinement**
As the editor, I want the system to analyze my feedback weekly and suggest adjustments to search criteria or source weighting, so that results improve over time.

**US-14: View Current Rules**
As the editor, I want to be able to see the current filtering rules and source priorities the system is using, so that I understand why I'm seeing certain results.

**US-15: Edit Rules**
As the editor, I want to be able to edit the filtering rules and source priorities, so that I can directly shape what the system looks for.

---

## Workflow Diagrams

### Daily Morning Flow

```
8:00 AM EST
    │
    ▼
System searches sources (Exa API + RSS feeds)
    │
    ▼
~200-300 raw candidates retrieved
    │
    ▼
AI filters against Amish criteria
    │
    ▼
~50 candidates pass filter
    │
    ▼
Candidates stored in database
    │
    ▼
Email composed and sent to:
  - john@jlapp.net
  - adam@adamdavidson.com
    │
    ▼
Adam reviews email over morning coffee
```

### Article Rating Flow

```
Adam sees article in email
    │
    ├─── Clicks "Good!" ───────────────────────────┐
    │                                               │
    │                                               ▼
    │                                    AI generates deep dive report
    │                                               │
    │                                    ┌──────────┼──────────┐
    │                                    │          │          │
    │                                    ▼          ▼          ▼
    │                                  Email    Google Doc  Spreadsheet
    │                                              │
    │                                              ▼
    │                                    Doc lands in "Not Yet Used"
    │
    ├─── Clicks "No" ──────────────────────────────┐
    │                                               │
    │                                               ▼
    │                                    Rejection logged in database
    │                                    (no further action)
    │
    └─── Clicks "Why Not" ─────────────────────────┐
                                                    │
                                                    ▼
                                         Browser opens feedback form
                                                    │
                                                    ▼
                                         Adam types explanation
                                                    │
                                                    ▼
                                         Feedback saved to database
```

### Article Lifecycle Flow

```
Article approved ("Good!")
    │
    ▼
Google Doc created in "Not Yet Used" folder
Row added to spreadsheet (checkbox unchecked)
    │
    │
    │ ─── Adam writes and publishes article ───
    │         │
    │         ▼
    │     Adam checks "used" box in spreadsheet
    │         │
    │         ▼
    │     Doc moves to "Used" folder
    │
    │
    │ ─── Adam decides not to use article ───
    │         │
    │         ▼
    │     Adam leaves "used" unchecked, marks "passed"
    │         │
    │         ▼
    │     Doc moves to "Passed" folder
    │
    ▼
Article lifecycle complete
```

### Weekly Refinement Flow

```
Sunday (or chosen day)
    │
    ▼
System analyzes past week's feedback:
  - Rejection patterns
  - "Why Not" explanations
  - Source performance (which sources produced "Good" articles?)
    │
    ▼
System generates suggested rule changes:
  - "Consider excluding stories about X"
  - "Source Y has low approval rate, deprioritize"
  - "Stories about Z are consistently approved, find more"
    │
    ▼
Adam receives refinement report via email
    │
    ▼
Adam reviews, edits if needed, approves changes
    │
    ▼
Updated rules take effect for next week
```

---

## Email Specifications

### Daily Candidate Email

**Subject:** `Plain News Candidates - [Date]`

**Recipients:** 
- john@jlapp.net
- adam@adamdavidson.com

**Format:** HTML email with 50 article blocks. Each block contains:
- Headline (linked to source)
- Source name and date
- 2-3 sentence summary
- 1 sentence on why it might work for Amish readers
- Three buttons: [Good!] [No] [Why Not]

### Deep Dive Report Email

**Subject:** `Story Ready: [Headline]`

**Recipients:** Same as above

**Format:** HTML email containing the full deep dive report (same content as the Google Doc)

### Weekly Refinement Email

**Subject:** `Weekly Refinement Suggestions - [Date Range]`

**Recipients:** Same as above

**Format:** Summary of feedback patterns, suggested changes, link to edit rules

---

## Data Requirements

The system must track:

1. **Every article candidate** ever surfaced (for avoiding duplicates and analyzing patterns)
2. **Every rating decision** (Good, No, or Why Not with notes)
3. **Source metadata** (which sources produce approved articles)
4. **Current filtering rules** (editable by Adam)
5. **Article lifecycle status** (Not Yet Used → Used or Passed)

---

## Integration Points

1. **Exa API** - Primary search engine for finding articles
2. **RSS Feeds** - Secondary source for reliable publications
3. **Anthropic API (Claude)** - Filtering candidates, generating deep dives, analyzing feedback
4. **SendGrid** - Sending emails
5. **Google Drive API** - Creating and moving documents
6. **Google Sheets API** - Maintaining the article log
7. **Web Server** - Handling button clicks from emails, serving feedback form

---

## Non-Requirements

Things this system explicitly does NOT do:

- Publish articles (Adam writes and publishes manually)
- Manage multiple users or permissions
- Provide analytics dashboards
- Support mobile apps
- Integrate with social media
- Handle payments or subscriptions
- Serve content to Amish readers
