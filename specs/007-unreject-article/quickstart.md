# Quickstart: Unreject Article Button

## Overview

Add "Unreject" buttons to admin pages that allow John to rescue incorrectly rejected articles with a single click.

## Implementation Steps

### Step 1: Add Flask Route

Add to `app/routes.py`:

```python
@app.route('/admin/unreject-article', methods=['POST'])
def unreject_article():
    """Unreject an article, changing status from rejected to pending."""
    from flask import request, redirect, flash, url_for
    
    article_url = request.form.get('article_url')
    if not article_url:
        flash('No article URL provided', 'error')
        return redirect(request.referrer or url_for('admin_filter_runs'))
    
    session = SessionLocal()
    try:
        article = session.query(Article).filter(
            Article.external_url == article_url
        ).first()
        
        if not article:
            flash('Article not found', 'error')
            return redirect(request.referrer or url_for('admin_filter_runs'))
        
        if article.status == ArticleStatus.PENDING:
            flash('Article is already pending', 'info')
            return redirect(request.referrer or url_for('admin_filter_runs'))
        
        # Update status
        article.status = ArticleStatus.PENDING
        article.filter_status = FilterStatus.PASSED
        session.commit()
        
        flash(f'Article unrejected: {article.headline[:50]}...', 'success')
        return redirect(request.referrer or url_for('admin_filter_runs'))
        
    finally:
        session.close()
```

### Step 2: Add Button to Rejection Analysis Template

In `app/templates/admin/rejection_analysis.html`, add form button for each article:

```html
<form method="POST" action="{{ url_for('unreject_article') }}" style="display:inline;">
    <input type="hidden" name="article_url" value="{{ trace.article_url }}">
    <button type="submit" class="btn btn-success btn-sm">Unreject</button>
</form>
```

### Step 3: Add Button to Article Journey Template

In `app/templates/admin/article_journey.html`, add button near article title:

```html
{% if article and article.status.value == 'rejected' %}
<form method="POST" action="{{ url_for('unreject_article') }}" style="display:inline;">
    <input type="hidden" name="article_url" value="{{ article_url }}">
    <button type="submit" class="btn btn-success">Unreject This Article</button>
</form>
{% endif %}
```

### Step 4: Add Flash Message Display

Ensure base admin template shows flash messages:

```html
{% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
    {% for category, message in messages %}
      <div class="alert alert-{{ category }}">{{ message }}</div>
    {% endfor %}
  {% endif %}
{% endwith %}
```

## Testing

1. Navigate to `/admin/filter-runs`
2. Click into a run, then view rejection analysis
3. Click "Unreject" on any article
4. Verify flash message appears
5. Check `/admin/articles` - article should show status=pending

## Files Changed

- `app/routes.py` - Add unreject_article route
- `app/templates/admin/rejection_analysis.html` - Add button
- `app/templates/admin/article_journey.html` - Add button
- `app/templates/admin/filter_run_detail.html` - Add button (optional)

