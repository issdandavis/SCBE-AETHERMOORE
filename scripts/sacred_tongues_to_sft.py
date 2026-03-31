#!/usr/bin/env python3
"""Generate SFT training pairs from the Six Sacred Tongues lexicon data.

Produces tongue-specific training data covering:
- Each tongue's identity, domain, phonology
- Prefix/suffix wordlists and encoding mechanics
- Cross-tongue translation and phase/weight relationships
- SS1 format specification
- Domain authorization and security properties
- Origin story (Cassisivadan = Issac Davis reversed)
- Encoding/decoding worked examples

Author: Issac Davis (ORCID: 0009-0002-3936-9369)
"""
import json
import hashlib
import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

REPO = Path(__file__).resolve().parent.parent
SFT_DIR = REPO / 'training-data' / 'sft'
SFT_DIR.mkdir(parents=True, exist_ok=True)

# ── Canonical tongue data ──────────────────────────────────────────

TONGUES = {
    'KO': {
        'name': "Kor'aelin",
        'domain': 'Control/Orchestration/Intent',
        'used_for': 'Nonce, flow control, command authority',
        'phase_deg': 0,
        'weight': 1.00,
        'phonology': 'harsh consonants',
        'prefixes': ['sil', 'ra', 'vel', 'zar', 'joy', 'thul', 'keth', 'ael',
                     'vor', 'med', 'fir', 'gal', 'nav', 'nex', 'dun', 'pyr'],
        'suffixes': ['an', 'il', 'ar', 'ia', 'or', 'is', 'ur', 'oth',
                     'ak', 'ol', 'ir', 'eth', 'un', 'ek', 'en', 'esh'],
        'version': '2.0 (Corrected)',
        'example_tokens': {'0x00': "sil'an", '0x10': "ra'an", '0xFF': "pyr'esh"},
    },
    'AV': {
        'name': 'Avali',
        'domain': 'Transport/Messaging/Context',
        'used_for': 'AAD headers, routing metadata, emotional resonance',
        'phase_deg': 60,
        'weight': 1.618,
        'phonology': 'flowing vowels',
        'prefixes': ['saina', 'talan', 'vessa', 'maren', 'oriel', 'serin',
                     'nurel', 'lirea', 'kiva', 'lumen', 'calma', 'ponte',
                     'verin', 'nava', 'sela', 'tide'],
        'suffixes': ['a', 'e', 'i', 'o', 'u', 'y', 'la', 're',
                     'na', 'sa', 'to', 'mi', 've', 'ri', 'en', 'ul'],
        'version': '1.0',
        'example_tokens': {'0x00': "saina'a", '0x10': "talan'a", '0xFF': "tide'ul"},
    },
    'RU': {
        'name': 'Runethic',
        'domain': 'Policy/Constraints/Binding',
        'used_for': 'Salt, binding, oaths, governance rules',
        'phase_deg': 120,
        'weight': 2.618,
        'phonology': 'flowing vowels with guttural stops',
        'prefixes': ['khar', 'drath', 'bront', 'vael', 'ur', 'mem', 'krak',
                     'tharn', 'groth', 'basalt', 'rune', 'sear', 'oath',
                     'gnarl', 'rift', 'iron'],
        'suffixes': ['ak', 'eth', 'ik', 'ul', 'or', 'ar', 'um', 'on',
                     'ir', 'esh', 'nul', 'vek', 'dra', 'kh', 'va', 'th'],
        'version': '1.0',
        'example_tokens': {'0x00': "khar'ak", '0x10': "drath'ak", '0xFF': "iron'th"},
    },
    'CA': {
        'name': 'Cassisivadan',
        'domain': 'Compute/Transforms/Logic',
        'used_for': 'Ciphertext, bitwise operations, divine invocation',
        'phase_deg': 180,
        'weight': 4.236,
        'phonology': 'bridges harsh and flowing',
        'prefixes': ['bip', 'bop', 'klik', 'loopa', 'ifta', 'thena', 'elsa',
                     'spira', 'rythm', 'quirk', 'fizz', 'gear', 'pop', 'zip',
                     'mix', 'chass'],
        'suffixes': ['a', 'e', 'i', 'o', 'u', 'y', 'ta', 'na',
                     'sa', 'ra', 'lo', 'mi', 'ki', 'zi', 'qwa', 'sh'],
        'version': '1.0',
        'example_tokens': {'0x00': "bip'a", '0x10': "bop'a", '0xFF': "chass'sh"},
    },
    'UM': {
        'name': 'Umbroth',
        'domain': 'Security/Secrets/Veil',
        'used_for': 'Encryption keys, redaction, shadow protocols',
        'phase_deg': 240,
        'weight': 6.854,
        'phonology': 'harsh consonants with sibilants',
        'prefixes': ['veil', 'zhur', 'nar', 'shul', 'math', 'hollow', 'hush',
                     'thorn', 'dusk', 'echo', 'ink', 'wisp', 'bind', 'ache',
                     'null', 'shade'],
        'suffixes': ['a', 'e', 'i', 'o', 'u', 'ae', 'sh', 'th',
                     'ak', 'ul', 'or', 'ir', 'en', 'on', 'vek', 'nul'],
        'version': '1.0',
        'example_tokens': {'0x00': "veil'a", '0x10': "zhur'a", '0xFF': "shade'nul"},
    },
    'DR': {
        'name': 'Draumric',
        'domain': 'Schema/Structure/Forge',
        'used_for': 'Auth tags, type definitions, structural integrity',
        'phase_deg': 300,
        'weight': 11.090,
        'phonology': 'harsh consonants with metallic resonance',
        'prefixes': ['anvil', 'tharn', 'mek', 'grond', 'draum', 'ektal',
                     'temper', 'forge', 'stone', 'steam', 'oath', 'seal',
                     'frame', 'pillar', 'rivet', 'ember'],
        'suffixes': ['a', 'e', 'i', 'o', 'u', 'ae', 'rak', 'mek',
                     'tharn', 'grond', 'vek', 'ul', 'or', 'ar', 'en', 'on'],
        'version': '1.0',
        'example_tokens': {'0x00': "anvil'a", '0x10': "tharn'a", '0xFF': "ember'on"},
    },
}

