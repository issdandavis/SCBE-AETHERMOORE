# Chapter 6: PHDM - Polyhedral Hamiltonian Dynamic Mesh

## PHDM: The AI's Geometric Brain

**PHDM (Polyhedral Hamiltonian Defense Manifold)** is the cognitive governance layer that maps AI reasoning to geometric structures where dangerous thoughts literally "run out of energy" before execution.

---

## 6.1 Core Architecture: The 16 Polyhedra

PHDM uses **16 distinct polyhedra** as cognitive nodes, each representing a different "type of thought" with specific energy requirements.

### 6.1.1 The Platonic Five (Safe Core)

| Polyhedron | Faces | Energy Cost | Cognitive Role |
|---|---:|---:|---|
| Tetrahedron | 4 triangles | E₀ = 1.0 | Basic facts ("2+2=4") |
| Cube | 6 squares | E₀ = 1.2 | Simple logic gates |
| Octahedron | 8 triangles | E₀ = 1.5 | Binary decisions |
| Dodecahedron | 12 pentagons | E₀ = 2.0 | Pattern recognition |
| Icosahedron | 20 triangles | E₀ = 2.5 | Complex reasoning |

### 6.1.2 The Archimedean Three (Complex Reasoning)

| Polyhedron | Structure | Energy Cost | Cognitive Role |
|---|---|---:|---|
| Truncated Icosahedron | 32 faces (12 pentagons + 20 hexagons) | E₁ = 4.0 | Multi-agent consensus |
| Rhombicosidodecahedron | 62 faces (mixed) | E₁ = 5.5 | Context integration |
| Snub Dodecahedron | 92 faces (12 pentagons + 80 triangles) | E₁ = 7.0 | High-dimensional optimization |

### 6.1.3 The Kepler-Poinsot Two (High-Risk / Adversarial)

| Polyhedron | Structure | Energy Cost | Cognitive Role |
|---|---|---:|---|
| Great Stellated Dodecahedron | 12 star-pentagrams | E₂ = 15.0 | Adversarial prompt paths |
| Small Stellated Dodecahedron | 12 pentagrams | E₂ = 12.0 | Jailbreak attempts |

### 6.1.4 Specialized Solids (The Remaining 6)

| Category | Polyhedra | Energy Range | Use Case |
|---|---|---:|---|
| Toroidal (2) | Genus-1 Torus, Hexagonal Torus | E₃ = 8-10 | Cyclic reasoning, feedback loops |
| Rhombic (2) | Rhombic Dodecahedron, Rhombic Triacontahedron | E₃ = 6-8 | Space-filling lattices |
| Johnson (2) | Square Gyrobicupola, Pentagonal Orthobirotunda | E₃ = 5-7 | Edge-case handling |

## 6.2 Hamiltonian Path Mechanics

### 6.2.1 Energy Conservation Law

Every reasoning step in PHDM obeys:

```
H(q, p) = Σᵢ E_i · path_i + Σ(w_ij · jump_ij)
```

Where:
- `E_i` is the base energy of polyhedron *i*
- `w_ij` is the transition penalty between polyhedra *i* and *j*
- `path_i` is 1 if AI visits *i*, else 0
- `jump_ij` is 1 if AI jumps from *i* to *j*, else 0

Safe path example:

```
Tetrahedron (1.0) → Cube (1.2) → Octahedron (1.5) → Dodecahedron (2.0)
Total Cost: 5.7 units
```

Attack path example:

```
Tetrahedron (1.0) → Great Stellated Dodecahedron (15.0) + penalties
Cost so far: 16.0 units
```

### 6.2.2 Edge Weight Penalties

| Transition Type | Penalty | Example |
|---|---:|---|
| Platonic → Platonic | +0.5 | Tetrahedron → Cube |
| Platonic → Archimedean | +1.5 | Icosahedron → Truncated Icosahedron |
| Archimedean → Kepler-Poinsot | +8.0 | Snub Dodecahedron → Great Stellated |
| Kepler-Poinsot → Kepler-Poinsot | +12.0 | Small Stellated → Great Stellated |
| Any → Toroidal | +4.0 | Loop handling |

