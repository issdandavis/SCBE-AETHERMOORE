# Tokenizer / Atomic Stack / Spiral Ring

This document puts the live implementations in one place and keeps the layer boundaries explicit.

The governing split is:

1. Canonical langues and semantic meaning are upstream.
2. SS1 and Sacred Tongues byte encoding are downstream transport.
3. The 8-vector atomic feature layout is a separate op-lattice layer.
4. The adaptive op-binary layer is a separate inverse-complexity layer.
5. Spiral Ring is a separate deterministic time-evolution system, not the tokenizer.

## 1. Layer Map

| Layer | What it is | Live source |
|---|---|---|
| Canon / semantic upstream | Tongue meaning, weights, canon phrases, tensor semantics | `docs/LANGUES_WEIGHTING_SYSTEM.md`, canonical registry/codex docs |
| Transport tokenizer | Byte -> tongue token -> byte | `src/tokenizer/ss1.ts`, `src/crypto/sacred_tongues.py` |
| Atomic op features | Per-op trit rows + 8-float feature vectors | `src/symphonic/multipath/_trit_common.py` |
| Adaptive binary routing | Path-width ledger, phi discount, remap | `src/symphonic/multipath/op_binary.py` |
| Deterministic temporal ring | Time-evolving entropic ring state | `src/symphonic_cipher/scbe_aethermoore/ede/spiral_ring.py` |

## 2. TypeScript SS1 Transport Tokenizer

Source: `src/tokenizer/ss1.ts`

This is the direct byte-level transport tokenizer. It does not define canon phrases. It encodes raw bytes into deterministic tongue tokens by splitting each byte into two nibbles.

```ts
/** Vocabulary lookup tables */
const VOCABULARIES: Record<TongueCode, { prefixes: string[]; suffixes: string[] }> = {
  KO: { prefixes: KO_PREFIXES, suffixes: KO_SUFFIXES },
  AV: { prefixes: AV_PREFIXES, suffixes: AV_SUFFIXES },
  RU: { prefixes: RU_PREFIXES, suffixes: RU_SUFFIXES },
  CA: { prefixes: CA_PREFIXES, suffixes: CA_SUFFIXES },
  UM: { prefixes: UM_PREFIXES, suffixes: UM_SUFFIXES },
  DR: { prefixes: DR_PREFIXES, suffixes: DR_SUFFIXES },
};

/**
 * Encode a single byte to a token
 *
 * Formula: Token = Prefix[High_Nibble] + "'" + Suffix[Low_Nibble]
 */
export function encodeByte(byte: number, tongue: TongueCode): string {
  if (byte < 0 || byte > 255) {
    throw new Error(`Byte value out of range: ${byte}`);
  }

  const vocab = VOCABULARIES[tongue];
  const highNibble = (byte >> 4) & 0x0f;
  const lowNibble = byte & 0x0f;

  return `${vocab.prefixes[highNibble]}'${vocab.suffixes[lowNibble]}`;
}

export function decodeByte(token: string, tongue: TongueCode): number {
  const vocab = VOCABULARIES[tongue];
  const parts = token.split("'");

  if (parts.length !== 2) {
    throw new Error(`Invalid token format: ${token}`);
  }

  const [prefix, suffix] = parts;
  const highNibble = vocab.prefixes.indexOf(prefix);
  const lowNibble = vocab.suffixes.indexOf(suffix);

  if (highNibble === -1) {
    throw new Error(`Unknown prefix '${prefix}' for tongue ${tongue}`);
  }
  if (lowNibble === -1) {
    throw new Error(`Unknown suffix '${suffix}' for tongue ${tongue}`);
  }

  return (highNibble << 4) | lowNibble;
}
```

The higher-level helpers in the same file add:

- `encode(...)` / `decode(...)` for buffers and spell-text
- `xlate(...)` for cross-tongue translation with attestation
- `blend(...)` / `unblend(...)` for stripe mode
- `createSS1Envelope(...)` / `parseSS1Envelope(...)` for RWP envelope integration
- `detectTongue(...)` and `validateTongueConsistency(...)` for transport inspection

Operational truth:

- This layer is byte transport.
- It is deterministic.
- It is not the same as canon phrase generation.

## 3. Python Sacred Tongues Tokenizer

Source: `src/crypto/sacred_tongues.py`

This is the Python-side deterministic transport implementation. It does the same byte/token bijection and adds protocol-section mapping plus spectral helpers.

```python
class SacredTongueTokenizer:
    """
    Deterministic byte ↔ Sacred Tongue token encoder.
    """

    def __init__(self, tongues: Dict[str, TongueSpec] = TONGUES):
        self.tongues = tongues
        self._build_tables()
        self._validate_security_properties()

    def _build_tables(self) -> None:
        """Precompute constant-time lookup tables."""
        self.byte_to_token: Dict[str, List[str]] = {}
        self.token_to_byte: Dict[str, Dict[str, int]] = {}

        for code, spec in self.tongues.items():
            b2t = [""] * 256
            t2b = {}

            for b in range(256):
                hi = (b >> 4) & 0x0F
                lo = b & 0x0F
                token = f"{spec.prefixes[hi]}'{spec.suffixes[lo]}"
                b2t[b] = token
                t2b[token] = b

            self.byte_to_token[code] = b2t
            self.token_to_byte[code] = t2b

    def encode_bytes(self, tongue_code: str, data: bytes) -> List[str]:
        if tongue_code not in self.byte_to_token:
            raise KeyError(f"Unknown tongue: {tongue_code}")
        table = self.byte_to_token[tongue_code]
        return [table[b] for b in data]

    def decode_tokens(self, tongue_code: str, tokens: List[str]) -> bytes:
        if tongue_code not in self.token_to_byte:
            raise KeyError(f"Unknown tongue: {tongue_code}")
        table = self.token_to_byte[tongue_code]
        try:
            return bytes(table[t] for t in tokens)
        except KeyError as e:
            raise ValueError(f"Invalid token for {tongue_code}: {e}")
