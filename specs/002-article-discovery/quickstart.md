# Quickstart Guide: Article Discovery

## Prerequisites

- Feature 001 (Database Schema) complete and migrated
- Python 3.13+ with virtual environment active
- Railway PostgreSQL database accessible
- API keys for Anthropic and Exa

## Setup Steps

### 1. Install Dependencies

```bash
cd /home/adamd/projects/amish_news
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Add to `.env`:

```bash
# Anthropic API (Claude Haiku filtering)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Exa API (AI-powered web search)
EXA_API_KEY=your-exa-key-here

# Job configuration (optional - defaults shown)
FILTER_SCORE_THRESHOLD=0.5
BATCH_SIZE=15
```

### 3. Seed Initial Data

```bash
# Seed RSS sources and Exa queries from sources.md
python scripts/seed_data.py --sources

# Seed FilterRules from an_story_criteria.md
python scripts/seed_data.py --rules

# Verify seeding
python -c "
from app.database import SessionLocal
from app.models import Source, FilterRule
session = SessionLocal()
print(f'Sources: {session.query(Source).count()}')
print(f'FilterRules: {session.query(FilterRule).count()}')
session.close()
"
```

### 4. Test Individual Components

```bash
# Test RSS fetching
python -c "
from app.services.rss_fetcher import fetch_rss_feed
articles = fetch_rss_feed('https://www.upi.com/rss/OddNews.rss')
print(f'Fetched {len(articles)} articles')
"

# Test Exa search
python -c "
from app.services.exa_searcher import search_articles
results = search_articles('unusual animal friendship heartwarming')
print(f'Found {len(results)} results')
"

# Test Claude filtering
python -c "
from app.services.claude_filter import filter_articles
test_article = {'headline': 'Dog befriends duck', 'content': '...'}
result = filter_articles([test_article])
print(f'Filter score: {result[0][\"filter_score\"]}')
"
```

### 5. Run Discovery Job Manually

```bash
# Full job run
python scripts/daily_job.py

# Expected output:
# Job start: 2025-11-26T13:00:00Z
# RSS sources: 10/10 succeeded, 150 articles
# Exa queries: 12/12 succeeded, 130 articles
# Deduplication: 32 duplicates removed
# Filtering: 248 evaluated, 52 passed (≥0.5)
# Storage: 48 new candidates stored
# Job complete: 185 seconds, $0.82 estimated cost
```

### 6. Verify Results

```bash
# Check articles in database
python -c "
from app.database import SessionLocal
from app.models import Article, ArticleStatus
session = SessionLocal()
pending = session.query(Article).filter(Article.status == ArticleStatus.PENDING).count()
print(f'Pending candidates: {pending}')
session.close()
"
```

### 7. Configure Railway Cron (Production)

Add to `railway.toml`:

```toml
[[crons]]
name = "daily-discovery"
schedule = "0 13 * * *"  # 8am EST = 1pm UTC
command = "python scripts/daily_job.py"
```

Deploy to Railway:
```bash
git add .
git commit -m "feat(002): Add daily article discovery job"
git push railway main
```

## Troubleshooting

### RSS Fetch Errors

```bash
# Check specific feed
python -c "
import feedparser
d = feedparser.parse('https://example.com/feed.xml')
print(f'Version: {d.version}')
print(f'Status: {d.status}')
print(f'Bozo: {d.bozo}')
if d.bozo:
    print(f'Error: {d.bozo_exception}')
"
```

### Exa API Errors

```bash
# Verify API key
python -c "
import os
from exa_py import Exa
exa = Exa(os.environ['EXA_API_KEY'])
result = exa.search('test query', num_results=1)
print(f'Results: {len(result.results)}')
"
```

### Claude API Errors

```bash
# Verify API key
python -c "
import os
from anthropic import Anthropic
client = Anthropic()
response = client.messages.create(
    model='claude-3-haiku-20240307',
    max_tokens=100,
    messages=[{'role': 'user', 'content': 'Say hello'}]
)
print(response.content[0].text)
"
```

## Cost Monitoring

Daily job logs estimated costs. Monitor via:

```bash
# Check recent job logs
grep 'cost_estimate' /var/log/discovery.log | tail -7

# Monthly projection
# ~$0.86/day × 30 = ~$26/month (well under $50 budget)
```

## Next Steps

After verifying discovery works:

1. **Feature 003 (Email Delivery)**: Send daily email with pending candidates
2. **Feature 004 (Feedback Routes)**: Enable Good/No/Why Not buttons
3. **Feature 006 (Weekly Refinement)**: Analyze feedback to improve filtering

