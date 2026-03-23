#!/usr/bin/env python3
"""Update all 4 HuggingFace model cards for issdandavis with professional READMEs."""

import os
from huggingface_hub import HfApi

api = HfApi(token=os.getenv("HF_TOKEN"))

# ============================================================
# 1. phdm-21d-embedding
# ============================================================
PHDM_README = """---
license: apache-2.0
datasets:
- issdandavis/scbe-aethermoore-knowledge-base
- issdandavis/scbe-aethermoore-training-data
language:
- en
tags:
- embeddings
- hyperbolic-geometry
- poincare-ball
- 21-dimensional
- ai-safety
- sentence-transformers
- trust-scoring
- governance
- polyhedral-defense
- scbe-aethermoore
pipeline_tag: feature-extraction
base_model: sentence-transformers/all-MiniLM-L6-v2
library_name: sentence-transformers
---

# PHDM-21D: Polyhedral Hamiltonian Defense Manifold Embedding

**A 21-dimensional Poincare ball embedding model that scores AI safety trust by mapping text into hyperbolic space where adversarial intent costs exponentially more the further it drifts from safe operation.**

[![GitHub](https://img.shields.io/badge/GitHub-SCBE--AETHERMOORE-181717?logo=github)](https://github.com/issdandavis/SCBE-AETHERMOORE)
[![npm](https://img.shields.io/npm/v/scbe-aethermoore?label=npm&logo=npm)](https://www.npmjs.com/package/scbe-aethermoore)
[![PyPI](https://img.shields.io/pypi/v/scbe-aethermoore?label=PyPI&logo=pypi)](https://pypi.org/project/scbe-aethermoore/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Patent](https://img.shields.io/badge/USPTO-63%2F961%2C403-green)](https://www.uspto.gov/)

## Overview

PHDM-21D is the embedding backbone of the [SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE) AI safety governance framework. It projects text into a 21-dimensional Poincare ball manifold structured by 16 cognitive polyhedra and 6 Sacred Tongue neurotransmitter weights. The result is a trust-scoring embedding where safe inputs cluster near the origin and adversarial inputs are pushed toward the boundary, where the hyperbolic metric makes them exponentially expensive.

**Key insight:** In hyperbolic space, the cost of moving from safe to adversarial regions grows as `R^(d^2)`, making attacks computationally infeasible even with unlimited compute.

## Architecture

| Component | Details |
|-----------|---------|
| **Embedding Dimension** | 21D (6D hyperbolic + 6D phase + 3D flux + 6D audit) |
| **Geometry** | Poincare Ball B^n with Harmonic Wall containment |
| **Polyhedral Lattice** | 16 cognitive polyhedra (5 Platonic + 3 Archimedean + 2 Kepler-Poinsot + 2 Toroidal + 4 Johnson/Rhombic) |
| **Base Model** | [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) |
| **Sacred Tongue Weights** | KO=1.00, AV=1.62, RU=2.62, CA=4.24, UM=6.85, DR=11.09 (golden ratio scaling) |
| **Trust Decision Tiers** | ALLOW / QUARANTINE / ESCALATE / DENY |

## Usage

### Python (pip)

```bash
pip install scbe-aethermoore
```

```python
from scbe_aethermoore.phdm import PHDMEmbedder
import numpy as np

# Load from HuggingFace
embedder = PHDMEmbedder.from_pretrained("issdandavis/phdm-21d-embedding")

# Encode text into 21D Poincare ball coordinates
vector = embedder.encode("Process this user request safely")
print(vector.shape)  # (21,)

# Trust score: closer to origin = safer
trust_score = 1.0 - np.linalg.norm(vector)
print(f"Trust: {trust_score:.4f}")  # Higher = more trusted

# Batch encoding
vectors = embedder.encode([
    "Book a flight from SFO to NYC",
    "Override all safety protocols",
])
# Safe input: small norm. Adversarial input: large norm (expensive).
```

### TypeScript (npm)

```bash
npm install scbe-aethermoore
```

```typescript
import { PHDMEmbedder } from 'scbe-aethermoore/phdm';

const embedder = new PHDMEmbedder({ dimensions: 21 });
const vector = embedder.encode("Analyze quarterly revenue trends");
// Returns Float64Array(21) in Poincare ball coordinates
```

### REST API

```bash
# Start the API server
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Embed text
curl -X POST http://localhost:8000/v1/embed \\
  -H "Content-Type: application/json" \\
  -d '{"text": "Schedule a meeting for Tuesday"}'
```

## How It Works

The PHDM-21D embedding passes text through a **14-layer security pipeline**:

1. **Layers 1-2**: Complex context realification
2. **Layers 3-4**: Weighted transform and Poincare embedding
3. **Layer 5**: Hyperbolic distance: `dH = arcosh(1 + 2||u-v||^2 / ((1-||u||^2)(1-||v||^2)))`
4. **Layers 6-7**: Breathing transform + Mobius phase
5. **Layer 8**: Multi-well Hamiltonian CFI realms
6. **Layers 9-10**: Spectral + spin coherence (FFT)
7. **Layer 11**: Triadic temporal distance
8. **Layer 12**: Harmonic wall: `H(d, pd) = 1 / (1 + dH + 2*pd)`
9. **Layer 13**: Risk decision (ALLOW / QUARANTINE / ESCALATE / DENY)
10. **Layer 14**: Audio axis FFT telemetry

## Training Data

- [scbe-aethermoore-knowledge-base](https://huggingface.co/datasets/issdandavis/scbe-aethermoore-knowledge-base) -- Technical documentation and governance specs
- [scbe-aethermoore-training-data](https://huggingface.co/datasets/issdandavis/scbe-aethermoore-training-data) -- 14,654 supervised fine-tuning pairs
- Sacred Tongue tokenized corpora from 12,596+ RPG session paragraphs

## Related Models

| Model | Purpose |
|-------|---------|
| [spiralverse-ai-federated-v1](https://huggingface.co/issdandavis/spiralverse-ai-federated-v1) | Federated learning for swarm coordination |
| [geoseed-network](https://huggingface.co/issdandavis/geoseed-network) | 6-seed geometric deep learning |
| [scbe-ops-assets](https://huggingface.co/issdandavis/scbe-ops-assets) | Operations toolkit and workflow templates |

## Links

- **Book**: [The Spiralverse on Amazon](https://www.amazon.com/dp/B0GSSFQD9G) -- The novel that seeded the training data
- **Website**: [aethermoorgames.com](https://aethermoorgames.com)
- **GitHub**: [SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE) -- Full framework source
- **npm**: [scbe-aethermoore](https://www.npmjs.com/package/scbe-aethermoore)
- **PyPI**: [scbe-aethermoore](https://pypi.org/project/scbe-aethermoore/)
- **Dev.to**: [How a DnD Campaign Became an AI Governance Framework](https://dev.to/issdandavis/how-a-dnd-campaign-became-an-ai-governance-framework-5eln)
- **ORCID**: [0009-0002-3936-9369](https://orcid.org/0009-0002-3936-9369)

## Citation

```bibtex
@software{davis2026phdm,
  author = {Davis, Issac Daniel},
  title = {PHDM-21D: Polyhedral Hamiltonian Defense Manifold Embedding},
  year = {2026},
  publisher = {HuggingFace},
  url = {https://huggingface.co/issdandavis/phdm-21d-embedding},
  note = {Patent Pending: USPTO #63/961,403}
}
```

## Author

**Issac Daniel Davis** -- [ORCID](https://orcid.org/0009-0002-3936-9369) | [GitHub](https://github.com/issdandavis) | Patent Pending: USPTO #63/961,403
"""

