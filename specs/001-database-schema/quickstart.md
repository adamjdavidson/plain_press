# Quickstart: Database Schema Setup

**Feature**: 001-database-schema  
**Date**: 2025-11-26  
**Audience**: Developers setting up local environment or deploying to Railway

## Prerequisites

- Python 3.11+
- PostgreSQL 15+ (local or Railway)
- Git repository cloned
- Virtual environment tool (venv, poetry, etc.)

---

## Step 1: Install Dependencies

```bash
# Create and activate virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install sqlalchemy==2.0.23 \
            alembic==1.12.1 \
            psycopg2-binary==2.9.9 \
            python-dotenv==1.0.0

# Or install from requirements.txt (if created)
pip install -r requirements.txt
```

---

## Step 2: Configure Database Connection

### Local Development

Create `.env` file in repository root:

```bash
# .env (local development)
DATABASE_URL=postgresql://localhost:5432/amish_news_dev
FLASK_ENV=development
FLASK_DEBUG=True
```

**Start local PostgreSQL**:
```bash
# macOS (Homebrew)
brew services start postgresql@15

# Linux (systemd)
sudo systemctl start postgresql

# Docker (alternative)
docker run --name amish-postgres \
  -e POSTGRES_PASSWORD=devpassword \
  -e POSTGRES_DB=amish_news_dev \
  -p 5432:5432 \
  -d postgres:15
```

**Create database**:
```bash
# If using system PostgreSQL
createdb amish_news_dev

# If using Docker PostgreSQL
docker exec -it amish-postgres createdb -U postgres amish_news_dev
```

### Railway Deployment

Railway automatically provisions PostgreSQL and sets `DATABASE_URL` environment variable. No manual database creation needed.

**Configure Railway environment** (via Railway dashboard):
```bash
DATABASE_URL=${{Postgres.DATABASE_URL}}  # Auto-populated by Railway
FLASK_ENV=production
FLASK_DEBUG=False
```

---

## Step 3: Initialize Alembic

**Create Alembic configuration** (first time only):

```bash
# Initialize Alembic
alembic init migrations

# This creates:
# - migrations/ directory
# - migrations/versions/ (empty, for migration files)
# - migrations/env.py (Alembic environment config)
# - alembic.ini (Alembic settings)
```

**Configure Alembic to use application models**:

Edit `migrations/env.py`:

```python
# migrations/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import your models' Base
from app.models import Base

# this is the Alembic Config object
config = context.config

# Override sqlalchemy.url with DATABASE_URL from environment
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

# Rest of env.py remains default...
```

Edit `alembic.ini` (set SQLAlchemy URL placeholder):

```ini
# alembic.ini
[alembic]
script_location = migrations
prepend_sys_path = .

# This will be overridden by env.py from DATABASE_URL
sqlalchemy.url = 

[loggers]
keys = root,sqlalchemy,alembic
# ... (rest remains default)
```

---

## Step 4: Create Database Models

**Create application models** in `app/models.py`:

See `data-model.md` for complete SQLAlchemy model definitions. Key structure:

```python
# app/models.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

# Create declarative base
Base = declarative_base()

# Import all model classes
from app.models.article import Article
from app.models.source import Source
from app.models.feedback import Feedback
from app.models.filter_rule import FilterRule
from app.models.email_batch import EmailBatch
from app.models.deep_dive import DeepDive
from app.models.refinement_log import RefinementLog

# Database engine and session factory
def create_db_engine():
    database_url = os.getenv("DATABASE_URL")
    return create_engine(
        database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=os.getenv("FLASK_DEBUG", "False") == "True"
    )

engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

**Alternative: Single file approach** (acceptable for MVP):

All models can live in `app/models.py` as one file (simpler for small projects). See `data-model.md` for complete model code.

---

## Step 5: Generate Initial Migration

**Create first migration** (autogenerate from models):

```bash
# Generate migration
alembic revision --autogenerate -m "Initial schema"