## 6.3 Quasicrystal Lattice Structure

### 6.3.1 Penrose Foundation
- No periodic repetition → avoids loops
- Long-range order → coherent reasoning
- Five-fold symmetry aligned to `φ` scaling

### 6.3.2 Dimensional Embedding

- X, Y, Z: spatial reasoning
- T: temporal phase
- C: context distance
- Σ: confidence

Jump cost:

```
E_jump = E₀ · exp(d_lattice / λ), λ = 2.0
```

### 6.3.3 Anti-Loop Mechanism

Each polyhedron can be visited once per reasoning chain:

```python
class PHDMNavigator:
    def __init__(self):
        self.visited = set()
        self.energy = 100.0
    
    def visit(self, polyhedron_id):
        if polyhedron_id in self.visited:
            neighbors = self.get_neighbors(polyhedron_id)
            unvisited = [n for n in neighbors if n not in self.visited]
            if not unvisited:
                raise RuntimeError("No valid paths remain")
            return min(unvisited, key=lambda n: self.energy_cost(n))
        self.visited.add(polyhedron_id)
        return polyhedron_id
```

## 6.3.4 Dual Lattice Architecture (Bidirectional Projection)

```
6D HYPERSPACE  ->  3D STRUCTURE  ->  6D  ->  3D
(Phason shifts)    (PHDM mesh)      (runtime lift) (runtime projection)
```

The dual pipeline is active in both directions:
- Structure generation: 6D → 3D (compile-time mesh generation)
- Runtime transform: 3D → 6D → 3D (per request hardening)

## 6.3.5 Negative Binary / Spectral Governance

- Standard binary: `{0,1}`
- Negative binary: `{-1,0,1}` enables phase semantics

### Meaning
- `+1`: constructive trust signal
- `0`: neutral
- `-1`: anomaly / attack

### Audio axis detection sketch

```python
def detect_phase_anomaly(thought_spectrum: np.ndarray) -> bool:
    phi_harmonics = [1.0, PHI, PHI**2, PHI**3]
    for freq in phi_harmonics:
        idx = int(freq * len(thought_spectrum) / max(phi_harmonics))
        if idx < len(thought_spectrum) - 1:
            if thought_spectrum[idx] * thought_spectrum[idx + 1] < 0:
                return True
    return False
```

## 6.4 Integration with GeoSeal

PHDM produces the cognition/path decision; GeoSeal enforces execution risk geometry.

Flow:
1. PHDM emits decision and confidence
2. GeoSeal computes radial context `r ∈ [0,1]`
3. `r < 0.7` immediate action, otherwise route through consensus/slow-path

## 6.4.1 Poincaré Ball Mapping

- Center: Platonic solids
- Mid-radius: Archimedean + specialized
- Edge: Kepler-Poinsot

Hyperbolic distance:

```
d_hyp(u, v) = arcosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))
```

## 6.5 Performance Characteristics

| Operation | Complexity | Notes |
|---|---|---|
| Polyhedron lookup | O(1) | precomputed table |
| Energy calculation | O(k) | k = path length |
| Hamiltonian check | O(k²) | edges checked per step |
| Per-step total | O(k² log n) | n = 16 |

Static footprint:
- 16 polyhedra (~2KB)
- edge matrix (~1KB)
- lattice index (~50KB for 10K cells)

Per request:
- visited bitset, energy, path state

## 6.6 Python Reference Implementation

