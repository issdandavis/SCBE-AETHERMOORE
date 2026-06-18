# Syntactic phylogeny: language similarity by identical construct spelling

Edge = fraction of the 32 constructs two languages spell *identically* (normalized).
Computed from the table, not asserted -- but this is SURFACE spelling, a family tree of
NOTATION (brace / colon / ML family), NOT the shape of the computation.

## What this is NOT

Surface spelling is not semantics, and the two come apart:
- identical spelling, different meaning: `==` is one glyph in Java/C#/JS/Python but means
  reference vs value vs coercing equality (`1 == "1"` is False in Python, true in JS).
- different spelling, same computation: Haskell `map f xs` and Python `[f(x) for x in xs]`
  compute the same thing -- yet Haskell scores as the outlier here.
So these distances are notation lineage, not semantic distance. Use this as a TRANSPILER
WORK-ALLOCATION map: identical cells emit trivially; the divergences (the Haskell column)
are where real semantic effort lives. The same-computation axis is the IR +
polyglot_conformance.py (which RUNS the backends); see semantic_vs_syntax.py for proof.

## Nearest neighbours (each language's 3 closest faces by notation)

- **python** -> ruby (0.41), swift (0.38), lua (0.34)
- **javascript** -> typescript (0.91), csharp (0.56), java (0.50)
- **typescript** -> javascript (0.91), csharp (0.53), java (0.50)
- **c** -> cpp (0.66), csharp (0.53), zig (0.53)
- **cpp** -> c (0.66), csharp (0.53), java (0.53)
- **csharp** -> java (0.59), javascript (0.56), kotlin (0.56)
- **go** -> swift (0.56), javascript (0.41), typescript (0.41)
- **rust** -> c (0.44), cpp (0.44), swift (0.38)
- **java** -> csharp (0.59), cpp (0.53), kotlin (0.53)
- **kotlin** -> scala (0.59), csharp (0.56), java (0.53)
- **swift** -> go (0.56), kotlin (0.50), csharp (0.44)
- **ruby** -> javascript (0.44), typescript (0.44), python (0.41)
- **php** -> javascript (0.34), typescript (0.34), zig (0.31)
- **lua** -> python (0.34), julia (0.28), swift (0.25)
- **scala** -> kotlin (0.59), csharp (0.50), javascript (0.47)
- **julia** -> kotlin (0.44), swift (0.44), go (0.38)
- **haskell** -> scala (0.28), julia (0.28), python (0.25)
- **zig** -> c (0.53), javascript (0.41), typescript (0.41)
