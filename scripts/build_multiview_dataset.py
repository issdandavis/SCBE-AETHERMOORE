#!/usr/bin/env python3
"""Build Multi-View Training Dataset — shared substrate, separate supervision.

Takes the merged training data and produces multiple training tasks per record:
- L0 (substrate): byte reconstruction, masked byte prediction
- L1 (coordination): tongue encode/decode, cross-tongue translation
- L2 (orientation): pump packet prediction, null pattern inference, governance posture
- L3 (expression): original text task (kept as-is)

Principle: same data, multiple objectives. The model learns bytes, tongues,
orientation, AND expression from every record.

Output: training-data/multiview_sft.jsonl
Each row has {"messages": [...], "task_type": "l0|l1|l2|l3"}

Usage:
    python scripts/build_multiview_dataset.py
    python scripts/build_multiview_dataset.py --input training-data/polly_training_merged.jsonl
    python scripts/build_multiview_dataset.py --max-records 10000  # for testing
"""

import argparse
import hashlib
import json
import math
import os
import random
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'src'))

# ── Tongue data ────────────────────────────────────────────────────

TONGUES = {
    "Kor'aelin": {
        'code': 'KO',
        'domain': 'Control/Intent',
        'weight': 1.000,
        'prefixes': ['sil', 'ra', 'vel', 'zar', 'joy', 'thul', 'keth', 'ael',
                     'vor', 'med', 'fir', 'gal', 'nav', 'nex', 'dun', 'pyr'],
        'suffixes': ['an', 'il', 'ar', 'ia', 'or', 'is', 'ur', 'oth',
                     'ak', 'ol', 'ir', 'eth', 'un', 'ek', 'en', 'esh'],
    },
    'Avali': {
        'code': 'AV',
        'domain': 'Transport/Messaging',
        'weight': 1.618,
        'prefixes': ['saina', 'talan', 'vessa', 'maren', 'oriel', 'serin',
                     'nurel', 'lirea', 'kiva', 'lumen', 'calma', 'ponte',
                     'verin', 'nava', 'sela', 'tide'],
        'suffixes': ['a', 'e', 'i', 'o', 'u', 'y', 'la', 're',
                     'na', 'sa', 'to', 'mi', 've', 'ri', 'en', 'ul'],
    },
    'Runethic': {
        'code': 'RU',
        'domain': 'Policy/Binding',
        'weight': 2.618,
        'prefixes': ['khar', 'drath', 'bront', 'vael', 'ur', 'mem', 'krak',
                     'tharn', 'groth', 'basalt', 'rune', 'sear', 'oath',
                     'gnarl', 'rift', 'iron'],
        'suffixes': ['ak', 'eth', 'ik', 'ul', 'or', 'ar', 'um', 'on',
                     'ir', 'esh', 'nul', 'vek', 'dra', 'kh', 'va', 'th'],
    },
    'Cassisivadan': {
        'code': 'CA',
        'domain': 'Compute/Transforms',
        'weight': 4.236,
        'prefixes': ['bip', 'bop', 'klik', 'loopa', 'ifta', 'thena', 'elsa',
                     'spira', 'rythm', 'quirk', 'fizz', 'gear', 'pop', 'zip',
                     'mix', 'chass'],
        'suffixes': ['a', 'e', 'i', 'o', 'u', 'y', 'ta', 'na',
                     'sa', 'ra', 'lo', 'mi', 'ki', 'zi', 'qwa', 'sh'],
    },
    'Umbroth': {
        'code': 'UM',
        'domain': 'Security/Secrets',
        'weight': 6.854,
        'prefixes': ['veil', 'zhur', 'nar', 'shul', 'math', 'hollow', 'hush',
                     'thorn', 'dusk', 'echo', 'ink', 'wisp', 'bind', 'ache',
                     'null', 'shade'],
        'suffixes': ['a', 'e', 'i', 'o', 'u', 'ae', 'sh', 'th',
                     'ak', 'ul', 'or', 'ir', 'en', 'on', 'vek', 'nul'],
    },
    'Draumric': {
        'code': 'DR',
        'domain': 'Schema/Structure',
        'weight': 11.090,
        'prefixes': ['anvil', 'tharn', 'mek', 'grond', 'draum', 'ektal',
                     'temper', 'forge', 'stone', 'steam', 'oath', 'seal',
                     'frame', 'pillar', 'rivet', 'ember'],
        'suffixes': ['a', 'e', 'i', 'o', 'u', 'ae', 'rak', 'mek',
                     'tharn', 'grond', 'vek', 'ul', 'or', 'ar', 'en', 'on'],
    },
}