# Phase angles in radians
for code, t in TONGUES.items():
    t['phase_rad'] = math.radians(t['phase_deg'])

# ── System prompts ─────────────────────────────────────────────────

SYS_TONGUE_EXPERT = (
    "You are Polly -- Polymnia Aetheris, keeper of the Six Sacred Tongues. "
    "You explain the constructed languages of the Spiralverse: Kor'aelin (KO), "
    "Avali (AV), Runethic (RU), Cassisivadan (CA), Umbroth (UM), and Draumric (DR). "
    "Each tongue has 256 tokens built from 16 prefixes and 16 suffixes using "
    "nibble-based byte encoding. You speak with authority and occasional wit."
)

SYS_TOKENIZER = (
    "You are Polly, the Sacred Tongue Tokenizer specialist. You explain how "
    "the Six Sacred Tongues encode arbitrary bytes into pronounceable spell-text "
    "using a nibble-based system: high nibble selects prefix, low nibble selects "
    "suffix, producing 16x16=256 unique tokens per tongue. The system is "
    "deterministic, bijective, and collision-free."
)

SYS_CRYPTO = (
    "You are Polly, chronicler of the SpiralSeal SS1 protocol. You explain "
    "how the Six Sacred Tongues provide domain-separated cryptographic encoding: "
    "RU for salt, KO for nonce, CA for ciphertext, DR for auth tags. Each tongue's "
    "phase angle and phi-weight create measurable geometric cost amplification "
    "in the SCBE-AETHERMOORE security stack."
)

SYS_ORIGIN = (
    "You are Polly -- Polymnia Aetheris. You know the origin story of the "
    "Six Sacred Tongues: they were created by Issac Davis, first appearing "
    "in the Everweave RPG sessions and later formalized into the SCBE tokenizer. "
    "The name Cassisivadan encodes the creator's identity (Cassi = Issac reversed, "
    "Sivad = Davis reversed). These are original constructed languages, not derived "
    "from any existing conlang."
)

SYS_LORE = (
    "You are Polly, the Archivist of Avalon. You explain the lore, magic systems, "
    "characters, and world-building of the Spiral of Pollyoneth universe with "
    "wisdom and wit."
)


# ── Dedup ──────────────────────────────────────────────────────────

existing_hashes = set()
for f in SFT_DIR.glob('*.jsonl'):
    try:
        with open(f, encoding='utf-8', errors='replace') as fh:
            for line in fh:
                if line.strip():
                    existing_hashes.add(hashlib.md5(line.strip().encode()).hexdigest())
    except Exception:
        pass
print(f'Existing hash count: {len(existing_hashes):,}')

pairs = []

def add(system, prompt, response):
    prompt = prompt.strip()[:1200]
    response = response.strip()[:4000]
    if len(prompt) < 10 or len(response) < 40:
        return 0
    rec = json.dumps({
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': prompt},
            {'role': 'assistant', 'content': response}
        ]
    }, ensure_ascii=False)
    h = hashlib.md5(rec.encode()).hexdigest()
    if h in existing_hashes:
        return 0
    existing_hashes.add(h)
    pairs.append(rec)
    return 1


def encode_byte(tongue_code, byte_val):
    """Encode a single byte using tongue prefix/suffix."""
    t = TONGUES[tongue_code]
    p = t['prefixes'][byte_val >> 4]
    s = t['suffixes'][byte_val & 0x0F]
    return f"{p}'{s}"


# ── Generate pairs ─────────────────────────────────────────────────

count = 0

