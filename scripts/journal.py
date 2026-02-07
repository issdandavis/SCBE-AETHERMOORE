#!/usr/bin/env python3
"""SCBE-AETHERMOORE Encrypted Journal Helper

Encrypts journal entries with AES-256-GCM and stores them in Dropbox.
Links entries to Notion Journal Index page.

Usage:
    python journal.py add "Your journal entry text"
    python journal.py list
    python journal.py read <entry_id>
"""

import os
import sys
import json
import base64
import hashlib
from datetime import datetime
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import dropbox
import requests

# Configuration from environment
DROPBOX_TOKEN = os.environ.get('DROPBOX_TOKEN')
JOURNAL_KEY = os.environ.get('SCBE_JOURNAL_KEY')  # Base64-encoded 32-byte key
NOTION_TOKEN = os.environ.get('NOTION_TOKEN')
NOTION_JOURNAL_DB = os.environ.get('NOTION_JOURNAL_DB')

DROPBOX_JOURNAL_PATH = '/SCBE-AETHERMOORE/journal'


def get_key() -> bytes:
    """Load AES-256-GCM key from environment."""
    if not JOURNAL_KEY:
        raise ValueError("SCBE_JOURNAL_KEY environment variable not set")
    return base64.b64decode(JOURNAL_KEY)


def encrypt_entry(plaintext: str) -> tuple[bytes, bytes]:
    """Encrypt journal entry with AES-256-GCM.
    
    Returns:
        (ciphertext, nonce) tuple
    """
    key = get_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce for GCM
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
    return ciphertext, nonce


def decrypt_entry(ciphertext: bytes, nonce: bytes) -> str:
    """Decrypt journal entry."""
    key = get_key()
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode('utf-8')


def create_entry_id() -> str:
    """Generate unique entry ID from timestamp."""
    return datetime.utcnow().strftime('%Y%m%d_%H%M%S')


def save_to_dropbox(entry_id: str, data: dict) -> str:
    """Save encrypted entry to Dropbox."""
    if not DROPBOX_TOKEN:
        raise ValueError("DROPBOX_TOKEN environment variable not set")
    
    dbx = dropbox.Dropbox(DROPBOX_TOKEN)
    
    # Serialize to JSON with base64-encoded binary fields
    payload = {
        'id': entry_id,
        'date': data['date'],
        'topic': data.get('topic', ''),
        'linked_notions': data.get('linked_notions', []),
        'linked_github_refs': data.get('linked_github_refs', []),
        'ciphertext': base64.b64encode(data['ciphertext']).decode('ascii'),
        'nonce': base64.b64encode(data['nonce']).decode('ascii'),
    }
    
    file_path = f"{DROPBOX_JOURNAL_PATH}/{entry_id}.json"
    dbx.files_upload(
        json.dumps(payload, indent=2).encode('utf-8'),
        file_path,
        mode=dropbox.files.WriteMode.overwrite
    )
    
    return file_path


def add_to_notion_index(entry_id: str, summary: str, date: str) -> None:
    """Add one-line link to Notion Journal Index page."""
    if not NOTION_TOKEN or not NOTION_JOURNAL_DB:
        print("Notion credentials not configured, skipping index update")
        return
    
    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }
    
    # Create a new row in the Journal Index database
    data = {
        'parent': {'database_id': NOTION_JOURNAL_DB},
        'properties': {
            'Name': {'title': [{'text': {'content': summary[:50]}}]},
            'Entry ID': {'rich_text': [{'text': {'content': entry_id}}]},
            'Date': {'date': {'start': date}},
        }
    }
    
    response = requests.post(
        'https://api.notion.com/v1/pages',
        headers=headers,
        json=data
    )
    
    if response.status_code == 200:
        print(f"Added to Notion Journal Index: {entry_id}")
    else:
        print(f"Failed to add to Notion: {response.status_code}")


def add_entry(text: str, topic: str = '', linked_notions: list = None, 
              linked_github_refs: list = None) -> str:
    """Add a new encrypted journal entry."""
    entry_id = create_entry_id()
    date = datetime.utcnow().isoformat()
    
    # Encrypt the entry
    ciphertext, nonce = encrypt_entry(text)
    
    # Prepare entry data
    data = {
        'date': date,
        'topic': topic,
        'linked_notions': linked_notions or [],
        'linked_github_refs': linked_github_refs or [],
        'ciphertext': ciphertext,
        'nonce': nonce,
    }
    
    # Save to Dropbox
    dropbox_path = save_to_dropbox(entry_id, data)
    print(f"Saved encrypted entry to Dropbox: {dropbox_path}")
    
    # Add to Notion index
    summary = text[:50] + '...' if len(text) > 50 else text
    add_to_notion_index(entry_id, summary, date[:10])
    
    return entry_id


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'add':
        if len(sys.argv) < 3:
            print("Usage: journal.py add <text>")
            sys.exit(1)
        text = ' '.join(sys.argv[2:])
        entry_id = add_entry(text)
        print(f"Created journal entry: {entry_id}")
    
    elif command == 'list':
        # List entries from Dropbox
        if not DROPBOX_TOKEN:
            print("DROPBOX_TOKEN not configured")
            sys.exit(1)
        dbx = dropbox.Dropbox(DROPBOX_TOKEN)
        try:
            result = dbx.files_list_folder(DROPBOX_JOURNAL_PATH)
            for entry in result.entries:
                if entry.name.endswith('.json'):
                    print(entry.name[:-5])  # Remove .json extension
        except dropbox.exceptions.ApiError as e:
            print(f"Error listing entries: {e}")
    
    elif command == 'read':
        if len(sys.argv) < 3:
            print("Usage: journal.py read <entry_id>")
            sys.exit(1)
        entry_id = sys.argv[2]
        # Download and decrypt entry
        if not DROPBOX_TOKEN:
            print("DROPBOX_TOKEN not configured")
            sys.exit(1)
        dbx = dropbox.Dropbox(DROPBOX_TOKEN)
        file_path = f"{DROPBOX_JOURNAL_PATH}/{entry_id}.json"
        try:
            _, response = dbx.files_download(file_path)
            data = json.loads(response.content)
            ciphertext = base64.b64decode(data['ciphertext'])
            nonce = base64.b64decode(data['nonce'])
            plaintext = decrypt_entry(ciphertext, nonce)
            print(f"\n=== {entry_id} ===")
            print(f"Date: {data['date']}")
            print(f"Topic: {data.get('topic', 'N/A')}")
            print(f"\n{plaintext}\n")
        except Exception as e:
            print(f"Error reading entry: {e}")
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == '__main__':
    main()