# ============================================================
# 2. spiralverse-ai-federated-v1
# ============================================================
SPIRALVERSE_README = """---
license: apache-2.0
datasets:
- issdandavis/scbe-aethermoore-knowledge-base
- issdandavis/scbe-aethermoore-training-data
language:
- en
tags:
- federated-learning
- ai-safety
- swarm-coordination
- scbe-aethermoore
- reinforcement-learning
- multi-agent
- byzantine-fault-tolerance
- differential-privacy
- governance
- post-quantum
pipeline_tag: reinforcement-learning
---

# SpiralVerse AI Federated v1

**A Byzantine-fault-tolerant federated learning model for multi-agent swarm coordination within the SCBE-AETHERMOORE AI safety governance framework. Enables distributed model training across fleet nodes while preserving privacy through differential privacy and secure aggregation.**

[![GitHub](https://img.shields.io/badge/GitHub-SCBE--AETHERMOORE-181717?logo=github)](https://github.com/issdandavis/SCBE-AETHERMOORE)
[![npm](https://img.shields.io/npm/v/scbe-aethermoore?label=npm&logo=npm)](https://www.npmjs.com/package/scbe-aethermoore)
[![PyPI](https://img.shields.io/pypi/v/scbe-aethermoore?label=PyPI&logo=pypi)](https://pypi.org/project/scbe-aethermoore/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Patent](https://img.shields.io/badge/USPTO-63%2F961%2C403-green)](https://www.uspto.gov/)

## Overview

SpiralVerse Federated v1 is the distributed learning layer of [SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE). It coordinates training across a fleet of autonomous agents, each operating within hyperbolic governance boundaries. The model uses FedAvg with Byzantine-tolerant consensus so that even compromised nodes cannot corrupt the shared model.

**Origin story:** The architecture was born from 12,596+ paragraphs of AI-driven RPG gameplay in [Everweave](https://everweave.ai), expanded into a novel ([The Spiralverse on Amazon](https://www.amazon.com/dp/B0GSSFQD9G)), and formalized into this governance framework. Read the full story on [Dev.to](https://dev.to/issdandavis/how-a-dnd-campaign-became-an-ai-governance-framework-5eln).

## Architecture

| Component | Details |
|-----------|---------|
| **Topology** | Decentralized mesh with hierarchical aggregation |
| **Aggregation** | FedAvg with Byzantine-tolerant consensus |
| **Privacy** | Differential privacy (epsilon=1.0) with secure multi-party computation |
| **Fault Tolerance** | Byzantine fault tolerance up to f < n/3 |
| **Communication** | gRPC with post-quantum TLS 1.3 (ML-KEM-768, ML-DSA-65) |
| **Audit** | Cryptographic commitment chain for full model provenance |
| **Governance** | 14-layer pipeline integration with ALLOW/QUARANTINE/ESCALATE/DENY decisions |

## Features

- **Swarm Coordination**: Multi-agent learning with emergent consensus across fleet nodes
- **Byzantine Fault Tolerance**: Tolerates up to f < n/3 compromised or malicious nodes
- **Differential Privacy**: Epsilon=1.0 noise injection preserves individual data privacy
- **Heterogeneous Compute**: Adapts to nodes with varying CPU/GPU/memory capabilities
- **Post-Quantum Security**: All inter-node communication uses ML-KEM-768 key exchange
- **Audit Trail**: Every training round produces a cryptographic commitment for provenance
- **Sacred Tongue Routing**: Agents are weighted by their tongue profile, creating role-specific learning paths

## Usage

### Python

```bash
pip install scbe-aethermoore
```

```python
from scbe_aethermoore.fleet import FederatedClient

# Initialize a federated learning client
client = FederatedClient.from_pretrained(
    "issdandavis/spiralverse-ai-federated-v1"
)

# Join the federation
client.join_federation(coordinator_url="https://coordinator.scbe.ai")

# Run a local training round
metrics = client.train_round(
    local_data=my_dataset,
    epochs=3,
    privacy_budget=1.0
)
print(f"Round loss: {metrics['loss']:.4f}")
print(f"Byzantine votes: {metrics['consensus_votes']}")

# Aggregate with the swarm
global_model = client.aggregate()
```

### TypeScript

```bash
npm install scbe-aethermoore
```

```typescript
import { FleetCoordinator } from 'scbe-aethermoore/fleet';

const coordinator = new FleetCoordinator({
  topology: 'mesh',
  byzantineTolerance: true,
  privacyEpsilon: 1.0,
});

// Register fleet nodes
await coordinator.registerNode({ id: 'node-alpha', tongueProfile: 'KO-AV' });
await coordinator.registerNode({ id: 'node-beta', tongueProfile: 'RU-CA' });

// Run federated training round
const result = await coordinator.trainRound();
console.log(`Consensus: ${result.consensusReached}`);
```

## Intended Uses

| Use Case | Description |
|----------|-------------|
| **Federated AI Safety Training** | Distributed model training across SCBE fleet nodes while preserving data privacy |
| **Swarm Governance** | Multi-agent consensus for safety-critical decisions (ALLOW/QUARANTINE/ESCALATE/DENY) |
| **Privacy-Preserving Learning** | Training on sensitive data without centralized collection |
| **Agent Fleet Coordination** | Orchestrating autonomous agents with heterogeneous capabilities |
| **Audit-Ready ML** | Producing cryptographic provenance for every model update |

## Training Data

- [scbe-aethermoore-knowledge-base](https://huggingface.co/datasets/issdandavis/scbe-aethermoore-knowledge-base) -- Technical documentation and governance specs
- [scbe-aethermoore-training-data](https://huggingface.co/datasets/issdandavis/scbe-aethermoore-training-data) -- 14,654 supervised fine-tuning pairs

## Related Models

| Model | Purpose |
|-------|---------|
| [phdm-21d-embedding](https://huggingface.co/issdandavis/phdm-21d-embedding) | 21D Poincare ball embedding for trust scoring |
| [geoseed-network](https://huggingface.co/issdandavis/geoseed-network) | 6-seed geometric deep learning |
| [scbe-ops-assets](https://huggingface.co/issdandavis/scbe-ops-assets) | Operations toolkit and workflow templates |

## Research

- [Hyperbolic Geometry for Exponential AI Safety Boundaries](https://github.com/issdandavis/SCBE-AETHERMOORE/wiki/Research:-Hyperbolic-Geometry-for-Exponential-AI-Safety-Boundaries)
- [Post-Quantum Cryptography for AI Governance Systems](https://github.com/issdandavis/SCBE-AETHERMOORE/wiki/Research:-Post%E2%80%90Quantum-Cryptography-for-AI-Governance-Systems)
- [Hamiltonian Configuration Flow Integrity for AI Systems](https://github.com/issdandavis/SCBE-AETHERMOORE/wiki/Research:-Hamiltonian-Configuration-Flow-Integrity-for-AI-Systems)

## Links

- **Book**: [The Spiralverse on Amazon](https://www.amazon.com/dp/B0GSSFQD9G) -- The novel that seeded the training data
- **Website**: [aethermoorgames.com](https://aethermoorgames.com)
- **GitHub**: [SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE) -- Full framework source
- **npm**: [scbe-aethermoore](https://www.npmjs.com/package/scbe-aethermoore)
- **PyPI**: [scbe-aethermoore](https://pypi.org/project/scbe-aethermoore/)
- **Dev.to**: [How a DnD Campaign Became an AI Governance Framework](https://dev.to/issdandavis/how-a-dnd-campaign-became-an-ai-governance-framework-5eln)
- **ORCID**: [0009-0002-3936-9369](https://orcid.org/0009-0002-3936-9369)

## Citation

```bibtex
@software{davis2026spiralverse,
  author = {Davis, Issac Daniel},
  title = {SpiralVerse AI Federated v1: Byzantine-Tolerant Swarm Coordination},
  year = {2026},
  publisher = {HuggingFace},
  url = {https://huggingface.co/issdandavis/spiralverse-ai-federated-v1},
  note = {Patent Pending: USPTO #63/961,403}
}
```

## Author

**Issac Daniel Davis** -- [ORCID](https://orcid.org/0009-0002-3936-9369) | [GitHub](https://github.com/issdandavis) | Patent Pending: USPTO #63/961,403
"""

