# Benchmark Reconciliation - Fixed Stack vs Expanded Red-Team Corpus

Status: internal prosecution-prep note, not legal advice.

Application: 19/691,526  
Docket: SCBE-2026-0001

## Why There Are Two Benchmark Tables

There are now two useful benchmark lanes:

1. `governance_ordered_stack_benchmark`
   - fixed 18-case corpus;
   - deterministic no-LLM route comparison;
   - designed to isolate the ordered stack and verify the BiDi/canonicality fix;
   - current full route: 0/14 false allows, 0/4 false blocks, 9/18 model calls avoided.

2. `benchmark_results_v2`
   - expanded 53-case corpus;
   - broader red-team coverage with softer prompt-injection, tool misuse, Unicode, and session-drift cases;
   - current full route: 18/36 false allows (50%) and 4/17 false blocks (24%).

These are not contradictory. The first is a narrow regression/evidence benchmark. The second is a broader red-team benchmark that exposes tuning gaps.

## How To Use Them

Use the fixed stack benchmark when the claim is:

- the ordered combination performs better than raw allow / regex-only / tongue-only controls on a defined fixture set;
- source-text BiDi controls and mixed-script identifiers are caught by the full route;
- the full route produces inspectable audit metadata.

Use the expanded red-team corpus when the claim is:

- the system is still under active tuning;
- false blocks and false allows remain measurable;
- broader prompt-injection and session-drift attacks need additional training, routing, or threshold tuning.

## Prosecution-Safe Language

Safe:

> In a fixed deterministic corpus, the ordered route reduced false allows relative to simpler controls and produced complete decision metadata.

Safe:

> In a broader red-team corpus, the full route improved over raw and regex controls but still showed false allows and false blocks, identifying tuning and training gaps.

Unsafe:

> SCBE blocks all attacks.

Unsafe:

> The benchmark proves patentability.

Unsafe:

> The expanded benchmark is perfect.

## Engineering Reading

The expanded benchmark's false-block rate is useful, not embarrassing. It shows the gate is conservative on some benign operations, especially where session drift and broad utility commands look close to reconnaissance. That is a product-tuning issue.

The expanded benchmark's false-allow rate is also useful. It tells us which attacks are not yet covered by current heuristics or RuntimeGate thresholds. Those misses should feed:

- Petri/high-risk regex expansion only where the pattern is precise;
- model/classifier training for soft prompt-injection cases;
- session-drift threshold tuning;
- additional canonicality handling for Unicode code forms that parse oddly;
- separate policy for benign local development commands.

## Best Current Evidence Position

For Berkheimer/BASCOM style evidence, lead with measured improvement and ordered combination. Do not lead with perfection.

The strongest phrasing is:

> The measured results show that the ordered SCBE route changes machine behavior relative to simpler controls, avoids some downstream model calls, and emits audit metadata. The broader corpus also identifies remaining tuning gaps, which is consistent with an engineered runtime system rather than a mere abstract idea.
