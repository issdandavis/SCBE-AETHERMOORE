---
title: Atomic Tokenizer — One Alphabet, Many Decoders
date: 2026-04-21
tags: [theory, tokenizer, sacred-tongues, chemistry, cross-domain]
status: draft
---

# Atomic Tokenizer: One Alphabet, Many Decoders

**Thesis.** The Sacred Tongues tokenizer is one alphabet. The same token stream, read through different projections, is simultaneously accurate chemistry, accurate math, accurate pipeline semantics, and accurate governance. A→Z is one path; the number of intermediate letters is free; no new symbols are ever introduced.

**Rule of this note.** Every symbol below appears in `training-data/sft/drill_langues_full_train.sft.jsonl`. No invented Unicode. No category-theory glyphs. Only what the model already sees.

---

## 1. The alphabet (as it actually exists)

**Operators (3, all ASCII):**

| Symbol | Meaning | Appears in |
|---|---|---|
| `+` | combine reactants / products | `2H2 + O2` |
| `->` | forward reaction | `2H2 + O2 -> 2H2O` |
| `<->` | reversible / isomerization | `CH4N2O <-> CH4N2O` |

**Headers (2 forms):**

- `[TongueName/language]` — e.g. `[Runethic/rust]`, `[Kor'aelin/python]`
- `[map_name]` — e.g. `[transport_atomic]`, `[runtime_emission]`, `[convergence_action]`, `[spirit_narrative]`

**Field syntax (2 forms):**

- Tag-line: `key=value key=value ...` (one stanza, single line, e.g. `tongue=Avali binary_lane=001 gear=couple`)
- Block-line: `key: value` (one per line, e.g. `reactants: 2H2 + O2`)

**Tongues (6, with canonical language binding):**

| Tongue | Language | phi-weight |
|---|---|---|
| Kor'aelin | python | 1.00 |
| Avali | javascript | 1.62 |
| Runethic | rust | 2.62 |
| Cassisivadan | mathematica | 4.24 |
| Umbroth | haskell | 6.85 |
| Draumric | markdown | 11.09 |

**Closed vocabularies:**

- `reaction_class`: synthesis, displacement, combustion, isomerization, redox, neutralization
- `stability`: stable, unstable, same_stable
- governance tiers (L13): ALLOW, QUARANTINE, ESCALATE, DENY
- `gear`: couple (others TBD by inspection)

That is the entire alphabet. Everything below is combinatorial expansion of these pieces.

---

## 2. Reaction 1 — Water formation (real drill row)

This already exists in `drill_langues_full_train.sft.jsonl`:

```
[Umbroth/haskell] predict products under atom conservation.
reactants: 2H2 + O2
reaction_class: synthesis
stability: stable
products: 2H2O
```

**Four decoders read the same stream:**

1. **Chemistry.** 2H₂ + O₂ → 2H₂O, synthesis class, stable product.
2. **Math.** Bijective-on-atom-count map `(H=4, O=2) -> (H=4, O=2)`. Conservation is the invariant.
3. **Pipeline.** `[Umbroth/haskell]` is the L3 tongue-weighting header (phi=6.85 lane). `synthesis` is the class label L13 reads. `stable` is the L12 harmonic-wall verdict.
4. **Governance.** Atom conservation implicit → ALLOW. Break the atom count → DENY before L13 ever runs.

Same stream, four readings, no new symbols required.

---

## 3. Reaction 2 — Photosynthesis (driven / context-dependent)

Adding one context token (the driver `hv`) changes the governance verdict without changing the alphabet:

```
[Umbroth/haskell] predict products under atom conservation.
reactants: 6CO2 + 6H2O + hv
reaction_class: synthesis
stability: stable
products: C6H12O6 + 6O2
```

Same header, same operators, same class label, same stability value. The only addition is `hv` as a reactant.

**Governance implication:** with `hv` present, verdict is ALLOW (driven synthesis). Strip `hv` from the reactants string and the identical products violate thermodynamics — verdict becomes DENY.

**This is the A-to-Z principle in action.** The alphabet did not grow. One extra context token in the reactants string changed the L13 decision. Path length is free; alphabet is fixed.