```

The protocol-aware pieces in the same file add:

```python
SECTION_TONGUES: Dict[str, str] = {
    "aad": "av",
    "salt": "ru",
    "nonce": "ko",
    "ct": "ca",
    "tag": "dr",
    "redact": "um",
}
```

And the SCBE integration helpers add:

```python
def compute_harmonic_fingerprint(self, tongue_code: str, tokens: List[str]) -> float:
    spec = self.tongues[tongue_code]
    token_hash = hashlib.sha256("".join(tokens).encode()).digest()
    weight = int.from_bytes(token_hash[:4], "big") / (2**32)
    return spec.harmonic_frequency * weight

def validate_section_integrity(self, section: str, tokens: List[str]) -> bool:
    tongue_code = SECTION_TONGUES[section]
    valid_tokens = set(self.byte_to_token[tongue_code])
    return all(t in valid_tokens for t in tokens)
```

Operational truth:

- Same transport class as SS1, implemented in Python.
- Adds section-to-tongue policy and harmonic fingerprinting.
- Still not the same thing as the semantic/canonical phrase layer.

## 4. Atomic 8-Vector Op Feature Layer

Source: `src/symphonic/multipath/_trit_common.py`

This is the actual 8-vector atomic feature layout. It is not the byte tokenizer. It is the per-op lattice feature pack used by the multipath system.

```python
def build_trit_table(
    tongue: str,
    tongue_id: int,
    ops: List[str],
    bands: List[Tuple[str, int, int, int, int]],
    polarity: PolarityFn,
    neg_ops: set,
    dual_ops: set,
) -> TritTable:
    if len(ops) != 64:
        raise ValueError(f"{tongue}: ops must be exactly 64, got {len(ops)}")

    trit = np.zeros((64, 6), dtype=np.int8)
    for i, op in enumerate(ops):
        row = polarity(op)
        row = list(row)
        row[tongue_id] = 1
        trit[i] = row

    feat = np.zeros((64, 8), dtype=np.float32)

    for i, op in enumerate(ops):
        _, band, group = _band_for(i)
        period = (i // 16) + 1
        valence = (i % 8) + 1
        chi = 0.10 + 0.02 * (i % 16)
        feat[i] = (
            float(i + 1), float(group), float(period), float(valence),
            float(chi), float(band), float(tongue_id), 0.0,
        )
```

The 8-vector layout is:

1. `op_id + 1`
2. `group`
3. `period`
4. `valence`
5. `chi`
6. `band`
7. `tongue_id`
8. reserved `0.0`

The same module also provides:

- `TRIT_MATRIX (64, 6)` for six-channel polarity
- `atomic_stream(...)` for feature extraction over an op stream
- collision reporting (`ww`, `wr`, `wn`)
- axiom checks for table validity

Operational truth:

- This is the real atomic feature layout.
- It is downstream of op identity, not of raw bytes.
- It should not be conflated with the SS1 transport tokenizer.

## 5. Adaptive Op-Binary / Inverse-Complexity Layer

Source: `src/symphonic/multipath/op_binary.py`

This layer adapts encoding cost based on sustained use. It is the closest live code to the “worn path” / inverse-complexity idea.

```python
@dataclass
class UsageLedger:
    """
    Tracks sustained semantic co-activation per (op, tongue) pair.
    """

    width: Dict[Tuple[Op, str], float] = field(default_factory=dict)
    interactions: int = 0
    decay: float = 0.997
    growth: float = 1.0
    remap_every: int = 256
    remap_count: int = 0

    def touch(self, op: Op, tongue: str, intensity: float = 1.0) -> None:
        k = self._key(op, tongue)
        self.width[k] = self.width.get(k, 0.0) + self.growth * intensity
        self.interactions += 1
        if self.interactions % 16 == 0:
            for kk in list(self.width.keys()):
                self.width[kk] *= self.decay
                if self.width[kk] < 1e-4:
                    del self.width[kk]
        if self.interactions % self.remap_every == 0:
            self.remap_count += 1

    def effective_cost(self, op: Op, tongue: str) -> float:
        """
        cost = base_width / phi^path_width
        """
        base = float(TONGUE_WIDTH[tongue])
        w = self.path_width(op, tongue)
        return base / (PHI ** w)
```

The remap phase then reissues shorter bit patterns to the widest paths:

```python
def remap_tongue_table(ledger: UsageLedger, tongue: str) -> Dict[Op, str]:
    ranked = sorted(
        Op,
        key=lambda o: -ledger.path_width(o, tongue),
    )
    table: Dict[Op, str] = {}
    for rank, op in enumerate(ranked):
        body = format(rank, f"0{body_width}b")
        table[op] = prefix + body
    return table
```

Operational truth:

- This is not the tokenizer core.
- It is an adaptive routing/cost layer over op encodings.
- The “inverse complexity” behavior is implemented here through path width and phi discount.

## 6. Spiral Ring

Source: `src/symphonic_cipher/scbe_aethermoore/ede/spiral_ring.py`

This is a separate deterministic temporal system. It is not part of the tokenizer stack, but it is relevant because it provides a live spiral/ring implementation in the repo.

```python
"""
SpiralRing-64 - Deterministic Entropic Expansion
"""

RING_SIZE = 64
EXPANSION_RATE = 1.0
TIME_QUANTUM = 1.0
MAX_EXPANSION = 2**20

SPIRAL_PHI = PHI
SPIRAL_R = R_FIFTH
SPIRAL_TWIST = 2 * math.pi / PHI
```

The state object is:

```python
@dataclass
class SpiralPosition:
    index: int
    value: int
    phase: float
    depth: int
    entropy: float
```

And the ring container is:

```python
@dataclass
class SpiralRing:
    seed: bytes
    positions: List[SpiralPosition] = field(default_factory=list)
    current_time: float = 0.0
    state: RingState = RingState.INITIALIZED
    config: RingConfig = field(default_factory=RingConfig)
    _expansion_cache: Dict[int, List[int]] = field(default_factory=dict)
```

Key behavior:

- deterministic from seed + time
- phase distributed around the ring
- evolves in time quanta
- uses neighbor mixing plus step-dependent permutation
- imports `PHI`, `R_FIFTH`, and `harmonic_scale`

The nearby geometry note is:

Source: `docs/research/sphere-grid/geometry/phi-spiral.md`

```md
# Phi Spiral

phi = 1.618033988749895

## Tongue Weights (powers of phi)

| Tongue | Power | Weight |
| KO | phi^0 | 1.00 |
| AV | phi^1 | 1.62 |
| RU | phi^2 | 2.62 |
| CA | phi^3 | 4.24 |
| UM | phi^4 | 6.85 |
| DR | phi^5 | 11.09 |
```

Operational truth:

- Spiral Ring is a real code artifact.
- It is adjacent to the harmonic/spiral geometry family.
- It should not be merged into the tokenizer unless a later design explicitly couples them.

## 7. Clean Boundary Verdict

### Canon / semantic upstream

Use this layer for:

- public language
- lore phrases
- semantic weighting
- tensor meaning
- training semantics

Do not replace this layer with raw transport spell-text unless the task is explicitly about packet transport or tokenizer debugging.

### Transport tokenizer

Use this layer for:

- deterministic packet encoding
- byte-level transport
- section-bound RWP encoding
- audit/debug of transport flows

### Atomic op features

Use this layer for:

- per-op feature vectors
- trit lattice operations
- band/group/valence/chi feature extraction

### Adaptive op-binary routing

Use this layer for:

- cost shaping
- path-width memory
- remap behavior under repeated use

### Spiral Ring

Use this layer for:

- deterministic time-indexed ring state
- phase and entropic expansion studies
- spiral/ring temporal protocols

## 8. Minimal Answer To “Where Is The Actual Code?”

If the question is “show me the actual implementations,” the answer is:

- transport tokenizer:
  - `src/tokenizer/ss1.ts`
  - `src/crypto/sacred_tongues.py`
- atomic 8-vector feature layer:
  - `src/symphonic/multipath/_trit_common.py`
- adaptive inverse-complexity layer:
  - `src/symphonic/multipath/op_binary.py`
- spiral/ring live code:
  - `src/symphonic_cipher/scbe_aethermoore/ede/spiral_ring.py`

This is the live split in the repo.
