# Machine Crystal Path-State Research Brief

Date: 2026-06-27

## Question

Can higher-level geometric shapes become executable expressions by using angular relations, derivative-like path metrics, quasicrystal-style projection, and PHDM path gates?

## Result

Yes, as an executable software model:

```text
higher shape expression
  -> macro lowering
  -> octahedral crystal face path
  -> discrete path-curvature metrics
  -> PHDM path-state gate
  -> bounded tape-machine execution receipt
```

Implemented in:

```text
python/scbe/machine_crystal_higher.py
scripts/benchmarks/bench_machine_crystal_higher.py
```

## Definitions we are using

### Face turn angle

Each crystal face has a normal vector. The face turn angle between two executed
faces is the angle between their normals.

```text
theta(face_a, face_b) = arccos(dot(n_a, n_b) / (|n_a| |n_b|))
```

### Discrete path curvature

A program is a path of faces. The curvature/roughness signal is the first
difference between consecutive face turn angles:

```text
dtheta_i = theta_i+1 - theta_i
```

This gives a curvature/roughness signal for a shape program.

This is not the Julia-Caratheodory angular derivative from complex analysis.
There is no holomorphic self-map of the disk here; this module measures
polyhedral face-path turning.

### Quasicrystal light path

Use golden-angle phase steps to generate non-repeating 3D projection rays. Each
ray exits one octahedral face and selects one operation. This is inspired by
cut-and-project quasicrystal construction, but it is not a full crystallographic
model.

### Path-state injection

The phrase "code injection" is implemented here as controlled program injection:
a higher-level shape expression may inject a program into the crystal runtime
only if a PHDM path-state gate allows it.

Rules:

- PHDM `ALLOW`: execute.
- PHDM `ESCALATE`: compile, do not execute.
- PHDM `DENY`: refuse.

## Higher shape macros

| Shape | Lowering | Meaning |
| --- | --- | --- |
| `star` | `+` | increment current cell |
| `shadow` | `-` | decrement current cell |
| `cube` | `>` | move to right memory cell |
| `root` | `<` | move to left memory cell |
| `lens` | `.` | emit current cell |
| `triangle` | `[->+<]` | move current cell into right neighbor |
| `prism` | `[->+>+<<]>>[-<<+>>]<<` | copy current cell into right neighbor while preserving source |
| `spiral` | `[-]` | clear current cell |

Example:

```text
star*5 prism cube lens
```

Meaning:

1. Put value `5` in current cell.
2. Copy it into the right cell.
3. Move to the right cell.
4. Emit it.

Expected output: byte `0x05`.

## Benchmark plan

The benchmark runs:

- 65 correctness cases: `star*N prism cube lens` for N = 0..64.
- 128 golden-angle light paths, each 64 projected rays, measured by discrete path curvature.
- Safe PHDM path execution.
- Risk PHDM path refusal or compile-only behavior.

## Research sources

- Cut-and-project quasicrystal definition: https://tilings.math.uni-bielefeld.de/glossary/cut-and-project/
- Mathematical quasicrystals intro: https://www.math.uh.edu/~haynes/files/SLO1.pdf
- Geometry of Interaction machine: https://dl.acm.org/doi/10.1145/199448.199483
- Typed Geometry of Interaction: https://www.cambridge.org/core/journals/mathematical-structures-in-computer-science/article/towards-a-typed-geometry-of-interaction/762142E58DFC91D9BFF256FAEF8026F9
- Polyhedral graphs as 3-connected planar graphs: https://pmc.ncbi.nlm.nih.gov/articles/PMC9474462/

## Honest boundary

This proves a software execution model, not a physical optical computer. The
light/projection language is a geometric control metaphor backed by deterministic
software lowering and receipts.

The `quasicrystal_unique_hashes` benchmark proves distinct generated programs,
not crystallographic aperiodic order. The load-bearing claim is only that the
program generator uses golden-angle/phi-spaced sampling.
