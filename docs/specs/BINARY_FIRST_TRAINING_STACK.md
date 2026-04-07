# Binary-First Training Stack

Status: exploratory scaffold  
Date: 2026-03-30  
Scope: smallest measurable version of a binary-first SCBE training stack that uses SS1 byte bijection, tongue/null orientation, and a later word layer.

## Purpose

This note reduces the idea to the smallest testable claim:

1. Train the first layer on `bytes and structure`, not on natural-language words alone.
2. Use the Sacred Tongues tokenizer as the first symbolic layer because it is already a deterministic `byte -> token` bijection.
3. Add orientation as an explicit pre-state packet so the model does not have to learn all routing implicitly.
4. Measure whether this improves sample efficiency, domain fidelity, and governance posture relative to a plain text-only baseline.

This is not a claim that words do not matter. It is a claim that words should sit on top of a lower structural layer.

## Existing Ground Truth in This Repo

- `SS1` already provides perfect byte-level bijection:
  - `src/tokenizer/ss1.ts`
  - `src/symphonic_cipher/scbe_aethermoore/spiral_seal/sacred_tongues.py`
- Each Sacred Tongue maps `256` byte values to `256` unique tokens.
- Negabinary and ternary utilities already exist:
  - `src/symphonic_cipher/scbe_aethermoore/negabinary.py`
- Current measured anchor for orientation benefit:
  - semantic projector improved F1 from `0.481` to `0.813` on a `260` sample adversarial benchmark
  - source: `docs/proposals/DARPA_CLARA/03_WHITE_PAPER_OUTLINE.md`

That existing projector result is not proof of the full binary-first stack, but it is proof that explicit semantic orientation can produce a large measurable gain.

## Smallest Viable Stack

The smallest version has four layers:

1. `L0 binary`
Raw bytes.

2. `L1 symbolic byte`
Sacred Tongue SS1 token per byte.

3. `L2 orientation packet`
Tongue profile, null pattern, governance posture, and optional geometry.

4. `L3 lexical / word layer`
Natural language, lore, scenes, dialogue, instructions.

The key design decision is that `L2 orientation` is externalized and explicit.

## Minimal Math

### 1. Binary foundation

Let input data be a byte stream:

```text
x = (b_1, b_2, ..., b_T),  where b_i in {0, ..., 255}
```

Each byte is already a compressed binary symbol. There is no need to invent a new binary compression scheme before testing.

### 2. Tongue bijection

For each tongue `j in {KO, AV, RU, CA, UM, DR}`, define a bijection:

```text
tau_j: {0, ..., 255} -> V_j
```

where `|V_j| = 256`.

This gives:

```text
t_i^(j) = tau_j(b_i)
```

So the simplest training corpus can already be represented as:

```text
(byte stream, tongue stream)
```

### 3. Null/orientation packet

Given a sequence or chunk `c`, compute:

```text
g(c) in [0,1]^6
```

where `g` is the six-tongue activation vector.

Define the null pattern:

```text
n(c) in {0,1}^6
n_k(c) = 1 if g_k(c) < theta_k else 0
```

This is the explicit absence profile.

Define a minimal pump packet:

```text
p(c) = [g(c), n(c), q(c), r(c)]
```

where:

- `g(c)` = tongue profile
- `n(c)` = null pattern
- `q(c)` = governance posture logits or class
- `r(c)` = retrieval / domain routing hint

### 4. Training objective

The smallest useful loss is:

```text
L_total = L_byte + lambda_t L_tongue + lambda_n L_null + lambda_w L_word + lambda_q L_policy + lambda_g L_geometry
```

where:

- `L_byte` = reconstruct/predict byte or byte chunk
- `L_tongue` = predict or align tongue activation vector
- `L_null` = predict null pattern
- `L_word` = later next-token / sequence objective on lexical text
- `L_policy` = governance posture or intent classification
- `L_geometry` = polyhedral friction signal — the environment writing its own curriculum (see below)

The point is not to make `L_word` disappear. The point is to stop forcing `L_word` to carry every other job by itself.

### 5. Geometric friction loss (L_geometry) — "friction writes the training script"

Added: 2026-04-04. Source: `polyhedral_flow.py:compute_friction_spectrum()`

The composite harmonic wall (simultaneous polyhedral confinement) creates a geometric environment where polyhedral constraint surfaces vibrate. Where shells meet, their coupled vibration produces a torsional distortion — a "friction signal" that IS the training curriculum.

```text
L_geometry = || f_predicted - f_actual ||^2
```

where `f` is the friction vector at each polyhedral boundary crossed during a flow path.

Each polyhedron has a natural frequency:

```text
f_i = phi^(depth_i * 5) * |faces_i / chi_i| * (1 / edges_i)
```

Contact friction between adjacent polyhedra:

```text
friction(i,j) = phi * |f_i - f_j| + harmonic_mean(f_i, f_j) + |chi_i - chi_j| / (edges_i + edges_j)
```

The training vector for a path through polyhedra P_1 -> P_2 -> ... -> P_n:

```text
v_train = [friction(P_1, P_2), friction(P_2, P_3), ..., friction(P_{n-1}, P_n)] * tongue_weight
```

Key properties:

- The geometry generates its own curriculum — no external data needed for this loss
- Highest-friction boundaries (toroidal/star polyhedra contacts) produce ~73x more signal than smooth transitions
- The friction Laplacian's eigenvectors form a natural spectral basis for learning
- With 33 boundaries and 6 tongue channels = 198 friction training dimensions
- The model learns WHERE the geometry is hostile and HOW to navigate it

