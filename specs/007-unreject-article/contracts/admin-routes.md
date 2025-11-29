# Admin Routes Contract: Unreject Article

## POST /admin/unreject-article

Unreject an article, changing its status from rejected to pending.

### Request

**Method**: POST  
**Content-Type**: application/x-www-form-urlencoded

**Form Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `article_url` | string | Yes | The article's external URL (unique identifier) |

### Response

**Success (302 Found)**:
- Redirects to HTTP Referer header value
- Falls back to `/admin/filter-runs` if no Referer
- Flash message: "Article unrejected successfully"

**Error (404 Not Found)**:
- Article with given URL not found
- Flash message: "Article not found"
- Redirects to Referer or `/admin/filter-runs`

**Error (400 Bad Request)**:
- Article already has status=PENDING
- Flash message: "Article is already pending"
- Redirects to Referer

### Database Changes

On success, updates the Article record:
```
status: REJECTED → PENDING
filter_status: REJECTED → PASSED
```

### Example Usage

```html
<form method="POST" action="/admin/unreject-article">
    <input type="hidden" name="article_url" value="{{ article.external_url }}">
    <button type="submit" class="btn btn-success btn-sm">Unreject</button>
</form>
```

### Security Considerations

- No authentication required (single-user system)
- CSRF protection can be added via Flask-WTF if needed
- URL parameter is validated against database (no SQL injection via ORM)

