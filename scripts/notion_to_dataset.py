#!/usr/bin/env python3
"""Export Notion pages to JSONL training data for SCBE-AETHERMOORE AI training.

Categories:
  - technical: Architecture, APIs, security systems
  - lore: World-building, Sacred Tongue, Spiralverse stories
  - relationships: Character dynamics, collaboration patterns
  - timelines: Event sequences, historical progressions
  - all: Export everything
"""
import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from notion_client import Client

try:
    from training_auditor import audit_dataset_records
except Exception:  # noqa: BLE001
    audit_dataset_records = None

# Content category mappings from Notion workspace
CATEGORY_TAGS = {
    'technical': ['architecture', 'api', 'security', 'deployment', 'infrastructure',
                  'cryptography', 'governance', 'fleet', 'agent', 'phdm', 'geoseal',
                  'lattice', 'harmonic', 'voxel', 'drift', 'sentinel'],
    'lore': ['sacred tongue', 'spiralverse', 'worldforge', 'aethermoore',
             'six tongues', 'fantasy', 'story', 'narrative', 'world'],
    'relationships': ['relationship', 'collaboration', 'character', 'polly',
                      'izack', 'moeshaun', 'dorm', 'academy', 'loop'],
    'timelines': ['timeline', 'history', 'progression', 'sequence',
                  'phase', 'milestone', 'roadmap', 'schedule']
}


def classify_content(title, text):
    """Auto-classify content into categories based on keywords."""
    combined = (title + ' ' + text[:500]).lower()
    categories = []
    for cat, keywords in CATEGORY_TAGS.items():
        if any(kw in combined for kw in keywords):
            categories.append(cat)
    return categories or ['general']


def extract_text_from_blocks(blocks):
    """Recursively extract plain text from Notion blocks."""
    text_parts = []
    for block in blocks:
        block_type = block.get('type', '')
        if block_type in ('paragraph', 'heading_1', 'heading_2', 'heading_3',
                          'bulleted_list_item', 'numbered_list_item', 'quote',
                          'callout', 'toggle'):
            rich_text = block.get(block_type, {}).get('rich_text', [])
            text = ''.join(rt.get('plain_text', '') for rt in rich_text)
            if text:
                text_parts.append(text)
        if block.get('has_children'):
            text_parts.append('[nested content]')
    return '\n'.join(text_parts)


def export_page(notion, page_id, category_filter):
    """Export a single Notion page as a training record."""
    try:
        page = notion.pages.retrieve(page_id=page_id)
        title_prop = page.get('properties', {}).get('title', {})
        if not title_prop:
            for prop in page.get('properties', {}).values():
                if prop.get('type') == 'title':
                    title_prop = prop
                    break
        title_parts = title_prop.get('title', [])
        title = ''.join(t.get('plain_text', '') for t in title_parts) if title_parts else 'Untitled'
        blocks = notion.blocks.children.list(block_id=page_id)
        text = extract_text_from_blocks(blocks.get('results', []))
        categories = classify_content(title, text)
        if category_filter != 'all' and category_filter not in categories:
            return None
        return {
            'id': page_id,
            'title': title,
            'text': text,
            'categories': categories,
            'source': 'notion',
            'project': 'SCBE-AETHERMOORE',
            'exported_at': datetime.utcnow().isoformat(),
            'url': page.get('url', '')
        }
    except Exception as e:
        print(f'Error exporting page {page_id}: {e}')
        return None


def search_all_pages(notion):
    """Search for all pages accessible to the integration."""
    all_pages = []
    start_cursor = None
    while True:
        params = {'filter': {'property': 'object', 'value': 'page'}, 'page_size': 100}
        if start_cursor:
            params['start_cursor'] = start_cursor
        results = notion.search(**params)
        all_pages.extend(results.get('results', []))
        if not results.get('has_more'):
            break
        start_cursor = results.get('next_cursor')
    return all_pages


def main():
    parser = argparse.ArgumentParser(description='Export Notion to training data')
    parser.add_argument('--category', default='all', help='Category filter')
    parser.add_argument('--output', default='training-data/', help='Output directory')
    parser.add_argument('--audit-threshold', type=float, default=0.78, help='Anomaly threshold for training data audit')
    parser.add_argument('--fail-on-quarantine', action='store_true', help='Exit non-zero if dataset audit status is QUARANTINE')
    args = parser.parse_args()

    token = os.environ.get('NOTION_TOKEN')
    if not token:
        raise ValueError('NOTION_TOKEN environment variable required')

    notion = Client(auth=token)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f'Searching Notion workspace for pages...')
    pages = search_all_pages(notion)
    print(f'Found {len(pages)} pages')

    records = []
    for page in pages:
        record = export_page(notion, page['id'], args.category)
        if record:
            records.append(record)
            print(f'  Exported: {record["title"]} [{", ".join(record["categories"])}]')

    # Write JSONL output
    output_file = output_dir / f'notion_export_{args.category}_{datetime.utcnow().strftime("%Y%m%d")}.jsonl'
    with open(output_file, 'w') as f:
        for record in records:
            f.write(json.dumps(record) + '\n')

    # Write metadata
    meta = {
        'total_pages': len(pages),
        'exported_records': len(records),
        'category_filter': args.category,
        'export_date': datetime.utcnow().isoformat(),
        'category_breakdown': {}
    }
    for record in records:
        for cat in record['categories']:
            meta['category_breakdown'][cat] = meta['category_breakdown'].get(cat, 0) + 1

    audit_report = None
    if audit_dataset_records is not None:
        audit_report = audit_dataset_records(records, threshold=args.audit_threshold)
        audit_file = output_dir / f'audit_{args.category}_{datetime.utcnow().strftime("%Y%m%d")}.json'
        with open(audit_file, 'w') as f:
            json.dump(audit_report, f, indent=2)
        print(f'Audit report: {audit_file} [status={audit_report.get("status")}]')
        meta['audit'] = {
            'status': audit_report.get('status'),
            'threshold': audit_report.get('threshold'),
            'flagged_count': audit_report.get('flagged_count'),
            'hashchain_root': audit_report.get('hashchain_root')
        }
    else:
        print('Warning: training_auditor unavailable; skipping dataset audit')

    with open(output_dir / 'metadata.json', 'w') as f:
        json.dump(meta, f, indent=2)

    print(f'\nExported {len(records)} records to {output_file}')
    print(f'Category breakdown: {meta["category_breakdown"]}')
    if args.fail_on_quarantine and isinstance(audit_report, dict) and audit_report.get('status') == 'QUARANTINE':
        raise SystemExit('Dataset audit returned QUARANTINE (fail-on-quarantine enabled).')


if __name__ == '__main__':
    main()
