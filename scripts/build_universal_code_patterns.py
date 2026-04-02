#!/usr/bin/env python3
"""Build universal coding patterns training data.

Extracts patterns that exist across ALL programming languages:
- Control flow (if/else, loops, recursion)
- Data transformation (map, filter, reduce, sort)
- Error handling (try/catch, validation)
- Functions (params, returns, closures)
- Algorithms (search, sort, traverse)
- Design patterns (factory, observer, middleware)

Shows the SAME pattern in Python AND TypeScript side by side,
plus byte-level (L0) and tongue-encoded (L1) views.

The model learns: patterns are language-independent.
Syntax changes. Structure doesn't.
"""

import json, os, sys, random, hashlib, re
sys.stdout.reconfigure(encoding='utf-8')
random.seed(42)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TONGUES = {
    'KO': (['sil','ra','vel','zar','joy','thul','keth','ael','vor','med','fir','gal','nav','nex','dun','pyr'],
           ['an','il','ar','ia','or','is','ur','oth','ak','ol','ir','eth','un','ek','en','esh']),
    'CA': (['bip','bop','klik','loopa','ifta','thena','elsa','spira','rythm','quirk','fizz','gear','pop','zip','mix','chass'],
           ['a','e','i','o','u','y','ta','na','sa','ra','lo','mi','ki','zi','qwa','sh']),
    'DR': (['anvil','tharn','mek','grond','draum','ektal','temper','forge','stone','steam','oath','seal','frame','pillar','rivet','ember'],
           ['a','e','i','o','u','ae','rak','mek','tharn','grond','vek','ul','or','ar','en','on']),
}

def enc(t, b):
    p, s = TONGUES[t]
    return f"{p[b>>4]}'{s[b&0xF]}"

def encode_text(tongue, text, max_bytes=24):
    raw = text.encode('utf-8', errors='replace')[:max_bytes]
    return ' '.join(f'{tongue}:{enc(tongue, b)}' for b in raw)

all_tasks = []
hashes = set()

def add(task):
    h = hashlib.md5(json.dumps(task, ensure_ascii=False).encode()).hexdigest()
    if h not in hashes:
        hashes.add(h)
        all_tasks.append(task)

# ── 1. Collect real TypeScript functions ──────────────────────────

print("Scanning TypeScript files...")
ts_functions = []
for root, dirs, files in os.walk(os.path.join(REPO, 'src')):
    dirs[:] = [d for d in dirs if d not in ('node_modules', 'dist', '__pycache__')]
    for f in files:
        if not f.endswith('.ts'):
            continue
        try:
            path = os.path.join(root, f)
            with open(path, encoding='utf-8', errors='replace') as fh:
                content = fh.read()
            # Extract exported functions
            pattern = r'(?:export\s+)?(?:async\s+)?function\s+\w+[^{]*\{[^}]{20,800}\}'
            matches = re.findall(pattern, content, re.DOTALL)
            for m in matches[:5]:  # limit per file
                if 20 < len(m) < 1500:
                    rel = os.path.relpath(path, REPO)
                    ts_functions.append({'code': m, 'lang': 'typescript', 'file': rel})
        except:
            pass

print(f"Found {len(ts_functions)} TypeScript functions")

# ── 2. Collect real Python functions ──────────────────────────────

print("Scanning Python files...")
py_functions = []
for root, dirs, files in os.walk(os.path.join(REPO, 'src')):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if not f.endswith('.py'):
            continue
        try:
            path = os.path.join(root, f)
            with open(path, encoding='utf-8', errors='replace') as fh:
                lines = fh.readlines()
            func_lines = []
            in_func = False
            for line in lines:
                if line.strip().startswith('def ') or line.strip().startswith('async def '):
                    if func_lines and len(func_lines) > 2:
                        code = ''.join(func_lines)
                        if 20 < len(code) < 1500:
                            rel = os.path.relpath(path, REPO)
                            py_functions.append({'code': code, 'lang': 'python', 'file': rel})
                    func_lines = [line]
                    in_func = True
                elif in_func:
                    if line.strip() and not line[0].isspace() and not line.strip().startswith('#'):
                        if func_lines and len(func_lines) > 2:
                            code = ''.join(func_lines)
                            if 20 < len(code) < 1500:
                                rel = os.path.relpath(path, REPO)
                                py_functions.append({'code': code, 'lang': 'python', 'file': rel})
                        func_lines = []
                        in_func = False
                    else:
                        func_lines.append(line)
            if func_lines and len(func_lines) > 2:
                code = ''.join(func_lines)
                if 20 < len(code) < 1500:
                    rel = os.path.relpath(path, REPO)
                    py_functions.append({'code': code, 'lang': 'python', 'file': rel})
        except:
            pass

