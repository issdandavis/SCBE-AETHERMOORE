#!/usr/bin/env python3
"""Push exported Notion training data to Hugging Face Dataset repo."""
import os
import json
import argparse
from pathlib import Path
from huggingface_hub import HfApi, login


def main():
    parser = argparse.ArgumentParser(description='Push training data to HF')
    parser.add_argument('--input', default='training-data/', help='Input directory')
    parser.add_argument('--repo', required=True, help='HF dataset repo id')
    args = parser.parse_args()

    token = os.environ.get('HF_TOKEN')
    if not token:
        raise ValueError('HF_TOKEN environment variable required')

    login(token=token)
    api = HfApi()
    input_dir = Path(args.input)

    # Upload all JSONL files and metadata
    files_uploaded = 0
    for file_path in input_dir.glob('*'):
        if file_path.suffix in ('.jsonl', '.json'):
            print(f'Uploading {file_path.name} to {args.repo}...')
            api.upload_file(
                path_or_fileobj=str(file_path),
                path_in_repo=f'data/{file_path.name}',
                repo_id=args.repo,
                repo_type='dataset',
                commit_message=f'Update training data: {file_path.name}'
            )
            files_uploaded += 1

    # Update README with dataset card info
    meta_path = input_dir / 'metadata.json'
    if meta_path.exists():
        with open(meta_path) as f:
            meta = json.load(f)
        readme = f"""---
license: mit
task_categories:
  - text-generation
  - text-classification
language:
  - en
tags:
  - scbe-aethermoore
  - ai-governance
  - fantasy-lore
  - training-data
size_categories:
  - 1K<n<10K
---

# SCBE-AETHERMOORE Training Data

Auto-exported from Notion workspace for AI training.

## Categories
- **technical**: Architecture, security, fleet coordination
- **lore**: Spiralverse stories, Sacred Tongue, world-building
- **relationships**: Character dynamics, collaboration patterns
- **timelines**: Event sequences, historical progressions

## Stats
- Total pages scanned: {meta.get('total_pages', 'N/A')}
- Records exported: {meta.get('exported_records', 'N/A')}
- Last export: {meta.get('export_date', 'N/A')}
- Category breakdown: {json.dumps(meta.get('category_breakdown', {}))}
"""
        api.upload_file(
            path_or_fileobj=readme.encode(),
            path_in_repo='README.md',
            repo_id=args.repo,
            repo_type='dataset',
            commit_message='Update dataset card'
        )

    print(f'Uploaded {files_uploaded} files to {args.repo}')


if __name__ == '__main__':
    main()