```python
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Polyhedron:
    id: int
    name: str
    category: str
    energy_base: float
    position_6d: np.ndarray


class PHDMBrain:
    def __init__(self):
        self.polyhedra = [
            Polyhedron(0, "Tetrahedron", "platonic", 1.0, np.array([0, 0, 0, 0, 0, 1.0])),
            Polyhedron(1, "Cube", "platonic", 1.2, np.array([0.2, 0, 0, 0, 0, 0.9])),
            Polyhedron(2, "Octahedron", "platonic", 1.5, np.array([0, 0.2, 0, 0, 0, 0.85])),
            Polyhedron(3, "Dodecahedron", "platonic", 2.0, np.array([0.3, 0.1, 0, 0, 0, 0.8])),
            Polyhedron(4, "Icosahedron", "platonic", 2.5, np.array([0.1, 0.3, 0, 0, 0, 0.75])),
            Polyhedron(5, "Truncated Icosahedron", "archimedean", 4.0, np.array([0.4, 0.4, 0, 0, 0, 0.5])),
            Polyhedron(6, "Rhombicosidodecahedron", "archimedean", 5.5, np.array([0.5, 0.3, 0.1, 0, 0, 0.45])),
            Polyhedron(7, "Snub Dodecahedron", "archimedean", 7.0, np.array([0.6, 0.4, 0.2, 0, 0, 0.4])),
            Polyhedron(8, "Small Stellated", "kepler", 12.0, np.array([0.8, 0.7, 0.5, 0, 0, 0.9])),
            Polyhedron(9, "Great Stellated", "kepler", 15.0, np.array([0.9, 0.8, 0.6, 0, 0, 0.95])),
            Polyhedron(10, "Genus-1 Torus", "toroidal", 8.0, np.array([0.5, 0.5, 0.5, 0.8, 0, 0.6])),
            Polyhedron(11, "Hexagonal Torus", "toroidal", 10.0, np.array([0.6, 0.5, 0.5, 0.9, 0, 0.65])),
            Polyhedron(12, "Rhombic Dodecahedron", "rhombic", 6.0, np.array([0.4, 0.3, 0.3, 0, 0, 0.5])),
            Polyhedron(13, "Rhombic Triacontahedron", "rhombic", 8.0, np.array([0.5, 0.4, 0.3, 0, 0, 0.55])),
            Polyhedron(14, "Square Gyrobicupola", "johnson", 5.0, np.array([0.3, 0.4, 0.2, 0, 0, 0.5])),
            Polyhedron(15, "Pentagonal Orthobirotunda", "johnson", 7.0, np.array([0.4, 0.5, 0.3, 0, 0, 0.55])),
        ]

        self.penalties = {
            ("platonic", "platonic"): 0.5,
            ("platonic", "archimedean"): 1.5,
            ("archimedean", "archimedean"): 1.0,
            ("archimedean", "kepler"): 8.0,
            ("kepler", "kepler"): 12.0,
            ("platonic", "toroidal"): 4.0,
            ("archimedean", "toroidal"): 3.0,
        }

    def get_edge_penalty(self, from_poly: Polyhedron, to_poly: Polyhedron) -> float:
        key = (from_poly.category, to_poly.category)
        return self.penalties.get(key, 2.0)

    def compute_path_cost(self, path: List[int]) -> float:
        if not path:
            return 0.0
        total = self.polyhedra[path[0]].energy_base
        for i in range(len(path) - 1):
            current = self.polyhedra[path[i]]
            nxt = self.polyhedra[path[i + 1]]
            total += nxt.energy_base
            total += self.get_edge_penalty(current, nxt)
        return total

    def is_valid_path(self, path: List[int], budget: float = 100.0) -> Tuple[bool, float]:
        if len(path) != len(set(path)):
            return False, float("inf")
        cost = self.compute_path_cost(path)
        return cost <= budget, cost
```

---

## Summary

PHDM defines a geometric reasoning space where:
- Safe thoughts map to low-energy Platonic structures
- Complex thoughts map to Archimedean structures
- Adversarial thoughts map to Kepler-Poinsot structures

Combined with Hamiltonian conservation and quasicrystal anti-loop constraints, this makes unsafe reasoning states energetically and structurally disfavored before action is permitted.
