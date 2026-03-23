# Six Sacred Tongues

> Bijective 256-token conlangs for cryptographic encoding. Each tongue has 16 prefixes x 16 suffixes = 256 unique tokens mapping bytes 0-255.

## The Tongues

| Tongue | Role | Color | 3D Axis | Phase (rad) | Weight |
|--------|------|-------|---------|-------------|--------|
| **KO** | Control | Cyan | +X | 0 | 1.000 |
| **AV** | Transport | Purple | -X | pi/3 | 1.618 |
| **RU** | Policy | Green | +Y | 2pi/3 | 2.618 |
| **CA** | Compute | Orange | -Y | pi | 4.236 |
| **UM** | Security | Red | +Z | 4pi/3 | 6.854 |
| **DR** | Schema | Violet | 5pi/3 | 5pi/3 | 11.090 |

## Token Format
```
token = prefix[byte >> 4] + "'" + suffix[byte & 0x0F]
```
Example: byte 0x2A in KO = `vel'or` (prefix[2] + suffix[10])

## Key Properties
- **Bijective**: Every byte maps to exactly one token per tongue (256 unique)
- **Deterministic**: Same byte always produces same token
- **Cross-translatable**: KO tokens -> AV tokens preserving exact byte payload
- **Attestable**: HMAC attestation on every cross-translation

## Weights & Phases
The golden-ratio weights (1, phi, phi^2, ...) create a natural hierarchy:
- KO (base) → DR (11.09x weight)
- Phase offsets distribute tongues evenly around the unit circle
- Used for blending patterns and priority ordering

## Platform Mapping (Web Agent)
| Platform | Tongue | Rationale |
|----------|--------|-----------|
| Twitter/X | KO | Control (short, direct) |
| LinkedIn | AV | Transport (professional flow) |
| Bluesky | RU | Policy (open protocol) |
| Mastodon | CA | Compute (federated logic) |
| WordPress/Medium | DR | Schema (structured content) |
| GitHub | CA | Compute (code) |
| HuggingFace | UM | Security (model safety) |

## Cross-References
- [[Tongue Domain Mappings]] — CDDM domain assignments per tongue
- [[Evolving Lexicons]] — Mutation and speciation
- [[3D Spatial Engine]] — Tongue-colored 3D visualization
- [[14-Layer Architecture]] — Tongues are Layer 2

## Academic Grounding
- Shannon (1948) "A Mathematical Theory of Communication" — bijective encoding
- Okrent (2009) "In the Land of Invented Languages" — conlang design
- The tongue system is a [[Category Theory References|category-theoretic]] bijection: an isomorphism in the category **Set** between `{0..255}` and the token set.
