# Intermodel Binary/Token Ledger v1

Status: deterministic bridge, exact EOT lattice, bounded action-mask compiler, and measured quine-wafer tree growth implemented; learned benefit and external execution authority absent
Date: 2026-11-12

## Result

The repository already had the binary and token families. This bridge does not
replace them. It makes their common identity explicit and adds the missing
model-to-model join.

The canonical object is an exact source-byte occurrence:

```text
ByteDeed = (source_sha256, byte_offset, byte_value)
```

Bit, balanced-trit, Six Tongues, CA opcode, wafer address, lexical token, BPE
token, and model token are typed views of that deed. Deterministic views remain
one observation; they do not multiply Shannon capacity.

## Reused authorities

| Existing surface | Reused responsibility |
|---|---|
| `python/scbe/bit_spine.py` | exact byte ↔ bit ↔ six balanced-trit conversion |
| `src/crypto/sacred_tongues.py` | six bijective 256-token byte views |
| `python/scbe/ca_opcode_table.py` | fixed 64-cell CA opcode catalog |
| `python/scbe/semantic_opcode_vm.py` | sparse exact byte-opcode contracts |
| `python/scbe/prime_token_catalog.py` | source spans, byte identity, and pinned BPE views |
| `python/scbe/cross_vector_token_analysis.py` | exact UTF-8 token spans and typed vector analysis |
| `src/tokenizer/code_weight_packets.py` | code lexical stream and language-neutral operation signature |
| `src/tokenizer/semantic_code_bridge.py` | operation-path → semantic-atom mapping |
| `python/scbe/cross_token_language_grid.py` | action-byte → bit/trit/tongue/radial join |
| `python/scbe/algebraic_radial_token_table.py` | seeded radial cells and bounded sector mechanics |
| `C:/dev/training-research/virtual_lithography.py` | bounded mask -> exposure -> resist -> endpoint teaching benchmark; not an action compiler |
| `C:/dev/training-research/lithography_cross_system.py` | Poisson/relaxation/STISTA teaching surfaces; not execution authority |

## New bridge

`python/scbe/intermodel_token_ledger.py` and
`python/scbe/token_honeycomb_nest.py` add eleven bounded receipts:

1. `scbe.binary-token-atlas.v2` stores each unique byte type once, then records
   source-position deeds. It exposes the existing bit, trit, six-tongue, opcode,
   and wafer views and verifies every inverse.
2. `scbe.model-token-span-trace.v1` binds a model/tokenizer ID to exact UTF-8
   byte spans and a tokenizer fingerprint.
3. `scbe.intermodel-token-seam-ledger.v1` partitions one source at every model
   boundary. A long BPE token, a byte token, and a code token can therefore meet
   on common minimal byte seams without pretending their token IDs are equal.
4. `scbe.code-token-intermodel-ledger.v1` joins different source languages only
   when their existing operation signatures match. Every operation cell points
   back to the exact source token bytes for each model/language.
5. `scbe.typed-token-honeycomb-nest.v1` derives an 18-coordinate weight carrier
   from exact bytes, places tokens into radial cells, and gives every occupant a
   unique honeycomb sub-address. Same-type comparisons look backward through a
   bounded candidate window rather than allocating an all-pairs table.
6. `scbe.b256-token-honeycomb-nest.v1` validates a frozen B256 vocabulary hash,
   rejects duplicate byte strings, and places the complete table into the same
   nest without using token spelling to choose geometry.
7. `scbe.token-layer-geometry-21d.v1` derives fourteen geometric layer-address
   points lazily from one token seed. It is telemetry, not execution of the
   named 14-layer pipeline.
8. `scbe.interwoven-eot-token-lattice.v1` adds an explicit symbol 256 as an
   End-of-Token wall, preserves the teacher distribution pushed forward onto
   decoded byte strings as sparse byte-path conditionals, and lets multiple
   token tables share prefix geometry without averaging their measures.
9. `scbe.quine-wafer-token-tree-growth.v2` invokes the existing
   `clay-wafer-net` state and variable-injection quine APIs, reprints the same
   byte-exact token topology through bounded depth/face/micro-rotation views,
   and counts distinct view, weight-field, and combined-tree receipts.
