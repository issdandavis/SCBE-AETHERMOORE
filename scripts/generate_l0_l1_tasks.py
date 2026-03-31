#!/usr/bin/env python3
"""Generate dedicated L0 and L1 training tasks.

Creates diverse byte-level and tongue-encoding tasks that don't
depend on existing SFT pairs. These are pure substrate and
coordination training to bring L0 and L1 percentages up.

Output appended to: training-data/multiview_sft.jsonl

Task categories:
  L0: byte prediction, hex conversion, binary arithmetic, byte patterns
  L1: tongue encoding, decoding, cross-tongue translation, pattern completion
"""

import hashlib
import json
import math
import random
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
random.seed(42)

REPO = Path(__file__).resolve().parent.parent

# ── Tongue data ────────────────────────────────────────────────────

TONGUES = {
    "Kor'aelin": {
        'code': 'KO',
        'prefixes': ['sil', 'ra', 'vel', 'zar', 'joy', 'thul', 'keth', 'ael',
                     'vor', 'med', 'fir', 'gal', 'nav', 'nex', 'dun', 'pyr'],
        'suffixes': ['an', 'il', 'ar', 'ia', 'or', 'is', 'ur', 'oth',
                     'ak', 'ol', 'ir', 'eth', 'un', 'ek', 'en', 'esh'],
    },
    'Avali': {
        'code': 'AV',
        'prefixes': ['saina', 'talan', 'vessa', 'maren', 'oriel', 'serin',
                     'nurel', 'lirea', 'kiva', 'lumen', 'calma', 'ponte',
                     'verin', 'nava', 'sela', 'tide'],
        'suffixes': ['a', 'e', 'i', 'o', 'u', 'y', 'la', 're',
                     'na', 'sa', 'to', 'mi', 've', 'ri', 'en', 'ul'],
    },
    'Runethic': {
        'code': 'RU',
        'prefixes': ['khar', 'drath', 'bront', 'vael', 'ur', 'mem', 'krak',
                     'tharn', 'groth', 'basalt', 'rune', 'sear', 'oath',
                     'gnarl', 'rift', 'iron'],
        'suffixes': ['ak', 'eth', 'ik', 'ul', 'or', 'ar', 'um', 'on',
                     'ir', 'esh', 'nul', 'vek', 'dra', 'kh', 'va', 'th'],
    },
    'Cassisivadan': {
        'code': 'CA',
        'prefixes': ['bip', 'bop', 'klik', 'loopa', 'ifta', 'thena', 'elsa',
                     'spira', 'rythm', 'quirk', 'fizz', 'gear', 'pop', 'zip',
                     'mix', 'chass'],
        'suffixes': ['a', 'e', 'i', 'o', 'u', 'y', 'ta', 'na',
                     'sa', 'ra', 'lo', 'mi', 'ki', 'zi', 'qwa', 'sh'],
    },
    'Umbroth': {
        'code': 'UM',
        'prefixes': ['veil', 'zhur', 'nar', 'shul', 'math', 'hollow', 'hush',
                     'thorn', 'dusk', 'echo', 'ink', 'wisp', 'bind', 'ache',
                     'null', 'shade'],
        'suffixes': ['a', 'e', 'i', 'o', 'u', 'ae', 'sh', 'th',
                     'ak', 'ul', 'or', 'ir', 'en', 'on', 'vek', 'nul'],
    },
    'Draumric': {
        'code': 'DR',
        'prefixes': ['anvil', 'tharn', 'mek', 'grond', 'draum', 'ektal',
                     'temper', 'forge', 'stone', 'steam', 'oath', 'seal',
                     'frame', 'pillar', 'rivet', 'ember'],
        'suffixes': ['a', 'e', 'i', 'o', 'u', 'ae', 'rak', 'mek',
                     'tharn', 'grond', 'vek', 'ul', 'or', 'ar', 'en', 'on'],
    },
}

TONGUE_NAMES = list(TONGUES.keys())


def enc(tongue_name, b):
    t = TONGUES[tongue_name]
    return f"{t['prefixes'][b >> 4]}'{t['suffixes'][b & 0x0F]}"


# ── L0 generators ─────────────────────────────────────────────────

