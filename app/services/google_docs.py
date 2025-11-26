"""
Google Docs Integration Service

Creates and manages Google Docs for deep dive reports.
"""

import logging
import os
import re
from typing import Optional, Tuple

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Required scopes
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive.file',
]

# Retry settings
MAX_RETRIES = 3


def get_credentials():
    """
    Get Google API credentials from service account file.
    
    Requires GOOGLE_APPLICATION_CREDENTIALS environment variable
    pointing to the service account JSON file.
    """
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
    
    credentials = service_account.Credentials.from_service_account_file(
        creds_path, scopes=SCOPES
    )
    return credentials


def create_doc(
    title: str,
    content: str,
    folder_id: Optional[str] = None
) -> Tuple[str, str]:
    """
    Create a Google Doc with the given content.
    
    Args:
        title: Document title
        content: Markdown-ish content to insert
        folder_id: Optional Drive folder ID (defaults to GOOGLE_DRIVE_FOLDER_ID env var)
        
    Returns:
        Tuple of (doc_id, doc_url)
    """
    folder_id = folder_id or os.environ.get('GOOGLE_DRIVE_FOLDER_ID')
    
    credentials = get_credentials()
    docs_service = build('docs', 'v1', credentials=credentials)
    drive_service = build('drive', 'v3', credentials=credentials)
    
    # Create empty document
    doc = docs_service.documents().create(body={'title': title}).execute()
    doc_id = doc['documentId']
    
    logger.info(f"Created Google Doc: {doc_id}")
    
    # Move to folder if specified
    if folder_id:
        try:
            # Get current parents
            file = drive_service.files().get(
                fileId=doc_id, fields='parents'
            ).execute()
            previous_parents = ','.join(file.get('parents', []))
            
            # Move to new folder
            drive_service.files().update(
                fileId=doc_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            
            logger.info(f"Moved doc to folder: {folder_id}")
        except HttpError as e:
            logger.warning(f"Could not move doc to folder: {e}")
    
    # Insert content
    if content:
        requests = _build_content_requests(content)
        if requests:
            docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
    
    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    
    return doc_id, doc_url


def _build_content_requests(content: str) -> list:
    """
    Convert markdown-style content to Google Docs API requests.
    
    Supports:
    - # Heading 1
    - ## Heading 2
    - Plain paragraphs
    - - Bullet points
    """
    requests = []
    lines = content.strip().split('\n')
    
    # We need to insert in reverse order because we're always inserting at index 1
    insert_index = 1
    
    for line in lines:
        line = line.strip()
        if not line:
            # Empty line - add paragraph break
            requests.append({
                'insertText': {
                    'location': {'index': insert_index},
                    'text': '\n'
                }
            })
            insert_index += 1
            continue
        
        # Determine formatting
        style = None
        if line.startswith('# '):
            text = line[2:]
            style = 'HEADING_1'
        elif line.startswith('## '):
            text = line[3:]
            style = 'HEADING_2'
        elif line.startswith('### '):
            text = line[4:]
            style = 'HEADING_3'
        elif line.startswith('- ') or line.startswith('* '):
            text = '• ' + line[2:]  # Convert to bullet
            style = None
        else:
            text = line
            style = None
        
        # Insert text
        text_with_newline = text + '\n'
        requests.append({
            'insertText': {
                'location': {'index': insert_index},
                'text': text_with_newline
            }
        })
        
        # Apply paragraph style if needed
        if style:
            requests.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': insert_index,
                        'endIndex': insert_index + len(text_with_newline)
                    },
                    'paragraphStyle': {
                        'namedStyleType': style
                    },
                    'fields': 'namedStyleType'
                }
            })
        
        insert_index += len(text_with_newline)
    
    return requests


def share_doc_with_user(doc_id: str, email: str, role: str = 'writer') -> bool:
    """
    Share a document with a specific user.
    
    Args:
        doc_id: The document ID
        email: Email address to share with
        role: Permission role ('reader', 'writer', 'commenter')
        
    Returns:
        True if successful
    """
    try:
        credentials = get_credentials()
        drive_service = build('drive', 'v3', credentials=credentials)
        
        permission = {
            'type': 'user',
            'role': role,
            'emailAddress': email
        }
        
        drive_service.permissions().create(
            fileId=doc_id,
            body=permission,
            sendNotificationEmail=False
        ).execute()
        
        logger.info(f"Shared doc {doc_id} with {email}")
        return True
        
    except HttpError as e:
        logger.error(f"Error sharing doc: {e}")
        return False