10. `scbe.token-action-lithography.v1` binds exact lattice token identities to
    explicitly declared semantic VM contracts, assembles the mask to bytes,
    disassembles it for exact comparison, and optionally executes only inside
    the existing bounded semantic-opcode VM.
11. `scbe.hex-trit-cross-router.v1` gives each byte one binary/decimal/hex
    identity plus six reversible A--F route views arranged as three 16x16 trit
    sheets with two optional dual-trit lanes per sheet.

## Dependency graph

```text
                         exact source bytes
                                  |
                 +----------------+----------------+
                 |                                 |
                 v                                 v
       unique B256 type table             source-position deeds
 bit / trit / six tongues / opcode                 |
                 |                                 |
                 +----------------+----------------+
                                  |
                                  v
                    model token span traces
              byte / tongue / BPE / lexical / custom
                    |                           |
                    v                           v
       minimal exact byte seams       typed weighted token nest
                    |                 prefix tree + radial cell
                    |                 + honeycomb sub-address
                    +-------------+-------------+
                                  |
                                  v
                    same-source intermodel match
                                  |
                                  v
                       code operation signature
                                  |
                                  v
                    cross-language action cells
                                  |
                                  v
                   deterministic compiler proposal only

       token-teacher distributions (kept independent by table)
                                  |
                                  v
           shared byte-prefix interiors + explicit EOT walls
                                  |
                                  v
          bounded composed-path race / cross-table convergence
                                  |
                                  v
         existing 6D quine wafer / micro-rotation tree reprints
                                  |
                                  v
            collision and exact-reconstruction capacity ledger

       exact lattice token path + explicit action declaration
                                  |
                                  v
              token-action mask / closed VM contract lookup
                                  |
                                  v
            assemble -> disassemble equality -> bounded toy VM
```

## The two historical 18s

Two older structures both use the number 18 and must not be conflated:

- The relational root field has 18 channels: 12 non-Tongue STISTA views plus
  six independently retained Tongue views.
- The code support axis has 18 language faces: C, C++, C#, Go, Haskell, Java,
  JavaScript, Julia, Kotlin, Lua, PHP, Python, Ruby, Rust, Scala, Swift,
  TypeScript, and Zig.

The new token carrier also has 18 numeric coordinates, but for a different and
fully declared reason: eight mean bit channels, six mean balanced-trit
channels, and four sequence coordinates (length, mean byte, first byte, last
byte). It does not silently claim to be either historical 18-axis structure.

## Hex cross-columns and optional trit channels

`python/scbe/hex_trit_cross_router.py` implements the binary/decimal/hex
cross-column layer without duplicating byte identity. A byte `b` is placed at
the ordinary nibble coordinate:

```text
row = b >> 4
column = b & 0x0f
b = (row << 4) | column
```

That is one 16x16 table. Three balanced-trit channels `[-1, 0, +1]` reuse this
same table, and each channel has two reversible offset lanes. The six lanes are
named with hexadecimal roots `A..F`; opposite lane pairs use opposite axial
offsets. Every lane wraps modulo 16 and has an explicit inverse, so exhaustive
testing covers `256 cells x 6 roots = 1,536` round trips. A consumer may choose
one lane, several lanes, or none. The unused routes remain inert.

The route pairs `A/F`, `B/E`, and `C/D` have opposite offsets, so each pair
crosses at an explicit zero plane instead of blending positive and negative
coordinates. Each cell also carries an eight-step golden-phi precision ladder:

```text
radius_k = phi^(-(k + 1)),  k = 0..7
payload_k = the corresponding MSB-first bit of the byte
```

The outer levels can therefore act as coarse signed geometric routing, while
the deepest level remains the exact binary code. The ladder is a nested view of
the same eight bits, not a claim that irrational radii can be represented
exactly in hardware. Successive levels turn by the golden angle globally; a
separate offset derived from the high/low-nibble difference supplies local
orientation. Every point has an antipodal positive/negative strand at the same
depth. This borrows the useful local-versus-global helix idea from DNA as a
routing analogy; it is not a biophysical DNA model.