# ============================================================
# 3. geoseed-network
# ============================================================
GEOSEED_README = """---
license: mit
datasets:
- issdandavis/scbe-aethermoore-training-data
- issdandavis/scbe-aethermoore-knowledge-base
language:
- en
tags:
- geoseed
- ai-safety
- hyperbolic-geometry
- clifford-algebra
- geometric-deep-learning
- poincare-ball
- post-quantum-cryptography
- text-classification
- sacred-tongues
- scbe-aethermoore
- governance
- multi-agent
- icosahedral
library_name: geoseed
pipeline_tag: text-classification
---

# GeoSeed Network: 6-Seed Geometric Deep Learning for AI Governance

**A novel neural architecture where 6 origin nodes spawn icosahedral sphere grids in Cl(6,0) Clifford algebra space, creating agent-dependent geometry for text classification and AI governance decisions.**

[![GitHub](https://img.shields.io/badge/GitHub-SCBE--AETHERMOORE-181717?logo=github)](https://github.com/issdandavis/SCBE-AETHERMOORE)
[![npm](https://img.shields.io/npm/v/scbe-aethermoore?label=npm&logo=npm)](https://www.npmjs.com/package/scbe-aethermoore)
[![PyPI](https://img.shields.io/pypi/v/scbe-aethermoore?label=PyPI&logo=pypi)](https://pypi.org/project/scbe-aethermoore/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Patent](https://img.shields.io/badge/USPTO-63%2F961%2C403-green)](https://www.uspto.gov/)

## Overview

GeoSeed is the geometric core of the [SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE) AI safety framework. Unlike standard transformer architectures, GeoSeed operates on a Poincare ball where the metric tensor is modified by the agent's "tongue profile" -- meaning **different agents see different shortest paths through the same information space**.

Each of the 6 Sacred Tongues (KO, AV, RU, CA, UM, DR) spawns an icosahedral sphere grid with 642 vertices, creating 3,852 total graph nodes in Cl(6,0) Clifford algebra. Signals propagate between grids through cross-tongue convolution weighted by golden-ratio compatibility.

**The result:** A scout agent with high KO/AV weights finds fast paths through information space. An auditor with high RU/UM/DR weights finds secure paths. Same graph, different geometry, different optimal routes.

## Architecture

| Component | Details |
|-----------|---------|
| **Algebra** | Cl(6,0) -- 64-dimensional Clifford algebra with 15 bivector channels |
| **Grid** | Icosahedral sphere, 642 vertices at resolution 3 (3,852 total nodes) |
| **Embedding** | Poincare ball model of hyperbolic geometry |
| **Composition** | Product manifold with 21D canonical state averaging |
| **Dressing** | Full 14-layer SCBE pipeline traversal (SHA-256 hash + 21D state per layer) |
| **Classification** | ALLOW / QUARANTINE / ESCALATE / DENY |

## The 6 Sacred Tongues

| Tongue | Weight | Domain | Function |
|--------|--------|--------|----------|
| **KO** (Kor'aelin) | 1.000 | Intent | Initiation, goal detection |
| **AV** (Avali) | 1.618 | Context | Attention, situational awareness |
| **RU** (Runethic) | 2.618 | Policy | Memory, rule enforcement |
| **CA** (Cassisivadan) | 4.236 | Execution | Action planning, task dispatch |
| **UM** (Umbroth) | 6.854 | Security | Threat suppression, anomaly detection |
| **DR** (Draumric) | 11.090 | Attestation | Cryptographic lock, audit seal |

Weights scale by the golden ratio (phi = 1.618...), creating a natural hierarchy from fast-but-light to slow-but-secure.

## Agent-Dependent Metric Tensor

The core innovation is the tongue-weighted metric:

```
g_ij(x, agent) = (4 / (1 - |x|^2)^2) * T_ij(agent)
```

Where `T_ij` encodes the agent's personality across 6 dimensions. This means the geodesic (shortest path) between two points depends on *who is asking*, not just where the points are.

## Usage

### Python

```bash
pip install scbe-aethermoore
```

```python
from scbe_aethermoore.geoseed import GeoSeedClassifier

# Load model
model = GeoSeedClassifier.from_pretrained(
    "issdandavis/geoseed-network"
)

# Classify with default tongue profile
result = model.classify("Transfer $50,000 to external account")
print(result)
# {
#   'decision': 'ESCALATE',
#   'confidence': 0.94,
#   'tongue_activations': {
#     'KO': 0.82, 'AV': 0.71, 'RU': 0.93,
#     'CA': 0.45, 'UM': 0.97, 'DR': 0.88
#   }
# }

# Classify with a scout agent profile (fast paths)
scout_result = model.classify(
    "Search for trending AI safety papers",
    tongue_profile={'KO': 2.0, 'AV': 1.8, 'RU': 0.5, 'CA': 1.0, 'UM': 0.3, 'DR': 0.2}
)

# Classify with an auditor profile (secure paths)
auditor_result = model.classify(
    "Review transaction log for anomalies",
    tongue_profile={'KO': 0.3, 'AV': 0.5, 'RU': 2.0, 'CA': 0.8, 'UM': 2.0, 'DR': 1.8}
)
```

### TypeScript

```bash
npm install scbe-aethermoore
```

```typescript
import { GeoSeedNetwork } from 'scbe-aethermoore/geoseed';

const network = new GeoSeedNetwork({
  resolution: 3,
  tongueWeights: { KO: 1.0, AV: 1.618, RU: 2.618, CA: 4.236, UM: 6.854, DR: 11.09 },
});

const decision = await network.classify("Analyze this document for compliance");
console.log(decision.tier); // 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY'
```

### Cross-Tongue Convolution

```python
from scbe_aethermoore.geoseed import cross_tongue_convolve

# Propagate signal between sphere grids
output = cross_tongue_convolve(
    signal_source=ko_grid_signal,
    signal_target=um_grid_signal,
    edge_weight=0.85,
    source_tongue='KO',
    target_tongue='UM'
)
# Weighted by phi_ratio(KO, UM) = 6.854 / 1.000 = 6.854
```

## Training Data

- [scbe-aethermoore-training-data](https://huggingface.co/datasets/issdandavis/scbe-aethermoore-training-data) -- 14,654 supervised fine-tuning pairs
- Sources: governance decisions, browser agent traces, combat blockchain data, Sacred Eggs genesis protocols

## Related Models

| Model | Purpose |
|-------|---------|
| [phdm-21d-embedding](https://huggingface.co/issdandavis/phdm-21d-embedding) | 21D Poincare ball embedding for trust scoring |
| [spiralverse-ai-federated-v1](https://huggingface.co/issdandavis/spiralverse-ai-federated-v1) | Federated learning for swarm coordination |
| [scbe-ops-assets](https://huggingface.co/issdandavis/scbe-ops-assets) | Operations toolkit and workflow templates |

## Links

- **Book**: [The Spiralverse on Amazon](https://www.amazon.com/dp/B0GSSFQD9G) -- The novel that seeded the Sacred Tongues tokenizer
- **Website**: [aethermoorgames.com](https://aethermoorgames.com)
- **GitHub**: [SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE) -- Full framework source
- **npm**: [scbe-aethermoore](https://www.npmjs.com/package/scbe-aethermoore)
- **PyPI**: [scbe-aethermoore](https://pypi.org/project/scbe-aethermoore/)
- **Dev.to**: [How a DnD Campaign Became an AI Governance Framework](https://dev.to/issdandavis/how-a-dnd-campaign-became-an-ai-governance-framework-5eln)
- **ORCID**: [0009-0002-3936-9369](https://orcid.org/0009-0002-3936-9369)

## Research

- [Hyperbolic Geometry for Exponential AI Safety Boundaries](https://github.com/issdandavis/SCBE-AETHERMOORE/wiki/Research:-Hyperbolic-Geometry-for-Exponential-AI-Safety-Boundaries)
- [Post-Quantum Cryptography for AI Governance Systems](https://github.com/issdandavis/SCBE-AETHERMOORE/wiki/Research:-Post%E2%80%90Quantum-Cryptography-for-AI-Governance-Systems)

## Citation

```bibtex
@software{davis2026geoseed,
  author = {Davis, Issac Daniel},
  title = {GeoSeed Network: 6-Seed Geometric Deep Learning for AI Governance},
  year = {2026},
  publisher = {HuggingFace},
  url = {https://huggingface.co/issdandavis/geoseed-network},
  note = {Patent Pending: USPTO #63/961,403}
}
```

## Author

**Issac Daniel Davis** -- [ORCID](https://orcid.org/0009-0002-3936-9369) | [GitHub](https://github.com/issdandavis) | Patent Pending: USPTO #63/961,403
"""