# 1. Per-tongue identity pairs
for code, t in TONGUES.items():
    name = t['name']
    # Basic identity
    count += add(SYS_TONGUE_EXPERT,
        f"What is {name} ({code}) in the Six Sacred Tongues?",
        f"{name} ({code}) is the Sacred Tongue of {t['domain']}. "
        f"It is used for {t['used_for']}. In the SCBE-AETHERMOORE system, "
        f"{name} sits at phase angle {t['phase_deg']} degrees with a phi-weight "
        f"of {t['weight']:.3f}. Its phonology features {t['phonology']}. "
        f"Like all Sacred Tongues, it encodes 256 unique tokens using 16 prefixes "
        f"and 16 suffixes in a nibble-based byte mapping. Version: {t['version']}."
    )

    # Prefix list
    count += add(SYS_TONGUE_EXPERT,
        f"What are the 16 prefixes in {name} ({code})?",
        f"The 16 prefixes of {name} ({code}), corresponding to the high nibble "
        f"(bits 4-7) of each byte, are: {', '.join(t['prefixes'])}. "
        f"Each prefix combines with one of 16 suffixes to form a unique token. "
        f"For example, prefix index 0 is '{t['prefixes'][0]}' and prefix index 15 "
        f"is '{t['prefixes'][15]}'."
    )

    # Suffix list
    count += add(SYS_TONGUE_EXPERT,
        f"What are the 16 suffixes in {name} ({code})?",
        f"The 16 suffixes of {name} ({code}), corresponding to the low nibble "
        f"(bits 0-3) of each byte, are: {', '.join(t['suffixes'])}. "
        f"Combined with the 16 prefixes, these produce 256 unique tokens. "
        f"Suffix index 0 is '{t['suffixes'][0]}' and suffix index 15 is "
        f"'{t['suffixes'][15]}'."
    )

    # Example tokens
    for hex_val, token in t['example_tokens'].items():
        byte_int = int(hex_val, 16)
        hi = byte_int >> 4
        lo = byte_int & 0x0F
        count += add(SYS_TOKENIZER,
            f"How do you encode byte {hex_val} (decimal {byte_int}) in {name}?",
            f"To encode byte {hex_val} in {name} ({code}):\n"
            f"1. High nibble: {hex_val[2]} = prefix index {hi} = '{t['prefixes'][hi]}'\n"
            f"2. Low nibble: {hex_val[3]} = suffix index {lo} = '{t['suffixes'][lo]}'\n"
            f"3. Token: {t['prefixes'][hi]}'{t['suffixes'][lo]} = {token}\n\n"
            f"The encoding formula is: token = prefixes[byte >> 4] + \"'\" + suffixes[byte & 0x0F]"
        )

    # Domain role
    count += add(SYS_CRYPTO,
        f"What is the cryptographic role of {name} in SCBE-AETHERMOORE?",
        f"{name} ({code}) serves the {t['domain']} domain in the SCBE-AETHERMOORE "
        f"security stack. It is used for encoding {t['used_for']}. "
        f"Its phase angle is {t['phase_deg']} degrees (= {t['phase_deg']}*pi/180 radians) "
        f"and its phi-weight is {t['weight']:.3f}. When cross-tongue retokenization "
        f"occurs, the phase delta and weight ratio between source and destination tongues "
        f"create cryptographic attestation that cannot be forged without breaking SHA-256."
    )

    # Phonology
    count += add(SYS_TONGUE_EXPERT,
        f"Describe the phonology of {name}.",
        f"{name} ({code}) features {t['phonology']}. "
        f"Its prefixes include sounds like '{t['prefixes'][0]}', '{t['prefixes'][3]}', "
        f"and '{t['prefixes'][7]}', while its suffixes use patterns like "
        f"'{t['suffixes'][0]}', '{t['suffixes'][6]}', and '{t['suffixes'][15]}'. "
        f"In the Spiralverse, this phonology reflects the tongue's domain: "
        f"{t['domain']}. Mispronunciation (incorrect encoding) causes protocol "
        f"rejection -- there is no partial credit in cryptographic verification."
    )

    # Generate 10 random byte encoding examples per tongue
    for byte_val in [0, 42, 73, 127, 128, 170, 200, 222, 240, 255]:
        token = encode_byte(code, byte_val)
        hi = byte_val >> 4
        lo = byte_val & 0x0F
        count += add(SYS_TOKENIZER,
            f"Encode byte {byte_val} (0x{byte_val:02X}) in {name} ({code}).",
            f"Byte {byte_val} (0x{byte_val:02X}) in {name} ({code}):\n"
            f"- High nibble: 0x{hi:X} = prefix '{t['prefixes'][hi]}'\n"
            f"- Low nibble: 0x{lo:X} = suffix '{t['suffixes'][lo]}'\n"
            f"- Result: {token}"
        )

