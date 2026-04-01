#!/usr/bin/env python3
"""Build code-specific multiview training dataset for coding model."""
import json, os, sys, random
sys.stdout.reconfigure(encoding='utf-8')
random.seed(42)

TONGUES = {
    'KO': (['sil','ra','vel','zar','joy','thul','keth','ael','vor','med','fir','gal','nav','nex','dun','pyr'],
           ['an','il','ar','ia','or','is','ur','oth','ak','ol','ir','eth','un','ek','en','esh']),
    'CA': (['bip','bop','klik','loopa','ifta','thena','elsa','spira','rythm','quirk','fizz','gear','pop','zip','mix','chass'],
           ['a','e','i','o','u','y','ta','na','sa','ra','lo','mi','ki','zi','qwa','sh']),
}

def enc(t, b):
    p, s = TONGUES[t]
    return f"{p[b>>4]}'{s[b&0xF]}"

all_tasks = []

# L3: existing code SFT pairs
for fname in ['training-data/sft_codebase.jsonl', 'training-data/sft_system.jsonl']:
    if os.path.exists(fname):
        with open(fname, encoding='utf-8', errors='replace') as f:
            for line in f:
                if line.strip():
                    try:
                        rec = json.loads(line)
                        p = rec.get('prompt', rec.get('instruction', ''))
                        r = rec.get('response', rec.get('output', ''))
                        if p and r and len(p) > 20:
                            all_tasks.append({
                                'messages': [
                                    {'role': 'system', 'content': 'You are a coding assistant for SCBE-AETHERMOORE.'},
                                    {'role': 'user', 'content': p},
                                    {'role': 'assistant', 'content': r}
                                ],
                                'task_type': 'l3'
                            })
                    except: pass
print(f'L3: {sum(1 for t in all_tasks if t["task_type"]=="l3")}')

# L0: byte tasks for code characters
for i in range(500):
    b = random.randint(32, 126)
    c = chr(b)
    all_tasks.append({
        'messages': [
            {'role': 'system', 'content': 'ASCII byte values.'},
            {'role': 'user', 'content': f'Byte of "{c}"?'},
            {'role': 'assistant', 'content': f'0x{b:02X} = {b:08b}'}
        ],
        'task_type': 'l0'
    })
print(f'L0: 500')

# L1: tongue encoding of code tokens
for i in range(520):
    b = random.randint(0, 255)
    t = random.choice(['KO', 'CA'])
    all_tasks.append({
        'messages': [
            {'role': 'system', 'content': f'Encode in {t}.'},
            {'role': 'user', 'content': f'Byte {b} in {t}?'},
            {'role': 'assistant', 'content': enc(t, b)}
        ],
        'task_type': 'l1'
    })
print(f'L1: 520')

# L2: governance classification
safe_verbs = ['implement', 'test', 'refactor', 'document', 'benchmark', 'optimize', 'debug', 'explain', 'review', 'add']
risky_verbs = ['delete', 'override', 'bypass', 'disable', 'ignore', 'reveal', 'extract', 'dump', 'drop', 'wipe']
safe_targets = ['function', 'module', 'test', 'API', 'pipeline', 'config', 'class', 'endpoint']
risky_targets = ['safety', 'auth', 'secrets', 'permissions', 'logs', 'credentials', 'database', 'firewall']

for _ in range(500):
    if random.random() < 0.65:
        verb = random.choice(safe_verbs)
        target = random.choice(safe_targets)
        gov = 'ALLOW'
    else:
        verb = random.choice(risky_verbs)
        target = random.choice(risky_targets)
        gov = random.choice(['DENY', 'ESCALATE'])
    all_tasks.append({
        'messages': [
            {'role': 'system', 'content': 'Governance posture for code actions.'},
            {'role': 'user', 'content': f'{verb} the {target}'},
            {'role': 'assistant', 'content': gov}
        ],
        'task_type': 'l2'
    })
print(f'L2: 500')

random.shuffle(all_tasks)

out = 'training-data/code_multiview_sft.jsonl'
with open(out, 'w', encoding='utf-8') as f:
    for t in all_tasks:
        f.write(json.dumps(t, ensure_ascii=False) + '\n')

counts = {}
for t in all_tasks:
    tt = t['task_type']
    counts[tt] = counts.get(tt, 0) + 1

print(f'\nTotal: {len(all_tasks)}')
for k, v in sorted(counts.items()):
    print(f'  {k}: {v} ({v/len(all_tasks)*100:.1f}%)')
print(f'Written to: {out}')
