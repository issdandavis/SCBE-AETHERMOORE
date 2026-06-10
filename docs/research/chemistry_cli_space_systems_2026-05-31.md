# Chemistry-Native CLI and Space Chemistry Systems Research

Generated: 2026-05-31

## Executive Takeaway

SCBE should not claim to be the only AI CLI that can touch chemistry. Strong chemistry tools already exist. The defensible claim is narrower and stronger:

> SCBE has a governed chemistry-native CLI lane that combines symbolic chemistry, STISTA atomic-token flow, GeoSeed orbital invariants, private-proof hashes, and future bridges to established scientific chemistry engines.

The moat is not replacing RDKit, Open Babel, ASE, DeepChem, NASA CEA, or PAHdb. The moat is a governed agentic shell that can route them, audit them, preserve receipts, and keep private proof separate from public evidence.

## Existing External Chemistry Tools Worth Bridging

| Tool | What It Is | SCBE Bridge Target |
| --- | --- | --- |
| RDKit | Open-source cheminformatics toolkit with Python/C++ core, descriptors, 2D/3D molecular operations, ML descriptors, and database integration. | `scbe chem rdkit canonicalize`, descriptors, substructure search, fingerprints, molecule validation. |
| Open Babel / `obabel` | Command-line chemistry toolbox for converting, filtering, and manipulating chemical data across many molecular formats. | `scbe chem convert`, format detection, file normalization, pipeline receipts. |
| ASE | Atomic Simulation Environment for setting up, manipulating, running, visualizing, and analyzing atomistic simulations. | `scbe chem atoms`, simulation setup wrappers, calculator receipts, structure export. |
| DeepChem | Open-source Python library for deep learning in drug discovery, materials science, quantum chemistry, and biology. | `scbe chem ml`, dataset featurization, model cards, benchmark routing. |

## NASA / Space Chemistry Systems Worth Bridging

| System | What It Does | SCBE Bridge Target |
| --- | --- | --- |
| NASA CEA / CEA2022 | Chemical Equilibrium with Applications solves equilibrium product concentrations and thermodynamic/transport properties for complex mixtures; used for rocket performance, shocks, detonations, and combustion. | `scbe space-chem cea` wrapper for input decks, output parsing, provenance, and comparison reports. |
| CEARUN | Web/online interface that facilitates use of NASA CEA; CEA remains a gold-standard combustion/rocket thermochemistry code. | Local input-template generator and browser/API adapter where allowed. |
| NASA Ames PAHdb | Database and analysis tools for laboratory and computed PAH infrared spectra used to interpret astronomical observations, including JWST spectra. | `scbe astrochem pahdb` fetch/cache/fit pipeline with source receipts. |
| SAM / Curiosity | Mars rover instrument suite using gas chromatography, mass spectrometry, tunable laser spectroscopy, ovens, and wet chemistry for Martian samples and atmosphere. | Not direct control; use as design pattern for `sample -> instrument -> spectral evidence -> claim boundary`. |
| CheMin / Curiosity | Chemistry and Mineralogy X-ray diffraction instrument for identifying and quantifying minerals in Martian rocks and soils. | Benchmark-style data interpretation lane for mineral/spectral classification, not rover control. |
| Spacecraft Materials Selector | NASA software catalog item for spacecraft material selection expert support. | Future `scbe materials` advisory adapter with export-control and provenance boundaries. |

## Safe Claim Boundary

Current SCBE evidence supports:

- symbolic chemistry and molecule-like scoring,
- STISTA/atomic-tokenizer flow,
- chemical-fusion reconstruction,
- ternary chemistry proxy tests,
- GeoSeed hyperbolic orbital invariants,
- private-proof hash inventory.

Current SCBE evidence does not yet support:

- validated wet-lab synthesis planning,
- validated hazardous chemistry instructions,
- official NASA CEA compatibility,
- official NASA, RDKit, Open Babel, ASE, or DeepChem certification,
- autonomous spacecraft or rover instrument operation.

## Recommended CLI Branches

1. `feat/chem-cli-core`
   - `scbe chem atomize "text"`
   - `scbe chem fuse "tokens"`
   - `scbe chem bonds --coords ...`
   - `scbe chem orbitals --json`
   - `scbe chem prove`

2. `feat/chem-interop-bridges`
   - Detect optional tools: RDKit, Open Babel, ASE, DeepChem.
   - Expose wrappers only when installed.
   - Emit receipts with versions, command, input hash, output hash, and claim boundary.

3. `feat/space-chem-bridges`
   - NASA CEA/CEARUN input deck templates.
   - PAHdb cache/search/fit scaffold.
   - SAM/CheMin-inspired evidence workflow for sample/spectrum/claim reports.