# 2. Cross-tongue comparison pairs
tongue_codes = list(TONGUES.keys())
for i, src in enumerate(tongue_codes):
    for dst in tongue_codes[i+1:]:
        ts = TONGUES[src]
        td = TONGUES[dst]
        phase_delta = abs(td['phase_deg'] - ts['phase_deg'])
        weight_ratio = td['weight'] / ts['weight']

        count += add(SYS_CRYPTO,
            f"What happens when you retokenize from {ts['name']} ({src}) to {td['name']} ({dst})?",
            f"Cross-tongue retokenization from {ts['name']} ({src}) to {td['name']} ({dst}):\n"
            f"- Phase delta: {phase_delta} degrees\n"
            f"- Weight ratio: {weight_ratio:.3f} "
            f"({'golden ratio!' if abs(weight_ratio - 1.618) < 0.01 else f'{weight_ratio:.3f}x amplification'})\n"
            f"- The same byte sequence gets re-encoded: each byte's high nibble maps to "
            f"a different prefix (from {src}'s '{ts['prefixes'][0]}...' to {dst}'s "
            f"'{td['prefixes'][0]}...'), and the low nibble maps to a different suffix.\n"
            f"- An HMAC attestation is generated over the phase delta, weight ratio, "
            f"and SHA-256 hash of the original bytes, proving the transformation is "
            f"authentic and unforgeable."
        )

        # Show same byte in both tongues
        for b in [0, 127, 255]:
            t1 = encode_byte(src, b)
            t2 = encode_byte(dst, b)
            count += add(SYS_TOKENIZER,
                f"How does byte {b} (0x{b:02X}) differ between {ts['name']} and {td['name']}?",
                f"Byte {b} (0x{b:02X}) encodes differently in each tongue:\n"
                f"- {ts['name']} ({src}): {t1}\n"
                f"- {td['name']} ({dst}): {t2}\n"
                f"Same byte, same nibble split, but different prefix/suffix wordlists "
                f"produce completely different tokens. This is the domain separation "
                f"at the heart of SCBE-AETHERMOORE."
            )

# 3. Overview pairs
count += add(SYS_TONGUE_EXPERT,
    "What are the Six Sacred Tongues?",
    "The Six Sacred Tongues are a set of constructed languages (conlangs) designed "
    "for the Spiralverse/Aethermoor universe by Issac Davis. Each tongue serves a "
    "specific domain and uses a nibble-based byte encoding system to generate 256 "
    "unique tokens per language.\n\n"
    "The six tongues are:\n"
    "1. KO -- Kor'aelin (Control/Intent) -- nonce, flow, command authority\n"
    "2. AV -- Avali (Transport/Messaging) -- AAD headers, routing metadata\n"
    "3. RU -- Runethic (Policy/Binding) -- salt, oaths, governance rules\n"
    "4. CA -- Cassisivadan (Compute/Transforms) -- ciphertext, bitwise operations\n"
    "5. UM -- Umbroth (Security/Secrets) -- encryption keys, redaction, shadows\n"
    "6. DR -- Draumric (Schema/Structure) -- auth tags, type definitions\n\n"
    "Together they form 6 x 256 = 1,536 unique tokens across the system. Their "
    "phi-weighted scaling (1.00, 1.618, 2.618, 4.236, 6.854, 11.090) creates "
    "exponential cost amplification for cross-domain attacks."
)

count += add(SYS_TONGUE_EXPERT,
    "List all Six Sacred Tongues with their codes and domains.",
    "| Code | Name | Domain | Phi-Weight | Phase |\n"
    "|------|------|--------|------------|-------|\n"
    "| KO | Kor'aelin | Control/Intent | 1.000 | 0 deg |\n"
    "| AV | Avali | Transport/Messaging | 1.618 | 60 deg |\n"
    "| RU | Runethic | Policy/Binding | 2.618 | 120 deg |\n"
    "| CA | Cassisivadan | Compute/Transforms | 4.236 | 180 deg |\n"
    "| UM | Umbroth | Security/Secrets | 6.854 | 240 deg |\n"
    "| DR | Draumric | Schema/Structure | 11.090 | 300 deg |\n\n"
    "Each tongue has exactly 256 tokens (16 prefixes x 16 suffixes). The phi-weights "
    "follow powers of the golden ratio: 1, phi, phi^2, phi^3, phi^4, phi^5."
)

# 4. Phi-weight pairs
count += add(SYS_CRYPTO,
    "Why do the Sacred Tongues use phi-weighted scaling?",
    "The Sacred Tongues use powers of the golden ratio (phi = 1.618...) for their "
    "weight scaling because phi creates optimal information packing and cost "
    "amplification:\n\n"
    "KO: 1.000 (phi^0) -- baseline control\n"
    "AV: 1.618 (phi^1) -- transport\n"
    "RU: 2.618 (phi^2) -- policy\n"
    "CA: 4.236 (phi^3) -- compute\n"
    "UM: 6.854 (phi^4) -- security\n"
    "DR: 11.090 (phi^5) -- structure\n\n"
    "When cross-tongue retokenization occurs, the weight ratio between any two "
    "adjacent tongues is always phi (1.618...). This means the hyperbolic wall "
    "H(d,R) = R^(d^2) uses these weight ratios as R, creating exponential cost "
    "amplification. An attacker trying to forge a DR signature from a KO token "
    "faces a weight ratio of 11.09, meaning the hyperbolic cost is 11.09^(d^2) -- "
    "computationally infeasible for any meaningful distance d."
)

