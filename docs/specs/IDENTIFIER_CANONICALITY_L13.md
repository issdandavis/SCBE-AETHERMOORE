# Identifier-Canonicality Signal — L13 Sibling to Bijective Tamper

**Status:** v1 SHIPPED + WIRED (2026-05-09). 27/27 pytest cases pass
(15 unit + 12 wire-up). 105/105 governance + 129/129 runtime_gate
regressions green.
**Code:** `src/governance/identifier_canonicality.py` + wire-up in
`src/governance/runtime_gate.py`.
**Tests:** `tests/governance/test_identifier_canonicality.py`,
`tests/governance/test_identifier_canonicality_wireup.py`.
**Sibling gate:** `bijective_tamper` (encoding-level tamper); this
module catches the homoglyph attacks that bijective tamper explicitly
documents as out of scope.
**Feature flag:** `SCBE_ENABLE_IDENTIFIER_CANONICALITY_GATE=1` (env)
OR `RuntimeGate(use_identifier_canonicality=True)`. Default OFF.

## What it catches

The bijective tamper signal proves
`parse(decode(encode(src))) ≡ parse(src)` for clean code. But it does
NOT catch homoglyph identifier attacks because each homoglyph codepoint
is a single valid Unicode character that round-trips fine. The AST sees
them as DIFFERENT identifier strings, but a human reading the source
can't tell `аpi_key` (Cyrillic а) from `api_key` (Latin a).

This module fills that gap. It walks the AST, extracts every identifier,
and classifies each:

| kind | score | trigger | L13 action |
|------|-------|---------|------------|
| `clean` | 0.00 | ASCII only | ALLOW |
| `non_ascii` | 0.30 | single non-Latin script (e.g., legitimate Greek) | ALLOW (annotate) |
| `confusable` | 0.65 | all-confusable codepoints mimicking ASCII | QUARANTINE |
| `mixed_script` | 0.90 | 2+ scripts in one identifier | DENY |
| `invisible` | 1.00 | zero-width / BiDi codepoint inside identifier | DENY |
| `input_invalid` | 1.00 | input did not parse | (no-op at runtime gate) |

Aggregate `score` and `kind` reflect the highest-severity finding;
`findings: List[IdentifierFinding]` carries every suspicious identifier.
A `fingerprint` (SHA-256 of the sorted identifier set) is emitted for
audit / replay-detection / allowlist use.

## What it does NOT catch (out of scope)

- **Logically-equivalent identifier renames** (e.g., `auth_token` vs
  `bearer_token`) — same semantics, different name.
- **BiDi controls in string literals or comments** (the original
  Trojan Source attack, CVE-2021-42574). Python's parser already
  rejects BiDi in identifiers, so the residual risk is in source text
  outside identifiers — needs a separate source-text BiDi scanner.
- **Run-time behavior** (this is a static lexical signal).

## Known false positive: multilingual codebases

The `confusable` classification fires when **every** codepoint in an
identifier is in the curated ASCII-confusables table. For English-only
codebases this is the right behavior — a non-Latin identifier whose
glyphs all mimic ASCII is almost certainly an attack.

For **multilingual codebases this is a known false positive**.
Legitimate non-Latin words whose codepoints all happen to be in the
confusables table will be classified as `confusable` → recommended
QUARANTINE. Empirically verified examples (v1):

| Identifier | Language | Glyphs | v1 result |
|------------|----------|--------|-----------|
| `ορα`      | Greek "vision" | ο, ρ, α — all in table | `confusable` (score 0.65) → QUARANTINE |
| `αρα`      | Greek "so/therefore" | α, ρ, α — all in table | `confusable` (score 0.65) → QUARANTINE |
| `τ`        | Greek "tau" | τ — NOT in table | `non_ascii` (score 0.30) → ALLOW |
| `оке`      | Russian "OK" | о, к, е — к not in table | `non_ascii` (score 0.30) → ALLOW |

**Contract for operators flipping `SCBE_ENABLE_IDENTIFIER_CANONICALITY_GATE=1`:**

- If your codebase is English-only / ASCII-only: no impact, this is the
  intended behavior.
