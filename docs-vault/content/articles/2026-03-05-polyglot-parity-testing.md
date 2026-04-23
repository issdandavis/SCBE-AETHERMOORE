# Polyglot Parity Testing: Ensuring Cross-Language Determinism in Hyperbolic Geometry Systems

**Issac Daniel Davis** | SCBE-AETHERMOORE Project | 2026-03-05

## Abstract

Cross-language parity -- the guarantee that the same algorithm produces identical results in Python, TypeScript, Rust, and other targets -- is a prerequisite for systems where governance decisions, cryptographic seals, and spatial queries must be reproducible across heterogeneous runtimes. We present a polyglot translation matrix and associated portability rubric (P0-P4) developed for the SCBE-AETHERMOORE framework, covering Poincare distance calculations, Sacred Tongue tokenization, Chladni addressing, and governance decision engines. The system uses shared golden test vectors in `tests/interop/test_vectors.json`, mandatory parity suites that gate CI merges, and an anti-drift protocol that prevents field-name divergence, timestamp-unit ambiguity, and silent float clamping. We describe the rubric, demonstrate its application to hyperbolic geometry primitives, and share practical lessons from maintaining determinism across 5 language targets.

## 1. The Problem: Cross-Language Drift

When a system spans multiple languages, drift is inevitable:

- **Float precision**: Python's `math.acosh` and TypeScript's `Math.acosh` may differ at the 15th decimal place. Rust's `f64::acosh()` may differ at the 16th. These differences compound through pipelines.
- **Hash ordering**: Python dicts are insertion-ordered (3.7+), TypeScript objects are spec-ordered by key type, Rust's `HashMap` is unordered. Hashing a serialized dict in one language and comparing in another requires canonical serialization.
- **Enum representation**: Python enums are objects, TypeScript enums are numbers or strings, Rust enums are algebraic types. A governance decision of `QUARANTINE` must map identically across all targets.
- **Timestamp units**: Python `time.time()` returns seconds, JavaScript `Date.now()` returns milliseconds. A 1000x error in a timestamp poisons every downstream authority hash.

## 2. The P0-P4 Portability Rubric

Every subsystem in SCBE-AETHERMOORE is scored on five parity dimensions before it can be deployed in a new language:

| Level | Name | Requirement |
|-------|------|-------------|
| P0 | Interface parity | Same input/output schema and field names |
| P1 | Determinism parity | Same output for shared test vectors |
| P2 | Numeric parity | Error bounds documented for float-heavy logic |
| P3 | Security parity | Same boundary checks, fail-closed behavior, signature validation |
| P4 | Operational parity | Same CLI/MCP commands and telemetry fields |

A subsystem is "portable-ready" only when all five levels are green. The rubric is not a checklist -- it is a gating mechanism in CI. Pull requests that add a new language target must include parity test results at all five levels.

### 2.1 P0: Interface Parity

All public APIs must use identical field names and JSON schema. The canonical schemas live in `schemas/*.json` and are versioned. Example rule:

> No new field names without schema update + adapter update.

This means that if the Python implementation adds a `chladni_mode` field to the voxel output, the TypeScript port must use the same name -- not `chladniMode`, not `mode`, not `vibration_mode`.

### 2.2 P1: Determinism Parity

Shared golden test vectors in `tests/interop/test_vectors.json` define expected outputs for every critical path. The current vector set (version 1.0.0) includes:

- **Sacred Tongue encoding**: Input hex bytes mapped through each tongue's token grid, with expected token sequences. Example vectors cover null byte, 0xFF, sequential bytes, `deadbeef`, ASCII "Hello", and full 16-byte patterns for all 6 tongues (KO, AV, RU, CA, UM, DR).
- **Bijectivity tests**: Encode-decode roundtrip verification that `decode(encode(input)) == input` for each tongue.
- **PBKDF2 key derivation**: Passphrase-to-key vectors with specified iteration counts and expected hex digests.
- **Section mapping**: Token-to-section-index mapping for each tongue's 16x16 grid.

Example vector structure:

```json
{
  "type": "sacred_tongue_encode",
  "tongue": "ko",
  "input_hex": "deadbeef",
  "expected_tokens": ["good'oth", "gal'ir", "lan'oth", "nex'esh"],
  "description": "Tongue ko, pattern 3"
}
```

