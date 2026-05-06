# MAHSS Physical Response Capture

This is the measurement lane for testing whether seeded MAHSS topologies produce
repeatable physical fingerprints. It is experiment-only until real same-seed
prints cluster tighter than different-seed prints.

## CSV Schema

The validator expects:

```csv
seed,repeat,sample_index,value,sample_rate_hz
part-a,0,0,0.00123,44100
```

Required columns are `seed`, `repeat`, and `value`. `sample_index` and
`sample_rate_hz` are kept for auditability.

## Import Recorded WAV Files

Record each tap as a short WAV file from a contact mic, phone, or audio
interface, then append it to the measurement CSV:

```powershell
python scripts/experiments/mahss_physical_capture.py import-wav `
  --wav artifacts/mahss_topology/raw/part-a-repeat-0.wav `
  --output artifacts/mahss_topology/physical_measurements.csv `
  --seed part-a `
  --repeat 0 `
  --max-samples 4096
```

Repeat at least three times per physical part. For authentication, use at least
two repeats for enrollment and one or more repeats for verification.

## Optional Live Recording

Live recording requires the optional package:

```powershell
pip install sounddevice
```

Then check devices:

```powershell
python scripts/experiments/mahss_physical_capture.py devices
```

Record one trace:

```powershell
python scripts/experiments/mahss_physical_capture.py record `
  --output artifacts/mahss_topology/physical_measurements.csv `
  --seed part-a `
  --repeat 0 `
  --seconds 2 `
  --sample-rate 44100 `
  --max-samples 4096
```

## Validate Measurements

```powershell
python scripts/experiments/mahss_topology_validation.py `
  --measurement-csv artifacts/mahss_topology/physical_measurements.csv `
  --enrollment-repeats 2 `
  --measurement-channel tap_impulse `
  --output artifacts/mahss_topology/physical_response_validation.json
```

Pass condition for a useful physical authentication signal:

```text
min_inter_seed_distance > max_intra_seed_distance
false_accept_count = 0
false_reject_count = 0
```

If the margin is negative, the measurement channel is too noisy or the topology
perturbations are too weak.
