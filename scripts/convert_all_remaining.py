#!/usr/bin/env python3
"""Convert ALL remaining unconverted data to SFT pairs."""
import json, hashlib, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

REPO = Path(__file__).resolve().parent.parent
SYSTEM = 'You are Polly, the SCBE-AETHERMOORE governance assistant.'

# Load existing hashes
existing_hashes = set()
for f in (REPO / 'training-data/sft').glob('*.jsonl'):
    with open(f, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            if line.strip():
                existing_hashes.add(hashlib.md5(line.strip().encode()).hexdigest())
print(f'Existing hashes: {len(existing_hashes)}')

def add_pair(out, prompt, response):
    prompt = prompt.strip()[:1000]
    response = response.strip()[:3000]
    if len(prompt) < 10 or len(response) < 30:
        return 0
    rec = json.dumps({
        'messages': [
            {'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': prompt},
            {'role': 'assistant', 'content': response}
        ]
    }, ensure_ascii=False)
    h = hashlib.md5(rec.encode()).hexdigest()
    if h in existing_hashes:
        return 0
    existing_hashes.add(h)
    out.write(rec + '\n')
    return 1

def convert_jsonl_dir(search_path, out_file, skip_dirs=None):
    skip_dirs = skip_dirs or set()
    count = 0
    with open(out_file, 'w', encoding='utf-8') as out:
        for jf in sorted(search_path.rglob('*.jsonl')):
            if any(s in str(jf) for s in skip_dirs):
                continue
            with open(jf, encoding='utf-8', errors='replace') as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except:
                        continue
                    p, r = '', ''
                    if 'messages' in rec:
                        for m in rec['messages']:
                            if m.get('role') == 'user': p = m.get('content', '')
                            elif m.get('role') == 'assistant': r = m.get('content', '')
                    elif 'prompt' in rec:
                        p, r = str(rec.get('prompt', '')), str(rec.get('response', ''))
                    elif 'instruction' in rec:
                        p, r = str(rec.get('instruction', '')), str(rec.get('response', ''))
                    elif 'input' in rec:
                        p, r = str(rec.get('input', '')), str(rec.get('output', ''))
                    count += add_pair(out, p, r)
    return count

def convert_md_dir(search_path, out_file, q_template='What is {}?'):
    count = 0
    with open(out_file, 'w', encoding='utf-8') as out:
        for md in sorted(search_path.rglob('*.md')):
            try:
                text = md.read_text(encoding='utf-8', errors='replace')
            except:
                continue
            for section in re.split(r'\n##\s+', text):
                lines = section.strip().split('\n')
                if len(lines) < 2:
                    continue
                heading = lines[0].strip().lstrip('#').strip()[:100]
                body = '\n'.join(lines[1:]).strip()
                if len(body) < 80 or not heading:
                    continue
                count += add_pair(out, q_template.format(heading), body[:2500])
    return count

sft = REPO / 'training-data/sft'
total = 0

# Part A: subdirectory JSONL sessions
c = convert_jsonl_dir(REPO / 'training-data', sft / 'all_sessions_sft.jsonl', skip_dirs={'sft'})
print(f'A) Subdirectory sessions: {c}')
total += c

# Part B: content/ markdown
c = convert_md_dir(REPO / 'content', sft / 'content_articles_sft.jsonl')
print(f'B) Content articles: {c}')
total += c

# Part C: kindle-app markdown
c = convert_md_dir(REPO / 'kindle-app', sft / 'kindle_content_sft.jsonl', 'Tell me about {}.')
print(f'C) Kindle content: {c}')
total += c

# Part D: training-data markdown (not sft/)
c = convert_md_dir(REPO / 'training-data', sft / 'training_data_markdown_sft.jsonl', 'Explain {}.')
print(f'D) Training-data markdown: {c}')
total += c

# Part E: scripts/ docstrings (technical)
c = convert_md_dir(REPO / 'scripts', sft / 'scripts_docs_sft.jsonl', 'How does {} work?')
print(f'E) Scripts docs: {c}')
total += c

print(f'\nNew pairs this round: {total}')

# Grand total
grand = 0
for f in sft.glob('*.jsonl'):
    with open(f, encoding='utf-8', errors='replace') as fh:
        grand += sum(1 for _ in fh)
print(f'GRAND TOTAL: {grand:,} SFT pairs')
