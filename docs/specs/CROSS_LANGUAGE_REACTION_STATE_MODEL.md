# Cross-Language Reaction State Model

Generated: 2026-05-31

## Purpose

SCBE maps tokenizer tongues to coding languages and operational roles. That lets a command travel across languages the way a chemical species travels across reaction states:

```text
natural language intent
  -> tongue packet
  -> source language form
  -> transformed language form
  -> recomputed scientific/code checks
  -> bounded output with loss notes and proof receipt
```

The goal is not to claim code is chemistry. The goal is to use chemistry-style accounting for cross-language operations: identity preservation, transformation, loss, recomposition, uncertainty, and validation.

## Tongue-to-Code Layer

Each tongue should carry a stable job across code, chemistry, and agent workflows.

| Tongue | Code-Language Role | Reaction Analogue | What It Preserves |
| --- | --- | --- | --- |
| KO | identity/base syntax | reactant identity | file, function, compound, command identity |
| AV | feature/description layer | observable properties | API shape, descriptors, spectra, visible traits |
| RU | operation/imperative layer | reaction operation | parse, compare, bind, release, compile, route |
| CA | law/constraint layer | conservation and valence rules | types, units, charge balance, tests, safety boundary |
| UM | uncertainty/loss layer | side products, ambiguity, entropy | lossy translation, unknowns, non-bijective steps |
| DR | resolved output layer | product state | recomposed artifact, final code, explanation, proof |

If specific coding languages are assigned to tongues elsewhere in the repo, the CLI should load that registry and attach this role map on top rather than replacing it.

## Reaction State Packet

Every cross-language transformation should emit a reaction packet:

```json
{
  "schema_version": "scbe_cross_language_reaction_state_v1",
  "step": 4,
  "bounded_operation": "translate|compile|decompose|recompose|compare|release",
  "source": {
    "language": "python",
    "tongue": "KO",
    "input_sha256": "..."
  },
  "target": {
    "language": "javascript",
    "tongue": "RU",
    "output_sha256": "..."
  },
  "semantic_engravings": [
    "function identity preserved",
    "snake_case renamed to camelCase"
  ],
  "loss_notes": [
    "comments omitted",
    "type annotations approximated"
  ],
  "recalculation": {
    "syntax_ok": true,
    "tests_ok": true,
    "scientific_checks_ok": null,
    "unit_checks_ok": null
  },
  "classification": "BIJECTIVE|LOSSY_RECOVERABLE|LOSSY_AMBIGUOUS|INVALID"
}
```

## Step Count Matters

Treat each translation or recomposition as a bounded reaction step.

Example:

```text
Step 0: human intent
Step 1: STISTA atomization
Step 2: Python source parse
Step 3: JavaScript translation
Step 4: test recalculation
Step 5: semantic-loss audit
Step 6: proof packet
```

The same applies to chemistry:

```text
Step 0: natural-language compound request
Step 1: compound identity resolution
Step 2: molecular graph load
Step 3: formula/descriptor decomposition
Step 4: atom-mud state
Step 5: recomposition search
Step 6: known-solution verification
Step 7: proof packet
```

Step count prevents hidden transformations. It shows where loss entered the system.

## Loss Engraving

Loss is not always failure. It becomes useful if engraved into the packet.

| Loss Type | Example | Classification |
| --- | --- | --- |
| Naming loss | `is_palindrome` becomes `isPalindrome` | recoverable if call sites update |
| Type loss | Python dynamic value becomes JS untyped value | recoverable with tests/schema |
| Comment loss | comments omitted | usually recoverable if behavior preserved |
| Topology loss | molecule becomes atom bag | ambiguous unless fragments/descriptors remain |
| Stereochemistry loss | chiral molecule loses stereo markers | potentially invalid for chemistry |
| Unit loss | grams/moles omitted | invalid for dimensional analysis |

## Recalculation Layer

After transformation, do not trust the translation. Recalculate it:

- code: parse, lint, typecheck, tests, golden outputs;
- chemistry: canonical SMILES, formula, valence, descriptors, fragment checks, optional quantum/descriptor engines;
- research: source URL, date, contradiction check, confidence;
- agent workflow: receipt hash, replay, resume, safety boundary.

This is where standard analytical/scientific tools enter. SCBE does not need to be the chemistry engine. It needs to call the engine, hash the result, and classify the transform.

## Multi-Language Chemical Composition Analogy

Coding languages are like different atomic families in this model:

- each language has allowed bonds/syntax,
- each has preferred valence/API conventions,
- each loses or gains expressive power in translation,
- each can preserve identity only if enough state cards travel with it.

Cross-language compilation should therefore carry:

```text
identity cards + operation cards + constraint cards + loss cards + proof cards
```

## CLI Direction

Future commands:

```bash
scbe react code --from python --to javascript --input file.py --json
scbe react chem --smiles "CCO" --mud-step 5 --json
scbe react audit --packet reaction.json --json
scbe react compare --left packet-a.json --right packet-b.json --json
```

Existing near-term anchors:

```bash
scbe bench compound-decompose --json
scbe bench chemistry --json
```

## Claim Boundary

This model supports governed cross-language and computational-chemistry transformations with explicit loss accounting. It does not prove biological efficacy, validate wet-lab chemistry, or guarantee semantic identity unless the packet classifies the path as bijective under a declared representation.

