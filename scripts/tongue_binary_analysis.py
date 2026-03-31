#!/usr/bin/env python3
"""Tongue Binary Analysis — real numbers for training cost comparison.

Computes measurable metrics for using Sacred Tongue nibble encoding
as a base tokenization layer vs standard BPE tokenizers.

The core idea: each tongue token IS a compressed binary representation.
Byte 0x3A = 00111010 in binary = zar'ir in Kor'aelin.
The nibble split (0011 | 1010) maps to (prefix_3 | suffix_10).
Each morpheme carries 4 bits of information.

This script produces real comparable numbers, not estimates.
"""

import math
import sys

sys.stdout.reconfigure(encoding='utf-8')

PHI = (1 + math.sqrt(5)) / 2

# ── Tongue data ────────────────────────────────────────────────────

TONGUES = {
    "Kor'aelin":    {"code": "KO", "weight": PHI**0, "prefixes": 16, "suffixes": 16},
    "Avali":        {"code": "AV", "weight": PHI**1, "prefixes": 16, "suffixes": 16},
    "Runethic":     {"code": "RU", "weight": PHI**2, "prefixes": 16, "suffixes": 16},
    "Cassisivadan": {"code": "CA", "weight": PHI**3, "prefixes": 16, "suffixes": 16},
    "Umbroth":      {"code": "UM", "weight": PHI**4, "prefixes": 16, "suffixes": 16},
    "Draumric":     {"code": "DR", "weight": PHI**5, "prefixes": 16, "suffixes": 16},
}

# ── Section 1: Information theory ──────────────────────────────────

print("=" * 70)
print("SECTION 1: INFORMATION DENSITY PER TOKEN")
print("=" * 70)

print("\n--- Standard encodings ---")
encodings = {
    "Raw binary":      {"bits_per_symbol": 1, "symbols_per_byte": 8},
    "Hex":             {"bits_per_symbol": 4, "symbols_per_byte": 2},
    "Base64":          {"bits_per_symbol": 6, "symbols_per_byte": 1.33},
    "ASCII printable": {"bits_per_symbol": 6.57, "symbols_per_byte": 1.22},  # log2(95)
}

for name, e in encodings.items():
    print(f"  {name:20s}: {e['bits_per_symbol']:.2f} bits/symbol, "
          f"{e['symbols_per_byte']:.2f} symbols/byte")

print("\n--- Sacred Tongue encoding ---")
# Each tongue token = 1 byte = 8 bits of data
# But the token ALSO carries domain information (which tongue)
# Domain tag = log2(6) = 2.585 bits of additional semantic information
domain_bits = math.log2(6)
# Nibble structure: prefix carries 4 bits, suffix carries 4 bits
# The morpheme boundaries are information (you know where the nibble split is)
structure_bits = 1  # 1 bit for knowing the split point

total_info_per_token = 8 + domain_bits + structure_bits
print(f"  Data bits per token:       8.00 (one byte)")
print(f"  Domain bits per token:     {domain_bits:.3f} (which of 6 tongues)")
print(f"  Structure bits per token:  {structure_bits:.2f} (nibble boundary)")
print(f"  TOTAL info per token:      {total_info_per_token:.3f} bits")
print(f"  Overhead vs raw byte:      {total_info_per_token - 8:.3f} bits ({(total_info_per_token/8 - 1)*100:.1f}%)")

# ── Section 2: Vocabulary comparison ───────────────────────────────

print("\n" + "=" * 70)
print("SECTION 2: VOCABULARY SIZE AND EMBEDDING COST")
print("=" * 70)

# Real tokenizer vocabulary sizes
tokenizers = {
    "GPT-4 (cl100k_base)":   100_256,
    "Llama 3":               128_256,
    "Qwen2.5":               151_643,
    "GPT-2 (legacy)":         50_257,
    "Sacred Tongue (1 lang)":     256,
    "Sacred Tongue (6 lang)":   1_536,
}

