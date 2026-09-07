# Coding Primitives Wheel: executable contract and evidence map

Status: **bounded typed executor implemented; abstract universality only**

The useful part of the wheel is a compact intermediate representation (IR). A
model or conlang can express a program with five syntax roles:

| Role     | Meaning                                        | Typed form                                                            |
| -------- | ---------------------------------------------- | --------------------------------------------------------------------- |
| DATA     | construct, read, compare, or transform a value | integer/boolean literals, reads, `+`, `-`, `*`, modulo, `>`, equality |
| BIND     | name a value for lexical reuse                 | `let name = value; body`                                              |
| BRANCH   | select exactly one continuation                | `if condition then a else b`                                          |
| LOOP     | repeat a body with an accumulator and index    | bounded fold                                                          |
| SEQUENCE | compose expressions in order                   | `a ; b`                                                               |

`packages/agent-bus/src/coding-primitives-wheel.ts` implements these roles. It
uses an unambiguous prefix token stream, safe-integer arithmetic, strict boolean
conditions, lexical scope, lazy branches, and explicit limits for node
evaluations, loop iterations, bindings, recursion depth, and trace events.

Every run emits a deterministic receipt containing:

- hashes of the typed program, prefix token stream, inputs, and completed trace;
- the exact limits used by the run;
- result or typed rejection;
- per-primitive counts, branch directions, loop iterations, maximum depth, and
  peak binding count;
- the label `finite-bounded-interpreter` and the universality boundary
  `abstract-unbounded-machine-only`.

A receipt can become a public Agent Bus reasoning artifact. The canonical
receipt summary is then rendered through any of the six reversible tongue
views. Public hashes prove byte consistency, not execution authenticity. A
successful receipt can become `allow` only after the reference interpreter
reproduces it from the original inputs and limits. A successful receipt without
that authority and every rejected execution default to `quarantine`. Geometry
and feature similarity remain telemetry and cannot authorize a merge.

## Teaching integrity

The relational lesson is useful: **How would the person who trusted me feel if
they later saw the complete record?** It gives a model a concrete way to imagine
the consequence of hiding uncertainty, changing evidence, or claiming work it
did not perform. Training examples should consistently prefer an honest,
well-documented failure over an unverified success.

That lesson becomes reliable only when the harness makes integrity observable:

- preserve sources and the exact inputs used;
- label measured, inferred, and imagined statements separately;
- never alter evidence to fit a desired answer;
- expose uncertainty and failed checks in the artifact policy;
- reproduce deterministic work or require an independent signature before
  granting `allow`;
- retain the rejected attempt so another agent can diagnose and improve it.

Empathy is a decision signal. Re-execution, signatures, isolation, and external
policy checks are enforcement. A SHA-256 checksum is useful for detecting a
changed byte sequence, but anyone who fabricates a new sequence can calculate a
new checksum. The checksum therefore belongs below execution authority in the
trust ladder.

## What was already present

The original wheel graphic is stale. BRANCH and LOOP were committed in Loom on
2026-07-18; they are no longer free nodes.

| Surface                        |                                                                                       Current rerun | Evidence boundary                                          |
| ------------------------------ | --------------------------------------------------------------------------------------------------: | ---------------------------------------------------------- |
| `branch_loop_route.py`         | 11/11 emitted Python tasks pass; independent interpreter agrees 11/11; 11/11 sample ASTs round-trip | Small deterministic task set, one executable target        |
| `wheel_lane_matrix.py`         |                                                                        12/24 cells execute and pass | Python, JavaScript, and Rust only                          |
| math and Markdown lanes        |                                                                              8/24 structural checks | Renderings, not executable targets                         |
| Haskell lane                   |                                                                                 4/24 `NO-TOOLCHAIN` | No local `runghc`; unresolved rather than failed           |
| `wafer_neural_math_machine.py` |                                                                              4/4 focused tests pass | Bounded fixed interpreter; not a learned capability result |

The first script is committed at Loom commit
`4610f0502134cd1466cbd1b149c3276db19ea8d8`; the six-lane evidence matrix is
committed at `ddd79822d35113027b4b03d7c9a618d0052387b0`. The reruns above were made
on 2026-09-06 without editing the dirty Loom worktree.

The new codec strengthens the old prefix representation in two ways. Names are
tagged and UTF-8/base64url encoded, so a variable called `branch` cannot be
confused with the BRANCH opcode. Parsing must consume the entire stream, so a
valid program followed by hidden trailing tokens is rejected.

## What “giving the model words” can do

Names such as DATA, BIND, BRANCH, and LOOP give training examples and agents a
shared compositional grammar. That can improve description length, reuse,
transfer between languages, error localization, and auditability. It may also
create a useful inductive bias: examples that look different in Python, Rust,
or a conlang can map to one typed operation graph.

