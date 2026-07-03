# Lis Biblioteca de Infinity / Conceptuali Poz Academica - 2026-06-27

Working meaning: every language, conlang, notation, binary lane, music lane, and book/reference system can be part of the coding library. The system may write through any face, but it must never lie about what that face can prove.

## Core rule

No fake code.

A language face can be any of these, but it must say which one it is:

| level | name | meaning | release claim allowed |
|---:|---|---|---|
| 0 | concept | idea/notation only | "conceptual mapping exists" |
| 1 | book | grammar/reference/manual exists | "reference lane exists" |
| 2 | emitter | system can emit source/text in that face | "emits source" |
| 3 | parser | system can read/lift that face into IR | "round-trip candidate" |
| 4 | interpreter | system can execute/evaluate it in a controlled runtime | "runs in interpreter" |
| 5 | compiler | system can compile/build it with a real toolchain | "compiles" |
| 6 | verified | emitted/lifted code ran against tests and produced a receipt | "verified by execution" |

## Product translation

- Rosetta Stone: concept and language mapping.
- STIB: executable opcode/program binary lane.
- Code Prism / LatticeOp: shared IR and code emission.
- Transference Gate: raw text/encoding into Python-safe text/source.
- Mixed Expression Lane: one packet can contain multiple language faces.
- Claim Gate: only verified faces can be release claims.

## The useful split

If we have a real compiler/interpreter, we use it.

If we do not have one, we still keep the language in the library as a book/reference face, but the claim is weaker:

- good: "We have a Runethic reference grammar and can emit annotated Runethic packets."
- bad: "Runethic compiled successfully" when no compiler exists.

## How to add a missing language or notation

1. Add a registry row.
2. Mark its capability level honestly.
3. Link its book/reference if level 1+.
4. Link emitter/parser/interpreter/compiler paths as they become real.
5. Add a receipt path only after something actually ran.
6. Promote the claim only after the claim gate sees code + test/demo + artifact.

## Why this matters

This lets AI sit in the workshop with every brush available: Python, Rust, Haskell, C, STIB, Sacred Tongues, color text, music/binary mapping, and future conlangs. The AI can sketch in any face, but product/release claims depend on the oven: compile, run, verify, receipt.