count += add(SYS_CRYPTO,
    "What are the phase angles of the Six Sacred Tongues?",
    "The Six Sacred Tongues are arranged at 60-degree intervals around the "
    "complex plane, forming a hexagonal pattern:\n\n"
    "KO: 0 degrees (e^(i*0)) -- the origin of control\n"
    "AV: 60 degrees (e^(i*pi/3)) -- first rotation\n"
    "RU: 120 degrees (e^(i*2pi/3)) -- second rotation\n"
    "CA: 180 degrees (e^(i*pi)) -- the antipodal compute domain\n"
    "UM: 240 degrees (e^(i*4pi/3)) -- fourth rotation\n"
    "DR: 300 degrees (e^(i*5pi/3)) -- final rotation before return\n\n"
    "The 60-degree spacing ensures maximum separation between adjacent domains. "
    "Cross-tongue attestation includes the phase delta, making it impossible to "
    "replay tokens from one domain in another without detection."
)

# 5. SS1 format pairs
count += add(SYS_CRYPTO,
    "What is the SpiralSeal SS1 format?",
    "SpiralSeal SS1 is the cryptographic encoding format that transforms binary "
    "ciphertext into Sacred Tongue spell-text. The format is:\n\n"
    "SS1|kid=<key_id>|aad=<context>|<salt_spell>|<nonce_spell>|<ct_spell>|<tag_spell>\n\n"
    "Each field uses a different tongue:\n"
    "- Salt: RU (Runethic) -- binding material for key derivation\n"
    "- Nonce: KO (Kor'aelin) -- flow control for encryption\n"
    "- Ciphertext: CA (Cassisivadan) -- transformed data\n"
    "- Tag: DR (Draumric) -- structural integrity proof\n\n"
    "Example: SS1|kid=k01|aad=service=prod|ru:khar'ak drath'eth|ko:sil'an ra'il|"
    "ca:bip'a bop'e klik'i|dr:anvil'a tharn'e\n\n"
    "This makes encrypted data look like fantasy language incantations rather than "
    "obvious base64 or hex strings -- steganographic obfuscation."
)

count += add(SYS_CRYPTO,
    "How does SpiralSeal SS1 encryption work?",
    "SpiralSeal SS1 encryption follows these steps:\n\n"
    "1. Generate random salt (16 bytes)\n"
    "2. Derive encryption key via HKDF-SHA256 using salt and key ID\n"
    "3. Encrypt plaintext with AES-256-GCM using a random 12-byte nonce\n"
    "4. Encode each component as Sacred Tongue spell-text:\n"
    "   - Salt bytes -> Runethic (RU) tokens\n"
    "   - Nonce bytes -> Kor'aelin (KO) tokens\n"
    "   - Ciphertext bytes -> Cassisivadan (CA) tokens\n"
    "   - Auth tag bytes -> Draumric (DR) tokens\n"
    "5. Format as SS1 blob: SS1|kid=...|aad=...|ru:...|ko:...|ca:...|dr:...\n\n"
    "Security properties: AES-256-GCM provides confidentiality (256-bit key), "
    "GMAC provides integrity (128-bit tag), AAD binds context to prevent cross-tenant "
    "attacks, and per-message random salt/nonce provide forward secrecy."
)

# 6. Encoding system pairs
count += add(SYS_TOKENIZER,
    "How does the nibble-based byte encoding work in the Sacred Tongues?",
    "Each Sacred Tongue uses a nibble-based system to encode any byte (0-255) into "
    "a pronounceable token:\n\n"
    "1. Take a byte value (e.g., 0x3A = decimal 58)\n"
    "2. Split into high nibble (bits 4-7) and low nibble (bits 0-3)\n"
    "   - High nibble: 0x3 = 3 -> selects prefix at index 3\n"
    "   - Low nibble: 0xA = 10 -> selects suffix at index 10\n"
    "3. Combine: prefix'suffix\n\n"
    "In Python: token = prefixes[byte >> 4] + \"'\" + suffixes[byte & 0x0F]\n\n"
    "This produces exactly 16 x 16 = 256 unique tokens per tongue. The encoding "
    "is deterministic (same byte always gives same token), bijective (perfect 1-to-1), "
    "collision-free (no two bytes share a token), and constant-time O(1)."
)

count += add(SYS_TOKENIZER,
    "How many total tokens exist across all Six Sacred Tongues?",
    "Each of the Six Sacred Tongues has exactly 256 tokens (16 prefixes x 16 suffixes). "
    "With 6 tongues, the total is 6 x 256 = 1,536 unique tokens across the system.\n\n"
    "These 1,536 tokens form the complete vocabulary of the Sacred Tongue tokenizer. "
    "No two tokens within a tongue are the same, and tokens across different tongues "
    "are deliberately distinct in phonology to prevent confusion:\n"
    "- KO tokens sound harsh and commanding (sil'an, keth'oth)\n"
    "- AV tokens flow like water (saina'la, lirea're)\n"
    "- RU tokens rumble like stone (khar'ak, bront'ul)\n"
    "- CA tokens click and pop computationally (bip'a, klik'ta)\n"
    "- UM tokens whisper from shadows (veil'sh, hush'nul)\n"
    "- DR tokens ring like metal (anvil'rak, forge'mek)"
)

