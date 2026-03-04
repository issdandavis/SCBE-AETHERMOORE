# Model Duty Cycle Routing

SCBE switchboard supports specialist duty profiles where each model has:

- `primary` jobs (main lane)
- `secondary` jobs (fallback lane when primary work is absent)
- `idle_jobs` (background low-priority work)

Config file:

- `config/governance/model_duty_profiles.json`

Routing behavior:

1. Base route score is computed from value/cost profile.
2. Duty fit adds a score bonus:
   - `primary_bonus_pct`
   - `secondary_bonus_pct`
3. Spectrum fit adds a non-linear boost:
   - `tongue_vector` (KO/AV/RU/CA/UM/DR)
   - `spectrum_bonus_pct`
   - `alignment = cosine(task_vector, profile_vector)`
   - boost formula: `1 + spectrum_bonus_pct * max(0, alignment)^2`
4. Highest final score wins.

Status output now includes:

- `duty_profiles_loaded`
- `idle_secondary_jobs`

This keeps specialist models focused while still useful between peak tasks.

## Why Spectrum Routing

Point-only routing (single label/keyword) is brittle when tasks overlap.
The spectrum layer treats tasks as an array across six Sacred Tongues, then
matches them against model specialization vectors.

This allows hybrid intent routing such as:

- research + governance
- code + architecture
- summarize + classify

without forcing a single hard class.

## CLI Update

`scripts/system/register_duty_profile.py` now supports:

- `--tongue-vector "ko=0.7,av=0.2,ru=0.6,ca=0.3,um=0.5,dr=0.4"`
- `--spectrum-bonus-pct 0.14`
