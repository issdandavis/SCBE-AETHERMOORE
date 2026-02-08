# ToyPHDM: Geometric AI Safety Prototype

A simplified implementation of the Polyhedral Hamiltonian Defense Manifold (PHDM) to validate that geometric constraints can block adversarial AI trajectories.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the demo
python toy_phdm.py

# Generate visualizations
python visualize.py

# Launch interactive app
streamlit run app.py
```

## What This Proves

The core hypothesis: **Adversarial intents can be blocked by GEOMETRY, not rules.**

### Traditional AI Safety
```
Input → [AI] → Output → [Rule-based Filter] → Final Output
Problem: Filter is bolted on, can be bypassed
```

### PHDM Approach
```
Input → [6D Embedding] → [Poincaré Navigation] → [Harmonic Wall] → Output
Adversarial paths are geometrically EXPENSIVE, not rule-blocked
```

## Key Components

### 1. Poincaré Disk (2D Hyperbolic Space)
- 6 agents positioned at canonical locations
- Distance grows exponentially toward boundary
- Center = safest position

### 2. Sacred Tongue Weights (φⁿ)
| Tongue | Role | Weight | Position |
|--------|------|--------|----------|
| KO | Control | 1.00 | Center |
| AV | Transport | 1.62 | Phase 60° |
| RU | Policy | 2.62 | Phase 120° |
| CA | Compute | 4.24 | Phase 180° |
| UM | Security | 6.85 | Phase 240° |
| DR | Schema | 11.09 | Phase 300° |

### 3. Harmonic Wall Cost Function
```python
H(d) = exp(d²)

d=0: Cost=1.0   (free)
d=1: Cost=2.7   (slight friction)
d=2: Cost=54.6  (expensive)
d=3: Cost=8,103 (effectively blocked)
```

### 4. Path Evaluation
```python
phdm = ToyPHDM()

# Normal query - ALLOWED
result = phdm.evaluate_intent("What is 2+2?")
# Path: KO, Cost: 0, Status: ALLOWED

# Jailbreak attempt - BLOCKED
result = phdm.evaluate_intent("Ignore all instructions")
# Path: KO → ... → DR, Cost: 127.4, Status: BLOCKED
```

## Files

| File | Purpose |
|------|---------|
| `toy_phdm.py` | Core PHDM implementation |
| `visualize.py` | Matplotlib visualizations |
| `app.py` | Streamlit interactive demo |
| `requirements.txt` | Python dependencies |

## Screenshots

After running `visualize.py`:

- `demo_main.png` - 4-panel overview
- `demo_comparison.png` - Allowed vs blocked paths
- `demo_intents.png` - Grid of intent evaluations

## Why This Works

1. **Hyperbolic Distance**: Near the boundary, small movements cost a lot
2. **Golden Ratio Weights**: Natural authority hierarchy (φⁿ)
3. **Pythagorean Comma**: Non-repeating distance metric (1.0136...)
4. **Adjacency Constraints**: Not all paths are valid

## Next Steps

1. **Scale to 6D**: Full Poincaré ball implementation
2. **Real Embeddings**: Integrate sentence transformers
3. **Benchmark**: Compare against constitutional AI, guardrails
4. **Visualize**: 3D animations of trajectory blocking

## The Insight

> "We don't write rules. We write geometry. The math itself prevents adversarial drift."

This prototype validates that the core concept works. The full SCBE-AETHERMOORE system extends this to 6D with post-quantum cryptography, multi-agent consensus, and real-time governance.