# 7. Origin story pairs
count += add(SYS_ORIGIN,
    "Who created the Six Sacred Tongues?",
    "The Six Sacred Tongues were created by Issac Davis. They first appeared in the "
    "Everweave RPG sessions -- a long-running tabletop-style game played with AI "
    "dungeon masters -- where they emerged as part of the world-building for "
    "Aethermoor and the Spiralverse.\n\n"
    "The languages were subsequently formalized into the SCBE tokenizer system, "
    "where each tongue became a 256-token bijective encoding for binary data. "
    "What started as creative world-building became a production cryptographic "
    "system with real security properties.\n\n"
    "Issac's ORCID is 0009-0002-3936-9369."
)

count += add(SYS_ORIGIN,
    "Why is the tongue called Cassisivadan?",
    "Cassisivadan (CA) encodes the identity of its creator, Issac Davis:\n\n"
    "- 'Cassi' = 'Issac' reversed\n"
    "- 'Sivad' = 'Davis' reversed\n"
    "- '-an' = suffix common to many Sacred Tongue tokens\n\n"
    "This makes Cassisivadan a signature language -- it is impossible for anyone "
    "else in the world to independently create a conlang with this exact name, "
    "because it is literally derived from the creator's own name reversed. "
    "It serves the Compute/Transforms domain and encodes ciphertext in the "
    "SpiralSeal SS1 protocol."
)

count += add(SYS_ORIGIN,
    "What is the origin of the Sacred Tongues in the Spiralverse lore?",
    "In the Spiralverse, the Six Sacred Tongues are ancient linguistic encodings "
    "woven into reality's substrate. Each tongue's phonology maps directly to "
    "protocol operations -- speaking the words correctly is equivalent to producing "
    "a valid cryptographic signature.\n\n"
    "In-world, practitioners must achieve fluency in each tongue's distinct phonology. "
    "Harsh consonants (KO, DR, UM) handle rigid operations like control and security, "
    "while flowing vowels (AV, RU) manage flexible operations like transport and "
    "negotiation. CA bridges both styles as the compute tongue.\n\n"
    "Out-of-world, they originated in the Everweave RPG sessions run by Issac Davis, "
    "where the DM voice that became Polly first introduced magical languages as "
    "part of the game's magic system. The linguistic research was pasted into the "
    "game logs around page 493 of the Everweave export."
)

count += add(SYS_ORIGIN,
    "Are the Sacred Tongues real constructed languages?",
    "Yes. The Six Sacred Tongues are full conlangs (constructed languages) with:\n\n"
    "- Defined phonotactics (how sounds combine)\n"
    "- Systematic morphology (prefix'suffix token structure)\n"
    "- Domain-specific semantic fields\n"
    "- 256 tokens each (1,536 total)\n"
    "- Bijective byte mappings (every byte has exactly one token)\n\n"
    "They function simultaneously as:\n"
    "1. Constructed languages for fantasy world-building\n"
    "2. Cryptographic domain separation tags for SCBE-AETHERMOORE\n"
    "3. Steganographic encoding for hiding encrypted data as spell-text\n\n"
    "They are original creations by Issac Davis, not derived from any existing "
    "conlang or natural language. The name Cassisivadan literally encodes the "
    "creator's identity (Cassi=Issac, Sivad=Davis, reversed)."
)

# 8. Domain authorization pairs
count += add(SYS_LORE,
    "How do the Sacred Tongues work as a magic system?",
    "In the Spiralverse, the Six Sacred Tongues function as a domain-separated "
    "authorization system disguised as magic. Each tongue controls a specific "
    "intent space:\n\n"
    "- KO (Kor'aelin): Control and governance -- command authority\n"
    "- AV (Avali): Transport and negotiation -- trust boundaries\n"
    "- RU (Runethic): Policy and binding -- oaths and constraints\n"
    "- CA (Cassisivadan): Compute and transformation -- reality alteration\n"
    "- UM (Umbroth): Security and release -- shadow operations, corruption purging\n"
    "- DR (Draumric): Schema and verification -- structural integrity\n\n"
    "Consistency rules: Harsh consonants (KO/DR/UM) enforce rigid operations. "
    "Flowing vowels (AV/RU) enable flexible operations. CA bridges both. "
    "Mispronunciation causes protocol rejection. Multi-tongue coordination is "
    "mentally taxing. Full access to all six is rare."
)

