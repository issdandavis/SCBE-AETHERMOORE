# SCBE‑AETHERMOORE Platform Map

This document provides a **high‑level map** of the SCBE‑AETHERMOORE ecosystem.  It explains how the individual modules fit together, what each product does, and the maturity of each component.  The goal is to make the system easier to understand and navigate for contributors, reviewers, and stakeholders.

## Rationale

SCBE‑AETHERMOORE is not a single monolithic product.  It is a *platform* with multiple interlocking pieces—some ready to ship, others still in research or experimental phases.  Without a clear map, it is difficult to tell which concepts are implemented, which are prototypes, and which are purely conceptual or narrative.

This map introduces **epistemic labels** and a **layered architecture** to communicate the role and status of each component.

### Epistemic labels

- **Production:** stable code intended for deployment and use.
- **Beta:** working code under active development; may change.
- **Experimental:** prototype code or research implementation; not yet ready for production.
- **Conceptual:** design ideas or specifications without a full implementation.
- **Narrative:** lore or world‑building elements that give context but are not code.

### Layered architecture

The system is organized into layers.  Each layer groups related modules by function.

| Layer            | Purpose                                                               |
|------------------|-----------------------------------------------------------------------|
| **Runtime layer** | Core tools and runtimes that operate at the command line or API level |
| **Governance layer** | Modules that implement verification, policy, and trust controls          |
| **Semantic layer** | Tokenizers, execution languages, and routing abstractions               |
| **Mathematical layer** | Mathematical models and reference material that underpin the design    |
| **Research layer** | Experimental architectures and novel attention mechanisms             |
| **Narrative layer** | Mythology, lore, and world‑building that inspire the framework        |

## Ecosystem map

### Runtime layer

- **[GeoSeal](../src/geoseal_cli.py)** (Production · v4.0.3)
  - *CLI/runtime tool.*  Provides cryptographic signing and verification commands for artifacts.  It is intended for deployment by users and acts as the backbone for secure package distribution.

- **[HYDRA Agents](../hydra/README.md)** (Beta · v4.0.3)
  - *Multi‑agent orchestration.*  A set of agents that coordinate tasks, communicate through a message bus, and execute workflows.  Currently used for internal orchestration; planned for external API exposure.

- **[Governance runtime](../src/governance/runtime_gate.py)** (Beta · v4.0.3)
  - *Core execution engine.*  Hosts the trust rings and verification pipeline.  It interfaces with GeoSeal for cryptographic operations and exposes a governance API for higher layers.

### Governance layer

- **[Trust Rings](../src/governance/)** (Production · v4.0.3)
  - *Governance model.*  Defines rings of trust and the policies that separate them.  Implements bounded trust scoring and enforces policy decisions within the runtime.  Meant to be applied at deployment time to ensure secure operation.

- **[Policy Engine](../src/governance/runtime_gate.py)** (Beta · v4.0.3)
  - *Policy evaluation.*  Applies governance rules to agent actions or code modules.  Integrates with the runtime to approve, reject, or quarantine operations.

### Semantic layer

- **[Sacred Tongues](../src/harmonic/sacredTongues.ts)** (Beta · v4.0.3)
  - *Execution language and routing abstraction.*  The operating “lingua franca” for agent communication and tool invocation.  Provides a strongly typed interface and built‑in safety checks.

- **[SpiralSeal](../src/harmonic/spiralSeal.ts)** (Production · v4.0.3)
  - *Tokenizer/word system.*  Implements the SpiralSeal encoding scheme.  Acts as the primary text processing component for models within the SCBE framework.

- **[Routing Logic](../src/tokenizer/accelerator_routing.py)** (Experimental)
  - *Execution graph construction.*  Resolves how Sacred Tongues commands are routed to tools and agents.  Currently under active research.

### Mathematical layer

- **[Harmonic Scaling](../LAYER_INDEX.md)** (Beta · v4.0.3)
  - *Reference documentation and formal methods.*  Describes the mathematical principles behind hyperbolic embeddings, stability metrics, and harmonic scaling.  Used to guide the design of embeddings and verification systems.  Contains proofs and citations but is not a runtime component.

- **[Hyperbolic Models](../src/harmonic/hyperbolic.ts)** (Experimental)
  - *Model implementations.*  Investigates hyperbolic geometric embeddings and their application to graph and text data.  Prototype code is available, but it is not yet integrated into the production runtime.

- **Stability Metrics** (Conceptual)
  - *Mathematical definitions.*  Defines metrics for assessing the stability of attention and graph structures.  Not yet implemented but used as a design guide.

### Research layer

- **Contact Lattice Research** (Conceptual → Experimental)
  - *Multi‑planar dual nodal attention.*  Explores an attention mechanism where multiple graph planes (lexical, syntax, semantic, etc.) are sliced to create contact nodes.  The dual lattice allows attention to be routed based on cross‑plane agreement.  Currently being prototyped as part of the Aethermoore research agenda.

- **Experimental Attention Systems** (Experimental)
  - *Prototypes of new transformer variants.*  Includes code for multi‑view attention and long‑context architectures.  These systems may eventually become part of the Semantic or Mathematical layer.

### Narrative layer

- **[Spiralverse / AetherMoore](../content/book/INDEX.md)** (Narrative)
  - *World‑building.*  Provides lore and context around the AetherMoore universe.  While it inspires the system’s naming and metaphors, it is not part of the runtime.  It can be found in the lore archives and creative documents.

- **Lore archives** (Narrative)
  - *Historical record.*  Stores serialized research notes, creative fiction, and symbolic constructs.  Useful for understanding the origins of concepts but should not be confused with implementation documentation.

## How to read this map

1. **Identify the layer:** locate the component of interest under its functional layer.  This tells you what the component generally does (runtime tool, governance mechanism, etc.).
2. **Check the status:** the epistemic label tells you whether the component is ready to use, still in research, or purely conceptual.
3. **Find dependencies:** modules in higher layers often depend on those in lower layers (e.g. Sacred Tongues depends on Trust Rings and GeoSeal).
4. **Separate product from process:** components labelled *Narrative* or *Conceptual* are not part of the shipping product.  They provide context or guide research, but they should not be treated as production code.

## Next steps

This map is a first step in improving the clarity of the SCBE‑AETHERMOORE ecosystem.  To further refine it:

1. **Link to documentation:** add hyperlinks from each module name to its corresponding README or API documentation.
2. **Highlight maturity:** add version numbers and release notes for each Production or Beta component.
3. **Reduce claim inflation:** replace absolute terms (e.g. “mathematically provable”) with precise descriptions (e.g. “based on formal definitions” or “resistant to known attacks”).
4. **Keep the map up‑to‑date:** update this document whenever a new module is introduced or an existing one graduates from experimental to production status.