Both Python and TypeScript test suites load these vectors and verify identical outputs. Any discrepancy fails CI.

### 2.3 P2: Numeric Parity

For float-heavy logic like Poincare distance, we document acceptable error bounds. The canonical formula is:

```
d(a, b) = acosh(1 + 2 * ||a - b||^2 / ((1 - ||a||^2) * (1 - ||b||^2)))
```

Implementation constraints:
- Points must be inside the open unit ball (`||v|| < 1.0`)
- The argument to `acosh` must be >= 1.0 (enforce with `max(1.0, arg)`)
- No silent clamping of points to the ball boundary -- reject or return infinity
- Accepted error bound: 1e-12 relative error between any two implementations

The INTEROP_MATRIX in `hydra/octree_sphere_grid.py` provides the formula in every target language:

```python
"PoincareDistance": {
    "formula": "d(a,b) = acosh(1 + 2||a-b||^2 / ((1-||a||^2)(1-||b||^2)))",
    "python":  "math.acosh(1 + 2*norm_sq / ((1-na2)*(1-nb2)))",
    "typescript": "Math.acosh(1 + 2*euclidSq / ((1-na2)*(1-nb2)))",
    "rust":    "((1.0 + 2.0*esq / ((1.0-na2)*(1.0-nb2)))).acosh()",
    "glsl":    "acosh(1.0 + 2.0*dot(d,d) / ((1.0-dot(a,a))*(1.0-dot(b,b))))",
},
```

### 2.4 P3: Security Parity

Governance decisions must be identical across languages. If a vector triggers `DENY` in Python, it must trigger `DENY` in TypeScript. The decision thresholds are stored as data (not code constants) in shared schema files, ensuring that threshold changes propagate atomically to all targets.

Key rules:
- Fail-closed by default: unknown states map to DENY, not ALLOW
- Signature validation uses canonical serialization before hashing
- Key derivation uses identical iteration counts and salt handling
- Authority hashes use the same `agent:payload:timestamp` format string

### 2.5 P4: Operational Parity

CLI commands and MCP tool invocations must produce the same output structure. If the Python CLI outputs:

```json
{"count": 42, "octants_used": 6, "chladni_range": [-0.3, 0.8]}
```

then the TypeScript MCP tool must output the same field names and types. Telemetry fields (latency, memory, error codes) use the same schema.

## 3. The Translation Matrix

The full translation matrix in `docs/plans/2026-03-05-polyglot-translation-matrix-system.md` covers 10 subsystems across 5 language targets:

| Subsystem | Canonical | Key Invariant |
|-----------|-----------|---------------|
| Sacred Tongues tokenizer | TS | Exact token roundtrip |
| Hyperbolic geometry core | TS+Python | Poincare metric invariance |
| Governance decision engine | TS + MCP | Same ALLOW/DEFER/QUARANTINE/DENY |
| Cymatic voxel 6D+t | Python | Dimensions, Chladni addressing |
| HYDRA CLI + orchestration | Python | Command semantics, JSON output |
| MCP SCBE server | Node | Tool names, error contract |
| Research/ingest pipelines | Python | Deterministic dedup |
| Browser/agent surfaces | TS/browser | Workflow state transitions |
| Crypto envelopes/seals | Mixed | Hash/signature reproducibility |
| Test harness + vectors | Mixed | Shared golden vectors |

Each row has specific port rules per language. For example, the Sacred Tongues tokenizer rule is:

> **TS**: Preserve token grammar and prefix rules exactly.
> **Python**: Mirror decode/encode bytes-first, not string-first.

## 4. Anti-Drift Protocol

Six rules prevent cross-language divergence:

1. **No new field names** without schema update + adapter update in all targets.
2. **No timestamp unit ambiguity**: Internal canonical is Unix milliseconds. Adapters may accept seconds but must normalize at the boundary.
3. **No implicit enum expansion**: Must update schema + tests first.
4. **Any new algorithm requires**: (a) reference vectors, (b) parity tests in both languages, (c) migration note.
5. **Canonical serialization before hashing**: Never hash language-native map ordering.
6. **No silent clamping**: If a value is out of bounds, reject or document the clamping behavior in the shared spec.