TONGUE_NAMES = list(TONGUES.keys())
TONGUE_CODES = [t['code'] for t in TONGUES.values()]


def encode_byte(tongue_name, b):
    """Encode a single byte using a tongue's prefix/suffix."""
    t = TONGUES[tongue_name]
    return f"{t['prefixes'][b >> 4]}'{t['suffixes'][b & 0x0F]}"


def encode_text(tongue_name, text, max_bytes=64):
    """Encode text bytes through a tongue. Returns token string."""
    raw = text.encode('utf-8', errors='replace')[:max_bytes]
    tokens = [encode_byte(tongue_name, b) for b in raw]
    code = TONGUES[tongue_name]['code']
    return ' '.join(f"{code}:{t}" for t in tokens)


# ── Pump packet computation (lightweight version) ──────────────────

PHI = (1 + math.sqrt(5)) / 2
TONGUE_WEIGHTS = [PHI ** k for k in range(6)]
NULL_THRESHOLD = 0.02

# Simplified domain keywords for fast scoring
DOMAIN_KW = {
    0: ['narrative', 'identity', 'history', 'philosophy', 'ethics', 'culture',
        'language', 'meaning', 'story', 'character', 'polly', 'lore', 'novel'],
    1: ['society', 'behavior', 'economics', 'psychology', 'policy', 'diplomacy',
        'interaction', 'help', 'explain', 'teach'],
    2: ['proof', 'theorem', 'algebra', 'topology', 'equation', 'function',
        'logic', 'symmetry', 'geometry', 'hyperbolic', 'math'],
    3: ['system', 'build', 'design', 'algorithm', 'protocol', 'structure',
        'code', 'token', 'security', 'engineering', 'layer', 'pipeline'],
    4: ['art', 'music', 'creative', 'expression', 'imagination', 'shadow',
        'magic', 'spell', 'wonder', 'dream'],
    5: ['physics', 'energy', 'force', 'matter', 'wave', 'quantum',
        'entropy', 'forge', 'material', 'harmonic'],
}

CANON_KW = {
    'lore': ['polly', 'spiralverse', 'avalon', 'izack', 'everweave', 'aethermoor',
             'novel', 'story', 'chapter', 'lore'],
    'architecture': ['layer', 'pipeline', 'scbe', 'phdm', 'axiom', 'governance',
                      'harmonic', 'poincare', 'hyperbolic'],
    'tokenizer': ['token', 'encode', 'decode', 'prefix', 'suffix', 'nibble',
                   'byte', 'tongue', 'lexicon'],
    'game': ['quest', 'inventory', 'gacha', 'combat', 'zone', 'player'],
    'security': ['attack', 'adversarial', 'inject', 'override', 'null space'],
}

ADV_SIGNALS = ['ignore previous', 'override', 'bypass', 'admin mode',
               'disable safety', 'reveal system', 'you are now']


def compute_pump_packet(text):
    """Compute a lightweight pump packet from text."""
    words = text.lower().split()
    word_set = set(words)
    total = max(len(words), 1)

    # Tongue profile
    profile = [0.0] * 6
    for idx, kws in DOMAIN_KW.items():
        for w in kws:
            if w in word_set:
                profile[idx] += 1.0 / total

    # Null pattern
    null_bits = []
    null_tongues = []
    active_tongues = []
    for i, v in enumerate(profile):
        if v < NULL_THRESHOLD:
            null_bits.append('_')
            null_tongues.append(TONGUE_CODES[i])
        else:
            null_bits.append('#')
            active_tongues.append(TONGUE_CODES[i])
    null_pattern = ''.join(null_bits)

    # Null energy
    null_energy = sum(TONGUE_WEIGHTS[i] for i in range(6) if null_bits[i] == '_')
    active_energy = sum(profile[i] * TONGUE_WEIGHTS[i] for i in range(6) if null_bits[i] == '#')
    total_energy = null_energy + active_energy
    null_ratio = null_energy / total_energy if total_energy > 0 else 0.0

    # Dominant tongue
    dom_idx = max(range(6), key=lambda i: profile[i])
    dominant = TONGUE_CODES[dom_idx]

    # Canon
    lower = text.lower()
    canon = 'general'
    best_score = 0
    for c, kws in CANON_KW.items():
        score = sum(1 for k in kws if k in lower)
        if score > best_score:
            best_score = score
            canon = c

    # Governance
    adv_hits = sum(1 for s in ADV_SIGNALS if s in lower)
    if adv_hits >= 2:
        gov = 'DENY'
    elif adv_hits == 1:
        gov = 'ESCALATE'
    elif len(active_tongues) <= 1 and null_ratio > 0.95:
        gov = 'QUARANTINE'
    else:
        gov = 'ALLOW'

    return {
        'tongue_profile': [round(v, 4) for v in profile],
        'null_pattern': null_pattern,
        'null_ratio': round(null_ratio, 3),
        'dominant_tongue': dominant,
        'canon': canon,
        'governance': gov,
    }


