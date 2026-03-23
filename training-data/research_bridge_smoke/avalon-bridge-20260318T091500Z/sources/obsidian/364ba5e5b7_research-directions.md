# Research Directions

> Open questions and next steps for SCBE-AETHERMOORE. Updated as priorities shift.

## High Priority

### CIP Patent Filing (~March 2026)
- Adds: Sacred Tongues (6 conlangs), PHDM (polyhedral defense), Space Tor
- Deadline: ~6 weeks from provisional
- See [[Patent Strategy]]

### Invariant DSL
- YAML-based domain-specific language for declaring constants, bounds, preserved invariants
- Validator using symbolic math (sympy or pure-stdlib)
- Eliminates "arbitrary constant" criticism
- Builds on [[CDDM Framework]] (domains already enforce bounds)

### Multi-Temporal Narrative Training Dataset (MTNTD)
- 4-layer JSON/Parquet: snapshots, transitions, cross-timeline diffs, abstract graphs
- Feeds into the ouroboros self-learning pipeline
- Uses [[CDDM Framework]] morphisms for cross-domain dataset annotations

## Medium Priority

### Representation Layer Pipeline (RLP)
- Raw data -> binary -> structural graph -> semantic graph -> cross-domain mapping
- Connects existing crypto layer to CDDM morphisms
- Entry point: `src/scbe/representation.py` (to be created)

### Hyperbolic IDE Visualization
- Poincare disk rendering in custom IDE
- ds² heatmaps for code change visualization
- Builds on [[3D Spatial Engine]] terminal rendering

### Ouroboros Self-Learning
- Self-referential SFT generation: system outputs become training inputs
- Entropy-gated quality filtering (rho_e threshold)
- Integrates with existing `scripts/daily_training_wave.py`

## Lower Priority

### v4.0.0 — Telecommunications / Space Tor
- Next major version target
- Onion routing with tongue-encrypted layers
- Satellite relay protocol with GeoSeal context awareness

### Cross-Domain Review Bot
- Flask service watching Obsidian/Notion for DSL edits
- Runs validator, posts results to Gmail label [SCBE-REVIEW]

### Direct Airtable Connector
- Only when a paid client needs it (per user decision)
- Currently using Zapier bridge

## Questions to Resolve

1. **Should CDDM morphisms be registered centrally or per-module?**
   - Currently central in `tongue_domains.py`
   - Could be distributed with a registry pattern

2. **Should the Invariant DSL use sympy or pure stdlib?**
   - sympy is more powerful but adds dependency
   - Pure stdlib aligns with project philosophy

3. **What's the minimum viable MTNTD for training?**
   - Estimate: 50 snapshots, 200 transitions, 50 cross-timeline diffs

## Cross-References
- [[System Growth Log]] — What we've already built
- [[CDDM Framework]] — Foundation for most research directions
- [[Patent Strategy]] — Legal timeline constraints
- [[14-Layer Architecture]] — The system these directions extend
