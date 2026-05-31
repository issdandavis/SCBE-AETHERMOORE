# ARC-Style Grid Benchmark

Status: executable local pretest, not an official ARC-AGI-2 score.

This lane evaluates SCBE/NeuroGolf on synthetic ARC-shaped grid tasks. Each task
contains public train examples, a held-out test input, and a hidden expected
output known only to the benchmark harness.

## Command

```bash
python scripts/benchmark/arc_style_grid_benchmark.py
```

Artifacts:

- `artifacts/benchmarks/arc_style_grid/latest_report.json`
- `artifacts/benchmarks/arc_style_grid/LATEST.md`

## Latest Local Result

```text
decision=HOLD
identity=0/5
neurogolf=4/5
```

Current unresolved task:

- `arc_local_tile_mirror`

This is a useful failure. The lane proves that the restricted IR solver beats
the identity baseline on local ARC-style tasks, while preserving a concrete next
target: improve composed 2x2 mirror-tiling induction without overfitting to one
fixture.

## Bifurcated Reasoning

Each fixture records two reasoning paths:

- Constructive branch: the candidate transformation the solver is trying.
- Defender branch: the invariant or falsification check that prevents a lucky
  but wrong transform from being accepted.

The branch flow is:

```text
train examples
  -> constructive hypothesis flow / defender falsification flow
  -> restricted IR program plus receipt hash
  -> hidden expected-output comparison
```

This matches the "different vessels, same flow" model: branches may travel
different directions, but they merge into one auditable receipt.

## Patent Provenance Boundary

The benchmark report links back to local patent/workbench evidence as
implementation provenance only. It does not assert patentability, validity, or
legal sufficiency.

Proof and goal are separated:

- Proof layer: the steps in the sand: fixtures, synthesized IR, topology
  vectors, hidden-output comparison, receipt hashes, and reports.
- Goal layer: the place we are walking toward: a generalizable grid-reasoning
  agent that learns from failures and later runs official ARC-AGI-2 tasks.
- Boundary: proof supports the path taken; it does not by itself prove the end
  goal has been reached.

Linked local references:

- `docs/PATENT_DETAILED_DESCRIPTION.md`
- `docs/specs/EVALUATION_CONTRACT_v1.md`
- `docs/legal/patent-workbench/claim_support_scan.md`
- `docs/benchmarks/HARD_AGENTIC_BENCHMARK_PRETEST.md`

Chain of provenance:

1. Synthetic ARC-style fixture JSON is written under artifacts.
2. Restricted NeuroGolf IR is synthesized from train examples.
3. Hidden expected output is compared outside the task prompt.
4. Per-lane receipt hash is generated from prediction, expected output,
   topology, and program metadata.
5. Stable JSON and Markdown reports are emitted for audit review.

## Claim Boundary

Allowed:

- SCBE has a local ARC-style grid benchmark.
- The current NeuroGolf lane scores `4/5` against an identity baseline of `0/5`.
- The benchmark emits bifurcated reasoning traces and patent-provenance links.

Not allowed:

- Official ARC-AGI-2 score.
- General human-level abstract reasoning claim.
- Claim that the unresolved tile-mirror fixture is solved.
