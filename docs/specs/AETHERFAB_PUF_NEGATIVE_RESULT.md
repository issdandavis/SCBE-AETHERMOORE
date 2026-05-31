# Raw Seeded-Topology PUF: Simulation-Stage Disconfirmation

**Status:** parked diagnostic, not a production architecture.  
**Architecture status:** `RAW_SEEDED_TOPOLOGY_PUF_DISCONFIRMED_STANDALONE_2026_05`  
**Harness:** `scripts/experiments/puf_measurement_analysis.py`

## Proposal

The narrow proposal tested here was to derive deterministic topology
perturbations from a cryptographic or post-quantum seed, fabricate the resulting
geometry, measure the physical response, and use that raw geometry response as a
standalone physically unclonable identity signal.

The attractive part is clear: one seed can deterministically produce many
manufacturable variants, and each physical object can be audited through
measurement. The failure mode is also clear: if the seed reproduces too much of
the identity-bearing structure, an attacker who knows the seed gets a strong
head start.

## Method

The v2 surrogate simulation used a weak PUF model rather than an expensive FEM
model:

1. Expand seed into a topology feature vector.
2. Add stochastic fabrication noise at swept amplitudes.
3. Project the feature vector through a fixed measurement operator.
4. Quantize responses into bit vectors.
5. Compare three Hamming-distance distributions.

The three distributions are:

- `intra`: same physical device, repeated measurement
- `clone`: same seed, different fabrication realization
- `inter`: different seed, different fabrication realization

The important attacker model is the `clone` distribution. If same-seed clones
are close to the original, the seed behaves like a reproducible barcode. If
same-seed clones are far above the intra-device noise floor and approach the
inter-device random baseline, the architecture may be PUF-like.

## Finding

The raw standalone seeded-topology PUF idea is structurally weak in the
realistic printer-tolerance regime. A surrogate v2 simulation compared three
distance distributions:

- `intra`: same physical device, repeated measurement
- `clone`: same seed, different fabrication realization
- `inter`: different seed, different fabrication realization

At realistic SLA/SLS/FDM tolerance bands, same-seed clone pairs stayed much
closer to the original than random inter-device pairs. That means an attacker
who knows the seed can fabricate a near-clone under this narrow model. In that
regime, raw seeded topology behaves closer to a reproducible barcode than a
standalone physically unclonable function.

The architecture only moved toward PUF-like behavior when fabrication noise
became large relative to the seed feature scale. That is not a good security
story: if fabrication noise dominates the seed, the seed is no longer the useful
identity primitive.

Approximate simulated regime:

| Fabrication noise sigma | Practical reading | Clone behavior |
|---|---|---|
| `0.001` | sub-SLA / idealized | clone indistinguishable from noise floor |
| `0.025` | SLA-like | marginal; clone much closer than random inter-device |
| `0.050` | SLS-like | inadequate cloning resistance |
| `0.100` | FDM-like | detectable clone distance, still far below random baseline |
| `0.300+` | deliberately poor / exotic | first PUF-like regime in the surrogate |

The crossover around sigma approximately `0.3` is the red flag. A system that
only becomes unclonable when fabrication error is large relative to the intended
feature scale is not a strong seeded-topology security primitive.

## Interpretation

Deterministic structure and unclonability are in tension. Deterministic
seed-derived geometry makes the object reproducible. PUF security comes from
uncontrolled physical variation that is stable for the enrolled device but hard
to recreate in a second fabrication run.

The raw standalone architecture inverted that relationship: the public or
recoverable seed carried too much identity. The printer did not add enough
useful variation at realistic tolerances to defeat a same-seed attacker.

This does **not** disconfirm the broader Sacred Egg / GeoSeal / genesis stack.
That stack adds layers the surrogate did not model: encrypted initialization
payloads, hatch conditions, fail-to-noise behavior, context-bound attestation,
batch offsets, cube hashes, and post-fabrication enrollment. Those layers can
change the production security question from "does raw geometry alone resist
cloning?" to "does the full protocol make cloning operationally, cryptographically,
or economically infeasible?"

## What remains useful

The measurement harness is still useful as a diagnostic and negative-result
tool:

```powershell
python scripts/experiments/puf_measurement_analysis.py measurements.csv `
  --report artifacts/aetherfab/puf_measurement_report.json
```

Expected CSV shape:

```csv
device_id,seed_id,fabrication_id,read_id,z_1hz,z_10hz,z_100hz
seed-a-print-0,seed-a,fab-0,0,0.11,0.20,0.33
seed-a-print-0,seed-a,fab-0,1,0.10,0.21,0.32
seed-a-print-1,seed-a,fab-1,0,0.28,0.41,0.51
seed-b-print-0,seed-b,fab-0,0,0.72,0.60,0.12
```

The harness reports:

- `reliability`: `1 - mean(intra)`
- `uniqueness`: `mean(inter)`
- `clone_gap`: `min(clone) - max(intra)`
- `clone_vs_inter_ratio`: whether same-seed clones approach random-pair distance
- `works_against_seed_clone`: whether a fuzzy extractor can reject same-seed clones

Green synthetic tests only prove the harness math. They do not prove the
seeded-topology architecture works on real printed parts.

Every JSON report emitted by the harness includes:

```json
{
  "architecture_status": "RAW_SEEDED_TOPOLOGY_PUF_DISCONFIRMED_STANDALONE_2026_05"
}
```

The CLI also prints the negative-finding warning so the status travels with
terminal output, not only with this note.

## Disposition

Future PUF work should treat the Sacred Egg stack as a protocol envelope and
test the stronger challenge-selector model:

1. Keep geometry uniform enough that the public seed does not reveal a
   reproducible macro-identity.
2. Enroll each fabricated device by measuring a large challenge-response
   database.
3. Use a public PQC-derived seed to select the measurement challenge for each
   session.
4. Authenticate by comparing the observed response against the enrolled
   per-device response distribution.

That model needs a different harness:

```csv
device_id,challenge_id,read_id,<response columns>
```

Do not extend the raw seeded-topology harness as if it validates the whole
Sacred Egg production path. Extend it only for negative-result documentation,
exotic fabrication processes, or as one component inside a larger Sacred
Egg/GeoSeal/challenge-response validation.

## Meta-Finding

This is a useful SCBE-AETHERMOORE governance example. A plausible AI-generated
engineering proposal moved through several agents. The simulation-before-
fabrication step caught the weakness of the **raw geometry-only** version before
hardware spend. The negative result is now attached to the diagnostic harness so
future agents do not quietly convert a parked sub-architecture into a production
claim about the entire Sacred Egg system.
