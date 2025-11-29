# Data Model: Story Quality Filter

**Feature**: 001-story-quality-filter  
**Date**: 2025-11-29

## Schema Changes

### Article Table Extension

Add two new nullable columns to the existing `articles` table:

```sql
ALTER TABLE articles ADD COLUMN content_type VARCHAR(50);
ALTER TABLE articles ADD COLUMN wow_score FLOAT;
```

### SQLAlchemy Model Update

```python
# In app/models.py - Article class

class Article(Base):
    # ... existing fields ...
    
    # Quality Filter Fields (new)
    content_type: Mapped[Optional[str]] = Column(
        String(50), 
        nullable=True,
        comment="Content classification: news_article, event_listing, directory_page, about_page, other_non_news"
    )
    wow_score: Mapped[Optional[float]] = Column(
        Float, 
        nullable=True,
        comment="Wow factor score 0.0-1.0: how surprising/delightful/unusual is this story?"
    )
```

### Field Definitions

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `content_type` | VARCHAR(50) | Yes | NULL | Classification result from Claude. Valid values: `news_article`, `event_listing`, `directory_page`, `about_page`, `other_non_news` |
| `wow_score` | FLOAT | Yes | NULL | Wow factor score from Claude (0.0-1.0). Higher = more surprising/delightful/unusual. |

### Constraints

- `content_type`: No database-level constraint, but application validates against allowed values
- `wow_score`: No constraint, but application expects values in range [0.0, 1.0]

### Indexes

No additional indexes required. These fields are primarily for display and debugging, not query filtering. If admin filtering by content_type becomes frequent, consider:

```sql
CREATE INDEX ix_articles_content_type ON articles(content_type);
```

---

## Migration

### Alembic Migration File

```python
"""Add quality filter fields to articles

Revision ID: xxx_add_quality_fields
Revises: [previous_revision]
Create Date: 2025-11-29

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'xxx_add_quality_fields'
down_revision = '[previous_revision]'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('articles', sa.Column('content_type', sa.String(50), nullable=True))
    op.add_column('articles', sa.Column('wow_score', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('articles', 'wow_score')
    op.drop_column('articles', 'content_type')
```

### Migration Notes

1. **Zero-downtime**: Adding nullable columns with no default is safe for production
2. **Existing data**: Existing articles will have NULL for both fields
3. **Backfill**: Not required - only newly filtered articles need values
4. **Rollback**: Simple column drop, no data loss concerns

---

## Entity Relationships

No new relationships. These are scalar fields on the existing Article entity.

```
Article
├── id (PK)
├── ... (existing fields)
├── filter_score (existing)
├── filter_notes (existing)
├── content_type (NEW)  ← Classification from quality filter
└── wow_score (NEW)     ← Wow factor from quality filter
```

---

## Data Flow

### Before (current)

```
Article Discovery → Claude Filter → filter_score, filter_notes → Threshold Check → Email
```

### After (with quality filter)

```
Article Discovery → Claude Filter → content_type, wow_score, filter_score, filter_notes
                                           ↓
                                    Content Type Check (must be news_article)
                                           ↓
                                    Wow Score Check (must be >= threshold)
                                           ↓
                                    Filter Score Check (must be >= threshold)
                                           ↓
                                         Email
```

---

## Validation Rules

### content_type Validation

Application-level validation in `claude_filter.py`:

```python
VALID_CONTENT_TYPES = {
    "news_article",
    "event_listing", 
    "directory_page",
    "about_page",
    "other_non_news"
}

def validate_content_type(value: str) -> bool:
    return value in VALID_CONTENT_TYPES
```

### wow_score Validation

```python
def validate_wow_score(value: float) -> bool:
    return 0.0 <= value <= 1.0
```

---

## State Transitions

No new state machine. The existing `ArticleStatus` enum remains unchanged.

Quality filter fields are metadata applied during the `PENDING` state before any status transition occurs.