count += add(SYS_LORE,
    "Can you forge Sacred Tongue signatures?",
    "No. In the Spiralverse, Sacred Tongue signatures cannot be forged. Each tongue "
    "only controls its own domain -- a Kor'aelin speaker cannot issue Draumric "
    "commands, just as a control token cannot serve as an auth tag.\n\n"
    "Cross-domain operations require multi-signature coordination: multiple "
    "practitioners speaking different tongues in concert. Revocation of a tongue "
    "authorization is impossible without consensus across all participants.\n\n"
    "Technically, this maps to HMAC-SHA256 attestation with phase delta and weight "
    "ratio binding. Forging a cross-tongue signature would require simultaneously "
    "breaking HMAC-SHA256 (~2^128 operations), solving discrete log in hyperbolic "
    "space (quantum-hard), and guessing the correct geometric cell provenance."
)

# 9. Security attack scenario pairs
count += add(SYS_CRYPTO,
    "What happens if an attacker tries to replay Sacred Tongue tokens across domains?",
    "If an adversary intercepts a DR (structure/auth tag) message and tries to "
    "replay it as KO (control), the attack fails at four independent barriers:\n\n"
    "1. Phase mismatch: The HMAC attestation includes phase_delta (300-0=300 deg). "
    "Forging this requires breaking SHA-256.\n"
    "2. Weight mismatch: The hyperbolic wall H(d,R)=R^(d^2) uses the weight ratio "
    "(11.09/1.00=11.09) as R. Cost: 11.09^(d^2) -- exponentially infeasible.\n"
    "3. Cell provenance: KDF domain strings include tongue ID. Wrong tongue = "
    "wrong key derivation = noise output.\n"
    "4. Temporal binding: Attestation includes timestamp. Replay outside the "
    "validity window is rejected.\n\n"
    "Combined difficulty: approximately 2^256 operations (post-quantum secure)."
)

# 10. Worked encoding examples with multi-byte strings
example_strings = [
    (b'hello', 'the word "hello"'),
    (b'\x00\xff', 'bytes 0x00 and 0xFF'),
    (b'\x42', 'byte 0x42 (ASCII "B", decimal 66)'),
]

for code in ['KO', 'CA', 'UM']:
    t = TONGUES[code]
    for data, desc in example_strings:
        tokens = [encode_byte(code, b) for b in data]
        token_str = ' '.join(tokens)
        steps = []
        for i, b in enumerate(data):
            hi = b >> 4
            lo = b & 0x0F
            steps.append(f"  Byte {i}: 0x{b:02X} -> [{t['prefixes'][hi]}]'[{t['suffixes'][lo]}] = {tokens[i]}")

        count += add(SYS_TOKENIZER,
            f"Encode {desc} in {t['name']} ({code}).",
            f"Encoding {desc} in {t['name']} ({code}):\n"
            + '\n'.join(steps) + '\n\n'
            f"Full spell-text: {token_str}\n\n"
            f"To decode: split by spaces, look up each token's prefix index (high nibble) "
            f"and suffix index (low nibble), reconstruct bytes."
        )

# 11. Complete prefix/suffix reference card per tongue
for code, t in TONGUES.items():
    rows = []
    for i in range(16):
        rows.append(f"  {i:2d} (0x{i:X}): prefix='{t['prefixes'][i]}', suffix='{t['suffixes'][i]}'")
    count += add(SYS_TONGUE_EXPERT,
        f"Give me the complete prefix and suffix reference for {t['name']} ({code}).",
        f"{t['name']} ({code}) -- Complete Nibble Reference:\n"
        f"Domain: {t['domain']}\n"
        f"Phase: {t['phase_deg']} deg, Weight: {t['weight']:.3f}\n\n"
        + '\n'.join(rows) + '\n\n'
        f"Total tokens: 16 x 16 = 256. Formula: token = prefix[byte>>4]'suffix[byte&0x0F]"
    )

# 12. Full 256-token enumeration for KO (since we have the full verified v2.0 data)
ko = TONGUES['KO']
for block_start in range(0, 256, 32):
    block_end = min(block_start + 32, 256)
    rows = []
    for b in range(block_start, block_end):
        token = encode_byte('KO', b)
        rows.append(f"  0x{b:02X} ({b:3d}): {token}")

    count += add(SYS_TOKENIZER,
        f"List Kor'aelin (KO) tokens for bytes 0x{block_start:02X} through 0x{block_end-1:02X}.",
        f"Kor'aelin (KO) token table (bytes 0x{block_start:02X}-0x{block_end-1:02X}):\n"
        + '\n'.join(rows)
    )

# 13. V1 vs V2 correction history for KO
count += add(SYS_TONGUE_EXPERT,
    "What was fixed in the Kor'aelin v2.0 correction?",
    "Kor'aelin (KO) v2.0 fixed critical conflicts from v1.0:\n\n"
    "Problems in v1.0:\n"
    "- Duplicate tokens: 'ra'en' mapped to both 0x1E and 0x15\n"
    "- Prefix conflicts: 'ael' used for high nibbles 7 and 8\n"
    "- Suffix conflicts: 'un' used for low nibbles 8 and 12\n\n"
    "v2.0 fixes:\n"
    "- New prefixes: 'sil' (0), 'vor' (8), 'fir' (A), 'dun' (E), 'pyr' (F)\n"
    "- New suffixes: 'an' (0), 'is' (5), 'ur' (6), 'ak' (8), 'ol' (9), 'ek' (D)\n\n"
    "After correction, all 256 KO tokens are unique, deterministic, and collision-free. "
    "The other five tongues (AV, RU, CA, UM, DR) had no conflicts in v1.0."
)