`quantized_helix_state` makes the settling rule explicit. The selected bit is
mapped to a pole `{-1,+1}`; a quantized weight trit preserves it (`+1`), places
it in the neutral well (`0`), or inverts it (`-1`). The route's trit region
adds the sideways component, while the antipodal point retains the lower
negative-space embedding. This transition changes routing coordinates only;
the byte and its bit plane are never rewritten.

For an actual 256-bit block, `build_256_bit_traversal_stack` treats the 32-byte
payload as 256 ordered sheet descriptors. Each sheet retains its exact byte
index, MSB-first bit index, bit/polarity, shared 16x16 byte-root cell, A--F
route, neighbors, and phi depth. It stores zero duplicate root tables and
reconstructs the original 32 bytes exactly. This is different from the integer
256 (which needs nine binary digits) and from the 256 possible values of one
byte.

The 16x16 root is also a rook graph. Each byte has 30 one-hop neighbors (15 in
its row and 15 in its column), and any nonaligned target is reached in exactly
two hops through either cross-cell. Exhaustive coverage is `256` same-cell,
`7,680` ordered one-hop, and `57,600` ordered two-hop pairs, so the root-graph
diameter is exactly two. The two crossover choices provide a deterministic
starting point for collision avoidance. Tokens nested below a byte root still
require their local honeycomb/trie attachment step; the diameter claim is not
silently extended to the whole 4,096-token vocabulary.

This is typed routing structure, not additional entropy: all six views decode
to the same byte. It also does not turn hexadecimal letters, trit channels, or
wafer addresses into opcodes. Action meaning still requires the explicit ISA
binding and compiler round trip described below.

## Six-deck contextual ledger

A useful operational analogy is six decks containing the same 256 card faces
with six different backs. The A--F roots are those backs: a receiver can choose
a route from the back without changing the byte printed on the face. This is
why the six deterministic views do not count as six independent facts.

Different games at the casino correspond to independent token tables. A shared
byte-prefix node may participate in several games, but every table retains its
own interior mass, EOT wall mass, continuation mass, and history. The system is
therefore counting tokens in two separate senses:

```text
composition ledger = exact identities, consumed routes, remaining path mass
context ledger     = table/game, speaker, timing, affect, intent, prior turns
```

The first is deterministic accounting. The second can change the conditional
distribution used for the next race, but only when those contextual values are
observed, declared, or learned. Conversation and emotional ebb-and-flow may
reweight a table; they cannot rewrite byte identity, erase provenance, or grant
compiler authority. The current implementation proves the composition ledger
and independent table measures. It does not yet claim a learned affective or
long-horizon conversation state.

## Hardware-to-abstraction connection seams

The connection points are typed boundaries rather than another monolithic
layer:

| Boundary | Existing owner | State |
|---|---|---|
| serialized bits -> exact byte roots | `intermodel_token_ledger.py`, `hex_trit_cross_router.py` | exact software round trip |
| byte roots -> trit/dual-trit sheet views | `hex_trit_cross_router.py` | six reversible views |
| token bytes -> local weighted nodes | `token_honeycomb_nest.py` | bounded deterministic occupancy |
| independent tables -> prefix/EOT paths | `eot_token_lattice.py` | exact pushed-forward measures |
| token nodes -> 14 lazy geometric addresses | `token_layer_geometry.py` | telemetry only |
| exact topology -> wafer reprints | `token_tree_wafer_growth.py` | measured deterministic capacity |
| selected token deeds -> executable bytes | `token_action_lithography.py` | explicit bounded VM authority |
| optical mask -> printed endpoint | `C:/dev/training-research/virtual_lithography.py` | software optics simulation only |

The genuinely missing seam is a multi-stream convergence sieve between the EOT
race and action binding. It should build a conflict graph over incoming paths,
reserve edge-disjoint or explicitly time/phase-multiplexed channels, and land
compatible routes in a bounded annular "cup" around the target region. The cup
defines a local coordinate sub-plane; it does not rewrite the enclosed token.
Any laser, wavelength, or phase realization remains a hardware target until it
is calibrated and measured. In the software architecture this seam is graph
routing with collision receipts, not assumed photonics.

