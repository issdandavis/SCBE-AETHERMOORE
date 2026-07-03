# Outcome Computation Systems - Open Questions

Date: 2026-06-27

1. Should SCBE add a formal proof lane?
   Best candidates: Dafny first, then Lean/Rocq for smaller kernels.

2. Should the p/n/e and particle-chem layers get property-based tests?
   Use Hypothesis to generate formula/reaction cases and shrink failures.

3. Should conservation constraints be mirrored into Z3?
   That would turn selected p/n/e checks into symbolic satisfiability checks.

4. Should PHDM path gating get a model-checking spec?
   TLA+ or a small Python state model could test safe/risk route transitions.

5. Should block/flow export exist?
   Blockly or Node-RED export would make the geometry relation map usable by
   non-coders and small AIs.

6. What is the hidden benchmark?
   Current receipts are known examples. A serious benchmark needs held-out
   cases generated after the rules are fixed.

7. What is the benchmark target?
   Options: chemical conservation, shape-to-program macros, conlang-to-opcode,
   mixed-language emit/execute, PHDM route rejection, or all of them.