4. `feat/chem-safety-gate`
   - Deny or quarantine hazardous synthesis, energetic material, toxicity, or illegal-drug requests.
   - Allow benign educational, file-conversion, descriptor, and public-data workflows.
   - Put human approval before any wet-lab actionable output.

## Product Framing

SCBE should present chemistry as a command-line evidence room:

```text
Human intent -> STISTA atomization -> chemistry/space tool adapter -> governed execution -> receipt -> private/public proof packet
```

That is more valuable than claiming to be a replacement chemistry package. It lets a weak or strong model use real chemistry tools safely by following explicit steps, examples, expected outputs, and audit trails.

## Middle-Layer Design

We should do both: keep SCBE's symbolic chemistry/STISTA layer and bridge to real scientific chemistry systems through a governed middle layer.

```text
                 public/private proof packets
                          ^
                          |
Human/AI request -> SCBE Chem Middle Layer -> External engines/data
                          |
                          v
          STISTA atoms / GeoSeed orbitals / symbolic bonds
```

### Layer A: SCBE Native Chemistry

This is the internal symbolic layer:

- STISTA atomic tokenization,
- chemical fusion reconstruction,
- tongue molecule/bond scoring,
- ternary chemistry proxies,
- GeoSeed orbital invariants,
- private-proof hash inventory.

This layer is useful for agent routing, semantic decomposition, claim boundaries, and safety reasoning.

### Layer B: Chem Middle Layer

This is the translation and governance layer:

- canonical request schema: `intent`, `material_or_molecule`, `representation`, `operation`, `risk_class`, `allowed_engines`;
- adapter registry for RDKit, Open Babel, ASE, DeepChem, NASA CEA, PAHdb, SAM/CheMin-style data lanes;
- deterministic receipt schema: input hash, normalized input, engine, version, command, output hash, safety decision, claim boundary;
- bidirectional mapping: STISTA atoms can propose routes, external engines can return validated structures/properties that re-enter STISTA as evidence atoms;
- private/public split: public artifact gets hashes and result summaries; private artifact keeps patent/internal license material local.

### Layer C: External Chemistry and Space Systems

This is where validated scientific tools live:

- RDKit for cheminformatics and descriptors,
- Open Babel for conversion and file normalization,
- ASE for atomistic structures/simulation setup,
- DeepChem for ML chemistry workflows,
- NASA CEA/CEARUN for equilibrium/rocket thermochemistry,
- PAHdb for astrochemistry spectra,
- SAM/CheMin-style workflows for sample/spectrum/mineral evidence.

### Why This Is Stronger

The middle layer lets SCBE act like a governed chemistry operating shell:

- weak models can follow a tool contract without hallucinating chemistry,
- strong models get real engines and audit trails,
- hazardous or wet-lab actionable requests can be denied/quarantined,
- website claims can cite executable local receipts and external-tool provenance,
- patent/private proof remains hash-linked without exposing the private text.

### First Implementation Target

Build `scbe chem bridge` as the middle-layer entrypoint:

```bash
scbe chem atomize "oxidizer fuel equilibrium"
scbe chem bridge --engine rdkit --operation descriptors --smiles "CCO" --json
scbe chem bridge --engine obabel --from smi --to sdf --input molecule.smi --output molecule.sdf
scbe chem bridge --engine cea --template rocket --fuel CH4 --oxidizer O2 --json
scbe chem prove --public
```

Initial adapters should be capability-detection only unless the tools are installed. The benchmark should pass by proving graceful detection, safe denial/quarantine, STISTA fallback, and receipt generation.

## Sources

- RDKit official documentation: https://www.rdkit.org/
- RDKit overview: https://www.rdkit.org/new_docs/Overview.html
- Open Babel documentation: https://openbabel.org/
- Open Babel command-line documentation: https://openbabel.org/docs/Command-line_tools/babel.html
- ASE documentation: https://docs.ase-lib.org/index.html
- DeepChem GitHub/docs: https://github.com/deepchem/deepchem
- NASA CEA software catalog: https://software.nasa.gov/software/LEW-17687-1
- NASA CEA 3.0 beta documentation: https://nasa.github.io/cea/
- NASA CEARUN introduction: https://cearun.grc.nasa.gov/intro.html
- NASA Ames PAHdb page: https://www.nasa.gov/?p=484873
- Astrochemistry databases: https://www.astrochem.org/databases.php
- NASA Laboratory Astrophysics and Astrochemistry: https://www.nasa.gov/general/laboratory-astrophysics-and-astrochemistry/
- NASA SAM overview: https://ssed.gsfc.nasa.gov/sam/samiam.html
- NASA Curiosity science instruments: https://science.nasa.gov/mission/msl-curiosity/science-instruments/
- NASA Spacecraft Materials Selector software catalog: https://software.nasa.gov/software/MFS-31328-1