## Weight fill, pressure, residue, and assimilation

The local `token_honeycomb_nest.py` uses a sequential axial spiral to give
colliding occupants unique logical addresses. It is **not** the same profile as
`C:/dev/clay_home/honeycomb_nest.py`, whose physical-scale argument uses
norm-3 Eisenstein nesting, `sqrt(3)` scale steps, and plus/minus 30-degree
rotation. No lithographic scale proof is inherited across that boundary; a
future adapter must name and test the crosswalk.

Each radial cell keeps a deterministic running field. For normalized incoming
carrier `v_t`, previous centroid `c_(t-1)`, and prior occupancy `n`:

```text
insertion residual: r_t = v_t - c_(t-1)
assimilation gain:  a_t = 1 / (n + 1)
new centroid:       c_t = c_(t-1) + a_t r_t
remaining residue: q_t = (1 - a_t) r_t
node pressure:      p_t = log(1 + n + 1)
```

The remaining 18D residual is projected through one declared first-harmonic
18D-to-2D basis. Dot products against the six axial hex directions form the
honeycomb halo; opposite directions are therefore exact sign inverses. The
receipt separately retains (a) cumulative post-insertion residue and (b) the
current Welford residual sum of squares about the final centroid. This is a
transparent running aggregate, not backpropagation or a learned embedding
update.

## Lazy 21D token-layer geometry

`python/scbe/token_layer_geometry.py` gives each occupied token node fourteen
on-demand geometric layer addresses. It does not store fourteen copies of the
token table. It also does **not** pass state through the real L1 -> L14
pipeline: every point is independently regenerated from the same token seed,
and prior points are used only for dH/drift telemetry. The local 18-coordinate
carrier is extended with three typed runtime coordinates:

```text
[0..17]  exact-byte-derived local carrier
[18]     current pipeline layer, scaled from L1..L14 into [-1, +1]
[19]     bounded node pressure, occupancy / (occupancy + 1)
[20]     signed unassimilated-residue ratio
```

Six consecutive carrier triads receive phase-offset breathing factors, so the
motion is lobe-local rather than one global expansion. The resulting vector is
mapped into the existing safe 21D Poincare ball and adjacent layer points are
measured with the existing hyperbolic `dH` metric. Q1e6 decimal drift records
both integer ticks and the sub-tick residue, allowing the approximation to be
reconstructed without treating rounding dust as new information.

This layout is a typed token-routing profile. It is deliberately **not** the
same semantic layout as either the 21D Unified Brain State
(`6 context + 6 navigation + 3 cognitive + 3 semantic + 3 swarm`) or the PHDM
text profile (`6 hyperbolic + 6 phase + 3 flux + 6 audit`). A later adapter may
translate between named profiles; an unnamed positional cast is forbidden.

## Exact EOT walls and interwoven token tables

