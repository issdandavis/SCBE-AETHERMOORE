# Loom

A tiny **universal loop machine** that weaves one program into many languages — built for agentic AI code generation. An agent writes one small program; Loom:

1. **weaves** it into runnable **Python / JavaScript / C** that are *equal by construction*,
2. reads the **topology of its run** to detect infinite loops, and
3. checks **near-mirror symmetry** — whether the program round-trips through unparse→parse *exactly*, or only behaviorally.

It is standalone (no other project deps; numpy not required).

## The machine

A Minsky register machine — **Turing-complete with ≥2 registers**. Registers are non-negative integers (default 0).

```
inc R        ; R += 1
dec R L      ; if R > 0 then R -= 1 (fall through) else goto L
jmp L        ; goto L
out R        ; append R to the output trace
halt         ; stop
```

`#` or `;` starts a comment; `name:` is a label (its own line or prefixing an instruction).

## Quick start

```python
from python.loom import parse, run, emit_python, cross_check, mirror_check

ADD = """
loop: dec r1 done    ; r2 += r1
      inc r2
      jmp loop
done: out r2
      halt
"""
prog = parse(ADD)
run(prog, {"r1": 3, "r2": 4}).output     # -> [7]
run(parse("s: jmp s")).status            # -> "loop"  (revisited state = infinite loop)
cross_check(prog, [{"r1": 3, "r2": 4}])  # -> {"all_agree": True, "backends": [...]}
mirror_check(ADD)                        # -> {"exact_mirror": True, ...}
```

## The three ideas (and the honest caveats)

- **Points & loops.** A run is a sequence of state-points `(pc, registers)`. Because the machine is deterministic, a **revisited state closes a loop** — a self-intersection of the trajectory — which *proves* the program never halts. Loop detection is therefore **sound but incomplete**: a detected revisit is certainly infinite; not finding one within the step budget means *undetermined*, never *halts*. (You can't, in general, decide your own halting — the formal version of "you can't fully match yourself".)
- **Cross-linguistic coherence.** Each emitter generates the same `pc`-dispatch loop, so the language outputs are identical by construction; `cross_check` *verifies* it by actually running the reference interpreter, the emitted Python, and (if `node`/`gcc` are present) the emitted JS/C, confirming every backend agrees.
- **Near mirror symmetry.** `mirror_check` round-trips a program (`unparse`→`parse`). **Exact mirror** = structurally identical. **Near mirror** = behaviorally identical but structurally not quite (e.g. a jump-to-end becomes an explicit `halt`) — symmetric in effect, not in form. **Broken** = behavior changed (should never happen).

## Also

- `behaviorally_equivalent(src_a, src_b, inits)` — do two *different* programs produce the same output on a battery of inputs? (A behavior-space "collision" — for an agent deduping candidate solutions.)