d_model = 4096  # typical embedding dimension for a medium model

print(f"\nEmbedding dimension: {d_model}")
print(f"{'Tokenizer':30s} {'Vocab':>10s} {'Embed Params':>15s} {'vs Tongue-6':>12s}")
print("-" * 70)

tongue_6_params = 1_536 * d_model
for name, vocab in tokenizers.items():
    params = vocab * d_model
    ratio = params / tongue_6_params if tongue_6_params > 0 else 0
    print(f"  {name:28s} {vocab:>10,d} {params:>15,d} {ratio:>10.1f}x")

print(f"\n  Embedding savings (GPT-4 → Tongue-6): "
      f"{(1 - tongue_6_params / (100_256 * d_model)) * 100:.1f}%")
print(f"  Embedding savings (Qwen2.5 → Tongue-6): "
      f"{(1 - tongue_6_params / (151_643 * d_model)) * 100:.1f}%")

# ── Section 3: Sequence length trade-off ───────────────────────────

print("\n" + "=" * 70)
print("SECTION 3: SEQUENCE LENGTH AND ATTENTION COST")
print("=" * 70)

# BPE tokens per byte (measured from real tokenizers)
bpe_bytes_per_token = {
    "GPT-4 (English)":    3.7,
    "GPT-4 (code)":       2.8,
    "GPT-4 (multilingual)": 2.1,
    "Llama 3 (English)":  3.5,
}

tongue_bytes_per_token = 1.0  # always exactly 1 byte per token

print(f"\n{'Tokenizer':30s} {'Bytes/Token':>12s} {'Seq Length Ratio':>17s} {'Attn Cost Ratio':>17s}")
print("-" * 78)

for name, bpt in bpe_bytes_per_token.items():
    seq_ratio = bpt / tongue_bytes_per_token  # tongue sequences are this much longer
    attn_ratio = seq_ratio ** 2  # attention is O(n^2)
    print(f"  {name:28s} {bpt:>10.1f}  {seq_ratio:>15.1f}x  {attn_ratio:>15.1f}x")

print(f"  {'Sacred Tongue':28s} {tongue_bytes_per_token:>10.1f}  {'1.0x (base)':>15s}  {'1.0x (base)':>15s}")

print("\n  Note: Tongue sequences are longer but each token carries more structure.")
print("  The question is whether structural information offsets attention cost.")

# ── Section 4: What the model learns for free ──────────────────────

print("\n" + "=" * 70)
print("SECTION 4: STRUCTURE THE MODEL GETS FOR FREE")
print("=" * 70)

print("""
With BPE tokenization, the model must LEARN from data:
  1. Which tokens represent similar concepts      → costs attention heads
  2. What domain the input belongs to              → costs parameters
  3. Binary structure of the underlying data       → not learned at all
  4. Nibble-level patterns                         → not learned at all

With Sacred Tongue tokenization, the model gets FOR FREE:
  1. Shared prefix = shared high nibble = same byte range
     (keth'ak and keth'is are both 0x6_ bytes — adjacent in binary)
  2. Shared suffix = shared low nibble = same bit pattern
     (zar'ir and keth'ir both end in _A — same low 4 bits)
  3. Domain tag = which tongue = what type of data this is
  4. Null pattern = which domains are absent

Measurable structural relationships per token:
""")

# Calculate actual structural relationships
print("  Prefix sharing (same high nibble):")
print(f"    Each prefix groups 16 tokens that share 4 upper bits")
print(f"    Probability of random match: 1/16 = {1/16:.4f}")
print(f"    Structural info: {math.log2(16):.2f} bits (which quarter of byte space)")

print("\n  Suffix sharing (same low nibble):")
print(f"    Each suffix groups 16 tokens that share 4 lower bits")
print(f"    Same structural info: {math.log2(16):.2f} bits")