def gen_l0_hex_to_binary():
    """Convert hex byte to binary."""
    b = random.randint(0, 255)
    return {
        'messages': [
            {'role': 'system', 'content': 'Convert hexadecimal bytes to binary.'},
            {'role': 'user', 'content': f'What is 0x{b:02X} in binary?'},
            {'role': 'assistant', 'content': f'0x{b:02X} = {b:08b} (decimal {b})'},
        ],
        'task_type': 'l0',
    }


def gen_l0_binary_to_hex():
    """Convert binary to hex."""
    b = random.randint(0, 255)
    return {
        'messages': [
            {'role': 'system', 'content': 'Convert binary to hexadecimal.'},
            {'role': 'user', 'content': f'What is {b:08b} in hex?'},
            {'role': 'assistant', 'content': f'{b:08b} = 0x{b:02X} (decimal {b})'},
        ],
        'task_type': 'l0',
    }


def gen_l0_nibble_split():
    """Split a byte into nibbles."""
    b = random.randint(0, 255)
    hi = b >> 4
    lo = b & 0x0F
    return {
        'messages': [
            {'role': 'system', 'content': 'Split bytes into high and low nibbles.'},
            {'role': 'user', 'content': f'Split 0x{b:02X} into nibbles.'},
            {'role': 'assistant', 'content': f'High nibble: 0x{hi:X} ({hi}), Low nibble: 0x{lo:X} ({lo})'},
        ],
        'task_type': 'l0',
    }


def gen_l0_ascii_byte():
    """Convert ASCII character to byte value."""
    c = chr(random.randint(32, 126))
    b = ord(c)
    return {
        'messages': [
            {'role': 'system', 'content': 'Convert ASCII characters to byte values.'},
            {'role': 'user', 'content': f'What is the byte value of ASCII "{c}"?'},
            {'role': 'assistant', 'content': f'"{c}" = 0x{b:02X} = {b:08b} = decimal {b}'},
        ],
        'task_type': 'l0',
    }


def gen_l0_byte_sequence():
    """Encode a short word as bytes."""
    words = ['Hello', 'Polly', 'Izack', 'magic', 'quest', 'sword', 'spell',
             'tower', 'flame', 'stone', 'forge', 'dream', 'light', 'shadow',
             'rune', 'bind', 'seal', 'gate', 'path', 'tree', 'moon', 'star',
             'wind', 'wave', 'song', 'myth', 'lore', 'code', 'byte', 'null']
    word = random.choice(words)
    raw = word.encode('utf-8')
    hex_str = ' '.join(f'0x{b:02X}' for b in raw)
    return {
        'messages': [
            {'role': 'system', 'content': 'Convert text to UTF-8 byte sequences.'},
            {'role': 'user', 'content': f'What are the bytes of "{word}"?'},
            {'role': 'assistant', 'content': f'"{word}" = {hex_str} ({len(raw)} bytes)'},
        ],
        'task_type': 'l0',
    }


def gen_l0_byte_arithmetic():
    """Simple byte arithmetic."""
    a = random.randint(0, 200)
    b = random.randint(0, 55)
    op = random.choice(['+', '-', '^', '&', '|'])
    if op == '+':
        result = (a + b) & 0xFF
        desc = f'0x{a:02X} + 0x{b:02X} = 0x{result:02X} (mod 256)'
    elif op == '-':
        result = (a - b) & 0xFF
        desc = f'0x{a:02X} - 0x{b:02X} = 0x{result:02X} (mod 256)'
    elif op == '^':
        result = a ^ b
        desc = f'0x{a:02X} XOR 0x{b:02X} = 0x{result:02X}'
    elif op == '&':
        result = a & b
        desc = f'0x{a:02X} AND 0x{b:02X} = 0x{result:02X}'
    else:
        result = a | b
        desc = f'0x{a:02X} OR 0x{b:02X} = 0x{result:02X}'
    return {
        'messages': [
            {'role': 'system', 'content': 'Perform byte-level arithmetic operations.'},
            {'role': 'user', 'content': f'Compute: 0x{a:02X} {op} 0x{b:02X}'},
            {'role': 'assistant', 'content': desc},
        ],
        'task_type': 'l0',
    }


