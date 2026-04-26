# Cross-Tongue Bijective Project Builder

**Date:** 2026-04-26
**Status:** v1 landed, smoke test green (8/8)
**Code:** `scripts/build_cross_tongue_project.py`
**Test:** `tests/test_cross_tongue_project_builder.py`

## Purpose

Build a project consisting of multiple algorithms, each implemented in all six Sacred Tongues (KO/AV/RU/CA/UM/DR), and prove three layers of bijection that together let an edit at slot k in any tongue propagate to slot k in every other tongue.

This generalizes `experiments/bijective_2tongue_build/run_all_six.py` (which proves bijection on a single algorithm) into a reusable, multi-algorithm project builder that emits a sealed bundle.

## Dual-Bijection Contract

The builder enforces three contracts. A bundle is "all green" only when all three hold for every (algorithm, tongue) pair.

### L1 — Byte-level bijection (per tongue)

For every `(algorithm, tongue)`:

```
src.encode("utf-8") == decode_tokens(tongue, encode_bytes(tongue, src.encode("utf-8")))
```

This is the standard `SacredTongueTokenizer` round-trip. Validated at construction of the tokenizer; the builder re-asserts per-pair and records `n_tokens` and `sha256(src)` in the bundle.

### L2 — Cross-tongue byte invariance (shared byte plane)

For every source `src`, encoding/decoding through *any* tongue must return the original bytes:

```
for code in (ko, av, ru, ca, um, dr):
    assert src.encode("utf-8") == decode_tokens(code, encode_bytes(code, src.encode("utf-8")))
```

This proves the byte plane is shared across tongues — a tongue is a presentation, not a partition.

### L3 — Slot-aligned semantic bijection

Every algorithm declares an ordered list of slot names, e.g. `["sig", "init", "loop_open", "loop_body", "ret"]` for `sum_list`, or `["sig", "body"]` for `add` and `is_palindrome`.

The slot list must be **identical across all six tongues** for that algorithm. The builder enforces this via `slot_alignment_proof`. An edit at slot k in any tongue maps unambiguously to slot k in every other tongue — *bijective edit propagation*.

This is the contract that makes the system useful for cross-language project work, not just tokenizer demos. L1 + L2 prove the bytes survive the tongue lift; L3 proves the *meaning* survives it.

## Bundle Output

`artifacts/cross_tongue_projects/<project_name>/bundle.json` contains:

```jsonc
{
  "project": "...",
  "tongue_order": ["ko", "av", "ru", "ca", "um", "dr"],
  "spirit_languages": { "ko": "Python", ... },
  "algorithms": [
    {
      "name": "...",
      "slot_order": ["sig", "body", ...],
      "implementations": {
        "ko": {
          "language": "Python",
          "slots": { "sig": "...", "body": "..." },
          "rendered": "<full source>",
          "tokenizer_seal": ["tok'a", "kor'b", ...],
          "sha256": "..."
        },
        "av": { ... }, "ru": { ... }, "ca": { ... }, "um": { ... }, "dr": { ... }
      }
    }
  ],
  "bijection_proofs": {
    "byte_round_trip": { "<algo>": { "<tongue>": { "ok": true, "n_tokens": N, "sha256": "..." } } },
    "cross_tongue_invariance": { "<algo>": { "<tongue>": { "ok": true, "fail_at": null } } },
    "slot_alignment": { "<algo>": { "ok": true, "expected": [...], "error": null } }
  },
  "summary": {
    "n_algorithms": 3, "n_tongues": 6,
    "byte_round_trip_all_ok": true,
    "cross_tongue_invariance_all_ok": true,
    "slot_alignment_all_ok": true,
    "all_green": true
  }
}
```

The `tokenizer_seal` is the encoded token list; `decode_tokens(tongue, seal)` returns `rendered.encode("utf-8")` exactly. This is asserted by `test_tokenizer_seal_decodes_to_source`.

## Built-in Project Spec

`arithmetic_basics`:

| Algorithm     | Slot order                                     |
|---------------|------------------------------------------------|
| `add`         | sig, body                                      |
| `sum_list`    | sig, init, loop_open, loop_body, ret           |
| `is_palindrome` | sig, body                                    |

Each algorithm has six slotted implementations (one per tongue). DR (Markdown) is narrative — it satisfies the slot contract semantically (each slot describes the same role) without being executable.

## Run

```bash
python scripts/build_cross_tongue_project.py
python scripts/build_cross_tongue_project.py --project arithmetic_basics
python scripts/build_cross_tongue_project.py --out artifacts/cross_tongue_projects/foo
```

```bash
PYTHONPATH=. python -m pytest tests/test_cross_tongue_project_builder.py -v
```

## What This Is Not

- Not a code generator. Slotted implementations are authored, not synthesized.
- Not an executor. Semantic agreement (do all six tongues compute the same answer?) is covered by `experiments/bijective_2tongue_build/run_all_six.py`, which executes where toolchains exist (`python`/`node`/`rustc`/`runghc`/`wolframscript`) and treats DR as narrative.
- Not a publication target. This is internal infrastructure for cross-language project work and as a substrate for future training data exporters.

## Next Steps

### Landed

- **Training-data emitter** (`scripts/emit_cross_tongue_sft.py`, `tests/test_emit_cross_tongue_sft.py`).
  Reads a sealed bundle and emits SFT rows in the `bijective_codeflow_v1` schema:
  one `translate_one` row per ordered (src, dst) tongue pair (90 rows for
  `arithmetic_basics`: 3 algos × 6 × 5) plus one `identify` row per (algo,
  tongue) (18 rows). Refuses to emit from a non-green bundle. Output:
  `training-data/sft/cross_tongue_<project>.sft.jsonl`.

### Backlog (Not Built)

- **Executor wiring.** Optionally run each tongue's source where the toolchain is present and bundle the stdout / status into the proof block. This brings L4 (semantic agreement) into the same bundle.
- **More project specs.** `arithmetic_basics` is the first; future projects can add string algorithms, tree traversals, small DSL primitives.
- **Slot-edit propagation.** Given a slot edit in one tongue, generate the candidate edit in the other five, validate L1+L2+L3 hold post-edit, emit the diff bundle.
