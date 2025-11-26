# Platform and Framework Suggestions

## Recommended Stack

### Hosting: Railway
**URL**: https://railway.app

**Why Railway:**
- All-in-one platform (app hosting, database, cron jobs)
- Simple deployment (push code, it deploys)
- Built-in Postgres with one click
- Native cron job support
- Environment variables UI for API keys
- Reasonable pricing (~$5/month base + usage)
- No sysadmin work required

**Alternatives considered:**

| Platform | Pros | Cons | Verdict |
|----------|------|------|---------|
| Render | Similar to Railway | Cron jobs require separate service | Slightly more complex |
| Fly.io | Great performance, global edge | More configuration required | Overkill for this use case |
| Hetzner VPS | Cheapest ($4/mo) | Manual Postgres setup, sysadmin work | Too much maintenance |
| DigitalOcean App Platform | Familiar | More expensive than Railway for equivalent | No advantage |
| Vercel | Great for frontend | Not ideal for backend cron jobs | Wrong tool |

**Railway setup will include:**
- One Python web service (Flask)
- One Postgres database
- Cron job configuration via `railway.toml` or Procfile

---

### Language: Python 3.11+

**Why Python:**
- Best Anthropic SDK support
- Simple, readable code
- Excellent libraries for RSS parsing, HTTP requests
- Adam may want to read/modify code; Python is approachable

---

### Web Framework: Flask

**Why Flask:**
- Minimal, simple
- Only need a few routes (handle button clicks, serve feedback form)
- No need for Django's complexity
- Easy to understand codebase

**Routes needed:**
- `GET /good/<article_id>` - Triggers deep dive
- `GET /no/<article_id>` - Logs rejection
- `GET /why-not/<article_id>` - Shows feedback form
- `POST /feedback` - Saves feedback
- `GET /rules` - View current filtering rules
- `POST /rules` - Update rules
- `GET /health` - Health check for Railway

---

### Database: PostgreSQL

**Why Postgres:**
- Robust, reliable
- Railway provides managed Postgres
- Good for structured data with relationships
- Can handle years of article history without issues
- Free tier sufficient for this workload

**ORM**: SQLAlchemy (simple, standard)

---

### Email: SendGrid

**Why SendGrid:**
- Reliable delivery
- Good free tier (100 emails/day, more than enough)
- Simple API
- HTML email support for buttons

**Alternative considered:**
- Resend: Newer, simpler API, but less proven at scale
- Amazon SES: Cheaper at volume, but more setup required

---

### Search: Exa API

**Why Exa:**
- Better for semantic search than Google/Bing APIs
- Returns full content, not just snippets
- Good for finding "oddball" content
- Used successfully in the prototype searches

**Complement with:**
- `feedparser` library for RSS feeds
- Direct HTTP requests to known sources

---

### AI: Anthropic Claude API

**Why Claude:**
- This project is already using Claude
- Excellent at nuanced filtering tasks
- Good at generating structured reports
- Haiku model for filtering (cheap, fast)
- Sonnet model for deep dives (better quality)

**Model recommendations:**
- `claude-3-haiku-20240307` for daily filtering (cheap, fast, good enough)
- `claude-sonnet-4-20250514` for deep dive reports (higher quality)

---

### Google Integration: Google APIs

**Required APIs:**
- Google Drive API (create and move documents)
- Google Sheets API (read/write spreadsheet)
- Google Docs API (create formatted documents)

**Authentication:**
- Service account with JSON key file
- Share target folder and spreadsheet with service account email

**Libraries:**
- `google-api-python-client`
- `google-auth`
- `google-auth-oauthlib`

---

## Dependency List

```
# requirements.txt

# Web framework
flask==3.0.0
gunicorn==21.2.0

# Database
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.13.0  # migrations

# HTTP and parsing
requests==2.31.0
feedparser==6.0.10
beautifulsoup4==4.12.2

# Email
sendgrid==6.11.0

# AI
anthropic==0.18.0
exa-py==1.0.0  # Exa search API

# Google
google-api-python-client==2.111.0
google-auth==2.25.2
google-auth-oauthlib==1.2.0

# Utilities
python-dotenv==1.0.0
schedule==1.2.1  # for cron-like scheduling if needed
pytz==2024.1  # timezone handling
```

---

## Environment Variables

```
# .env.example

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Exa Search
EXA_API_KEY=...

# SendGrid
SENDGRID_API_KEY=SG....
FROM_EMAIL=news@yourdomain.com

# Google (path to service account JSON)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_DRIVE_FOLDER_ID=...
GOOGLE_SHEET_ID=...

# App settings
EMAIL_RECIPIENTS=john@jlapp.net,adam@adamdavidson.com
FLASK_SECRET_KEY=...
BASE_URL=https://your-app.railway.app
```

---

## Project Structure

```
amish-news-finder/
├── README.md
├── requirements.txt
├── railway.toml
├── Procfile
├── .env.example
│
├── docs/
│   ├── constitution.md
│   ├── specification.md
│   ├── story_criteria.md
│   ├── sources.md
│   ├── platform_framework_suggestions.md
│   ├── data_model.md
│   ├── feedback_loop.md
│   └── email_format.md
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py          # SQLAlchemy models
│   ├── routes.py          # Flask routes
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── search.py      # Exa + RSS fetching
│   │   ├── filter.py      # Claude filtering
│   │   ├── email.py       # SendGrid sending
│   │   ├── deep_dive.py   # Report generation
│   │   ├── google.py      # Drive/Sheets integration
│   │   └── refinement.py  # Weekly learning
│   │
│   └── templates/
│       ├── daily_email.html
│       ├── deep_dive_email.html
│       ├── feedback_form.html
│       └── rules_editor.html
│
├── scripts/
│   ├── daily_job.py       # Main cron entry point
│   ├── weekly_refinement.py
│   └── setup_google.py    # One-time Google setup
│
├── migrations/            # Alembic migrations
│
└── tests/
    ├── test_filter.py
    ├── test_search.py
    └── test_email.py
```

---

## Railway Configuration

```toml
# railway.toml

[build]
builder = "nixpacks"

[deploy]
startCommand = "gunicorn app:create_app() --bind 0.0.0.0:$PORT"
healthcheckPath = "/health"
healthcheckTimeout = 100

[[cron]]
schedule = "0 13 * * *"  # 8am EST = 1pm UTC
command = "python scripts/daily_job.py"

[[cron]]
schedule = "0 14 * * 0"  # Sunday 9am EST = 2pm UTC
command = "python scripts/weekly_refinement.py"
```

---

## Cost Estimate

| Service | Monthly Cost |
|---------|--------------|
| Railway (app + db) | ~$5-10 |
| SendGrid | Free (under 100/day) |
| Anthropic API | ~$5-15 (depends on volume) |
| Exa API | ~$5-10 (depends on queries) |
| Google APIs | Free |
| **Total** | **~$15-35/month** |

This is well under the $50 budget target.

---

## Scaling Notes

This architecture can easily handle:
- Years of article history (Postgres scales fine)
- Higher daily volumes if needed
- Additional email recipients
- More sources

If the system ever needed to handle multiple publications or users, the main changes would be:
- Add user authentication
- Add publication/tenant model
- Separate databases or schemas per tenant

But for now, single-user simplicity is the right choice.
