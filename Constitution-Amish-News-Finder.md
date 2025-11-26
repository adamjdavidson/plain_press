# Constitution: Amish News Finder

## What This Project Is

This is a tool built for **John Lapp**, who publishes a newspaper for an Amish readership. The newspaper is called **Plain News**. John is the sole editor and needs approximately **20 articles per month**.

John has found that having a larger pool of candidates to choose from leads to better final selections. He wants to receive **~50 article candidates per day** via email, which he will then rate and filter down to his monthly 20.

This tool automates the discovery and initial filtering of news stories that might be appropriate for an Amish audience. It does not write the articles—John does that. It finds raw material.

## Who Uses This Tool

**John Lapp** is the only user. There are no other users. There is no public-facing interface. This is a personal productivity tool for a single editor.

John will:
- Receive a daily email with article candidates
- Rate articles as Good, No, or provide feedback on why something didn't work
- Receive detailed reports on articles he marks as "Good"
- Occasionally review and refine the criteria the system uses

## Core Principles

### 1. The Tool Serves the Editor, Not the Reader

The Amish readers never interact with this system. They read John's newspaper. This tool helps John find stories faster. All interfaces, emails, and reports are designed for John's workflow, not for publication.

### 2. Volume Creates Quality

John needs 20 articles/month but wants 50 candidates/day (~1,500/month). This 1.3% selection rate gives him abundant choice. The system should err on the side of including borderline candidates rather than being too restrictive—John can quickly reject, but he can't review what he never sees.

### 3. Learning Over Time

John's feedback should improve future searches. When he rejects an article with a note like "too focused on individual achievement," the system should learn to weight against similar stories. This learning happens weekly, not in real-time, to avoid chasing noise.

### 4. Simplicity Over Features

John is one person. He doesn't need dashboards, analytics, or complex workflows. He needs:
- One email per day
- Three buttons per article (Good / No / Why Not)
- Reports delivered to his email and Google Drive

If a feature doesn't directly serve these core actions, it shouldn't exist.

### 5. Transparency in Filtering

The system uses AI to filter candidates against Amish-appropriate criteria. John should be able to see the current rules the system is using and edit them. No black box.

### 6. Cheap and Reliable

This is a small operation. Monthly costs should stay under $50. Reliability matters more than performance—a delayed email is fine, a lost email is not.

## What Success Looks Like

- John spends 15-20 minutes each morning reviewing candidates
- He marks 2-5 as "Good" on a typical day
- The "Good" articles consistently become published pieces
- Over time, the ratio of Good to No improves as the system learns
- John rarely thinks "I wish I had seen something about X" because the system surfaces diverse, surprising content

## What Failure Looks Like

- John gets overwhelmed by volume or poor quality
- The system surfaces the same types of stories repeatedly
- "Good" articles frequently don't work out when John tries to write them
- The feedback loop doesn't noticeably improve results
- Technical issues interrupt the daily flow