# This creates: migrations/versions/XXXXX_initial_schema.py
```

**Review generated migration**:

```bash
# Open migration file
cat migrations/versions/*_initial_schema.py
```

**Expected content**:
- Creates all ENUM types (article_status, source_type, etc.)
- Creates all tables (articles, sources, feedback, etc.)
- Creates all indexes (ix_articles_daily_email, etc.)
- Creates foreign key constraints

**Manual additions** (if not auto-generated):

```python
# In upgrade() function, add CHECK constraint
op.create_check_constraint(
    "ck_articles_filter_score_range",
    "articles",
    "filter_score >= 0.0 AND filter_score <= 1.0"
)

# Add pgcrypto extension for gen_random_uuid()
op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
```

---

## Step 6: Run Migrations

**Apply migration** (creates tables in database):

```bash
# Run all pending migrations
alembic upgrade head

# Expected output:
# INFO  [alembic.runtime.migration] Running upgrade  -> abc123, Initial schema
```

**Verify tables created**:

```bash
# Connect to database
psql $DATABASE_URL

# List tables
\dt

# Expected tables:
# articles, sources, feedback, filter_rules, email_batches, deep_dives, refinement_logs, alembic_version
```

---

## Step 7: Seed Initial Data (Optional)

**Create seed script** for FilterRules from story_criteria.md:

```python
# scripts/seed_filter_rules.py
from app.database import SessionLocal
from app.models import FilterRule, RuleType, RuleSource

def seed_filter_rules():
    session = SessionLocal()
    
    try:
        # Check if rules already exist
        existing_count = session.query(FilterRule).count()
        if existing_count > 0:
            print(f"Filter rules already seeded ({existing_count} rules). Skipping.")
            return
        
        # Seed rules from story_criteria.md
        rules = [
            FilterRule(
                rule_type=RuleType.MUST_HAVE,
                rule_text="Story must be wholesome and uplifting",
                priority=1,
                source=RuleSource.ORIGINAL
            ),
            FilterRule(
                rule_type=RuleType.MUST_AVOID,
                rule_text="Avoid individual hero/achievement stories (conflicts with Amish humility)",
                priority=2,
                source=RuleSource.ORIGINAL
            ),
            FilterRule(
                rule_type=RuleType.GOOD_TOPIC,
                rule_text="Animals, food oddities, community efforts, nature, small-town traditions",
                priority=3,
                source=RuleSource.ORIGINAL
            ),
            FilterRule(
                rule_type=RuleType.MUST_AVOID,
                rule_text="No modern technology, death/tragedy, violence, politics, military content",
                priority=4,
                source=RuleSource.ORIGINAL
            ),
            # Add more rules from an_story_criteria.md
        ]
        
        session.add_all(rules)
        session.commit()
        print(f"Seeded {len(rules)} filter rules successfully.")
    
    except Exception as e:
        session.rollback()
        print(f"Error seeding rules: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    seed_filter_rules()
```

**Run seed script**:

```bash
python scripts/seed_filter_rules.py
```

---

## Step 8: Verify Setup

**Test database connectivity**:

```python
# scripts/test_connection.py
from app.database import SessionLocal
from app.models import Article, Source, FilterRule

def test_connection():
    session = SessionLocal()
    
    try:
        # Query filter rules
        rules = session.query(FilterRule).all()
        print(f"✅ Database connected. Found {len(rules)} filter rules.")
        
        # Query articles (should be empty)
        article_count = session.query(Article).count()
        print(f"✅ Articles table accessible. Count: {article_count}")
        
        # Query sources (should be empty)
        source_count = session.query(Source).count()
        print(f"✅ Sources table accessible. Count: {source_count}")
        
        print("\n✅ All tables accessible and operational!")
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    test_connection()
```

**Run test**:

```bash
python scripts/test_connection.py

# Expected output:
# ✅ Database connected. Found 4 filter rules.
# ✅ Articles table accessible. Count: 0
# ✅ Sources table accessible. Count: 0
# ✅ All tables accessible and operational!
```

---

## Common Commands Reference

### Alembic Commands

```bash
# Create new migration (autogenerate)
alembic revision --autogenerate -m "Add new column"

# Create empty migration (manual)
alembic revision -m "Add custom index"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current migration version
alembic current

# Show migration history
alembic history

# Stamp database (mark as migrated without running)
alembic stamp head
```

### Database Commands

```bash
# Connect to database
psql $DATABASE_URL

# List tables
\dt

# Describe table
\d articles

# Show indexes
\di

# Show constraints
\d+ articles

# Query table
SELECT * FROM filter_rules;
```

---

## Troubleshooting

### Issue: "relation does not exist"

**Cause**: Migrations not applied.

**Solution**:
```bash
alembic upgrade head
```

### Issue: "password authentication failed"

**Cause**: Incorrect DATABASE_URL credentials.

**Solution**:
```bash
# Check DATABASE_URL
echo $DATABASE_URL

# Verify connection manually
psql $DATABASE_URL

# Update .env with correct credentials
```

### Issue: "column 'filter_score' is not of type float"

**Cause**: Migration applied with wrong column type.

**Solution**:
```bash
# Rollback and reapply
alembic downgrade -1
alembic upgrade head
```

### Issue: "duplicate key value violates unique constraint"

**Cause**: Attempting to insert duplicate article URL or feedback for same article.

**Solution**: This is expected behavior (constraint working correctly). Check application logic to avoid duplicates before insertion.

### Issue: Alembic can't find models

**Cause**: Import path incorrect in `migrations/env.py`.

**Solution**:
```python
# Ensure correct import in env.py
from app.models import Base  # Adjust path if needed

# Add repository root to Python path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
```

---

## Railway Deployment

**Automatic migration on deploy**:

Create `Procfile` or railway.toml with migration command:

```toml
# railway.toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "alembic upgrade head && gunicorn app:create_app()"
healthcheckPath = "/health"
restartPolicyType = "on_failure"
```

**Or use Railway build command** (dashboard):
```bash
# Build Command (leave empty for default)

# Start Command
alembic upgrade head && gunicorn -w 4 -b 0.0.0.0:$PORT app:create_app()
```

**Verify migration ran**:
```bash
# Check Railway logs (dashboard or CLI)
railway logs

# Look for:
# INFO  [alembic.runtime.migration] Running upgrade  -> abc123, Initial schema
```

---

## Next Steps

After database setup complete:

1. ✅ **Database schema established** - All tables created, constraints enforced
2. ⏭️ **Implement article discovery** - Create service to fetch from Exa/RSS (feature 002)
3. ⏭️ **Implement email delivery** - Create service to send daily email (feature 003)
4. ⏭️ **Implement feedback routes** - Create Flask routes for Good/No/Why Not buttons (feature 004)

---

## Additional Resources

- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/15/)
- [Railway PostgreSQL Guide](https://docs.railway.app/databases/postgresql)

---

**Quickstart Complete**: Database is ready for application development!