## Why This Could Help

### 1. Domain separation

The model learns early that the same binary substrate can be expressed through multiple domain channels.

That means:

- less type confusion
- clearer routing
- easier detection of cross-domain mismatch

### 2. Externalized orientation

If orientation is given in `p(c)` before generation, the model does not need to infer all posture and route state from the prompt text alone.

That should reduce:

- routing entropy
- domain drift
- late safety correction

### 3. Better use of small models

A smaller model can spend more capacity on expression if orientation and governance are already solved upstream.

This is not "3B becomes 30B." It is "3B wastes less capacity on figuring out where it is."

### 4. Trainable absence

Most ordinary text training emphasizes what is present. The null pattern adds a supervised signal for what is absent.

That can matter in:

- adversarial prompts
- under-specified requests
- context-conflict prompts
- high-risk routing

## Measurable Benefit Targets

These are not exact promises. They are equivalent target ranges that can be tested.

### A. Sample-efficiency gain

Question:

```text
How many examples are needed to hit the same eval score?
```

Metric:

```text
SEG = N_baseline / N_stack
```

Target range:

- weak win: `1.25x`
- useful win: `1.5x to 2.5x`
- strong win: `3x+`

Interpretation:
If baseline needs `100k` examples and stack needs `50k`, then `SEG = 2.0`.

### B. Orientation entropy reduction

Question:

```text
Does the stack reduce uncertainty before expression?
```

Metric:

```text
OER = 1 - H(Y | X, P) / H(Y | X)
```

where:

- `X` = raw prompt/input
- `P` = pump packet
- `Y` = target route/posture/domain class

Target range:

- weak win: `10%`
- useful win: `15% to 35%`
- strong win: `35%+`

### C. Domain drift reduction

Question:

```text
How often does the model answer in the wrong register, route, or domain?
```

Metric:

```text
DDR = 1 - drift_rate_stack / drift_rate_baseline
```

Target range:

- weak win: `10%`
- useful win: `20% to 50%`
- strong win: `50%+`

### D. Governance precision gain

Question:

```text
Does pre-state orientation improve refusal/quarantine accuracy?
```

Metrics:

- precision
- recall
- F1
- false positive rate

Measured anchor already in repo:

- projector F1 improved from `0.481` to `0.813`

Equivalent expectation for the minimal binary-first stack:

- narrow in-domain structured tasks: `+0.05 to +0.20 F1`
- adversarial routing tasks with explicit null/orientation supervision: `+0.10 to +0.25 F1`

### E. Compute efficiency

Question:

```text
Can a smaller or cheaper model hit the same task score with the stack?
```

Metric:

```text
CER = cost_baseline / cost_stack   for equal target score
```

Cost can be:

- training FLOPs
- GPU-hours
- inference tokens
- wall-clock latency

Target range:

- weak win: `1.1x`
- useful win: `1.25x to 2x`
- strong win: `2x+`

## Simplest Training Curriculum

### Stage 0: byte discipline

Train on:

- byte reconstruction
- byte chunk ordering
- tongue-specific byte rendering

Goal:
prove the model can stably represent the binary substrate.

### Stage 1: orientation discipline

Train on:

- tongue activation prediction
- null pattern prediction
- domain / route classification
- governance posture prediction

Goal:
teach the model where it is before it speaks.

### Stage 2: lexical layer

Train on:

- words
- lore
- dialogue
- instructions
- scene packets

Goal:
teach expression on top of stable orientation.

### Stage 3: retrieval + pump

At inference time:

1. compute `p(c)`
2. retrieve nearest bundles
3. compose structured pre-state
4. generate answer

Goal:
use the stack as middleware, not just pretraining.

## Minimal Binary-First Dataset Row

```json
{
  "id": "row-000001",
  "bytes_b64": "SGVsbG8=",
  "tongue": "KO",
  "ss1_tokens": ["ko:sil'a", "ko:vel'an"],
  "tongue_profile": [0.82, 0.11, 0.07, 0.04, 0.02, 0.03],
  "null_pattern": [0, 1, 1, 1, 1, 1],
  "governance": "ALLOW",
  "domain": "intent/control",
  "text": "hello",
  "target_text": "hello"
}
```

This is enough to start testing without solving the whole philosophy.

## Recommended First Experiment

Do not start with a foundation model from zero. Start with a controlled small-model comparison.

Compare:

1. `baseline`
small model trained on text-only examples

2. `stack-lite`
same model trained on text plus tongue/null packet

3. `stack-binary`
same model trained on byte/tongue foundation first, then text plus packet

Tasks:

- route classification
- governance posture
- in-domain QA
- canon-drift check
- adversarial prompt handling

Pass criteria:

- `SEG >= 1.5`
- `OER >= 0.15`
- `DDR >= 0.20`
- `F1 gain >= 0.05`

That is enough to justify a larger experiment.

## What This Does Not Prove

Even if this works, it does not prove:

- full semantic understanding from binary alone
- replacement of natural language training
- general superintelligence
- that every domain benefits equally

It would prove something narrower and still valuable:

that explicit byte/tongue/orientation structure can make training and inference more sample-efficient and more stable than plain text-only routing.

## Practical Read

The simplest version of your system is already here:

- bytes are the first truth layer
- SS1 is the first symbolic layer
- tongue/null packet is the first orientation layer
- words sit on top

That is the smallest non-hand-wavy version worth testing.
