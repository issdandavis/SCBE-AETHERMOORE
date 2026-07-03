# Machine Crystal - Bhargava Cube Overlay

Date: 2026-06-27
Source trigger: YouTube link `1uJBf84R8r0`, identified as a video about Manjul Bhargava.

## Why this matters

Manjul Bhargava's cube law places eight integers on the corners of a cube. From
the three pairs of opposite faces, it constructs three binary quadratic forms.
Those three forms have the same discriminant.

That is directly adjacent to the Machine Crystal because the Machine Crystal
already has an 8-address cube/octahedron dual:

```text
8 cube corners = 8 octahedron faces = 8 Machine Crystal ops
```

So we can overlay Bhargava's arithmetic cube on top of the Machine Crystal's
geometric cube.

## Implemented

```text
python/scbe/machine_crystal_bhargava.py
scripts/benchmarks/bench_machine_crystal_bhargava.py
```

The implementation computes:

- one 8-entry cube,
- the three face-pair binary quadratic forms,
- each form's discriminant,
- and verifies the discriminants match.

## Validation command

```powershell
python scripts\benchmarks\bench_machine_crystal_bhargava.py
```

Receipt:

```text
artifacts/machine_crystal/bhargava_cube_overlay.json
```

## Honest boundary

Implemented:

- Bhargava-cube discriminant overlay.
- 128 deterministic cube checks.
- Machine Crystal index cube check.

Not implemented:

- Gauss composition law.
- class group arithmetic.
- Bhargava's full higher composition laws.

So the valid claim is:

```text
The Machine Crystal's 8-address cube can carry a Bhargava-cube integer overlay,
and the three associated binary quadratic forms have equal discriminants.
```

Do not claim:

```text
We implemented Bhargava's full composition law.
```

## Sources

- Video metadata: https://www.youtube.com/watch?v=1uJBf84R8r0
- Bhargava, Higher Composition Laws I: https://annals.math.princeton.edu/wp-content/uploads/annals-v159-n1-p03.pdf
- IMU Fields Medal release: https://www.mathunion.org/fileadmin/IMU/Prizes/Fields/2014/news_release_bhargava.pdf
- Princeton note: https://gradschool.princeton.edu/about/viget-honor-roll/manjul-bhargava
- Bhargava cube reference summary: https://en.wikipedia.org/wiki/Bhargava_cube
