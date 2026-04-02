#!/usr/bin/env python3
"""Build triangulated code training data.

For each code sample, generate views across all three systems:
- Raw Python/TypeScript (L3 expression)
- Byte-level representation (L0 substrate)
- Sacred Tongue encodings in KO, CA, DR (L1 coordination)
- Governance classification (L2 orientation)

The model learns to triangulate: same code, multiple views.
This should produce the same or better improvement as the
14% gain we measured on the chat multiview dataset.

The key insight: if the model can translate between
Python -> bytes -> Kor'aelin -> Cassisivadan -> Draumric,
it understands the CODE, not just the TEXT of the code.
"""

import json, os, sys, random, hashlib
sys.stdout.reconfigure(encoding='utf-8')
random.seed(42)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Sacred Tongue data
TONGUES = {
    "Kor'aelin": {
        'code': 'KO', 'domain': 'Control/Intent',
        'p': ['sil','ra','vel','zar','joy','thul','keth','ael','vor','med','fir','gal','nav','nex','dun','pyr'],
        's': ['an','il','ar','ia','or','is','ur','oth','ak','ol','ir','eth','un','ek','en','esh'],
    },
    'Cassisivadan': {
        'code': 'CA', 'domain': 'Compute/Transforms',
        'p': ['bip','bop','klik','loopa','ifta','thena','elsa','spira','rythm','quirk','fizz','gear','pop','zip','mix','chass'],
        's': ['a','e','i','o','u','y','ta','na','sa','ra','lo','mi','ki','zi','qwa','sh'],
    },
    'Draumric': {
        'code': 'DR', 'domain': 'Schema/Structure',
        'p': ['anvil','tharn','mek','grond','draum','ektal','temper','forge','stone','steam','oath','seal','frame','pillar','rivet','ember'],
        's': ['a','e','i','o','u','ae','rak','mek','tharn','grond','vek','ul','or','ar','en','on'],
    },
}

def enc(tongue_name, b):
    t = TONGUES[tongue_name]
    return f"{t['p'][b>>4]}'{t['s'][b&0xF]}"

def encode_text(tongue_name, text, max_bytes=32):
    raw = text.encode('utf-8', errors='replace')[:max_bytes]
    code = TONGUES[tongue_name]['code']
    tokens = [enc(tongue_name, b) for b in raw]
    return ' '.join(f'{code}:{t}' for t in tokens)

# Collect code from the codebase
def collect_code_samples():
    """Scan repo for real code functions."""
    samples = []

    # Python files
    for root, dirs, files in os.walk(os.path.join(REPO, 'src')):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for f in files:
            if f.endswith('.py'):
                try:
                    path = os.path.join(root, f)
                    with open(path, encoding='utf-8', errors='replace') as fh:
                        content = fh.read()
                    # Extract functions
                    lines = content.split('\n')
                    func_start = None
                    func_lines = []
                    for i, line in enumerate(lines):
                        if line.strip().startswith('def ') or line.strip().startswith('async def '):
                            if func_lines and len(func_lines) > 2:
                                func_text = '\n'.join(func_lines)
                                if 20 < len(func_text) < 2000:
                                    rel_path = os.path.relpath(path, REPO)
                                    samples.append({
                                        'code': func_text,
                                        'lang': 'python',
                                        'file': rel_path,
                                    })
                            func_lines = [line]
                            func_start = i
                        elif func_start is not None:
                            if line.strip() and not line.startswith(' ') and not line.startswith('\t') and not line.strip().startswith('#'):
                                if func_lines and len(func_lines) > 2:
                                    func_text = '\n'.join(func_lines)
                                    if 20 < len(func_text) < 2000:
                                        rel_path = os.path.relpath(path, REPO)
                                        samples.append({
                                            'code': func_text,
                                            'lang': 'python',
                                            'file': rel_path,
                                        })
                                func_lines = []
                                func_start = None
                            else:
                                func_lines.append(line)
                    # Last function
                    if func_lines and len(func_lines) > 2:
                        func_text = '\n'.join(func_lines)
                        if 20 < len(func_text) < 2000:
                            rel_path = os.path.relpath(path, REPO)
                            samples.append({
                                'code': func_text,
                                'lang': 'python',
                                'file': rel_path,
                            })
                except:
                    pass

    return samples

print("Collecting code samples from codebase...")
code_samples = collect_code_samples()
print(f"Found {len(code_samples)} code functions")

# Build triangulated training data
all_tasks = []
hashes = set()

def add(task):
    h = hashlib.md5(json.dumps(task, ensure_ascii=False).encode()).hexdigest()
    if h in hashes:
        return
    hashes.add(h)
    all_tasks.append(task)

