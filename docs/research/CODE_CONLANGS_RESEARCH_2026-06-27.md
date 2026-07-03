# Code Conlangs / Esolangs Research Brief

Date: 2026-06-27
Question: What are code conlangs/esolangs, how do they compile or run, and what kinds of programs do they actually run?

## Short answer

"Code conlangs" usually means esoteric programming languages: intentionally constructed programming languages made for art, humor, minimalism, obfuscation, education, or research rather than normal software productivity.

Most do not compile like C/Rust. They usually run through one of four paths:

1. Interpreter: parse the weird source and execute directly.
2. Transpiler/source-to-source compiler: translate the conlang to C, JavaScript, Python, or another host language.
3. Native compiler/JIT: compile to machine code, bytecode, LLVM, or an optimized VM.
4. Embedded host trick: the language is already valid host syntax, such as JavaScript-only encodings.

They can theoretically run any computable program if Turing complete, but in practice they mostly run:

- Hello World
- cat/echo programs
- calculators
- truth machines
- quines
- text encoders/decoders
- simple games
- interpreters for other esolangs
- puzzles and benchmark tasks
- demonstrations of compiler/interpreter design

## Major examples

| Language | Core idea | Runtime model | Practical program types |
|---|---|---|---|
| Brainfuck | Eight commands over a memory tape | Interpreter, compiler, JIT, hardware implementations exist | Hello World, cat, truth machine, quines, simple algorithms, self-interpreters |
| Befunge | 2D instruction grid with moving program counter | Interpreter; reference distribution also includes Befunge-to-C compiler | Stack programs, loops, I/O demos, self-modifying grid programs, games/puzzles |
| Piet | Source code is an image/painting; colors encode operations | Image parser + stack VM interpreter; community compilers exist | Visual Hello World, image programs, stack algorithms, art-code pieces |
| Whitespace | Only space/tab/linefeed are syntax | Tokenizer over whitespace + stack/heap/flow interpreter | Invisible programs, cat, Hello World, truth machines |
| Shakespeare | Programs look like Shakespeare plays | Python interpreter; reference and third-party SPL-to-C compilers exist | Text output, stack/state demos, verbose puzzle programs |
| Chef | Programs look like cooking recipes | Recipe parser + stack/value interpreter | Recipe-looking output programs, number/string demos |
| INTERCAL | Parody compiler language designed unlike existing languages | Compiler/interpreter dialects; originally compiler-oriented | Numeric I/O, deliberately painful algorithms, historical language art |
| LOLCODE | Meme-syntax language | C interpreter (`lci`) with lexer/parser/runtime | Hello World, simple scripting, stdlib demos |

## How they compile or run

### Interpreter-first languages

Most esolangs are easiest to implement as interpreters:

```text
source
  -> tokenizer/parser
  -> small VM state
  -> execute instruction by instruction
```

Examples:

- Brainfuck VM state: instruction pointer, memory pointer, byte/integer tape, bracket jump table.
- Befunge VM state: 80x25 toroidal grid, 2D program counter, direction vector, stack.
- Piet VM state: image color blocks, direction pointer, codel chooser, stack.
- Whitespace VM state: instruction tokens from spaces/tabs/newlines, stack, heap, labels.
- Shakespeare VM state: characters as variables/stacks, acts/scenes as labels, stage presence, dialogue instructions.

### Transpilers

Some conlangs are compiled by translating them into a mainstream host language:

```text
SPL / Befunge / Brainfuck
  -> C / JS / Python
  -> host compiler/runtime
```

This is often the easiest route for SCBE-style language experiments: write a clean parser and lower into a deterministic IR, then emit Python/TypeScript/Rust.

### Optimizing compilers

Even very small languages can be optimized:

- Collapse repeated operations like `+++++` or `>>>>`.
- Precompute bracket jumps.
- Convert simple loops to arithmetic.
- Emit C, LLVM IR, WebAssembly, or bytecode.

This works best for 1D linear languages such as Brainfuck. It is much harder for 2D/self-modifying languages like Befunge.

### Why some are hard to compile

Befunge was explicitly built around a program counter that can move in four directions across a two-dimensional torus and read/write its own playfield. That breaks many normal compiler assumptions:

- no simple linear control flow
- self-modifying source grid
- direction changes instead of structured blocks
- random direction operator

Compilers still exist, but interpreter-first design is more natural.

## What matters for SCBE

If SCBE makes or trains around code conlangs, the best architecture is:

```text
human-readable conlang source
  -> parser
  -> explicit AST
  -> small typed IR / action packet
  -> verifier
  -> host code or bounded tool action
```

Do not jump straight to "invented syntax runs real tools." Keep the lanes separated:

- syntax lane: what the human writes
- semantics lane: what the program means
- runtime lane: interpreter/transpiler behavior
- safety lane: verifier/gates/receipts
- host lane: Python/TypeScript/Rust/shell/browser target

## Training implications

Code conlangs are useful for model training/evaluation because they are out-of-distribution. A 2026 arXiv benchmark argues that esolangs expose reasoning gaps hidden by mainstream Python/MBPP-style benchmarks.

Use them in two ways:

1. Evaluation: test whether a model can learn a new instruction set from docs and interpreter feedback.
2. Product design: teach the model to emit structured action packets rather than arbitrary prose.

For browser-use and SCBE agent work, do not train only on synthetic examples. Add human-written, open-source, license-compatible language docs and tutorials when possible.

Candidate human-authored sources to consider later, after license review:

- Befunge-93 reference distribution/spec
- Shakespeare language docs
- LOLCODE specification/interpreter docs
- original/manual-style docs for Chef, Piet, INTERCAL, Whitespace, Brainfuck
- interpreter README files with permissive licenses

## Takeaway

The lesson is not that SCBE needs a gimmick language. The useful pattern is:

```text
weird human language
  -> tiny formal VM
  -> strict compiler/interpreter
  -> verifier
  -> real host action
```

That is exactly the shape needed for a safe AetherDesk browser/agent language.

## Example: Coding Conlang for Space Docking / Permeable Door (Manaan-style)

Using the SCBE conlang system (from conlang_macros.py + shorthand.py) to "code" a verified command for the liquid plug door transit.

Example sentence (from the binding):
kor-vael av-sai ru-thar bip'a draum-sel

Resolves to verified CA opcode (add), executed only on verified faces (py+rust), with paraphrase and seal.

In the space sim (scbe_manaan_docking.py), this sentence is "spoken" with physics args (speed, film) to get a verified result, used to adjust the physical film loss with honesty firewall (only narrow executed count).

See the integration in src/scbe_manaan_docking.py for full example with door-specific verified macro "film" registered via shorthand, admitted only if tests pass.

This demonstrates the conlang for real host action (computing film for the permeable membrane) with full provenance (claim manifest) and runtime verification.