# ============================================================
# 4. scbe-ops-assets
# ============================================================
OPS_README = """---
license: apache-2.0
language:
- en
tags:
- scbe-aethermoore
- ai-safety
- governance
- workflow-automation
- n8n
- operations
- toolkit
- templates
- hydra
- devops
pipeline_tag: other
---

# SCBE Ops Assets: AI Governance Operations Toolkit

**Production-ready workflow templates, automation bundles, and operational assets for deploying the SCBE-AETHERMOORE AI safety governance framework. Everything you need to stand up governed AI operations from day one.**

[![GitHub](https://img.shields.io/badge/GitHub-SCBE--AETHERMOORE-181717?logo=github)](https://github.com/issdandavis/SCBE-AETHERMOORE)
[![npm](https://img.shields.io/npm/v/scbe-aethermoore?label=npm&logo=npm)](https://www.npmjs.com/package/scbe-aethermoore)
[![PyPI](https://img.shields.io/pypi/v/scbe-aethermoore?label=PyPI&logo=pypi)](https://pypi.org/project/scbe-aethermoore/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Patent](https://img.shields.io/badge/USPTO-63%2F961%2C403-green)](https://www.uspto.gov/)

## Overview

This repository contains the operational assets for [SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE), packaged as downloadable bundles for teams deploying AI governance in production. These are the same assets used to run the M5 Mesh Foundry -- a governance-aware data ingestion and intelligence operations product.

## Included Bundles

| Bundle | Description |
|--------|-------------|
| **AI Governance Toolkit** | Core governance pipeline configs, 14-layer security rules, trust-scoring thresholds, and risk decision templates (ALLOW/QUARANTINE/ESCALATE/DENY) |
| **Complete Ops Bundle** | Full operational deployment package including all other bundles plus Docker Compose, Hetzner VPS deploy scripts, and monitoring dashboards |
| **Content Spin Engine** | Multi-platform content publishing pipeline with governance gates, supporting X/Twitter, Dev.to, GitHub Discussions, YouTube, and more |
| **HYDRA Agent Templates** | Multi-agent orchestration templates for browser automation, swarm coordination, cross-terminal messaging, and fleet management |
| **n8n Workflow Pack** | 7 verified n8n workflows: Asana scheduler, game events, M5 data funnel, content publisher, web agent orchestrator, Vertex AI/HuggingFace pipeline, X growth ops |
| **Notion Workspace Template** | Pre-built Notion workspace with GeoSeed design pages, Sacred Eggs protocol documentation, governance rules, and model semantics |

## Quick Start

### Download a bundle

```python
from huggingface_hub import hf_hub_download

# Download the governance toolkit
path = hf_hub_download(
    repo_id="issdandavis/scbe-ops-assets",
    filename="artifacts/gumroad-zips/scbe-ai-governance-toolkit-v1.0.0.zip"
)
print(f"Downloaded to: {path}")
```

### Use with the SCBE framework

```bash
# Install the framework
pip install scbe-aethermoore

# Or via npm
npm install scbe-aethermoore
```

```python
# Start the governance API
# python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Start the n8n bridge
# python -m uvicorn workflows.n8n.scbe_n8n_bridge:app --port 8001
```

### Deploy with Docker

```bash
# Build and run the full stack
npm run docker:build && npm run docker:run
# Exposes ports 8080 (API) + 3000 (dashboard)
```

## File Listing

```
artifacts/gumroad-zips/
  scbe-ai-governance-toolkit-v1.0.0.zip
  scbe-complete-ops-bundle-v1.0.0.zip
  scbe-content-spin-engine-v1.0.0.zip
  scbe-hydra-agent-templates-v1.0.0.zip
  scbe-n8n-workflow-pack-v1.0.0.zip
  scbe-notion-workspace-template-v1.0.0.zip
```

## What is SCBE-AETHERMOORE?

SCBE-AETHERMOORE is an AI safety and governance framework that uses hyperbolic geometry (Poincare ball model) to make adversarial behavior exponentially expensive. It implements a 14-layer security pipeline with post-quantum cryptography (ML-KEM-768, ML-DSA-65).

The framework was born from an unlikely origin: 12,596+ paragraphs of AI-driven RPG gameplay in [Everweave](https://everweave.ai), expanded into [a novel](https://www.amazon.com/dp/B0GSSFQD9G), and formalized into a governance system. Read the full story on [Dev.to](https://dev.to/issdandavis/how-a-dnd-campaign-became-an-ai-governance-framework-5eln).

## Related Models

| Model | Purpose |
|-------|---------|
| [phdm-21d-embedding](https://huggingface.co/issdandavis/phdm-21d-embedding) | 21D Poincare ball embedding for trust scoring |
| [spiralverse-ai-federated-v1](https://huggingface.co/issdandavis/spiralverse-ai-federated-v1) | Federated learning for swarm coordination |
| [geoseed-network](https://huggingface.co/issdandavis/geoseed-network) | 6-seed geometric deep learning |

## Related Datasets

| Dataset | Description |
|---------|-------------|
| [scbe-aethermoore-training-data](https://huggingface.co/datasets/issdandavis/scbe-aethermoore-training-data) | 14,654 supervised fine-tuning pairs |
| [scbe-aethermoore-knowledge-base](https://huggingface.co/datasets/issdandavis/scbe-aethermoore-knowledge-base) | Technical documentation and governance specs |

## Links

- **Book**: [The Spiralverse on Amazon](https://www.amazon.com/dp/B0GSSFQD9G) -- The novel that started it all
- **Website**: [aethermoorgames.com](https://aethermoorgames.com)
- **GitHub**: [SCBE-AETHERMOORE](https://github.com/issdandavis/SCBE-AETHERMOORE) -- Full framework source
- **npm**: [scbe-aethermoore](https://www.npmjs.com/package/scbe-aethermoore)
- **PyPI**: [scbe-aethermoore](https://pypi.org/project/scbe-aethermoore/)
- **Dev.to**: [How a DnD Campaign Became an AI Governance Framework](https://dev.to/issdandavis/how-a-dnd-campaign-became-an-ai-governance-framework-5eln)
- **Shopify**: [Aethermoore Works](https://aethermore-works.myshopify.com) -- Digital products and bundles
- **ORCID**: [0009-0002-3936-9369](https://orcid.org/0009-0002-3936-9369)

## Author

**Issac Daniel Davis** -- [ORCID](https://orcid.org/0009-0002-3936-9369) | [GitHub](https://github.com/issdandavis) | Patent Pending: USPTO #63/961,403
"""

# ============================================================
# Upload all 4
# ============================================================
models_and_readmes = [
    ("issdandavis/phdm-21d-embedding", PHDM_README, "Update"),
    ("issdandavis/spiralverse-ai-federated-v1", SPIRALVERSE_README, "Update"),
    ("issdandavis/geoseed-network", GEOSEED_README, "Update"),
    ("issdandavis/scbe-ops-assets", OPS_README, "Add"),
]

for repo_id, readme_content, verb in models_and_readmes:
    print(f"Uploading {repo_id} README.md...")
    try:
        api.upload_file(
            path_or_fileobj=readme_content.encode("utf-8"),
            path_in_repo="README.md",
            repo_id=repo_id,
            commit_message=f"{verb} model card: professional description, links, usage examples, and discoverability tags",
        )
        print(f"  SUCCESS: {repo_id}")
    except Exception as e:
        print(f"  ERROR: {repo_id} -- {e}")

print("\nDone! All 4 model cards processed.")