print(f"Found {len(py_functions)} Python functions")

# ── 3. Collect test files (both languages) ────────────────────────

print("Scanning test files...")
test_functions = []
for root, dirs, files in os.walk(os.path.join(REPO, 'tests')):
    dirs[:] = [d for d in dirs if d not in ('__pycache__', 'node_modules')]
    for f in files:
        if f.endswith('.py'):
            try:
                path = os.path.join(root, f)
                with open(path, encoding='utf-8', errors='replace') as fh:
                    content = fh.read()
                # Extract test functions
                for match in re.finditer(r'def (test_\w+)\([^)]*\)[^:]*:.*?(?=\ndef |\Z)', content, re.DOTALL):
                    code = match.group(0)
                    if 30 < len(code) < 1000:
                        rel = os.path.relpath(path, REPO)
                        test_functions.append({'code': code, 'lang': 'python', 'file': rel, 'is_test': True})
            except:
                pass

print(f"Found {len(test_functions)} test functions")

# ── 4. Universal patterns (language-independent concepts) ─────────

print("Generating universal pattern pairs...")

UNIVERSAL_PATTERNS = [
    {
        'pattern': 'Guard clause / Early return',
        'python': 'def process(data):\n    if not data:\n        return None\n    if not isinstance(data, dict):\n        raise ValueError("Expected dict")\n    return transform(data)',
        'typescript': 'function process(data: unknown): Result | null {\n  if (!data) return null;\n  if (typeof data !== "object") throw new Error("Expected object");\n  return transform(data);\n}',
        'concept': 'Check preconditions first, return/throw early. Keeps the happy path unindented.',
    },
    {
        'pattern': 'Map/Transform collection',
        'python': 'results = [transform(item) for item in items if item.valid]',
        'typescript': 'const results = items.filter(item => item.valid).map(item => transform(item));',
        'concept': 'Filter then transform a collection. Same pattern in every language: select subset, apply function.',
    },
    {
        'pattern': 'Error handling with context',
        'python': 'try:\n    result = risky_operation()\nexcept ConnectionError as e:\n    logger.error(f"Connection failed: {e}")\n    return fallback_value',
        'typescript': 'try {\n  const result = await riskyOperation();\n} catch (e) {\n  logger.error(`Connection failed: ${e}`);\n  return fallbackValue;\n}',
        'concept': 'Wrap risky operations, catch specific errors, log context, return safe fallback.',
    },
    {
        'pattern': 'Builder/Configuration pattern',
        'python': 'config = {\n    "model": BASE_MODEL,\n    "learning_rate": 2e-4,\n    "batch_size": 4,\n}\ntrainer = Trainer(**config)',
        'typescript': 'const config: TrainerConfig = {\n  model: BASE_MODEL,\n  learningRate: 2e-4,\n  batchSize: 4,\n};\nconst trainer = new Trainer(config);',
        'concept': 'Separate configuration from construction. Config is data, construction is action.',
    },
    {
        'pattern': 'Async/Await pattern',
        'python': 'async def fetch_data(url: str) -> dict:\n    async with aiohttp.ClientSession() as session:\n        async with session.get(url) as response:\n            return await response.json()',
        'typescript': 'async function fetchData(url: string): Promise<Record<string, unknown>> {\n  const response = await fetch(url);\n  return await response.json();\n}',
        'concept': 'Async I/O: declare intent, await result. The pattern is identical across languages.',
    },
    {
        'pattern': 'Hash map / Dictionary lookup',
        'python': 'TONGUE_WEIGHTS = {"KO": 1.0, "AV": 1.618, "RU": 2.618}\nweight = TONGUE_WEIGHTS.get(code, 1.0)',
        'typescript': 'const TONGUE_WEIGHTS: Record<string, number> = { KO: 1.0, AV: 1.618, RU: 2.618 };\nconst weight = TONGUE_WEIGHTS[code] ?? 1.0;',
        'concept': 'Key-value lookup with fallback default. Every language has this.',
    },
    {
        'pattern': 'Reduce/Accumulate',
        'python': 'total = sum(weights[i] * values[i] for i in range(6))',
        'typescript': 'const total = weights.reduce((sum, w, i) => sum + w * values[i], 0);',
        'concept': 'Combine a collection into a single value. Dot product, sums, aggregation.',
    },
    {
        'pattern': 'Factory function',
        'python': 'def create_pump(mode: str) -> PumpPacket:\n    if mode == "lore":\n        return PumpPacket(canon="lore", emotion="curious")\n    elif mode == "security":\n        return PumpPacket(canon="security", governance="ESCALATE")\n    return PumpPacket()',
        'typescript': 'function createPump(mode: string): PumpPacket {\n  if (mode === "lore") return { canon: "lore", emotion: "curious" };\n  if (mode === "security") return { canon: "security", governance: "ESCALATE" };\n  return defaultPacket();\n}',
        'concept': 'Create objects based on input. Centralize construction logic.',
    },
    {
        'pattern': 'Middleware/Pipeline',
        'python': 'def process(data):\n    data = validate(data)\n    data = transform(data)\n    data = enrich(data)\n    return output(data)',
        'typescript': 'const process = (data: Input) =>\n  pipe(data, validate, transform, enrich, output);',
        'concept': 'Chain of transformations. Each step takes output of previous. This IS the 14-layer pipeline.',
    },
    {
        'pattern': 'State machine',
        'python': 'TRANSITIONS = {\n    "ALLOW": ["QUARANTINE", "ALLOW"],\n    "QUARANTINE": ["ALLOW", "ESCALATE", "DENY"],\n    "ESCALATE": ["DENY", "QUARANTINE"],\n    "DENY": ["QUARANTINE"],\n}\ndef transition(current, event):\n    next_states = TRANSITIONS.get(current, [])\n    return next_states[0] if next_states else current',
        'typescript': 'const TRANSITIONS: Record<string, string[]> = {\n  ALLOW: ["QUARANTINE", "ALLOW"],\n  QUARANTINE: ["ALLOW", "ESCALATE", "DENY"],\n  ESCALATE: ["DENY", "QUARANTINE"],\n  DENY: ["QUARANTINE"],\n};\nconst transition = (current: string): string =>\n  TRANSITIONS[current]?.[0] ?? current;',
        'concept': 'Finite states with defined transitions. Governance decisions ARE state machines.',
    },
]

