# Quickstart: RSS Feed Management

**Feature**: 005-rss-feed-management  
**Date**: 2025-11-28

## Prerequisites

- Python 3.11+ installed
- Virtual environment activated (`source venv/bin/activate`)
- Database running and migrated
- Flask app configured

## Development Setup

```bash
# Navigate to project root
cd /home/adamd/projects/amish_news

# Activate virtual environment
source venv/bin/activate

# Ensure dependencies installed
pip install -r requirements.txt

# Database should be ready (no new migrations needed)
```

## Running the App

```bash
# Development server
flask run --debug

# Access admin sources page at:
# http://localhost:5000/admin/sources
```

## Feature Overview

### Add New RSS Feed
1. Navigate to `/admin/sources`
2. Fill in the "Add New Feed" form:
   - **Name**: Display name (e.g., "BBC Science")
   - **URL**: RSS feed URL (e.g., "https://feeds.bbci.co.uk/news/science/rss.xml")
   - **Notes**: Optional description
3. Click "Add Feed"
4. System validates the URL is a valid RSS/Atom feed
5. Feed appears in the list as active

### View RSS Feeds
- Navigate to `/admin/sources`
- See all RSS feeds with:
  - Name and URL
  - Status (Active/Paused)
  - Trust Score
  - Articles Surfaced/Approved/Rejected
  - Last Fetched timestamp

### Pause/Resume Feed
- Click "Pause" button next to any active feed
- Feed stops being fetched in daily pipeline
- Click "Resume" to reactivate

### Delete Feed
- Click "Delete" button next to any feed
- Confirm deletion in dialog
- Note: Cannot delete feeds that have associated articles

## Testing

```bash
# Run all tests
pytest

# Run integration tests only
pytest tests/integration/

# Test source management specifically
pytest tests/integration/test_source_management.py -v
```

## Manual Testing Checklist

- [ ] Add a valid RSS feed (e.g., https://www.goodnewsnetwork.org/feed/)
- [ ] Add an invalid URL (should show error)
- [ ] Add a duplicate URL (should show error)
- [ ] View the feed list (should show new feed)
- [ ] Pause a feed (should show as paused)
- [ ] Resume the feed (should show as active)
- [ ] Delete a feed with no articles (should succeed)
- [ ] Try to delete a feed with articles (should show error)

## File Locations

| File | Purpose |
|------|---------|
| `app/routes.py` | Route handlers (add to existing file) |
| `app/templates/admin/sources.html` | Feed management UI (new file) |
| `tests/integration/test_source_management.py` | Integration tests (new file) |

## Related Documentation

- [Specification](spec.md) - Feature requirements
- [Data Model](data-model.md) - Source entity details
- [API Contract](contracts/api.md) - Endpoint specifications
- [Research](research.md) - Technical decisions