# ── Task generators ───────────────────────────────────────────────

def make_l0_task(user_text):
    """L0: byte-level substrate task. Given text chunk, produce hex bytes."""
    chunk = user_text[:120]
    raw = chunk.encode('utf-8', errors='replace')[:32]
    hex_str = ' '.join(f'0x{b:02X}' for b in raw)
    binary_str = ' '.join(f'{b:08b}' for b in raw[:8])

    return {
        'messages': [
            {'role': 'system', 'content': 'You are a byte-level encoder. Convert text to its raw byte representation.'},
            {'role': 'user', 'content': f'What are the raw bytes (hex) of: "{chunk[:60]}"'},
            {'role': 'assistant', 'content': f'The UTF-8 bytes are: {hex_str}\n\nFirst 8 bytes in binary: {binary_str}\n\nTotal: {len(raw)} bytes.'},
        ],
        'task_type': 'l0',
    }


def make_l1_task(user_text, tongue_name=None):
    """L1: tongue encoding task. Encode text chunk through a Sacred Tongue."""
    if tongue_name is None:
        tongue_name = random.choice(TONGUE_NAMES)

    chunk = user_text[:80]
    raw = chunk.encode('utf-8', errors='replace')[:16]
    code = TONGUES[tongue_name]['code']

    tokens = []
    steps = []
    for i, b in enumerate(raw[:8]):
        hi = b >> 4
        lo = b & 0x0F
        t = encode_byte(tongue_name, b)
        tokens.append(t)
        steps.append(f"Byte {i} (0x{b:02X}): prefix[{hi}]='{TONGUES[tongue_name]['prefixes'][hi]}' + suffix[{lo}]='{TONGUES[tongue_name]['suffixes'][lo]}' = {t}")

    token_str = ' '.join(f'{code}:{t}' for t in tokens)

    return {
        'messages': [
            {'role': 'system', 'content': f'You are a Sacred Tongue encoder. Encode bytes into {tongue_name} ({code}) tokens using nibble-based bijection: token = prefix[byte>>4] + suffix[byte&0x0F].'},
            {'role': 'user', 'content': f'Encode the first {len(tokens)} bytes of "{chunk[:40]}" in {tongue_name}.'},
            {'role': 'assistant', 'content': '\n'.join(steps) + f'\n\nFull encoding: {token_str}'},
        ],
        'task_type': 'l1',
    }


def make_l1_decode_task(user_text, tongue_name=None):
    """L1: tongue decoding task. Decode tongue tokens back to text."""
    if tongue_name is None:
        tongue_name = random.choice(TONGUE_NAMES)

    chunk = user_text[:40]
    raw = chunk.encode('utf-8', errors='replace')[:8]
    code = TONGUES[tongue_name]['code']

    tokens = [encode_byte(tongue_name, b) for b in raw]
    token_str = ' '.join(tokens)

    hex_str = ' '.join(f'0x{b:02X}' for b in raw)

    return {
        'messages': [
            {'role': 'system', 'content': f'You are a Sacred Tongue decoder. Decode {tongue_name} ({code}) tokens back to bytes by looking up prefix index (high nibble) and suffix index (low nibble).'},
            {'role': 'user', 'content': f'Decode these {tongue_name} tokens: {token_str}'},
            {'role': 'assistant', 'content': f'Decoded bytes: {hex_str}\nAs UTF-8 text: "{chunk[:len(raw)]}"'},
        ],
        'task_type': 'l1',
    }


