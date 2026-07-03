# Outcome-Based Computation Systems Benchmark

Date: 2026-06-27

## Question

How does the SCBE Machine Crystal lane compare with the best systems in the
world, homemade systems, and everything between for outcome-based computation?

## Short answer

SCBE is not currently a world-class formal proof system.

It is closer to a hybrid of:

* property-based testing,
* low-code/visual composition,
* symbolic computation,
* executable receipts,
* geometry-routed DSL/compiler work.

Its strongest current niche is:

```text
shape/conlang/geometry expression -> executable or rejected result -> receipt
```

The best world systems beat it on formal guarantees. SCBE beats most of them on
geometric/visual composition and cross-domain experimental breadth.

## Best-in-class lanes

| Lane | Best reference systems | What they prove or produce |
|---|---|---|
| Formal proof assistant | Rocq/Coq, Lean, Isabelle/HOL | Machine-checked proof objects |
| Verified critical system | seL4, CompCert | Deep proofs for specific OS/compiler artifacts |
| Verification-aware programming | Dafny, Frama-C | Code plus specs, static verification, counterexamples |
| Model checking | TLA+, Alloy-style tools | Bad state/counterexample discovery in abstract systems |
| SMT solving | Z3 | Satisfiability/counterexample engine used inside other tools |
| Property testing | Hypothesis, QuickCheck | Generated tests and minimized counterexamples |
| Fuzzing | AFL++, libFuzzer/ClusterFuzz-style workflows | Concrete crash/security inputs from coverage feedback |
| AI coding benchmark | SWE-bench Verified | Whether an AI patch fixes real GitHub issues under a harness |
| Symbolic computation | Wolfram Language / Mathematica | Broad executable symbolic/numeric/domain computation |
| Home/hacker visual systems | Scratch, Blockly, Node-RED | Blocks/flows that let humans compose working systems |
| SCBE lane | Machine Crystal + PHDM + p/n/e + Bhargava overlays | Geometry-routed executable/rejected receipts |

## What SCBE currently does well

1. Outcome receipts:
   `review_machine_crystal_area.py` verifies the primitive crystal, higher
   shape macros, PHDM safe/risk gate, dual/Fano bridge, Bhargava overlays,
   p/n/e conservation, and particle chemistry.

2. Geometry-first authoring:
   The cube is an 8-address hub, the octahedron is the executable dual, Fano is
   the 7-nonzero incidence view, and PHDM/torus/tesseract/Bhargava/p/n/e layers
   are adjacent surfaces.

3. Failure as first-class output:
   Risky PHDM paths compile but do not execute. Fake chemistry/nuclear reactions
   are rejected with conservation reasons.

4. Training value:
   Receipts are useful for AI training because each example can be tagged as
   executed, rejected, or boundary-limited.

## Where SCBE is behind the world leaders

1. Formal proof depth:
   Coq/Lean/Isabelle/seL4/CompCert have machine-checked proof foundations. SCBE
   mostly has executable checks and receipts.

2. Industrial maturity:
   Frama-C, Dafny, CompCert, seL4, Z3, Hypothesis, and AFL-style tools have much
   larger ecosystems and longer production history.

3. Benchmark corpus size:
   SCBE's current Machine Crystal benchmark is small. It needs hundreds to
   thousands of adversarial/generated cases, hidden cases, and differential
   comparisons.

4. Domain completeness:
   p/n/e and chemistry layers are conservation gates over selected examples,
   not full NIST/chemistry/nuclear engines.

## Benchmark criteria

The runnable scorecard uses eight criteria:

| Criterion | Meaning |
|---|---|
| proof_strength | Machine-checkable proof or hard formal guarantee |
| executable_outcome | Can run and verify the produced result |
| counterexample_power | Finds bad states, fake inputs, or minimized failures |
| domain_breadth | Number of domains expressible without rebuilding |
| human_accessibility | Usability by normal builders/students/operators |
| artifact_reproducibility | Receipts, proof objects, deterministic reruns |
| visual_geometric_composition | Blocks, graphs, shapes, flows, geometry |
| ai_training_feedback | Useful feedback for AI agents and evals |

Run:

```powershell
python scripts\system\benchmark_outcome_computation_systems.py
```

Output:

```text
artifacts/outcome_computation/systems_benchmark.json
```

## Current scorecard interpretation

The benchmark is intentionally subjective but explicit. It says:

* Dafny-style systems are the closest world-class comparison for "code plus
  machine-checkable outcome".
* Hypothesis/QuickCheck are the closest comparison for "outcome by generated
  tests and counterexamples".
* Scratch/Blockly/Node-RED are the closest comparison for "homemade visual
  composability".
* Wolfram is the closest comparison for "broad computational language with
  high-level domain objects".
* SCBE's unique position is "geometric authoring plus executable/rejected
  receipts across mixed domains".

## Practical next benchmark upgrades

1. Add Hypothesis-generated cases for p/n/e and particle chemistry.
2. Add Z3 checks for conservation constraints.
3. Add TLA+-style state specs for PHDM safe/risk path gates.
4. Add a Dafny mini-spec for one shape macro, such as `triangle` transfer.
5. Add differential checks against Wolfram/SymPy for arithmetic overlays.
6. Add Blockly/Node-RED export for the geometry relation map.
7. Add hidden cases so SCBE cannot overfit its own examples.

## Sources

* Rocq/Coq: https://rocq-prover.org/
* Lean: https://lean-lang.org/
* Mathlib: https://lean-lang.org/use-cases/mathlib/
* seL4 proofs: https://sel4.systems/Verification/proofs.html
* CompCert: https://compcert.org/
* Dafny: https://dafny.org/
* Frama-C: https://frama-c.com/
* Z3: https://www.microsoft.com/en-us/research/project/z3-3/
* Z3 Guide: https://microsoft.github.io/z3guide/docs/logic/intro/
* TLA+ proof system: https://proofs.tlapl.us/doc/web/content/Home.html
* Hypothesis: https://hypothesis.readthedocs.io/
* ClusterFuzz coverage-guided fuzzing: https://google.github.io/clusterfuzz/reference/coverage-guided-vs-blackbox/
* SWE-bench: https://www.swebench.com/
* Wolfram Language: https://www.wolfram.com/language/
* Scratch: https://scratch.mit.edu/starter-projects
* Blockly: https://docs.blockly.com/
* Node-RED: https://github.com/node-red/node-red