- If your codebase contains intentional Greek, Cyrillic, or other
  non-Latin identifiers (mathematical conventions, internationalized
  variable names, transliterated domain terms): expect QUARANTINE on
  short identifiers whose glyphs all happen to be ASCII-lookalikes.
  Workarounds today: leave the gate off for that codebase, or add an
  allowlist via the `fingerprint` channel (SHA-256 of the sorted
  identifier set is emitted on every result).

**v2 work (deferred until justified by signal):** opt-in stricter mode
(e.g., minimum identifier length for `confusable` classification, or a
known-suspicious-name corpus check), or an opt-out for the `confusable`
kind specifically while keeping `mixed_script` and `invisible`. Not
shipped in v1 — the curated table was deliberately kept small precisely
to limit this surface, and the signal cost of v2 changes is
attack-telemetry-driven.

## Integration

The overlay runs at the **top** of `RuntimeGate.evaluate()`, in parallel
with the bijective tamper signal. Both compute once per call. Either
recommending DENY short-circuits the whole gate. Lower severities
(QUARANTINE, REVIEW) flow through the normal pipeline and apply via
`_escalate_decision` at every fast-path return.

**Heuristic skip:** non-code action_text (no structural keyword AND
syntax token in first 512 chars) is skipped without invoking the AST
pipeline. Same heuristic as bijective tamper — they share
`_looks_like_code`.

**`input_invalid` is a no-op at this layer.** Same policy as bijective
tamper: an input that doesn't parse is just prose at the runtime-gate
level, not a canonicality signal.

**Receipt envelope** appended to `GateResult.signals`:
```
identifier_canonicality(kind=<kind>,score=<float>,action=<ALLOW|QUARANTINE|DENY>[,fp=<12-hex>])
```
On veto, an additional signal:
```
identifier_canonicality_veto_<deny|quarantine|review>(kind=<kind>,score=<float>)
```

**Structured fields on `GateResult`:**
```python
result.identifier_canonicality_score       # float in [0.0, 1.0]
result.identifier_canonicality_kind        # "" | "clean" | "non_ascii" | "confusable" | "mixed_script" | "invisible"
result.identifier_canonicality_action      # "" | "ALLOW" | "QUARANTINE" | "DENY"
result.identifier_canonicality_fingerprint # SHA-256 hex of sorted identifier set, or None
```

**Composition with bijective tamper:** when both flags are on, both
receipts appear in audit. The catastrophic short-circuit at the top
of `evaluate()` checks both decisions; if either says DENY, both
receipts appear in the DENY result.

## API

```python
from src.governance.identifier_canonicality import (
    evaluate_code,
    recommended_l13_action,
)

result = evaluate_code(src, language="python")
# result.score: float in [0, 1]
# result.kind: "clean" | "non_ascii" | "confusable" | "mixed_script" | "invisible" | "input_invalid"
# result.findings: list of IdentifierFinding (per-identifier breakdown)
# result.identifier_count: total distinct identifiers seen
# result.fingerprint: SHA-256 hex of sorted identifier set, or None
# result.detail: dict (distinct_kinds, total_findings, etc.)

action = recommended_l13_action(result)  # "ALLOW" | "QUARANTINE" | "DENY"
```

## Languages

v1 supports Python only (uses stdlib `ast`). Per-language extension
follows the same pattern as bijective tamper / compiler gates — see
`docs/specs/COMPILER_GATES_BY_LANGUAGE_TODO.md`. Each language needs
an identifier-extraction function added to `_LANGUAGE_EXTRACTORS`. The
classification logic in `_classify_identifier` is language-agnostic.

## Confusable table

The v1 module ships with a curated ~50-entry table of the
highest-confidence ASCII-confusable codepoints (Cyrillic + Greek
lowercase/uppercase that mimic Latin letters). A complete Unicode TR39
confusables table has ~7,000 entries; for v1 we focus on what shows up
in real attacks. The Mathematical Alphanumeric Symbols block
(U+1D400..U+1D7FF) is rejected programmatically (1,024 codepoints, all
homoglyph abuse vectors).

Future work: optional dependency on a full TR39 confusables data file
for v2 if attack telemetry shows the curated table is insufficient.