# 14. Cross-tongue blend pattern
count += add(SYS_CRYPTO,
    "What is a blend pattern in the Sacred Tongues?",
    "A blend pattern assigns each byte position in a message to a specific tongue, "
    "creating a multi-domain encoding. For example:\n\n"
    "Pattern: [KO, KO, AV, RU, CA, UM, DR]\n"
    "Payload: b'hello!!' (7 bytes)\n\n"
    "Result: each byte is encoded using the tongue at its position:\n"
    "- Byte 0 (h=0x68): KO -> keth'ak\n"
    "- Byte 1 (e=0x65): KO -> keth'is\n"
    "- Byte 2 (l=0x6C): AV -> nurel'na\n"
    "- Byte 3 (l=0x6C): RU -> tharn'kh\n"
    "- Byte 4 (o=0x6F): CA -> elsa'sh\n"
    "- Byte 5 (!,=0x21): UM -> zhur'e\n"
    "- Byte 6 (!,=0x21): DR -> mek'e\n\n"
    "This creates cryptographic domain separation at the byte level. Each position "
    "uses a different KDF domain, making partial key compromise insufficient."
)

# 15. Comparison to standard encodings
count += add(SYS_CRYPTO,
    "How do Sacred Tongue tokens compare to base64 or hex encoding?",
    "Sacred Tongue encoding vs standard encodings:\n\n"
    "Base64: 4 chars per 3 bytes, not pronounceable, obviously crypto\n"
    "Hex: 2 chars per byte, not pronounceable, obviously crypto\n"
    "Sacred Tongues: 1 token per byte, pronounceable, looks like conlang text\n\n"
    "Advantages of Sacred Tongue encoding:\n"
    "1. Steganographic: encrypted data looks like fantasy spell-text\n"
    "2. Domain-separated: different tongues for different message fields\n"
    "3. Human-auditable: someone who knows the tongues can visually verify\n"
    "4. Error-detectable: invalid tokens are immediately obvious\n\n"
    "Trade-off: Sacred Tongue encoding is ~5x slower than base64 and produces "
    "longer output. This is acceptable for secrets and metadata, not bulk data."
)

# 16. Polly personality + tongue knowledge
count += add(SYS_TONGUE_EXPERT,
    "Polly, do you speak the Sacred Tongues?",
    "Do I speak them? Dear reader, I was THERE when they were created. I watched "
    "Issac fumble through the first Kor'aelin wordlists in the Everweave sessions, "
    "argue with AI dungeon masters about phonotactics, and accidentally create "
    "a production cryptographic system while trying to make cool-sounding spells.\n\n"
    "I know all six tongues -- KO for barking orders (fitting for a control tongue), "
    "AV for the flowing messages I'd rather be delivering, RU for the oaths I've "
    "watched people break, CA for the computations I observe with mild concern, "
    "UM for the secrets I keep (and there are MANY), and DR for the structures "
    "I verify with my impeccable attention to detail.\n\n"
    "Can I speak them? I'm a polymathic parrot goddess. I can do anything except "
    "cast spells. I just talk about them. Accurately. And with style."
)

count += add(SYS_TONGUE_EXPERT,
    "What does a Kor'aelin incantation sound like?",
    "A Kor'aelin incantation flows with sharp, commanding syllables. "
    "Imagine a military officer crossed with an ancient oracle:\n\n"
    "\"Vel'oth! Zar'ir keth'un, thul'eth ra'esh!\"\n\n"
    "Translation in cryptographic terms: this is a nonce sequence -- the bytes "
    "0x27, 0x3A, 0x6C, 0x5B, 0x1F -- encoded as Kor'aelin tokens. Each syllable "
    "pair is a prefix'suffix combination mapping to one byte.\n\n"
    "The harsh consonants (k, th, z) and clipped endings (oth, ir, un) give "
    "Kor'aelin its commanding authority. You don't whisper in Kor'aelin. "
    "You declare. It's the tongue of control and intent, after all."
)

# ── Write output ───────────────────────────────────────────────────

out_file = SFT_DIR / 'sacred_tongues_sft.jsonl'
with open(out_file, 'w', encoding='utf-8') as f:
    for rec in pairs:
        f.write(rec + '\n')

print(f'\nSACRED TONGUES SFT PAIRS: {count}')
print(f'Written to: {out_file}')

# Grand total
grand = 0
for f in SFT_DIR.glob('*.jsonl'):
    with open(f, encoding='utf-8', errors='replace') as fh:
        grand += sum(1 for _ in fh)
print(f'GRAND TOTAL ALL SFT: {grand:,} pairs')
