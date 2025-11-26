"""
URL Normalization Service

Normalizes URLs for deduplication across RSS feeds and Exa searches.
Removes tracking parameters, standardizes protocols and domains.
"""

import logging
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

logger = logging.getLogger(__name__)

# Query parameters to preserve (article identifiers)
PRESERVE_PARAMS = {'id', 'article', 'p', 'story', 'post', 'page'}

# Query parameters to always remove (tracking)
REMOVE_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'fbclid', 'gclid', 'ref', 'source', 'mc_cid', 'mc_eid',
    '_ga', '_gl', 'ncid', 'ocid', 'sr_share',
}


def normalize_url(url: str) -> str:
    """
    Normalize a URL for deduplication.
    
    Normalization rules:
    1. Convert to lowercase
    2. Standardize to https://
    3. Remove www. prefix
    4. Remove trailing slashes from path
    5. Remove tracking query parameters
    6. Remove fragments (#...)
    
    Args:
        url: Original URL
        
    Returns:
        Normalized URL string
    """
    if not url:
        return ''
    
    try:
        # Parse URL
        parsed = urlparse(url.lower().strip())
        
        # Standardize domain
        netloc = parsed.netloc
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        
        # Remove trailing slashes from path
        path = parsed.path.rstrip('/')
        if not path:
            path = ''
        
        # Filter query parameters
        if parsed.query:
            params = parse_qs(parsed.query, keep_blank_values=False)
            filtered_params = {}
            for key, values in params.items():
                key_lower = key.lower()
                # Keep only essential params, remove tracking
                if key_lower in PRESERVE_PARAMS:
                    filtered_params[key] = values
                elif key_lower not in REMOVE_PARAMS:
                    # Keep unknown params (might be important)
                    filtered_params[key] = values
            query = urlencode(filtered_params, doseq=True) if filtered_params else ''
        else:
            query = ''
        
        # Reconstruct URL
        normalized = urlunparse((
            'https',    # Always https
            netloc,     # Cleaned domain
            path,       # No trailing slash
            '',         # No params section
            query,      # Filtered query string
            ''          # No fragment
        ))
        
        return normalized
        
    except Exception as e:
        logger.warning(f"URL normalization failed for '{url}': {e}")
        return url  # Return original on error


def deduplicate_articles(articles: list[dict]) -> tuple[list[dict], int]:
    """
    Deduplicate articles by normalized URL.
    
    Args:
        articles: List of article dicts with 'url' key
        
    Returns:
        Tuple of (deduplicated articles, duplicate count)
    """
    seen_urls = set()
    unique_articles = []
    duplicates = 0
    
    for article in articles:
        url = article.get('url', '')
        if not url:
            continue
            
        normalized = normalize_url(url)
        
        if normalized in seen_urls:
            duplicates += 1
            logger.debug(f"Duplicate URL skipped: {url}")
        else:
            seen_urls.add(normalized)
            # Store both original and normalized URL
            article['normalized_url'] = normalized
            unique_articles.append(article)
    
    logger.info(f"Deduplication: {len(articles)} → {len(unique_articles)} ({duplicates} duplicates removed)")
    return unique_articles, duplicates