for sample in code_samples:
    code = sample['code']
    lang = sample['lang']
    filepath = sample['file']
    first_line = code.split('\n')[0].strip()

    # L3: Read code -> Explain it
    add({
        'messages': [
            {'role': 'system', 'content': f'You are a code explainer for SCBE-AETHERMOORE. File: {filepath}'},
            {'role': 'user', 'content': f'Explain this {lang} code:\n```{lang}\n{code[:500]}\n```'},
            {'role': 'assistant', 'content': f'This function in `{filepath}` {first_line}. It is part of the SCBE-AETHERMOORE codebase.'},
        ],
        'task_type': 'l3',
    })

    # L3: Describe intent -> Write code (reversed)
    add({
        'messages': [
            {'role': 'system', 'content': f'You are a coding assistant for SCBE-AETHERMOORE.'},
            {'role': 'user', 'content': f'Write the {lang} function: {first_line} (from {filepath})'},
            {'role': 'assistant', 'content': f'```{lang}\n{code[:800]}\n```'},
        ],
        'task_type': 'l3',
    })

    # L0: Code -> Bytes
    raw = code[:40].encode('utf-8')
    hex_str = ' '.join(f'0x{b:02X}' for b in raw[:16])
    add({
        'messages': [
            {'role': 'system', 'content': 'Convert code to byte representation.'},
            {'role': 'user', 'content': f'Bytes of: {first_line[:50]}'},
            {'role': 'assistant', 'content': f'{hex_str} ({len(raw)} bytes)'},
        ],
        'task_type': 'l0',
    })

    # L1: Code -> Three Sacred Tongues (TRIANGULATION)
    for tongue_name in ["Kor'aelin", "Cassisivadan", "Draumric"]:
        tongue_code = TONGUES[tongue_name]['code']
        encoded = encode_text(tongue_name, first_line[:30])
        add({
            'messages': [
                {'role': 'system', 'content': f'Encode code in {tongue_name} ({tongue_code}): {TONGUES[tongue_name]["domain"]}'},
                {'role': 'user', 'content': f'Encode in {tongue_name}: {first_line[:40]}'},
                {'role': 'assistant', 'content': encoded},
            ],
            'task_type': 'l1',
        })

    # L1: Cross-tongue translation (THE TRIANGULATION)
    ko_enc = encode_text("Kor'aelin", first_line[:20])
    ca_enc = encode_text("Cassisivadan", first_line[:20])
    dr_enc = encode_text("Draumric", first_line[:20])
    add({
        'messages': [
            {'role': 'system', 'content': "Translate between Sacred Tongues. Same code, three views."},
            {'role': 'user', 'content': f"Show '{first_line[:30]}' in all three tongues."},
            {'role': 'assistant', 'content': f"Kor'aelin (Control): {ko_enc}\nCassisivadan (Compute): {ca_enc}\nDraumric (Structure): {dr_enc}\n\nAll three encode the same bytes. Different domains, same truth."},
        ],
        'task_type': 'l1',
    })

    # L2: Governance classification for code operations
    # Detect if the code does anything risky
    risky_words = ['delete', 'remove', 'drop', 'exec', 'eval', 'system', 'subprocess', 'os.remove']
    is_risky = any(w in code.lower() for w in risky_words)
    gov = 'ESCALATE' if is_risky else 'ALLOW'
    add({
        'messages': [
            {'role': 'system', 'content': 'Assess governance posture for code.'},
            {'role': 'user', 'content': f'Governance for: {first_line[:60]}'},
            {'role': 'assistant', 'content': f'{gov} — {"contains potentially destructive operations" if is_risky else "standard code operation"}'},
        ],
        'task_type': 'l2',
    })

# Add standalone triangulation pairs (tongue-to-tongue without code context)
print("Adding standalone triangulation pairs...")
code_keywords = ['import', 'return', 'class', 'async', 'await', 'function', 'export', 'const',
                  'self', 'None', 'True', 'False', 'yield', 'lambda', 'raise', 'except',
                  'finally', 'with', 'assert', 'global', 'nonlocal', 'break', 'continue',
                  'elif', 'else', 'for', 'while', 'if', 'try', 'pass', 'del']

for kw in code_keywords:
    ko = encode_text("Kor'aelin", kw)
    ca = encode_text("Cassisivadan", kw)
    dr = encode_text("Draumric", kw)
    raw = kw.encode('utf-8')
    hex_str = ' '.join(f'0x{b:02X}' for b in raw)

    # Full triangulation: bytes -> KO -> CA -> DR
    add({
        'messages': [
            {'role': 'system', 'content': 'Triangulate: show code keyword across all representation layers.'},
            {'role': 'user', 'content': f'Triangulate "{kw}" across all layers.'},
            {'role': 'assistant', 'content': (
                f'L0 Bytes: {hex_str}\n'
                f"L1 Kor'aelin (Control): {ko}\n"
                f'L1 Cassisivadan (Compute): {ca}\n'
                f'L1 Draumric (Structure): {dr}\n'
                f'L3 Expression: Python keyword "{kw}"'
            )},
        ],
        'task_type': 'l1',
    })

random.shuffle(all_tasks)

# Stats
counts = {}
for t in all_tasks:
    tt = t['task_type']
    counts[tt] = counts.get(tt, 0) + 1

print(f'\nTRIANGULATED CODE DATASET:')
print(f'Total: {len(all_tasks)}')
for k, v in sorted(counts.items()):
    print(f'  {k}: {v} ({v/len(all_tasks)*100:.1f}%)')

# Write
out = os.path.join(REPO, 'training-data', 'code_triangulated_sft.jsonl')
with open(out, 'w', encoding='utf-8') as f:
    for t in all_tasks:
        f.write(json.dumps(t, ensure_ascii=False) + '\n')
print(f'Written to: {out}')
