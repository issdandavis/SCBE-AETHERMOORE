# Sacred Egg Challenge-Response PUF Harness

**Status:** candidate forward path.  
**Harness:** `scripts/experiments/sacred_egg_crp_puf_analysis.py`  
**Tests:** `tests/experiments/test_sacred_egg_crp_puf_analysis.py`

## Why this exists

The raw seeded-topology PUF test asks whether deterministic seed-derived
geometry alone can resist cloning. That narrow model is parked because the
simulation-stage result showed same-seed clones stay too close at realistic
printer tolerances.

The Sacred Egg architecture is a larger protocol. It can use geometry,
enrollment, GeoSeal context, hatch conditions, batch offsets, and sealed
receipts together. The right production-shaped question is therefore:

> Given an enrolled physical device and a public challenge selected by Sacred
> Egg / GeoSeal context, does the device produce a stable response that impostor
> devices cannot reproduce?

## CSV Schema

```csv
device_id,challenge_id,read_id,r_0,r_1,r_2
unit-a,challenge-1,0,0.10,0.90,0.11
unit-a,challenge-1,1,0.12,0.88,0.10
unit-b,challenge-1,0,0.91,0.10,0.89
```

Fields:

- `device_id`: enrolled physical part
- `challenge_id`: measurement challenge selected by Sacred Egg / GeoSeal context
- `read_id`: repeated read index
- response columns: impedance, RF, vibration, thermal, or other numeric features

## Distance Regimes

- `genuine`: same device, same challenge, repeated reads
- `impostor`: different device, same challenge
- `cross_challenge`: same device, different challenge

The authentication condition is:

```text
max(genuine) < min(impostor) / 2
```

The harness estimates:

- `reliability = 1 - mean(genuine)`
- `uniqueness = mean(impostor)`
- `challenge_separation = min(impostor) - max(genuine)`
- `works_for_authentication`
- `estimated_t_bits`
- `estimated_impostor_delta_bits`
- per-bit min-entropy estimate

## Command

```powershell
python scripts/experiments/sacred_egg_crp_puf_analysis.py measurements.csv `
  --report artifacts/aetherfab/sacred_egg_crp_puf_report.json
```

The command exits `0` only when the current measurements satisfy the estimated
authentication condition. It exits `2` when the measurement set overlaps or is
unproven.

## How It Fits Sacred Eggs

Sacred Eggs should not be treated as raw geometry. In the protocol framing:

1. `SacredEgg` / `GeoSeal` context selects or authorizes `challenge_id`.
2. The physical device produces response features.
3. The response is quantized and compared against enrollment.
4. A sealed receipt records challenge, response hash, measurement fixture, and
   decision metadata.

This keeps the seed as a challenge selector and authorization context rather
than the sole identity-bearing geometry.