# ── L1 generators ─────────────────────────────────────────────────

def gen_l1_encode_byte():
    """Encode a single byte in a random tongue."""
    tongue = random.choice(TONGUE_NAMES)
    b = random.randint(0, 255)
    token = enc(tongue, b)
    hi = b >> 4
    lo = b & 0x0F
    t = TONGUES[tongue]
    return {
        'messages': [
            {'role': 'system', 'content': f'Encode bytes as {tongue} ({t["code"]}) tokens.'},
            {'role': 'user', 'content': f'Encode byte {b} (0x{b:02X}) in {tongue}.'},
            {'role': 'assistant', 'content': (
                f"Prefix[{hi}] = '{t['prefixes'][hi]}', Suffix[{lo}] = '{t['suffixes'][lo]}'\n"
                f"Token: {token}"
            )},
        ],
        'task_type': 'l1',
    }


def gen_l1_decode_token():
    """Decode a tongue token back to a byte."""
    tongue = random.choice(TONGUE_NAMES)
    b = random.randint(0, 255)
    token = enc(tongue, b)
    t = TONGUES[tongue]
    hi = b >> 4
    lo = b & 0x0F
    return {
        'messages': [
            {'role': 'system', 'content': f'Decode {tongue} ({t["code"]}) tokens to bytes.'},
            {'role': 'user', 'content': f'Decode {tongue} token: {token}'},
            {'role': 'assistant', 'content': (
                f"Prefix '{t['prefixes'][hi]}' = index {hi}, "
                f"Suffix '{t['suffixes'][lo]}' = index {lo}\n"
                f"Byte: ({hi} << 4) | {lo} = {b} (0x{b:02X})"
            )},
        ],
        'task_type': 'l1',
    }


def gen_l1_cross_tongue():
    """Translate a byte between two tongues."""
    t1, t2 = random.sample(TONGUE_NAMES, 2)
    b = random.randint(0, 255)
    tok1 = enc(t1, b)
    tok2 = enc(t2, b)
    return {
        'messages': [
            {'role': 'system', 'content': f'Translate between Sacred Tongues. Same byte, different encoding.'},
            {'role': 'user', 'content': f'Translate {tok1} from {t1} to {t2}.'},
            {'role': 'assistant', 'content': f'{tok1} ({t1}) = byte 0x{b:02X} = {tok2} ({t2})'},
        ],
        'task_type': 'l1',
    }


def gen_l1_encode_word():
    """Encode a short word through a tongue."""
    tongue = random.choice(TONGUE_NAMES)
    words = ['Polly', 'rune', 'fire', 'seal', 'hex', 'key', 'egg', 'qi']
    word = random.choice(words)
    raw = word.encode('utf-8')[:6]
    code = TONGUES[tongue]['code']
    tokens = [enc(tongue, b) for b in raw]
    token_str = ' '.join(f'{code}:{t}' for t in tokens)
    return {
        'messages': [
            {'role': 'system', 'content': f'Encode text as {tongue} ({code}) token sequences.'},
            {'role': 'user', 'content': f'Encode "{word}" in {tongue}.'},
            {'role': 'assistant', 'content': f'{token_str}'},
        ],
        'task_type': 'l1',
    }


def gen_l1_prefix_group():
    """Which tongue has this prefix?"""
    tongue = random.choice(TONGUE_NAMES)
    t = TONGUES[tongue]
    prefix = random.choice(t['prefixes'])
    idx = t['prefixes'].index(prefix)
    return {
        'messages': [
            {'role': 'system', 'content': 'Identify Sacred Tongue prefixes and their nibble values.'},
            {'role': 'user', 'content': f"Which tongue uses the prefix '{prefix}' and what nibble does it represent?"},
            {'role': 'assistant', 'content': (
                f"'{prefix}' is a prefix in {tongue} ({t['code']}), representing "
                f"high nibble {idx} (0x{idx:X}). It covers bytes 0x{idx:X}0 through 0x{idx:X}F."
            )},
        ],
        'task_type': 'l1',
    }


