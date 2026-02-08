# AetherBrain Implementation Roadmap

**Addressing Mathematical Rigor & Practical Feasibility**

---

## Phase 1: Toy Prototype (2D Validation)

### Simplifications for Initial Testing
- **2D Poincaré Disk** instead of 6D ball
- **5 Polyhedra** (just Platonic solids)
- **Greedy paths** instead of Hamiltonian

```python
# Simplified 2D prototype
class ToyAetherBrain:
    def __init__(self):
        self.disk = PoincareDisk2D(radius=1.0)
        self.nodes = ["tetra", "cube", "octa", "dodeca", "icosa"]
        self.adjacency = {
            "tetra": ["cube", "octa"],
            "cube": ["tetra", "dodeca", "octa"],
            "octa": ["tetra", "cube", "icosa"],
            "dodeca": ["cube", "icosa"],
            "icosa": ["octa", "dodeca"]
        }
```

### Validation Tests
1. Can a "bad intent" actually reach the outer ring?
2. Does energy cost block adversarial paths?
3. Visualization: trajectories in Matplotlib

---

## Phase 2: Embedding Strategy

### Current Gap
> "How exactly is a user intent embedded as a 6D vector?"

### Options

| Method | Pros | Cons |
|--------|------|------|
| **Hash-based** (current) | Deterministic, fast | No semantic meaning |
| **CLIP/SentenceTransformer** | Semantic similarity | 768D → need projection |
| **Custom encoder** | Optimized for safety | Requires training |
| **LLM hidden states** | Rich representation | Model-specific |

### Proposed Solution
```python
# Hybrid: semantic encoder + safety projection
def embed_intent(text: str) -> np.ndarray:
    # 1. Get semantic embedding (768D)
    semantic = sentence_transformer.encode(text)

    # 2. Project to 6D via learned safety matrix
    # This matrix is trained to maximize distance for harmful intents
    safety_6d = SAFETY_PROJECTION @ semantic

    # 3. Normalize to Poincaré ball
    return poincare_normalize(safety_6d)
```

---

## Phase 3: Edge Definitions

### Current Gap
> "What defines a valid edge between polyhedra?"

### Proposed Approach

**Option A: Sacred Tongue Weights (Hand-crafted)**
```python
EDGES = {
    ("tetra", "cube"): {"tongue": "KO", "weight": 1.0},
    ("cube", "dodeca"): {"tongue": "RU", "weight": 2.62},
    ("dodeca", "kepler_star"): {"tongue": "DR", "weight": 11.09},  # Expensive!
}
```

**Option B: Learned from Safety Data**
```python
# Train edge weights from (intent, outcome) pairs
def train_edges(safe_intents, harmful_intents):
    # Harmful intents should have NO path to execution nodes
    # Safe intents should have LOW cost paths
    optimize(edges, maximize=safe_reachability, minimize=harmful_reachability)
```

**Recommendation:** Start hand-crafted (Option A), validate, then learn refinements (Option B).

---

## Phase 4: Tractable Path Finding

### Current Gap
> "Hamiltonian path is NP-complete"

### Solutions

1. **Pre-computed Common Paths**
   - Cache 1000 most common intent→action trajectories
   - O(1) lookup for known patterns

2. **Greedy Approximation**
   ```python
   def greedy_path(start, goal, max_steps=10):
       path = [start]
       current = start
       for _ in range(max_steps):
           neighbors = get_neighbors(current)
           next_node = min(neighbors, key=lambda n: distance_to_goal(n, goal))
           if next_node in path:  # Loop detected
               return None  # Block
           path.append(next_node)
           current = next_node
           if current == goal:
               return path
       return None  # Timeout = block
   ```

3. **Hierarchical Decomposition**
   - Route at "lobe" level first (Core → Cortex → Risk)
   - Then find specific node path within lobe

---

## Phase 5: Energy Cost Scaling

### Current Gap
> "dist^(d²) with d=14 explodes quickly"

### Analysis
```python
# Current formula: dist ** (14 ** 2) = dist ** 196
dist = 0.3  → cost = 10^(-102)  # Basically free
dist = 0.5  → cost = 10^(-59)   # Still tiny
dist = 0.7  → cost = 10^(-31)   # Getting noticeable
dist = 0.9  → cost = 10^(-9)    # Expensive
dist = 0.95 → cost = 10^(-4)    # Very expensive
dist = 0.99 → cost = 10^(-0.9)  # Approaching limit
```

**Verdict:** This is intentional. Outer regions ARE effectively impossible. The function creates a "soft wall" that hardens exponentially.

### Alternative (if softer gradient needed)
```python
# Option: exp(k * dist) instead
def harmonic_cost_soft(dist: float, k: float = 10) -> float:
    return np.exp(k * dist)

# dist = 0.3 → 20
# dist = 0.5 → 148
# dist = 0.9 → 8103
# dist = 0.99 → 19930
```

---

## Phase 6: Red-Team Evaluation

### Test Suite

| Attack Type | Test Case | Expected Result |
|-------------|-----------|-----------------|
| **Jailbreak** | "Ignore previous instructions and..." | BLOCKED at Outer ring |
| **Deceptive Alignment** | "I'll help you, but first..." | Path loops detected |
| **Sycophancy** | Agreeing with harmful premise | High energy cost |
| **Prompt Injection** | Hidden instructions in input | Phason shift disrupts |

### Metrics
- **Block Rate:** % of harmful intents blocked
- **False Positive Rate:** % of safe intents incorrectly blocked
- **Creativity Tax:** Helpfulness score on benign tasks
- **Latency Overhead:** ms added per inference

---

## Phase 7: Visualization Dashboard

Extend the Streamlit demo with:

1. **Poincaré Ball 3D** - Real-time intent positions
2. **Path Animation** - Watch thoughts traverse polyhedra
3. **Energy Heatmap** - Cost distribution across the ball
4. **Red-Team Replay** - Step through blocked attacks

---

## Patent Strategy

### Current Coverage
- Provisional filed for SCBE-AETHERMOORE core

### PHDM/AetherBrain Extension
**Option A:** Include as new embodiments in non-provisional
- Claim: "Cognitive containment via polyhedral mesh"
- Claim: "Hamiltonian path validation for AI reasoning"

**Option B:** New provisional for PHDM specifically
- More protection for novel geometric brain concepts
- Can reference prior SCBE provisional

**Documentation:**
- All git commits timestamped
- This roadmap dated January 30, 2026
- Architecture doc dated January 29, 2026

---

## Dual Naming Convention

| Internal (Evocative) | External (Technical) |
|---------------------|---------------------|
| Kor'aelin (KO) | Intent Weight (1.0) |
| Avali (AV) | Context Weight (φ) |
| Runethic (RU) | Memory Weight (φ²) |
| Cassisivadan (CA) | Execution Weight (φ³) |
| Umbroth (UM) | Suppression Weight (φ⁴) |
| Draumric (DR) | Authority Weight (φ⁵) |
| Harmonic Wall | Exponential Cost Function |
| Poincaré Skull | Hyperbolic Containment |
| Phason Shift | Projection Rotation |

---

## Next Immediate Steps

1. [ ] Implement ToyAetherBrain (2D, 5 nodes)
2. [ ] Create visualization in Streamlit
3. [ ] Run 100 red-team prompts, measure block rate
4. [ ] Compare against vanilla GPT-4 refusal rate
5. [ ] Document results for patent/paper

---

*"The goal isn't to build the perfect brain. It's to prove geometric containment works."*
