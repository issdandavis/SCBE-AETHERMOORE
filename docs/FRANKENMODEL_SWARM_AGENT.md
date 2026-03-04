# FrankenModel Swarm Agent

Builds a composite execution unit from 2-3 specialist models.

## Why
If one model can read and another can write, the swarm composes them into one governed execution path instead of forcing a single all-capability model.

## Run
```powershell
python scripts/system/frankenmodel_swarm_agent.py --input prototype/polly_eggs/examples/frankenmodel_swarm_sample.json
```

## Flow
1. Select up to 3 candidates that cover required capabilities.
2. Run M4 geometric synthesis gate.
3. Return `ALLOW/QUARANTINE/DENY` + selected team + composite coordinates.

## Output Fields
- `decision`
- `selected`
- `missing_capabilities`
- `composite_pos`
- `inherited_trust`
- `harmonic_energy`
