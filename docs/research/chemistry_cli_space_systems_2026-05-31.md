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

## Middle Layer Architecture (Next Target)

Decision: **we do both** — keep STISTA symbolic chemistry *and* bridge external scientific/space tools — and connect them with an explicit **middle translation layer**.

The middle layer sits between SCBE's STISTA symbolic chemistry and external scientific chemistry/space engines, translating in **both directions** while enforcing safety gates and emitting receipts at every hop. It is the governed seam, not a new chemistry engine.

```text
                 ┌─────────────────────────── SCBE MIDDLE LAYER ───────────────────────────┐
 STISTA symbolic │  symbolic→scientific:  atomize → map atoms → emit tool-native input deck │  External engines
 chemistry       │  scientific→symbolic:  parse tool output → atom-transfer matrix → proof  │  (RDKit, Open Babel,
 (atomize/fuse/  │  every hop:            safety gate (ALLOW/QUARANTINE/DENY) + receipt      │   ASE, DeepChem,
  orbitals/prove)│  provenance:           input hash, output hash, tool+version, claim band  │   NASA CEA, PAHdb)
                 └──────────────────────────────────────────────────────────────────────────┘
```

### Responsibilities

1. **Symbolic → scientific (outbound).** Translate STISTA atomic tokens / GeoSeed orbital state into a tool-native artifact (e.g. SMILES for RDKit/Open Babel, an ASE `Atoms` structure, a CEA input deck). Borrow the SMILES atom-map-number convention (`token:shell`) so symbolic atoms round-trip to real atom identities.
2. **Scientific → symbolic (inbound).** Parse external tool output back into SCBE's representation: an atom-transfer / transition matrix (the `AtomTransferRecorder` shape in `src/geoseed/transfer_recorder.py`), GeoSeed shell costs (`n·ln φ`), and a claim band.
3. **Governance per hop.** Route every translation and execution through the 14-layer governance gate (ALLOW / QUARANTINE / ESCALATE / DENY). Hazardous synthesis, energetic materials, toxicity, and illegal-drug requests are denied or quarantined; benign educational / conversion / descriptor / public-data workflows are allowed.
4. **Receipts + proof separation.** Each hop emits a receipt (input hash, output hash, tool name + version, command, decision, claim boundary). Private proof packets stay separate from public evidence.

### Interface sketch

- `scbe chem translate --to rdkit|obabel|ase|cea <stista-input>` — outbound symbolic→scientific.
- `scbe chem ingest --from <tool> <output-file>` — inbound scientific→symbolic, returns transfer matrix + claim band.
- `scbe chem bridge run --tool <tool> --intent "<text>"` — full governed loop: atomize → gate → translate → exec → ingest → receipt.

The middle layer is provider-agnostic and degrades gracefully: if an external engine is not installed, the symbolic side still runs and the receipt records the bridge as unavailable rather than failing.

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

2. `feat/chem-middle-layer`
   - Bidirectional STISTA <-> scientific translator (`scbe chem translate`, `scbe chem ingest`, `scbe chem bridge run`).
   - Per-hop governance gate + receipt emission.
   - Atom-map-number round-trip contract and atom-transfer-matrix ingest.

3. `feat/chem-interop-bridges`
   - Detect optional tools: RDKit, Open Babel, ASE, DeepChem.
   - Expose wrappers only when installed.
   - Emit receipts with versions, command, input hash, output hash, and claim boundary.

4. `feat/space-chem-bridges`
   - NASA CEA/CEARUN input deck templates.
   - PAHdb cache/search/fit scaffold.
   - SAM/CheMin-inspired evidence workflow for sample/spectrum/claim reports.

5. `feat/chem-safety-gate`
   - Deny or quarantine hazardous synthesis, energetic material, toxicity, or illegal-drug requests.
   - Allow benign educational, file-conversion, descriptor, and public-data workflows.
   - Put human approval before any wet-lab actionable output.

## Product Framing

SCBE should present chemistry as a command-line evidence room:

```text
Human intent -> STISTA atomization -> middle-layer translate -> chemistry/space tool adapter -> governed execution -> receipt -> private/public proof packet
```

That is more valuable than claiming to be a replacement chemistry package. It lets a weak or strong model use real chemistry tools safely by following explicit steps, examples, expected outputs, and audit trails. The middle layer is the part competitors do not have: a governed, receipted, bidirectional bridge between symbolic intent and established scientific chemistry/space engines.

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