The implementation follows the exact End-of-Token construction in
[*Breaking the Token Ceiling*](https://arxiv.org/abs/2609.12303). Let `w_i(t)`
be the sum of teacher-token probabilities whose decoded byte sequence is `t`,
let `p` be a byte prefix, and append the non-byte symbol `<eot>` to every
sequence:

```text
interior mass: M_i(p) = sum_t w_i(t) [p is a prefix of t<eot>]
edge mass:     M_i(p,a) = sum_t w_i(t) [pa is a prefix of t<eot>]
edge chance:   P_i(a|p) = M_i(p,a) / M_i(p)
```

The product down a complete byte path telescopes to its decoded-byte
pushforward mass:

```text
product_k P_i(a_k | a_0...a_(k-1)) = M_i(t<eot>) / M_i(empty)
```

If two token IDs decode to the same bytes, the byte path necessarily carries
their aggregate pushforward mass. Each token's individual teacher probability
and typed ID remain in the ledger, but the shared byte path cannot distinguish
the aliases. For an injective decoded vocabulary, path mass and token mass are
the same quantity.

Thus a short token ending at prefix `p` keeps its own probability on the EOT
wall instead of donating it to longer continuations. Prefix nodes are the
interiors, EOT edges are walls, and outgoing byte edges are exterior folds.
Each shared node carries one view per token table, so tables can intersect
without silently blending two teachers.

The immutable root alphabet remains 256 byte cells. Each byte also retains the
existing exact factorization into four orientations of 64 opcode cells:

```text
byte = (orientation << 6) | opcode_cell
```

`<eot>` is symbol 256 and deliberately has no byte/opcode address.

## Composite functions and the bounded path race

The 256-cell table is only the root. `race_interwoven_token_paths` can begin at
the empty root or any existing prefix cell, compose typed `append_byte` and
`close_token` functions one edge at a time, and sieve the candidate set after
every relative step. Trie nodes store parent/incoming-byte links instead of
copying every full prefix, so construction is linear in visited token bytes.
The race keeps three quantities separate:

```text
conditional path mass = product from the selected start cell
absolute teacher byte-path mass = start-prefix mass * conditional path mass
selection telemetry   = score_basis_mass ** probability_power
```

The power score is retained and sorted in the log domain so underflow cannot
silently reorder candidates. It may order or visualize a race, but it never
replaces the exact probability ledger. Beam width, maximum steps, total
expansions, retained completions, edge-probability floor, and cumulative-path
floor are separately bounded. Routes from independent tables converge only
when their exact byte continuations match; their histories and table IDs remain
attached.

The following are architectural correspondences, not hidden dependencies of the
base EOT race:

- `clay_math/growing_quine.py` grows by half-open monotone shells,
  never reassigning a parent address.
- `opcode_compose.py` already represents operations as composable postfix
  functions.
- `C:/dev/loom/clay_covering.py` already distinguishes exhaustive periodic
  coverage from a sampled prefix and refuses to call the latter proof.

Materializing every ordered composition would grow as `256^depth`; this module
therefore derives only reached prefixes and bounded race survivors. A long
autoregressive prediction requires a fresh distribution after each EOT. The
current race covers exactly one next-token distribution and says so in its
receipt.

The measured `token_tree_wafer_growth.py` run **does** invoke the existing
`C:/dev/clay-wafer-net/clay_wafer_net/wafer_6d_quine.py`; test doubles identify
themselves separately and cannot claim that external call. For each generated
tree the real adapter calls `state6` for the 64 local cells under all four byte
orientations and calls `variable_injection_quine` as a replay check. The input
B256 table is revalidated against its declared table SHA-256 first. Exact byte
identity stays fixed, while an ordered composition over every byte in each
token path tilts a copied probability field before rebuilding the EOT lattice.
This is a deterministic growth test, not neural training. The wafer's numeric
`opcode_cell` is a geometry key only; no CA/VM meaning is inferred from it.

## Token lithography and the static action slot

`python/scbe/token_action_lithography.py` now joins the exact EOT token path to
the deterministic compiler path already present in the repository. It reuses
that authority rather than inventing a second VM:

```text
learned weights / token race       proposes typed tokens (no authority)
             |
             v
explicit ActionTokenBinding        names exact table/token/bytes + VM contract
             |
             v
token_action_lithography           replays the live EOT path and its mass
             |
             v
semantic_opcode_vm.assemble        emits bijective opcode/operand bytes
             |
             +---- disassemble ---- exact round-trip mask check
             |
             v
semantic_opcode_vm.run_program     executes only the bounded toy VM

separate selector: ca64-v1 token bytes
             |
             v
tongue_isa.compile_ca_tokens       emits traced Python/TS/Go/Rust/C/Julia/
                                   Haskell/Zig stack-machine source
```

In this analogy, the weight field is the exposure pattern, typed token
selection is the mask, assembly is development, and the verified byte stream is
the etched action slot. Arbitrary lexical bytes are **not** executable merely
because their low six bits name a wafer cell. They become calls only through a
declared mapping into `semantic_opcode_vm.CONTRACTS` or the CA opcode table.
The compiler bridge rejects a token whose table ID, typed token ID, and exact
byte path do not select one live lattice path. It then requires the assembled
bytes to disassemble to the declared instruction sequence before optional toy
VM execution. `src/tokenizer/code_weight_packets.py` supplies exact lexical
spans and language-neutral operation signatures upstream. Geometry may route a
proposal, but the static compiler and governance plane retain execution
authority.

The semantic VM and CA64 compiler are different instruction sets even when a
numeric byte happens to coincide. A caller must select `semantic-vm-v1` or
`ca64-v1` before operand lowering. Existing all-target CA tests prove token
trace/disassembly recovery; they do not yet prove equivalent runtime semantics
for every one of the 64 operations in every target language.

This is separate from the existing physical analogy benchmark under
`C:/dev/training-research`: that code really simulates a bounded binary mask,
coherent six-beam exposure, pupil/defocus, resist response, and printed
endpoint. The action compiler does not call that optics simulator and does not
pretend an analogy is a hardware result.

The retained executable fixture under
`experiments/token_action_lithography_20261112/` binds five live lattice tokens
to `LOAD A 7`, `LOAD B 7`, `COMPARE A B`, `VERIFY`, and `HALT`:

| Action-mask measure | Result |
|---|---:|
| Exact selected token paths | 5 / 5 |
| Compiled/disassembled instructions | 5 / 5 exact |
| Bounded VM steps | 5 |
| VM status / verification | PASS / true |
| Lattice receipt | `a2a0da42576933f42ea835fd6c4af239209b08f2cdd487333d78afb49351ff73` |
| Program SHA-256 | `3cc0b9a6c04bcbbb33a6ab81f87fbbddabeb86bc0dabe8d6c35f66e9a3938bd3` |
| Action-mask receipt | `a0c1800a17066264b5b67ea3cd9e627feaffc2d3743cf0ee9899726819bc1f3b` |

This fixture tests a declared compiler path. It does not show that weights can
learn the declarations, that geometry improves action selection, or that the
toy VM is an operating system.

## Collision result on the frozen 4,096-token table

The pinned table at
`C:/dev/clay_home/tokenizers/clay_open_core_bpe_v1/B256_TOKEN_TABLE.json` was
run through the implementation on 2026-11-12:

| Measure | Result |
|---|---:|
| Frozen table SHA-256 | `fc85ad01480c1d0b72de32645b77538dfc0110cc58461eb9e8f9a50bc2d51009` |
| Tokens | 4,096 |
| Exact byte roots used | 256 |
| Prefix-trie nodes | 7,755 |
| Occupied radial cells | 26 / 64 |
| Tokens sharing an already occupied radial cell | 4,070 |
| Unique honeycomb-address collisions | **0** |
| Exact duplicate byte strings | **0** |
| Bounded prior comparisons | 97,732 |
| Current centroid residual M2 | 1,171.2342807634 |
| One observed construction time | 4.211 seconds |
| Combined receipt SHA-256 | `1170cebc9c53c3c6f225553c72b916c765067138e2ceded979262957a9d8b19e` |

The same frozen table was streamed through the lazy 21D layer geometry:

| Layer-geometry measure | Result |
|---|---:|
| Derived points | 57,344 = 4,096 tokens x 14 layers |
| Stored duplicate layer tables | **0** |
| Maximum Poincare radius | 0.7652762286 |
| Mean dH path per token | 3.1992813501 |
| Maximum adjacent-layer dH | 0.2633073563 |
| Maximum retained Q1e6 decimal residue | 4.99999949e-7 |
| Nested-address collisions | **0** |
| Real L1 -> L14 executions | **0** (address telemetry only) |

These are deterministic routing and telemetry measurements, not evidence of a
learned accuracy gain.

The 4,070 radial collisions are expected quantization occupancy, not lost token
identities. The honeycomb slot makes `(radial cell, axial q, axial r, slot)`
unique while the exact byte path remains the authority. The timing is one local
observation, not a throughput benchmark. The compact machine-readable evidence
is in `TOKEN_HONEYCOMB_B256_RESULT_20261112.json`.

## Quine-wafer token-tree growth capacity

The same 4,096-token B256 table was given a uniform starting measure so the
wafer transform, rather than corpus frequency, was the experimental variable.
One full 64-cell opcode shell was generated using the existing wafer's
`1/sqrt(3)` magnitude and `+30 degree` rotor, alternating signed faces, cycling
the 14 depth addresses, rotating globally by `0.0001 degree` per generation,
and applying an additional `0.00001 degree` local patch offset.

| Growth measure | Result |
|---|---:|
| Requested/built token trees | 64 / 64 |
| Token rows processed across generations | 262,144 |
| Distinct 256-cell wafer views | 64 |
| Distinct probability fields | 64 |
| Distinct combined tree receipts | 64 |
| First repeated receipt | none observed |
| Capacity statement | at least 64 under this bounded run |
| Unique root coordinates per tree | 256 / 256 |
| Coordinate collision groups | 0 in every tree |
| Prefix-trie nodes per tree | 7,755 |
| Maximum EOT reconstruction error | 2.168404344971009e-19 |
| Existing variable-injection quine checks | 64 / 64 passed |
| Growth receipt SHA-256 | `b050b3b1e6657a28d99594b54233b9c3aabaf326a906e27092e4775c6212c402` |

The topology hash remains constant because the token byte strings remain
constant. What grows are reproducible wafer views and probability fields. No
collision in 64 trials is a lower bound, not proof of an infinite or optimal
family. The full receipt is
`TOKEN_TREE_WAFER_GROWTH_B256_RESULT_20261112.json`.

Those deterministic reprints are branch points, not learned descendants. An
experience-bearing twin design should share the immutable parent topology and
then give each lane a lineage ID, context epochs, observations, rewards, and a
copy-on-write delta ledger. Only post-split evidence can establish behavioral
divergence. A later merge must retain both parent receipts and cannot call two
exact copies two independent facts at the moment of reproduction.

## Two wafer profiles, kept separate

Two exact 256-state factorizations already occur in the system. The ledger names
both so a consumer cannot silently transpose them:

```text
cube-face-byte-v1:   cell = byte >> 2; opcode orientation = byte & 3
ca-opcode-region-v1: opcode = byte & 63; region orientation = byte >> 6
```

Both round-trip exactly, but they answer different addressing questions. Their
profile names are part of the receipt.

## What is proven

- Each binary view reconstructs its original byte.
- Each Six Tongues token reconstructs its byte.
- Every model token points to the original byte slice and tokenizer fingerprint.
- Every nested token retains its byte-root path and a unique local address even
  when many weight vectors select the same radial cell.
- Same-family comparison is backward-only and bounded, so it cannot leak future
  tokens or grow into a dense quadratic table.
- Same-source model tokenizations meet on exact minimal seams, including Unicode.
- Python, TypeScript, Rust, and C implementations of the tested add operation
  meet on three operation cells while preserving all source-specific spans.
- Tampered traces and ledgers fail deterministic reconstruction.
- EOT conditional products reconstruct each exact byte-path mass to at most
  `1e-12`, including prefix tokens that would otherwise lose probability.
- Multiple token tables can share prefix cells while retaining separate edge
  masses and exact table provenance.
- Sixty-four measured quine-wafer reprints produce distinct view, weight-field,
  and combined-tree receipts while retaining the same exact B256 topology.

## What is not proven

- Shared byte overlap is not semantic equivalence.
- Equal operation signatures are not full program-equivalence proofs.
- A geometric, radial, or harmonic view does not authorize an action.
- Honeycomb proximity and residual halos are routing measurements, not semantic
  equivalence or proof of a learned gain.
- The bridge has not shown a learned accuracy, throughput, compression, or
  transfer gain.
- The bounded race is one-token search, not a long autoregressive decoder; a
  fresh context-dependent distribution is required after every EOT.
- Sixty-four collision-free deterministic reprints do not prove model quality,
  learned generalization, or unbounded growth capacity.
- Fourteen geometric addresses are not fourteen executed SCBE layers.
- No model weights, serving pointer, compiler authority, or governance policy
  are changed by this ledger.

## Next controlled attachment

Use the seam IDs as immutable token deeds for a small learned restriction layer.
Compare it with byte-only, lexical-only, dense equal-parameter, shuffled-binding,
and no-intervention controls. Preserve exact byte/action correctness, report
coverage and segmentation divergence in addition to accuracy, and require the
existing multi-seed/two-pooled-SD promotion gate.
