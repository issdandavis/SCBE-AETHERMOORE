# Chemical-Semantic Decomposition Bridge

Generated: 2026-05-31

## Purpose

SCBE should support two connected decomposition lanes:

1. **Real chemical decomposition**: atoms, isotopes, ions, electron states, bonds, orbitals, partial charges, spectra, reaction coordinates, and compound graphs.
2. **Semantic/code decomposition**: tokenizer atoms, code operations, command roles, parse/compare/release/merge/transform actions, permission states, and execution receipts.

The bridge only draws a semantic line between them when the relation is backed by a shared operation, measurable proxy, or explicitly declared analogy. This keeps the model useful without pretending symbolic atoms are the same thing as physical atoms.

## Chemical State Ladder

Real chemistry needs a more exact ladder than "add particles and the shape changes":

| Change | Chemical Meaning | Bridge Meaning |
| --- | --- | --- |
| Add/remove protons | Changes the element and nuclear charge. | Identity-class shift; the object becomes a different semantic kind. |
| Add/remove neutrons | Changes isotope and mass/stability without changing element identity. | Same semantic class with altered weight, durability, or provenance. |
| Add/remove electrons | Changes ionization state, charge distribution, bonding behavior. | Permission/activation shift; same object can interact differently. |
| Change electron configuration | Changes orbital occupation, reactivity, spectra. | Operation-mode shift; same token enters a different execution state. |
| Form/break bonds | Changes compound graph and emergent properties. | Composition/relationship change; joined tokens produce a new system behavior. |
| Change geometry/conformation | Changes spatial arrangement and binding/interaction. | Context-layout shift; same parts behave differently under new orientation. |
| Move along reaction coordinate | Continuous path between reactants, transition states, products. | Workflow path; intent becomes staged execution through reversible/irreversible steps. |

## Semantic Operation Correspondences

These mappings are not identity claims. They are operational correspondences used for analysis, teaching, and routing.

| Code / Tokenizer Operation | Chemical Analogue | Why It Maps |
| --- | --- | --- |
| `parse` | molecular decomposition / structure perception | Break a whole into typed parts and relations. |
| `compare` | similarity, fingerprint, spectral matching | Measure difference across a feature basis. |
| `release` | dissociation, emission, product release | A bound unit exits a system boundary. |
| `bind` / `merge` | bond formation / complex formation | Parts become a coupled object with new behavior. |
| `authorize` | ionization / activation threshold | State changes permit new interactions. |
| `deny` / `quarantine` | inhibitor / containment | Prevents unsafe interaction with the main system. |
| `compile` | reaction pathway realization | Abstract plan becomes executable state changes. |
| `rollback` | reverse reaction / repair pathway | Restore a prior lower-risk state if reversible. |
| `route` | reaction network / transport path | Choose a path through constraints and costs. |
| `hash` / `seal` | spectroscopy / fingerprint | Compact evidence that can be compared later. |

## Color and Spectral Analogy

Color is a good teaching example because it shows how one apparent thing can decompose into hidden components.

- A visible color can be represented as RGB, but RGB is only a display approximation.
- A material color is better represented by a reflectance spectrum across wavelengths.
- Chemical identity can show up through spectra: IR, UV-Vis, Raman, mass spectra, NMR, X-ray diffraction.
- A semantic token can similarly be represented as a visible word, a tokenizer ID, a STISTA atom, a code role, a risk state, and a provenance hash.

The SCBE bridge should prefer the deeper spectrum when available:

```text
visible label -> feature vector -> spectrum/descriptor -> relation graph -> receipt
```

## Multi-Lattice Comparative Fields

For compound research, represent each candidate in several fields:

| Field | Real Chemistry Source | SCBE Use |
| --- | --- | --- |
| Identity lattice | name, CID, InChIKey, canonical SMILES | Deduplicate and prevent name confusion. |
| Graph lattice | atoms, bonds, rings, functional groups | Compare structure and substructures. |
| Descriptor lattice | MW, LogP, TPSA, HBD/HBA, rotatable bonds | Filter drug-likeness and physical properties. |
| Electron field | partial charges, HOMO/LUMO, density proxy, orbital occupancy | Approximate reactivity and interaction regions. |
| Spectral field | IR/UV/Raman/MS/NMR/XRD data when available | Evidence fingerprint and material/compound matching. |
| Literature field | PubChem, ChEMBL, BindingDB, papers, patents | Separate known evidence from hypothesis. |
| Governance field | risk class, allowed operation, private/public proof | Keep unsafe or unverified actions out of execution. |

## Rule for Drawing a Semantic Line

Draw a semantic line only when at least one is true:

1. **Shared operation**: both systems perform the same abstract operation, such as parse, bind, release, compare, route, or transform.
2. **Measurable proxy**: a real descriptor or spectrum supports the comparison.
3. **Declared analogy**: the mapping is useful for teaching or routing but explicitly marked as symbolic.
4. **Executable receipt**: the relation came from a tool run with input hash, output hash, version, and claim boundary.

Do not draw a semantic line when it is only wordplay, visual resemblance, or a desired result without evidence.

## CLI Direction

The middle layer should eventually expose:

```bash
scbe chem atomize "release payload after compare"
scbe chem decompose --smiles "CCO" --fields graph,descriptor,electron-proxy
scbe chem compare --left caffeine --right theobromine --fields graph,descriptor,literature
scbe chem spectrum --input sample.ir --kind ir --json
scbe chem map-semantics --operation release --chemical-analogue dissociation --json
scbe chem prove --public
```

Each command should emit:

- normalized input,
- selected fields,
- tool/engine used,
- output hashes,
- semantic lines drawn,
- lines rejected,
- safety decision,
- claim boundary.

## Claim Boundary

This bridge supports governed computational chemistry research and semantic modeling. It does not prove biological efficacy, replace wet-lab validation, provide dosing advice, or produce synthesis instructions.

