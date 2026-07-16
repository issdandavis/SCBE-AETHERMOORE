# SCBE Pipeline Receipt

Command:

```powershell
node C:\Users\issda\SCBE-AETHERMOORE\bin\geoseal.cjs pipeline-receipt --content "def add(a,b): return a+b" --json
```

Purpose:

Create one inspectable receipt for the pipeline:

```text
raw utf8 bytes
-> binary / hex / trit spine
-> binary Turing probe
-> Sacred Tongue CLI token surface
-> CubeToken conlang faces
-> atomic token states
-> atomic neighbor gradient
-> code lane alignment
-> workflow composition
-> context code/conlang bridge
```

This does not replace the existing components. It records their relationship in one JSON object so humans, agents, and training jobs can see what happened.

## Why this matters

The SCBE code-language/conlang system has several valid surfaces:

- `python/scbe/bit_spine.py`
- `scbe.py`
- `src/tokenizer/ss1.ts`
- `python/scbe/cube_token.py`
- `python/scbe/atomic_tokenization.py`
- `src/tokenizer/atomic_workflow_units.py`
- `scripts/system/context_code_conlang_bridge.py`

The receipt command prevents those from being blended together without proof.

## Atomic gradient

The `atomic_workflow.gradient` block treats adjacent tokens as cells in a local flow field.

Each edge records:

- semantic shift
- trit distance
- band delta
- resilience delta
- adaptivity delta
- trust delta
- compatibility score
- flow class: `lock`, `slide`, or `boundary`

This gives the tokenizer a practical "slide into position" surface. Exact neighbors lock. Near neighbors become slide candidates. Hard semantic/trit jumps become boundaries.

## Useful examples

Receipt from text:

```powershell
geoseal pipeline-receipt --content "route classify submit select" --json
```

Receipt from file:

```powershell
geoseal pipeline-receipt --file C:\path\to\script.py --out C:\dev\aap_validation\pipeline_receipts\script.receipt.json --json
```

Use a different tongue or code target:

```powershell
geoseal pipeline-receipt --content "def solve(x): return x" --tongue CA --target-language javascript --json
```

## Training use

The receipt shape can become SFT/eval data:

- instruction: "Explain this SCBE pipeline receipt."
- instruction: "Which layer failed to round-trip?"
- instruction: "Convert this code intent into a conlang/code bridge packet."
- instruction: "Pick the cheapest safe route through the pipeline."

For AAP, each dataset/model run can be paired with a receipt so the training loop learns tool discipline: inspect, route, execute, score, select, and preserve evidence.
