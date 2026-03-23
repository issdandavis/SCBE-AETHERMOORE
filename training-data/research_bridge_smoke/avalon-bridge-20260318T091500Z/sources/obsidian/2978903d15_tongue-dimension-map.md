# Tongue Dimension Map

> How the 6 Sacred Tongues map to spatial dimensions.

## 6D Assignment (Canonical)

From `cymatic_voxel_net.py`:

| Tongue | 6D Dimension | Semantic Role |
|--------|-------------|---------------|
| KO | dim 0 | Control axis |
| AV | dim 1 | Transport axis |
| RU | dim 2 | Policy axis |
| CA | dim 3 | Compute axis |
| UM | dim 4 | Security axis |
| DR | dim 5 | Schema axis |

## Realm Centers in 6D Poincare Ball

```
KO: [0.0,  0.0,  0.0,  0.0,  0.0,  0.0]   (origin)
AV: [0.3,  0.1,  0.0,  0.0,  0.0,  0.0]   (near KO)
RU: [0.0,  0.4,  0.2,  0.0,  0.0,  0.0]   (mid-field)
CA: [-0.2, -0.3,  0.4,  0.1,  0.0,  0.0]  (offset)
UM: [0.0,  0.0, -0.5,  0.3,  0.2,  0.0]   (deep field)
DR: [0.1, -0.2,  0.0, -0.4,  0.3,  0.1]   (distributed)
```

## 3D Projection (Spatial Engine)

The [[3D Spatial Engine]] projects 6D to 3D via paired summation:

| 3D Axis | Tongue Pair | Projection |
|---------|------------|------------|
| X | KO (+) + AV (-) | v[0] + v[1] |
| Y | RU (+) + CA (-) | v[2] + v[3] |
| Z | UM (+) + DR (-) | v[4] + v[5] |

Positive tongue = positive axis direction, negative tongue = negative direction.

## Cross-References
- [[Six Sacred Tongues]] — Full tongue specification
- [[3D Spatial Engine]] — 3D projection implementation
- [[Tongue Domain Mappings]] — CDDM domain assignments
- [[Hyperbolic Geometry References]] — Poincare ball mathematics