for pat in UNIVERSAL_PATTERNS:
    # Cross-language comparison
    add({
        'messages': [
            {'role': 'system', 'content': 'Show universal coding patterns across languages.'},
            {'role': 'user', 'content': f'Show the "{pat["pattern"]}" pattern in Python and TypeScript.'},
            {'role': 'assistant', 'content': f'**{pat["pattern"]}**\n\n{pat["concept"]}\n\nPython:\n```python\n{pat["python"]}\n```\n\nTypeScript:\n```typescript\n{pat["typescript"]}\n```'},
        ],
        'task_type': 'l3',
    })

    # Pattern -> Python
    add({
        'messages': [
            {'role': 'system', 'content': 'Write code from pattern descriptions.'},
            {'role': 'user', 'content': f'Write the "{pat["pattern"]}" pattern in Python.'},
            {'role': 'assistant', 'content': f'```python\n{pat["python"]}\n```\n\n{pat["concept"]}'},
        ],
        'task_type': 'l3',
    })

    # Pattern -> TypeScript
    add({
        'messages': [
            {'role': 'system', 'content': 'Write code from pattern descriptions.'},
            {'role': 'user', 'content': f'Write the "{pat["pattern"]}" pattern in TypeScript.'},
            {'role': 'assistant', 'content': f'```typescript\n{pat["typescript"]}\n```\n\n{pat["concept"]}'},
        ],
        'task_type': 'l3',
    })

    # Python -> TypeScript translation
    add({
        'messages': [
            {'role': 'system', 'content': 'Translate code between Python and TypeScript.'},
            {'role': 'user', 'content': f'Convert this Python to TypeScript:\n```python\n{pat["python"]}\n```'},
            {'role': 'assistant', 'content': f'```typescript\n{pat["typescript"]}\n```'},
        ],
        'task_type': 'l3',
    })

    # TypeScript -> Python translation
    add({
        'messages': [
            {'role': 'system', 'content': 'Translate code between TypeScript and Python.'},
            {'role': 'user', 'content': f'Convert this TypeScript to Python:\n```typescript\n{pat["typescript"]}\n```'},
            {'role': 'assistant', 'content': f'```python\n{pat["python"]}\n```'},
        ],
        'task_type': 'l3',
    })

    # L0: Pattern name as bytes
    raw = pat['pattern'].encode('utf-8')[:20]
    hex_str = ' '.join(f'0x{b:02X}' for b in raw)
    add({
        'messages': [
            {'role': 'system', 'content': 'Code pattern names as bytes.'},
            {'role': 'user', 'content': f'Bytes of "{pat["pattern"][:20]}"?'},
            {'role': 'assistant', 'content': hex_str},
        ],
        'task_type': 'l0',
    })

    # L1: Pattern name in three tongues
    for tongue in ['KO', 'CA', 'DR']:
        encoded = encode_text(tongue, pat['pattern'][:20])
        add({
            'messages': [
                {'role': 'system', 'content': f'Encode pattern name in {tongue}.'},
                {'role': 'user', 'content': f'"{pat["pattern"][:30]}" in {tongue}?'},
                {'role': 'assistant', 'content': encoded},
            ],
            'task_type': 'l1',
        })

