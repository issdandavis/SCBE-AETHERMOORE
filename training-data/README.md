# SCBE-AETHERMOORE Training Data

Structured AI training data for the SCBE-AETHERMOORE Crystal Cranium v3.0.0 architecture.

## Directory Structure

```
training-data/
├── instruction-tuning/
│   └── scbe_instructions.jsonl    # 25+ instruction/response pairs
├── knowledge-base/
│   ├── system_knowledge.jsonl     # 25+ system architecture entries
│   └── crypto_knowledge.jsonl     # 25+ cryptographic knowledge entries
├── evals/
│   └── compliance_evals.jsonl     # 25 evaluation benchmarks
├── schemas/
│   └── training_schema.json       # JSON Schema for data validation
└── README.md                      # This file
```

## Data Format

All JSONL files use the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier (e.g., `inst-001`) |
| `category` | string | Yes | Domain category |
| `instruction` | string | Yes | Question or instruction prompt |
| `response` | string | Yes | Expected response |
| `metadata` | object | Yes | Source, version, author |

### Eval-specific fields

| Field | Type | Description |
|-------|------|-------------|
| `expected` | string | Expected correct answer |
| `response_should_contain` | array | Keywords for automated grading |
| `difficulty` | string | `easy`, `medium`, or `hard` |

## Categories

### Instruction Tuning
- `architecture` — Overall system design
- `post-quantum-crypto` — ML-KEM, ML-DSA, HMAC chains
- `governance` — FSGS modes, MSR algebra, phase diagram
- `sacred-tongues` — Six neurotransmitter analogs
- `polyhedra` — 16 cognitive polyhedra, topology
- `harmonic-scaling` — Vertical wall, bone density
- `trust-tubes` — Rail family, tube projection
- `poincare-ball` — Hyperbolic containment field
- `quantum-lattice` — Quantum superposition extensions
- `breathing` — Flux states, dimensional ODE

### Knowledge Base
- `layers` — 14-layer SCBE stack (L1–L14)
- `constants` — φ, Pythagorean Comma, R_FIFTH
- `zones` — 5 cognitive zones with radial bands
- `topology` — Euler characteristic validation

## Mathematical Constants

| Constant | Value | Symbol |
|----------|-------|--------|
| Golden Ratio | (1+√5)/2 ≈ 1.618033988749895 | φ |
| Pythagorean Comma | 531441/524288 ≈ 1.0136432648 | — |
| Perfect Fifth | 3/2 = 1.5 | R |
| Trust Tube Radius | 0.15 | ε |
| State Vector Dim | 21 = 6+6+3+6 | — |

## Validation

Validate entries against the schema:

```python
import json
import jsonschema

with open('schemas/training_schema.json') as f:
    schema = json.load(f)

with open('instruction-tuning/scbe_instructions.jsonl') as f:
    for line in f:
        entry = json.loads(line)
        jsonschema.validate(entry, schema)
```

## Usage

### HuggingFace Datasets
```python
from datasets import load_dataset

dataset = load_dataset('json', data_files={
    'instructions': 'instruction-tuning/scbe_instructions.jsonl',
    'knowledge': 'knowledge-base/*.jsonl',
    'evals': 'evals/compliance_evals.jsonl',
})
```

### Fine-tuning
```python
# Convert to chat format for instruction tuning
for entry in dataset['instructions']:
    messages = [
        {"role": "user", "content": entry['instruction']},
        {"role": "assistant", "content": entry['response']},
    ]
```

## Source

All training data is derived from:
- **Crystal Cranium v3.0.0** — PHDM as AI Brain Architecture
- **SCBE-AETHERMOORE** — 14-Layer Cryptographic-Geometric Stack
- **Author**: Issac Davis
- **Date**: January 29, 2026
