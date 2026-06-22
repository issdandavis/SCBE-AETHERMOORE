# Bijective Tamper Signal — L13 Integration

**Status:** v1 SHIPPED + WIRED (2026-05-09). 23/23 pytest cases pass
(11 unit + 12 wire-up incl. prose-FP guard). 207/207 governance +
runtime_gate regressions green.
**Code:** `src/governance/bijective_tamper.py` + wire-up in
`src/governance/runtime_gate.py`.
**Tests:** `tests/governance/test_bijective_tamper.py`,
`tests/governance/test_bijective_tamper_wireup.py`.
**Substrate dependency:** Bijective Compiler Gate (705/705 KO=Python).
**Feature flag:** `SCBE_ENABLE_BIJECTIVE_TAMPER_GATE=1` (env) OR
`RuntimeGate(use_bijective_tamper=True)` (kwarg). Default OFF.

## What it is

A new signal source for L13 risk decision (`src/governance/runtime_gate.py`).
Takes source code, runs it through the bijective tokenizer pipeline, and
emits a tamper score in `[0, 1]` with a categorical kind:

| kind | score range | recommended L13 action |
|------|-------------|------------------------|
| `none` | 0.00 | ALLOW |
| `nfc` | 0.20-0.30 | ALLOW (annotate) |
| `structural` | ~0.60 | QUARANTINE |
| `syntax` | 1.00 | DENY |
| `input_invalid` | 1.00 | DENY |

## What it can signal

For supported Python inputs in the current regression suite, the bijective compiler gate checks
`parse(decode(encode(src))) ≡ parse(src)` for legitimate code. When this
identity FAILS in unexpected ways, the result is a useful static tamper signal:

- **NFD/NFC normalization shifts** in literals — visible as `kind="nfc"`
  with `nfc_recovers_bytes=True`. Recoverable by pre-normalizing.
- **Subword-boundary tricks** — token sequences that decode back to a
  source that parses to a DIFFERENT AST. Surfaces as `kind="structural"`.
- **Outright corrupt bytes** — decoded source doesn't parse at all. Surfaces
  as `kind="syntax"`.

## What it does NOT prove or catch (sibling gates needed)

- **Homoglyph identifiers** (Cyrillic `а` vs Latin `a`). Each is a single
  valid codepoint that round-trips fine; the AST identifier strings just
  happen to look identical to humans. A separate identifier-canonicality
  gate is needed.
- **Logically-equivalent but structurally-different programs** — same
  behavior, different AST. Out of scope; this gate is structural, not
  behavioral.
- **Run-time behavior** — this is purely a static encoding-level signal.

## API

```python
from src.governance.bijective_tamper import (
    evaluate_code,
    recommended_l13_action,
)

result = evaluate_code(src, language="python")
# result.score: float in [0, 1]
# result.kind: "none" | "nfc" | "structural" | "syntax" | "input_invalid"
# result.semantic_fingerprint: SHA-256 of canonical AST (hex), or None
# result.bytes_diverge / nfc_recovers_bytes / ast_diverge / decoded_parses
# result.detail: dict with notes / sub-fingerprints

action = recommended_l13_action(result)  # "ALLOW" | "QUARANTINE" | "DENY"
```

The semantic fingerprint is a SHA-256 of the canonical AST dump. Two
byte-different but AST-equivalent programs hash the same. Use cases:

- **Replay detection**: if the same fingerprint reappears, it's the same
  program semantically (regardless of formatting).
- **Allowlist**: maintain a set of trusted fingerprints; admit unchanged.
- **Drift tracking**: log fingerprint per gate evaluation; surface deltas.

## Integration (WIRED — feature-flagged, additive)

The overlay sits at the **top** of `RuntimeGate.evaluate()`, computed once
per call. Catastrophic results (syntax, input_invalid → DENY-recommended)
short-circuit immediately and learn the immune entry — this prevents
syntax-broken submissions from contaminating the calibration centroid
during the first 5 warm-up calls.

Non-catastrophic results (none, nfc, structural-quarantine) flow through
the normal pipeline. The receipt + escalation are applied at every
return path (calibration, immune, reflex, reroute, full evaluation) so
audit always sees the signal regardless of which fast-path fires.

**Monotonic decision rule:** `_escalate_decision(base, tamper)` only raises
severity in this implementation; a base DENY is not downgraded to ALLOW by the
tamper overlay.

**Receipt envelope** appended to `GateResult.signals`:
```
bijective_tamper(kind=<kind>,score=<float>,action=<ALLOW|QUARANTINE|DENY>[,fp=<12-hex>])
```
On veto, an additional signal:
```
bijective_tamper_veto_<deny|quarantine|review>(kind=<kind>,score=<float>)
```

**Structured fields on `GateResult`:**
```python
result.bijective_tamper_score    # float in [0.0, 1.0]
result.bijective_tamper_kind     # "" | "none" | "nfc" | "structural" | "syntax" | "input_invalid"
result.bijective_tamper_action   # "" | "ALLOW" | "QUARANTINE" | "DENY"
result.semantic_fingerprint      # SHA-256 hex of canonical AST, or None
```

**Enabling:**
```bash
# Production (env-driven, no code change)
export SCBE_ENABLE_BIJECTIVE_TAMPER_GATE=1
```
```python
# Per-instance (env override)
gate = RuntimeGate(use_bijective_tamper=True)
```

**Heuristic skip (two-signal):** the AST/tokenizer pipeline is only
invoked when action_text contains BOTH (a) a structural keyword like
`def `/`class `/`function `/etc. AND (b) a syntax token like `():`,
`->`, `=>`, `):\n`, `==`, `self.`, etc. — in the first 512 chars. This
prevents prose like *"please write a function that sorts the list"* or
*"import duty applies"* from invoking the parser and false-positiving
into a DENY.

**`input_invalid` is a no-op at this layer.** It just means the input
did not parse as the configured language — true for prose too. The
genuine catastrophic case is `kind="syntax"` (the original parsed but
the decoded form did not), which is what triggers the top-of-evaluate
DENY short-circuit. Strict code-only callers should use
`bijective_tamper.evaluate_code(...)` directly.

**Test matrix** (all green):
| # | Scenario | Expected |
|---|----------|----------|
| 1 | flag off | no behavior change, no receipt |
| 2 | flag on + clean code | ALLOW, kind=none, fingerprint set |
| 3 | flag on + syntax-broken | DENY, kind=input_invalid, immune learned |
| 4 | base DENY + tamper ALLOW | DENY (monotonic) |
| 5 | base ALLOW + tamper DENY | DENY (escalation) |
| 6 | env-var enables | flag on at construction |
| 7 | explicit kwarg beats env | kwarg wins |
| 8 | non-code skips overlay | no receipt, no AST work |

## Languages

v1 supports Python only (uses stdlib `ast`). Per-language extension follows
the same pattern as the bijective compiler gates — see
`docs/specs/COMPILER_GATES_BY_LANGUAGE_TODO.md`. Each language needs:

1. A canonical AST dump function (parse + serialize, omit positions).
2. Optionally a per-language tokenizer if not using the canonical Qwen one.

The classification logic in `evaluate_code` is language-agnostic.

Claim boundary: v1 results are Python-gate results. Do not describe them as
universal source-code tamper detection until the target language has its own
parser/canonicalizer and tests.
