# Document Lanes

Use these lanes to keep the repo readable and to separate established material from active thinking.

## `docs/notes`

Use for:

- raw working notes
- session captures
- short temporary writeups
- incomplete or unclassified material

This is the intake lane.

## `docs/facts`

Use for:

- hard established facts
- implemented behavior that can be pointed to in code or tests
- canonical constants, formulas, and source-backed claims
- stable reference material

This lane should stay conservative.

## `docs/theories-untested`

Use for:

- research ideas
- speculative mappings
- metaphors promoted into candidate math
- architectural proposals not yet tested
- concept notes that should not be mistaken for runtime truth

This lane is for unproven but potentially useful structure.

## `docs/tested-results`

Use for:

- benchmark summaries
- experiment outputs
- test result packets
- validation summaries
- compact result writeups tied to a run, script, or suite

This lane is for evidence after execution.

## Filing rule

If a document mixes multiple lanes, split it or mark the sections clearly.

Shortest rule:

- unknown or fresh -> `notes`
- established and source-backed -> `facts`
- speculative and not validated -> `theories-untested`
- executed and measured -> `tested-results`