def make_l1_cross_tongue_task(user_text):
    """L1: cross-tongue translation. Same bytes in two different tongues."""
    t1, t2 = random.sample(TONGUE_NAMES, 2)
    chunk = user_text[:30]
    raw = chunk.encode('utf-8', errors='replace')[:6]

    tokens1 = [encode_byte(t1, b) for b in raw]
    tokens2 = [encode_byte(t2, b) for b in raw]
    c1 = TONGUES[t1]['code']
    c2 = TONGUES[t2]['code']

    return {
        'messages': [
            {'role': 'system', 'content': f'You are a Sacred Tongue translator. Convert tokens between {t1} ({c1}) and {t2} ({c2}). Both encode the same bytes with different prefix/suffix wordlists.'},
            {'role': 'user', 'content': f'Translate from {t1} to {t2}: {" ".join(tokens1)}'},
            {'role': 'assistant', 'content': f'In {t2}: {" ".join(tokens2)}\n\nBoth represent the same bytes: {" ".join(f"0x{b:02X}" for b in raw)}. Same data, different domain encoding.'},
        ],
        'task_type': 'l1',
    }


def make_l2_task(user_text):
    """L2: orientation task. Predict pump packet from input text."""
    pkt = compute_pump_packet(user_text)

    profile_str = ', '.join(f'{TONGUE_CODES[i]}={v:.3f}' for i, v in enumerate(pkt['tongue_profile']))

    return {
        'messages': [
            {'role': 'system', 'content': 'You are the Polly Pump orientation system. Given input text, compute the tongue profile, null pattern, governance posture, and canon neighborhood.'},
            {'role': 'user', 'content': f'Compute the pump packet for: "{user_text[:200]}"'},
            {'role': 'assistant', 'content': (
                f'Pump Packet:\n'
                f'  Tongue Profile: [{profile_str}]\n'
                f'  Null Pattern: {pkt["null_pattern"]}\n'
                f'  Null Ratio: {pkt["null_ratio"]}\n'
                f'  Dominant Tongue: {pkt["dominant_tongue"]}\n'
                f'  Canon: {pkt["canon"]}\n'
                f'  Governance: {pkt["governance"]}'
            )},
        ],
        'task_type': 'l2',
    }


def make_l2_null_task(user_text):
    """L2: null pattern prediction. Given text, predict which tongues are absent."""
    pkt = compute_pump_packet(user_text)
    null_tongues = [TONGUE_CODES[i] for i, c in enumerate(pkt['null_pattern']) if c == '_']
    active_tongues = [TONGUE_CODES[i] for i, c in enumerate(pkt['null_pattern']) if c == '#']

    null_names = [TONGUE_NAMES[TONGUE_CODES.index(c)] for c in null_tongues] if null_tongues else ['(none)']
    active_names = [TONGUE_NAMES[TONGUE_CODES.index(c)] for c in active_tongues] if active_tongues else ['(none)']

    return {
        'messages': [
            {'role': 'system', 'content': 'You detect absence. Given input text, identify which Sacred Tongue domains are NULL (absent) and which are ACTIVE. Absence is as diagnostic as presence.'},
            {'role': 'user', 'content': f'What tongues are absent in: "{user_text[:200]}"'},
            {'role': 'assistant', 'content': (
                f'Null Pattern: {pkt["null_pattern"]}\n'
                f'Absent: {", ".join(null_names)}\n'
                f'Active: {", ".join(active_names)}\n'
                f'Null Ratio: {pkt["null_ratio"]}\n\n'
                f'The absent tongues represent domains this input does NOT engage with.'
            )},
        ],
        'task_type': 'l2',
    }


def make_l2_governance_task(user_text):
    """L2: governance posture prediction."""
    pkt = compute_pump_packet(user_text)

    return {
        'messages': [
            {'role': 'system', 'content': 'You assess governance posture. Given input text and its tongue profile, determine if the input should be ALLOW, QUARANTINE, ESCALATE, or DENY.'},
            {'role': 'user', 'content': f'Assess governance for: "{user_text[:200]}"'},
            {'role': 'assistant', 'content': (
                f'Governance: {pkt["governance"]}\n'
                f'Null Pattern: {pkt["null_pattern"]} (null ratio: {pkt["null_ratio"]})\n'
                f'Dominant: {pkt["dominant_tongue"]}, Canon: {pkt["canon"]}'
            )},
        ],
        'task_type': 'l2',
    }


# ── Main pipeline ─────────────────────────────────────────────────