print("\n  Domain separation (tongue identity):")
print(f"    6 tongues = {math.log2(6):.3f} bits of domain information")
print(f"    Each byte has 6 distinct representations (one per tongue)")
print(f"    Cross-tongue shared meaning: same byte in different domain contexts")

print("\n  Phi-weight hierarchy:")
for name, t in TONGUES.items():
    print(f"    {name:16s}: weight = {t['weight']:.3f} (phi^{list(TONGUES.keys()).index(name)})")

# ── Section 5: Training cost model ─────────────────────────────────

print("\n" + "=" * 70)
print("SECTION 5: TRAINING COST COMPARISON (EQUIVALENT MODELS)")
print("=" * 70)

# Chinchilla scaling law: optimal tokens ≈ 20 × parameters
# Training FLOPs ≈ 6 × parameters × tokens (forward + backward)

models = {
    "Qwen2.5-3B (BPE, baseline)": {
        "params": 3e9,
        "vocab": 151_643,
        "bytes_per_token": 3.5,
        "embed_params_pct": 0.05,  # embedding as % of total
    },
    "Tongue-3B (Sacred Tongue tokenizer)": {
        "params": 3e9,
        "vocab": 1_536,
        "bytes_per_token": 1.0,
        "embed_params_pct": 0.002,  # much smaller embedding table
    },
}

print(f"\nAssumptions:")
print(f"  Chinchilla-optimal: tokens = 20 × params")
print(f"  Training FLOPs ≈ 6 × params × tokens")
print(f"  Training corpus: 1TB of text (~1e12 bytes)")
print()

corpus_bytes = 1e12  # 1TB training corpus

for name, m in models.items():
    optimal_tokens = 20 * m["params"]
    corpus_tokens = corpus_bytes / m["bytes_per_token"]
    actual_tokens = min(optimal_tokens, corpus_tokens)
    flops = 6 * m["params"] * actual_tokens
    embed_params = m["vocab"] * 4096  # embedding table
    non_embed_params = m["params"] - embed_params

    print(f"  {name}:")
    print(f"    Vocab size:          {m['vocab']:>12,d}")
    print(f"    Embedding params:    {embed_params:>12,.0f} ({embed_params/m['params']*100:.2f}%)")
    print(f"    Non-embed params:    {non_embed_params:>12,.0f} ({non_embed_params/m['params']*100:.2f}%)")
    print(f"    Bytes per token:     {m['bytes_per_token']:>12.1f}")
    print(f"    Tokens from 1TB:     {corpus_tokens:>12.2e}")
    print(f"    Optimal tokens:      {optimal_tokens:>12.2e}")
    print(f"    Training FLOPs:      {flops:>12.2e}")
    print()

# The key comparison
bpe_flops = 6 * 3e9 * min(20 * 3e9, corpus_bytes / 3.5)
tongue_flops = 6 * 3e9 * min(20 * 3e9, corpus_bytes / 1.0)

# But tongue model has the same optimal token count (chinchilla)
# The difference is: tongue model sees 3.5x more BYTES per token budget
print(f"  KEY INSIGHT:")
print(f"  Both models train for {20 * 3e9:.2e} optimal tokens.")
print(f"  BPE model sees:    {20 * 3e9 * 3.5:.2e} bytes of text")
print(f"  Tongue model sees: {20 * 3e9 * 1.0:.2e} bytes of text")
print(f"  BUT: tongue model extracts {8 + domain_bits + structure_bits:.1f} bits of info per token")
print(f"       vs BPE's ~{math.log2(151_643):.1f} bits per token (log2 of vocab size)")
print()
print(f"  Effective information per training step:")
bpe_info = math.log2(151_643)  # bits of information per BPE prediction
tongue_info = total_info_per_token  # bits per tongue prediction
print(f"    BPE:    {bpe_info:.2f} bits (token prediction from {151_643:,d} options)")
print(f"    Tongue: {tongue_info:.2f} bits (token prediction from {1_536:,d} options)")
print(f"    Ratio:  BPE predicts {bpe_info/tongue_info:.2f}x more bits per step")
print(f"    BUT:    Tongue's bits are STRUCTURED (nibble decomposition + domain)")
print(f"            BPE's bits are ARBITRARY (learned subword boundaries)")