# ── 5. Real code from BOTH languages with triangulation ──────────

print("Building cross-language triangulated pairs...")

# Take a sample of real functions from each language
py_sample = random.sample(py_functions, min(500, len(py_functions)))
ts_sample = random.sample(ts_functions, min(500, len(ts_functions)))
test_sample = random.sample(test_functions, min(300, len(test_functions)))

for sample_list in [py_sample, ts_sample, test_sample]:
    for s in sample_list:
        code = s['code']
        lang = s['lang']
        filepath = s['file']
        first_line = code.split('\n')[0].strip()[:60]

        # L3: Explain
        add({
            'messages': [
                {'role': 'system', 'content': f'Explain {lang} code from SCBE-AETHERMOORE.'},
                {'role': 'user', 'content': f'What does this do?\n```{lang}\n{code[:400]}\n```'},
                {'role': 'assistant', 'content': f'This {lang} function from `{filepath}` starts with `{first_line}`.'},
            ],
            'task_type': 'l3',
        })

        # L0: First line as bytes
        raw = first_line.encode('utf-8')[:16]
        add({
            'messages': [
                {'role': 'system', 'content': 'Code to bytes.'},
                {'role': 'user', 'content': f'Bytes: {first_line[:40]}'},
                {'role': 'assistant', 'content': ' '.join(f'0x{b:02X}' for b in raw)},
            ],
            'task_type': 'l0',
        })

        # L1: Three tongues
        for tongue in ['KO', 'CA', 'DR']:
            add({
                'messages': [
                    {'role': 'system', 'content': f'Encode in {tongue}.'},
                    {'role': 'user', 'content': f'{first_line[:30]} in {tongue}?'},
                    {'role': 'assistant', 'content': encode_text(tongue, first_line[:20])},
                ],
                'task_type': 'l1',
            })

        # L2: Governance
        risky = any(w in code.lower() for w in ['delete', 'remove', 'exec', 'eval', 'system', 'subprocess', 'os.remove', 'drop', 'truncate'])
        add({
            'messages': [
                {'role': 'system', 'content': 'Governance for code.'},
                {'role': 'user', 'content': f'Posture: {first_line}'},
                {'role': 'assistant', 'content': 'ESCALATE' if risky else 'ALLOW'},
            ],
            'task_type': 'l2',
        })

random.shuffle(all_tasks)

# Stats
counts = {}
for t in all_tasks:
    tt = t['task_type']
    counts[tt] = counts.get(tt, 0) + 1

print(f'\nUNIVERSAL CODE PATTERNS DATASET:')
print(f'Total: {len(all_tasks)}')
for k, v in sorted(counts.items()):
    print(f'  {k}: {v} ({v/len(all_tasks)*100:.1f}%)')

# Write
out = os.path.join(REPO, 'training-data', 'code_universal_patterns_sft.jsonl')
with open(out, 'w', encoding='utf-8') as f:
    for t in all_tasks:
        f.write(json.dumps(t, ensure_ascii=False) + '\n')
print(f'Written to: {out}')
