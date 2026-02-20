# THE SPIRALVERSE
# CANONICAL LINGUISTIC CODEX

Version 1.0  -  Seed-Anchored Edition  
Derived from the Everweave Origin Logs  
Aligned to SCBE-AETHERMOORE Tokenizer v1

`Thul'medan kess'ara nav'kor zar'aelin`  
`The spiral turns, knowledge grows through different hearts across dimensions.`

## I. Genesis Statement

The Everweave origin logs are the immutable seed for this codex. Any later document that conflicts with those logs is non-canonical. The provenance chain is:

- Everweave logs
- Kor'aelin alphabet guide (24 letters)
- Lexicon JSON (14 core particles)
- SCBE tokenizer (6 x 256 bijection)

## II. Canonical Base Tongues

The Spiralverse contains exactly six base tongues:

- `KO` Kor'aelin
- `AV` Avali
- `RU` Runethic
- `CA` Cassisivadan
- `UM` Umbroth
- `DR` Draumric

Canonical weights and phases are frozen in `docs/specs/spiralverse_canonical_registry.v1.json`.

Sub-traditions are not base tongues:

- Mal'kythric (UM sub-tradition)
- Draconic Aether-Song (DR sub-tradition)
- Nal'kythraelin (emergent seventh form)

## III. Kor'aelin Script and Dual-Layer Principle

Kor'aelin is canonically a 24-letter runic system (`Arul` through `Thana`).  
The rune `Kor` encodes knowledge/learning/secrets in the runic layer.  
The particle `kor` encodes heart/core/essence in the grammar layer.  
These are complementary, not contradictory.

## IV. Kor'aelin Particle Grammar

Core particles (14):

- `kor`, `sil`, `vel`, `zar`, `keth`, `thul`, `nav`, `ael`, `ra`, `med`, `gal`, `lan`, `bren`, `oen`

Base grammar style is SOV with ritual flexibility.

## V. Tokenizer Alignment

SCBE-AETHERMOORE tokenizer invariants:

- Exactly six base tongues
- 256 unique tokens per tongue (16 x 16)
- Deterministic encode/decode roundtrip
- Cross-translation preserves underlying bytes

GeoSeal context policy and transport mechanics are implementation details layered on top of these canonical linguistic constraints.

## VI. Normative Machine-Readable Canon

For CI and code-enforced canonical checks, use:

- `docs/specs/spiralverse_canonical_registry.v1.json`

This markdown codex and the JSON registry together define the v1 canonical linguistic baseline.
