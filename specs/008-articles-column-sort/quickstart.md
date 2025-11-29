# Quickstart: Sortable Article Columns

**Feature**: 008-articles-column-sort  
**Date**: 2025-11-29

## Overview

Add clickable column headers to `/admin/articles` that sort articles by that column.

## Implementation Steps

### 1. Update Route (app/routes.py)

Add sort column mapping and update query:

```python
from sqlalchemy import nullslast

# Add after imports
SORT_COLUMNS = {
    'date': Article.discovered_at,
    'score': Article.filter_score,
    'status': Article.status,
    'source': Article.source_name,
    'headline': Article.headline,
}

DEFAULT_DIRECTIONS = {
    'date': 'desc',
    'score': 'desc',
    'status': 'asc',
    'source': 'asc',
    'headline': 'asc',
}

@main.route('/admin/articles')
def admin_articles():
    # ... existing filter params ...
    
    # NEW: Get sort parameters
    sort_column = request.args.get('sort', 'date')
    sort_dir = request.args.get('dir', '')
    
    # Validate sort column
    if sort_column not in SORT_COLUMNS:
        sort_column = 'date'
    
    # Use default direction if not specified or invalid
    if sort_dir not in ('asc', 'desc'):
        sort_dir = DEFAULT_DIRECTIONS.get(sort_column, 'desc')
    
    # ... existing filter logic ...
    
    # Build sort order
    sort_attr = SORT_COLUMNS[sort_column]
    if sort_dir == 'desc':
        order = nullslast(sort_attr.desc())
    else:
        order = nullslast(sort_attr.asc())
    
    # Apply sort (replace existing order_by)
    articles = query.order_by(order).offset(...).limit(...).all()
    
    # Pass sort params to template
    return render_template('admin/articles.html',
        # ... existing params ...
        sort=sort_column,
        dir=sort_dir,
    )
```

### 2. Update Template (app/templates/admin/articles.html)

Add clickable headers with sort indicators:

```html
<!-- Add CSS for sort indicators -->
<style>
  th.sortable {
    cursor: pointer;
    user-select: none;
  }
  th.sortable:hover {
    background: #1e3a0f;
  }
  th .sort-indicator {
    margin-left: 5px;
    opacity: 0.5;
  }
  th.sorted .sort-indicator {
    opacity: 1;
  }
</style>

<!-- Replace static th with sortable links -->
<th class="sortable {% if sort == 'status' %}sorted{% endif %}">
  <a href="{{ url_for('main.admin_articles', 
      status=filters.status,
      min_score=filters.min_score,
      source=filters.source,
      search=filters.search,
      sort='status',
      dir='desc' if sort == 'status' and dir == 'asc' else 'asc'
  ) }}" style="color: white; text-decoration: none;">
    Status
    <span class="sort-indicator">
      {% if sort == 'status' %}{{ '▲' if dir == 'asc' else '▼' }}{% endif %}
    </span>
  </a>
</th>

<!-- Repeat for other sortable columns: Score, Headline, Source, Added -->
```

### 3. Helper Macro (optional)

For cleaner template code, create a sort header macro:

```html
{% macro sort_header(column, label, current_sort, current_dir, filters) %}
<th class="sortable {% if current_sort == column %}sorted{% endif %}">
  <a href="{{ url_for('main.admin_articles', 
      status=filters.status,
      min_score=filters.min_score,
      source=filters.source,
      search=filters.search,
      sort=column,
      dir='desc' if current_sort == column and current_dir == 'asc' else 'asc'
  ) }}" style="color: white; text-decoration: none;">
    {{ label }}
    <span class="sort-indicator">
      {% if current_sort == column %}{{ '▲' if current_dir == 'asc' else '▼' }}{% endif %}
    </span>
  </a>
</th>
{% endmacro %}

<!-- Usage -->
{{ sort_header('status', 'Status', sort, dir, filters) }}
{{ sort_header('score', 'Score', sort, dir, filters) }}
{{ sort_header('headline', 'Headline', sort, dir, filters) }}
{{ sort_header('source', 'Source', sort, dir, filters) }}
{{ sort_header('date', 'Added', sort, dir, filters) }}
```

## Testing Checklist

1. [ ] Click "Added" header → sorts by date (newest first)
2. [ ] Click "Added" again → reverses to oldest first
3. [ ] Click "Score" → sorts by score (highest first)
4. [ ] Click "Status" → groups by status alphabetically
5. [ ] Sort persists with filters applied (status, search)
6. [ ] Sort persists across pagination (page 2 shows sorted order)
7. [ ] Default page load shows newest articles first

