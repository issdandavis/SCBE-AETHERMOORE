---
tags: [prime-fog, color, circuit, visualization, derivatives]
updated_at: 2026-06-05
---

# Prime Color Circuit

Status: rendered as a visualization layer over the [[prime alphabet circuit]].
Useful for inspection; not a targeting lane by itself.

Color can carry two kinds of prime information:

1. **Discrete behavior colors** — residue, gap mod, wheel bucket, alphabet bucket.
2. **Floating derivative colors** — continuous values bucketed by quantile so
   texture remains visible:
   - normalized gap ratio: `(p_next - p) / log(p)`
   - log step: `log(p_next / p)`
   - ratio curvature: `log(p_next/p) - log(p/p_prev)`
   - gap acceleration: `gap_next - gap_prev`

## Render

Script:

```powershell
python scripts\research\prime_color_circuit_render.py --limit 1000000 --max-primes 50000 --circuits 8
```

Artifact:

```text
artifacts/prime_color_circuit/LATEST.md
```

Panels:

```text
artifacts/prime_color_circuit/panels/*.svg
```

Each SVG is 26 columns wide. Every 26 rows is one completed alphabet circuit
(`26 letters x 26 rotations`). Eight full circuits are rendered per panel.

## Encoded Panels

Discrete:

- `value_mod26`
- `gap_mod26`
- `wheel210_bucket26`
- `normalized_gap_bucket`
- `ratio_curvature_bucket`

Floating / derivative:

- `float_gap_ratio`
- `float_log_step`
- `float_ratio_curvature`
- `float_gap_acceleration`

Each has direct and rotating versions.

## Reading

Color makes structure visible, but the same discipline applies:

```text
visible band != new law
visible island != targeting lane
```

Strong bands usually mean known modular/wheel structure. Broken texture in the
floating derivative panels is a candidate for a later null-tested compression
question, not proof by eye.

The useful workflow is:

```text
color panel -> suspicious pattern -> define numeric axis -> test against null
```

So color is the scouting map. The gate still decides whether it has mass.