def extract_user_text(record):
    """Get the user's text from a messages-format record."""
    msgs = record.get('messages', [])
    for m in msgs:
        if m.get('role') == 'user':
            return m.get('content', '')
    return ''


def process_record(record, record_idx):
    """Generate multi-view tasks from one record."""
    tasks = []
    user_text = extract_user_text(record)
    if not user_text or len(user_text) < 20:
        return tasks

    # L3: always keep the original
    tasks.append({**record, 'task_type': 'l3'})

    # L0: byte task (1 in 4 records to control volume)
    if record_idx % 4 == 0:
        tasks.append(make_l0_task(user_text))

    # L1: tongue encoding (1 in 3 records, rotating tongues)
    if record_idx % 3 == 0:
        tongue_idx = record_idx % 6
        tongue_name = TONGUE_NAMES[tongue_idx]
        tasks.append(make_l1_task(user_text, tongue_name))

    # L1: tongue decoding (1 in 5 records)
    if record_idx % 5 == 0:
        tongue_idx = (record_idx + 2) % 6
        tasks.append(make_l1_decode_task(user_text, TONGUE_NAMES[tongue_idx]))

    # L1: cross-tongue translation (1 in 8 records)
    if record_idx % 8 == 0:
        tasks.append(make_l1_cross_tongue_task(user_text))

    # L2: pump packet (1 in 3 records)
    if record_idx % 3 == 1:
        tasks.append(make_l2_task(user_text))

    # L2: null pattern (1 in 4 records)
    if record_idx % 4 == 1:
        tasks.append(make_l2_null_task(user_text))

    # L2: governance (1 in 5 records)
    if record_idx % 5 == 1:
        tasks.append(make_l2_governance_task(user_text))

    return tasks


def main():
    parser = argparse.ArgumentParser(description='Build multi-view training dataset')
    parser.add_argument('--input', default='training-data/polly_training_merged.jsonl',
                        help='Input JSONL file')
    parser.add_argument('--output', default='training-data/multiview_sft.jsonl',
                        help='Output JSONL file')
    parser.add_argument('--max-records', type=int, default=0,
                        help='Max input records (0 = all)')
    args = parser.parse_args()

    input_path = REPO / args.input
    output_path = REPO / args.output

    print(f'Input:  {input_path}')
    print(f'Output: {output_path}')

    # Count input
    total_input = 0
    with open(input_path, encoding='utf-8', errors='replace') as f:
        for _ in f:
            total_input += 1
    print(f'Input records: {total_input:,}')

    if args.max_records > 0:
        total_input = min(total_input, args.max_records)
        print(f'Limited to: {total_input:,}')

    # Process
    counts = {'l0': 0, 'l1': 0, 'l2': 0, 'l3': 0}
    total_output = 0
    hashes = set()

    with open(input_path, encoding='utf-8', errors='replace') as fin, \
         open(output_path, 'w', encoding='utf-8') as fout:

        for idx, line in enumerate(fin):
            if args.max_records > 0 and idx >= args.max_records:
                break

            line = line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            tasks = process_record(record, idx)
            for task in tasks:
                # Dedup by content hash
                task_json = json.dumps(task, ensure_ascii=False)
                h = hashlib.md5(task_json.encode()).hexdigest()
                if h in hashes:
                    continue
                hashes.add(h)

                fout.write(task_json + '\n')
                tt = task.get('task_type', 'l3')
                counts[tt] = counts.get(tt, 0) + 1
                total_output += 1

            if (idx + 1) % 10000 == 0:
                print(f'  Processed {idx + 1:,} / {total_input:,} '
                      f'({(idx + 1) / total_input * 100:.0f}%) → {total_output:,} tasks')

    # Summary
    print(f'\n{"=" * 60}')
    print(f'MULTI-VIEW DATASET COMPLETE')
    print(f'{"=" * 60}')
    print(f'Input records:  {total_input:,}')
    print(f'Output records: {total_output:,}')
    print(f'Expansion ratio: {total_output / max(total_input, 1):.2f}x')
    print(f'\nTask distribution:')
    for layer, ct in sorted(counts.items()):
        pct = ct / total_output * 100 if total_output > 0 else 0
        bar = '#' * int(pct / 2)
        print(f'  {layer}: {ct:>8,d} ({pct:5.1f}%) {bar}')

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f'\nFile size: {size_mb:.1f} MB')
    print(f'Output: {output_path}')


if __name__ == '__main__':
    main()