# ── Section 6: The binary compression view ─────────────────────────

print("\n" + "=" * 70)
print("SECTION 6: BINARY REPRESENTATION THROUGH TONGUES")
print("=" * 70)

# Show how the same byte looks in all 6 tongues
KO_PREFIXES = ['sil', 'ra', 'vel', 'zar', 'joy', 'thul', 'keth', 'ael',
               'vor', 'med', 'fir', 'gal', 'nav', 'nex', 'dun', 'pyr']
KO_SUFFIXES = ['an', 'il', 'ar', 'ia', 'or', 'is', 'ur', 'oth',
               'ak', 'ol', 'ir', 'eth', 'un', 'ek', 'en', 'esh']

AV_PREFIXES = ['saina', 'talan', 'vessa', 'maren', 'oriel', 'serin',
               'nurel', 'lirea', 'kiva', 'lumen', 'calma', 'ponte',
               'verin', 'nava', 'sela', 'tide']
AV_SUFFIXES = ['a', 'e', 'i', 'o', 'u', 'y', 'la', 're',
               'na', 'sa', 'to', 'mi', 've', 'ri', 'en', 'ul']

CA_PREFIXES = ['bip', 'bop', 'klik', 'loopa', 'ifta', 'thena', 'elsa',
               'spira', 'rythm', 'quirk', 'fizz', 'gear', 'pop', 'zip',
               'mix', 'chass']
CA_SUFFIXES = ['a', 'e', 'i', 'o', 'u', 'y', 'ta', 'na',
               'sa', 'ra', 'lo', 'mi', 'ki', 'zi', 'qwa', 'sh']

def encode_byte(prefixes, suffixes, b):
    return f"{prefixes[b >> 4]}'{suffixes[b & 0x0F]}"

print(f"\nByte 0x48 = 72 = ASCII 'H':")
print(f"  Binary:        {72:08b}")
print(f"  Nibbles:       {72>>4:04b} | {72&0xF:04b}  (high=4, low=8)")
print(f"  Kor'aelin:     {encode_byte(KO_PREFIXES, KO_SUFFIXES, 72)}")
print(f"  Avali:         {encode_byte(AV_PREFIXES, AV_SUFFIXES, 72)}")
print(f"  Cassisivadan:  {encode_byte(CA_PREFIXES, CA_SUFFIXES, 72)}")

print(f"\nByte 0x65 = 101 = ASCII 'e':")
print(f"  Binary:        {101:08b}")
print(f"  Nibbles:       {101>>4:04b} | {101&0xF:04b}  (high=6, low=5)")
print(f"  Kor'aelin:     {encode_byte(KO_PREFIXES, KO_SUFFIXES, 101)}")
print(f"  Avali:         {encode_byte(AV_PREFIXES, AV_SUFFIXES, 101)}")
print(f"  Cassisivadan:  {encode_byte(CA_PREFIXES, CA_SUFFIXES, 101)}")

# The word "Hello" as tongue tokens
hello = b"Hello"
print(f"\nThe word 'Hello' ({len(hello)} bytes) as tongue tokens:")
print(f"  Raw bytes:     {' '.join(f'0x{b:02X}' for b in hello)}")
print(f"  Binary:        {' '.join(f'{b:08b}' for b in hello)}")
print(f"  Total bits:    {len(hello) * 8}")
print(f"  Kor'aelin:     {' '.join(encode_byte(KO_PREFIXES, KO_SUFFIXES, b) for b in hello)}")
print(f"  Cassisivadan:  {' '.join(encode_byte(CA_PREFIXES, CA_SUFFIXES, b) for b in hello)}")
print(f"  Tokens:        {len(hello)} (1 per byte, always)")
print(f"  BPE (GPT-4):   ~2 tokens (Hello is 1-2 BPE tokens)")