def gen_l1_masked_completion():
    """Complete a masked tongue token."""
    tongue = random.choice(TONGUE_NAMES)
    b = random.randint(0, 255)
    t = TONGUES[tongue]
    hi = b >> 4
    lo = b & 0x0F
    prefix = t['prefixes'][hi]
    suffix = t['suffixes'][lo]

    if random.random() < 0.5:
        # Mask prefix
        return {
            'messages': [
                {'role': 'system', 'content': f'Complete the masked {tongue} token.'},
                {'role': 'user', 'content': f"Complete: ???'{suffix} in {tongue} (byte 0x{b:02X})"},
                {'role': 'assistant', 'content': f"{prefix}'{suffix}"},
            ],
            'task_type': 'l1',
        }
    else:
        # Mask suffix
        return {
            'messages': [
                {'role': 'system', 'content': f'Complete the masked {tongue} token.'},
                {'role': 'user', 'content': f"Complete: {prefix}'??? in {tongue} (byte 0x{b:02X})"},
                {'role': 'assistant', 'content': f"{prefix}'{suffix}"},
            ],
            'task_type': 'l1',
        }


# ── Main ───────────────────────────────────────────────────────────

L0_GENERATORS = [
    gen_l0_hex_to_binary,
    gen_l0_binary_to_hex,
    gen_l0_nibble_split,
    gen_l0_ascii_byte,
    gen_l0_byte_sequence,
    gen_l0_byte_arithmetic,
]

L1_GENERATORS = [
    gen_l1_encode_byte,
    gen_l1_decode_token,
    gen_l1_cross_tongue,
    gen_l1_encode_word,
    gen_l1_prefix_group,
    gen_l1_masked_completion,
]


def main():
    target_l0 = 15000  # bring L0 from 16K to ~31K (14% of 223K)
    target_l1 = 15000  # bring L1 from 20K to ~35K (16% of 223K)

    hashes = set()
    l0_tasks = []
    l1_tasks = []

    print(f'Generating {target_l0} L0 tasks and {target_l1} L1 tasks...')

    while len(l0_tasks) < target_l0:
        gen = random.choice(L0_GENERATORS)
        task = gen()
        h = hashlib.md5(json.dumps(task, ensure_ascii=False).encode()).hexdigest()
        if h not in hashes:
            hashes.add(h)
            l0_tasks.append(task)

    while len(l1_tasks) < target_l1:
        gen = random.choice(L1_GENERATORS)
        task = gen()
        h = hashlib.md5(json.dumps(task, ensure_ascii=False).encode()).hexdigest()
        if h not in hashes:
            hashes.add(h)
            l1_tasks.append(task)

    all_tasks = l0_tasks + l1_tasks
    random.shuffle(all_tasks)

    # Append to multiview file
    out_path = REPO / 'training-data' / 'multiview_sft.jsonl'
    with open(out_path, 'a', encoding='utf-8') as f:
        for task in all_tasks:
            f.write(json.dumps(task, ensure_ascii=False) + '\n')

    # Also write standalone file
    standalone = REPO / 'training-data' / 'sft' / 'l0_l1_substrate_sft.jsonl'
    with open(standalone, 'w', encoding='utf-8') as f:
        for task in all_tasks:
            f.write(json.dumps(task, ensure_ascii=False) + '\n')

    print(f'Generated: {len(l0_tasks)} L0 + {len(l1_tasks)} L1 = {len(all_tasks)} tasks')
    print(f'Appended to: {out_path}')
    print(f'Standalone: {standalone}')

    # Recount totals
    counts = {'l0': 0, 'l1': 0, 'l2': 0, 'l3': 0}
    total = 0
    with open(out_path, encoding='utf-8', errors='replace') as f:
        for line in f:
            if line.strip():
                total += 1
                try:
                    tt = json.loads(line).get('task_type', 'l3')
                    counts[tt] = counts.get(tt, 0) + 1
                except:
                    pass

    print(f'\nUpdated multiview distribution:')
    for layer, ct in sorted(counts.items()):
        pct = ct / total * 100
        bar = '#' * int(pct / 2)
        print(f'  {layer}: {ct:>8,d} ({pct:5.1f}%) {bar}')
    print(f'  Total: {total:,}')


if __name__ == '__main__':
    main()