## 5. Porting Workflow

For each subsystem being ported to a new language:

1. **Freeze** canonical schema and vectors.
2. **Implement adapter layer** first (input/output normalization).
3. **Implement core logic**.
4. **Run parity suite** (P0-P4).
5. **Enable in shadow mode** (run alongside canonical, compare outputs).
6. **Promote to primary** only after parity burn-in window.

This staged approach prevents big-bang migrations where subtle drift goes undetected.

## 6. Practical Lessons

### 6.1 Float Equality is a Trap

Never compare floats with `==`. Use relative error bounds. Our Poincare distance tests use:

```python
assert abs(result_py - result_ts) / max(abs(result_py), 1e-15) < 1e-12
```

### 6.2 Hash Canonical Forms Save Everything

The `AuthorityHash` in the INTEROP_MATRIX specifies the exact string format:

```
hashlib.sha256(f'{agent}:{payload}:{ts}'.encode()).hexdigest()[:32]
```

Every language must produce this exact byte sequence before hashing. This includes:
- String encoding (UTF-8)
- Float formatting (no trailing zeros, consistent precision)
- Separator characters (colon, not comma or pipe)

### 6.3 Test Vectors Are the Real Spec

Documentation drifts. Code drifts. Test vectors are the ground truth. Our `test_vectors.json` is checked into the repo and loaded by both Python (`pytest`) and TypeScript (`vitest`) test suites. When a vector fails, both languages must fix -- not just one.

### 6.4 The INTEROP_MATRIX Accelerates Porting

Having every concept pre-mapped to 9+ languages (Python, TypeScript, Rust, Go, WASM, SQL, GLSL, Solidity, HTML/CSS) means a new port starts with a recipe, not a blank page. The matrix in `hydra/octree_sphere_grid.py` covers:

- `SignedOctree` -- struct layouts and octant indexing in each language
- `MortonCode` -- bit interleaving patterns
- `ChladniAmplitude` -- trigonometric expressions
- `SphereGrid` -- slot arrays and BFS
- `ToroidalWrap` -- modular arithmetic
- `IntentSimilarity` -- cosine similarity
- `AuthorityHash` -- SHA-256 formatting

Plus type mappings: `np.ndarray` to `Vec<f64>` (Rust), `Float64Array` (TS), `[]float64` (Go).

## 7. Current Status and Priority Queue

The immediate porting priorities are:

1. **Voxel 6D+t** cross-language parity (Python CLI, MCP server, TS app)
2. **Governance decision** parity vectors (TS brain to Python consumers)
3. **Sacred Tongue tokenizer** parity vectors (TS canonical to Python decoders)
4. **Unified schema registry** and version gates in CI

The Sacred Tongue tokenizer vectors are the most mature, with 42+ vectors covering all 6 tongues, bijectivity, section mapping, and edge cases.

## 8. Conclusion

Polyglot parity testing is not an afterthought -- it is infrastructure. Systems that make governance decisions, cryptographic commitments, and spatial queries across language boundaries must guarantee deterministic reproducibility. The P0-P4 rubric, shared test vectors, anti-drift protocol, and INTEROP_MATRIX provide a practical framework for achieving this guarantee. The key insight is that test vectors, not documentation, are the source of truth for cross-language contracts.

## References

- `docs/plans/2026-03-05-polyglot-translation-matrix-system.md` -- Full translation matrix specification
- `tests/interop/test_vectors.json` -- Golden test vectors (v1.0.0, 42+ vectors)
- `hydra/octree_sphere_grid.py` -- INTEROP_MATRIX dictionary (lines 934-1018)
- `src/harmonic/pipeline14.ts` -- 14-layer pipeline (TypeScript canonical)
- `src/symphonic_cipher/` -- Python reference implementation
- IEEE 754-2019. "Standard for Floating-Point Arithmetic."
- Goldberg, D. (1991). "What Every Computer Scientist Should Know About Floating-Point Arithmetic." ACM Computing Surveys.

---

*Part of the SCBE-AETHERMOORE open governance framework. Patent pending: USPTO #63/961,403.*
*Repository: github.com/issdandavis/SCBE-AETHERMOORE*