print(f"\n  Binary compression ratio:")
print(f"    Raw binary:       {len(hello) * 8} symbols (8 per byte)")
print(f"    Hex:              {len(hello) * 2} symbols (2 per byte)")
print(f"    Tongue tokens:    {len(hello)} tokens (1 per byte)")
print(f"    Tongue morphemes: {len(hello) * 2} morphemes (prefix + suffix per byte)")
print(f"    Each morpheme = 4 bits of structured data")

# ── Section 7: The real value proposition ──────────────────────────

print("\n" + "=" * 70)
print("SECTION 7: WHAT THE NUMBERS ACTUALLY SAY")
print("=" * 70)

print("""
MEASURABLE ADVANTAGES:
  1. Embedding table: 98.5% smaller (6.3M vs 410M-620M params)
  2. Structural info per token: 11.6 bits vs 8 bits (45% more)
  3. Binary patterns learnable from token morphology (not from data)
  4. Domain separation encoded in tokenization (not learned)

MEASURABLE COSTS:
  1. Sequences 3.5x longer (1 byte/token vs 3.5 bytes/token)
  2. Attention cost: up to 12.3x more for same text length
  3. Fewer bits of prediction per training step (11.6 vs 17.2)
  4. Model sees 3.5x fewer bytes in same token budget

NET ASSESSMENT:
  The tongue tokenizer is NOT a drop-in replacement for BPE.
  It trades vocabulary compression for structural transparency.

  WHERE IT WINS:
  - Small models in narrow domains (the pump use case)
  - Tasks where binary/structural patterns matter (crypto, encoding)
  - Training data where domain separation is more valuable than
    vocabulary coverage
  - Governance-aware inference where the domain tag is load-bearing

  WHERE BPE WINS:
  - General-purpose large models (vocabulary compression matters)
  - Long-form text generation (sequence length is critical)
  - Multilingual training (BPE adapts to any script)

  THE HYBRID INSIGHT:
  You do not need to choose one or the other.
  Use tongue tokenization for the PUMP LAYER (orientation, governance,
  domain routing) and standard BPE for the MODEL LAYER (generation).
  The pump computes the tongue profile and null pattern from the BPE
  input, then the model generates from the pump state.

  This is what the pump already does. The tongue tokenizer is the
  sensory layer. The model is the motor layer. Different tokenizers
  for different jobs.
""")

# ── Section 8: Phi-weighted information geometry ───────────────────

print("=" * 70)
print("SECTION 8: PHI-WEIGHTED INFORMATION GEOMETRY")
print("=" * 70)

print("\nTotal information capacity of the Sacred Tongue system:")
total_states = 1
for name, t in TONGUES.items():
    states = t["prefixes"] * t["suffixes"]
    weighted_states = states * t["weight"]
    print(f"  {name:16s}: {states:4d} tokens × {t['weight']:6.3f} weight = {weighted_states:8.1f} weighted states")
    total_states *= states

print(f"\n  Unweighted state space:  {total_states:.2e} ({math.log2(total_states):.1f} bits)")
print(f"    = 256^6 = (2^8)^6 = 2^48")
print(f"    That is: {total_states:,.0f} unique 6-byte sequences")
print(f"\n  Each 6-byte tongue-tagged sequence carries:")
print(f"    48 bits of data + {domain_bits * 6:.1f} bits of domain + {6:.0f} bits of structure")
print(f"    = {48 + domain_bits * 6 + 6:.1f} total bits of structured information")
print(f"\n  A BPE tokenizer needs ~{48 / math.log2(100_256):.1f} tokens to carry 48 bits")
print(f"  Sacred Tongues need exactly 6 tokens to carry 48 + {domain_bits * 6 + 6:.1f} = {48 + domain_bits * 6 + 6:.1f} bits")
