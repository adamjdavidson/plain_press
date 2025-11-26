"""
Content Fetcher Service

Fetches full article content from source URLs for deep dive generation.
"""

import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Request timeout (seconds)
FETCH_TIMEOUT = 30

# Maximum content length (characters)
MAX_CONTENT_LENGTH = 10000

# Common article content selectors (tried in order)
CONTENT_SELECTORS = [
    'article',
    '[role="main"]',
    '.article-content',
    '.post-content',
    '.entry-content',
    '.content',
    'main',
    '#content',
]


def fetch_article_content(url: str, fallback_content: Optional[str] = None) -> str:
    """
    Fetch and extract article content from a URL.
    
    Args:
        url: The article URL to fetch
        fallback_content: Content to use if fetch fails (e.g., article.raw_content)
        
    Returns:
        Extracted article text, cleaned and truncated
    """
    try:
        # Fetch the page
        response = httpx.get(
            url,
            timeout=FETCH_TIMEOUT,
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; PlainNewsFinder/1.0)',
                'Accept': 'text/html,application/xhtml+xml',
            }
        )
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form', 'iframe']):
            tag.decompose()
        
        # Try to find article content
        content = None
        for selector in CONTENT_SELECTORS:
            element = soup.select_one(selector)
            if element:
                content = element.get_text(separator='\n', strip=True)
                if len(content) > 200:  # Minimum viable content
                    break
        
        # Fallback to body text
        if not content or len(content) < 200:
            body = soup.find('body')
            if body:
                content = body.get_text(separator='\n', strip=True)
        
        if content:
            content = _clean_text(content)
            logger.info(f"Fetched {len(content)} chars from {url}")
            return _truncate(content, MAX_CONTENT_LENGTH)
        
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP error fetching {url}: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.warning(f"Request error fetching {url}: {e}")
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
    
    # Use fallback content
    if fallback_content:
        logger.info(f"Using fallback content for {url}")
        cleaned = _clean_text(fallback_content)
        return _truncate(cleaned, MAX_CONTENT_LENGTH)
    
    return ""


def _clean_text(text: str) -> str:
    """
    Clean extracted text by normalizing whitespace and removing noise.
    """
    # Strip HTML entities that might remain
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)
    text = re.sub(r'&#\d+;', ' ', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    # Remove common noise patterns
    text = re.sub(r'(Share|Tweet|Email|Print|Subscribe|Newsletter|Advertisement)(\s|$)', '', text, flags=re.IGNORECASE)
    
    return text.strip()


def _truncate(text: str, max_length: int) -> str:
    """
    Truncate text to max length at a word boundary.
    """
    if len(text) <= max_length:
        return text
    
    # Find last space before max_length
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    
    if last_space > max_length * 0.8:  # Only use if we don't lose too much
        truncated = truncated[:last_space]
    
    return truncated + '...'


def extract_from_html(html: str) -> str:
    """
    Extract text content from raw HTML string.
    
    Useful for processing article.raw_content which may contain HTML.
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Remove unwanted elements
    for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
        tag.decompose()
    
    text = soup.get_text(separator=' ', strip=True)
    return _clean_text(text)