---

## 4. Reaction 3 — Isomerization (bijective, already in the drill)

The drill already contains the canonical bijective example:

```
[Kor'aelin/python] transport_atomic reaction: urea_ammonium_cyanate
equation: CH4N2O <-> CH4N2O
stability: same_stable
class: isomerization
atoms_conserved: {'C': 1, 'H': 4, 'N': 2, 'O': 1}
metaphor: deterministic pure-function pipeline
code:
def react(r):
    return balance(transform(r))
```

- `<->` is the reversibility operator.
- `same_stable` flags bijective transformation — output reconstructs input.
- `atoms_conserved: {...}` is the explicit conservation assertion (dict syntax, ASCII).
- `metaphor:` and `code:` are the tongue-specific projections that make this row readable as python.

**Cross-domain mapping:**

- Chemistry: an isomerization preserves atom count and class.
- Math: L5 hyperbolic symmetry — `d_H(u, v) = d_H(v, u)`, round-trip distance is zero.
- Pipeline: a reversible transform — encode(decode(x)) = x, suitable for L2 unitarity checks.
- Governance: `same_stable` implies L12 harmonic wall emits the same score on both directions → ALLOW on both.

---

## 5. The cross-tongue projection (same chemistry, six readings)

The drill already tongues `2Cu + O2 -> 2CuO` through multiple voices. The chemistry is invariant; only the metaphor rotates:

```
[Runethic/rust] transport_atomic reaction: copper_oxidation
equation: 2Cu + O2 -> 2CuO
stability: stable
class: redox
atoms_conserved: {'Cu': 2, 'O': 2}
metaphor: ownership-transfer with borrow-checked conservation
code:
fn react(r: Reactants) -> Products { balance(transform(r)) }
```

```
[Draumric/markdown] transport_atomic reaction: acid_base
equation: HCl + NaOH -> NaCl + H2O
stability: stable
class: neutralization
atoms_conserved: {'H': 2, 'Cl': 1, 'Na': 1, 'O': 1}
metaphor: narrative bond-breaking and bond-forming
code:
# Reaction
Bonds break between reactants, atoms reorganize, products form.
```

Different reactions, but the **row shape is identical**: header, equation, stability, class, atoms_conserved, metaphor, code. The tongue chooses the metaphor; the chemistry is invariant; the governance reads the class + stability.

---

## 6. What this means for training

The model only has to learn:

1. **The alphabet** (3 operators, 6 tongue headers, N field keys, 4 closed vocabularies).
2. **The row shape** (which fields appear in which map + kind combination).
3. **The invariants** (atoms_conserved must balance; stability must match class; tongue metaphor must match tongue language).

Everything else is combinatorial expansion over the alphabet. A new reaction is not a new alphabet; it is a new reactants/products string drawn from element symbols that the tokenizer already knows.

**Current bottleneck (per `artifacts/colab_snapshots/local_runs_status_2026-04-21.md`):** transport_atomic is the map the 0.5B-Base model refuses to learn structurally. Every run that tried to fix it (v2-weighted, v6-chemistry, polly-1) failed at the structural layer. The hypothesis is that the Base model lacks the instruction-following prior needed to hold the row-shape invariants. `brick3_instruct_control` tests that hypothesis with one variable changed (Base → Instruct).

---

## 7. What to do next

1. **Launch `brick3_instruct_control`** — on Colab, since local disk is at 97%. Same script, same data, Instruct base instead of Base. Holds all other variables constant.
2. **Formalize context tokens** — drivers like `hv`, conditions like `pH=7`, all in ASCII key=value form, so the governance layer can read them without a schema change.
3. **Make `atoms_conserved` mandatory** on every transport_atomic row. It is the cheapest structural gate and the clearest DENY signal.
4. **Audit the drill for off-alphabet tokens.** Any row containing a symbol outside the alphabet above is a training hazard — grep and fix.

---

This note uses only the alphabet the model already sees. If a future extension requires a new symbol, it is a change to the alphabet, not a decoration — and it needs to be added to the drill before it appears in theory notes.