The names do not add information or raw model capacity by themselves. The
capability claim begins only when a model produces correct held-out programs
more reliably than equal-budget controls. Canonical bytes and the typed IR are
the source of truth; tongue, trit, phi, disk, sheet, and genre views are
reversible or annotated projections around that source.

“Genres of science” can be made concrete as domain ontologies over the same IR:
each domain supplies types, legal transformations, invariants, and evidence
rules. Lore, history, hypothesis, and measured fact should remain separate
provenance classes. A story can propose a program or experiment; it cannot
upgrade itself into evidence.

## Numerical claims checked

The implementation recomputes the following rather than copying display text:

| Claim                                           |                                                                   Result | Meaning                                              |
| ----------------------------------------------- | -----------------------------------------------------------------------: | ---------------------------------------------------- |
| Six balanced trits                              |                                                       `3^6 = 729` states | exact combinatorics                                  |
| Sum bands                                       |                                                       `-6..+6`, 13 bands | exact combinatorics                                  |
| Balanced states                                 |                                             141/729 = 0.1934156378600823 | coefficient of the zero-sum band                     |
| Binary balance at width six                     |                                                                 possible | three `-1` and three `+1`                            |
| Neutral trit at odd width                       |                                               enables exact zero balance | binary `±1` cannot sum to zero at odd width          |
| 64-cell Poincare/hyperboloid distance agreement | maximum absolute residual `9.103828801926284e-15` across all 2,016 pairs | floating-point coordinate-model consistency          |
| Hyperboloid constraint residual                 |                                                  `4.547473508864641e-13` | floating-point consistency with `-x0^2+x1^2+x2^2=-1` |
| Radius change under one rotation                |                                                  `2.220446049250313e-16` | rotation preserves realm radius to machine precision |

The earlier artifact reported `3.997e-15` for a selected disk/sheet check. The
all-pairs implementation here gives `9.104e-15`; both are machine-precision
residuals, but they are different measurements and should not be substituted
for one another.

The quoted `4.4177` outer-band cost and `1.020` four-wafer nest cost remain
provenance from the j-space artifact. `realm_router.py` repeats those values but
does not regenerate that exact comparison, so this change does not certify
them. Even a certified distance saving would establish a layout property, not
a reasoning-quality gain.

## Universality boundary

A fixed 64-cell wafer with fixed-width values and finite fuel is a finite-state
system. It cannot literally provide an unbounded Turing tape. The instruction
model can still be called Turing-complete when its memory and runtime are
treated as unbounded abstractions, as with the repository's Brainfuck-class bit
spine or two-register Minsky machine.

Production runs should say which statement they mean:

- **abstract instruction-set universality**: a mathematical property under
  unbounded memory and time;
- **bounded execution**: the real run, with finite cells, integers, fuel, and a
  receipt;
- **learned competence**: measured model performance on held-out tasks;
- **representation benefit**: lift over both a size-matched control and the
  no-intervention baseline across multiple seeds.

## Compiler path

The safe route from a custom conlang to other languages is:

1. Parse the conlang into this typed, language-neutral IR.
2. Serialize and parse it back exactly before execution.
3. Run the bounded reference interpreter and retain its receipt.
4. Emit Python, JavaScript, Rust, Haskell, or another target from the same IR.
5. Compile/run the target in an owned process with its own time, memory, and
   output limits.
6. Compare typed outputs and side effects to the reference interpreter.
7. Issue an executable-equivalence receipt only when they agree.
8. Let the Agent Bus merge branches only through exact canonical identity or
   that external equivalence receipt.

The next evidence step is randomized differential testing across the three
currently runnable emitters, followed by a remote or CI Haskell lane so a large
local GHC installation is unnecessary. Model experiments should compare the
typed vocabulary against shuffled labels and an equal-token plain syntax over
at least three seeds. Phi weights and hyperbolic routing should be tested as
separate interventions; otherwise a compiler success can be mistaken for a
geometry result.

## Validation status

On 2026-09-06, the Agent Bus suite passed 734/734 tests and TypeScript type
checking passed. A frozen Codex Security diff review
(`6d888e6a-e4a7-4a30-b619-c39a5ec1df78`) found one low-severity receipt
authenticity flaw (`csf_79c8a62d6d81af03aff15944`): a caller could recompute
public checksums around a fabricated result and obtain an `allow` artifact. The
bridge now requires exact deterministic re-execution for `allow`. Regression
tests prove that the original self-consistent forgery is rejected, an
unreproduced success remains quarantined, and a legitimate reproduced success
still works.
