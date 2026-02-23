# Model Synthesis Agent (2 or 3 models)

Couples 2 or 3 model nodes using M4 governance constraints.

## Run
```powershell
python scripts/system/model_synthesis_agent.py --input prototype/polly_eggs/examples/model_synthesis_sample.json
```

## Rules
- Poincare bound on each input model position.
- Pairwise negative-space midpoint rejection.
- Harmonic wall check using `phi^(d_perp^2)`.
- Composite trust inherits min(parent trust).

## Output
`ALLOW`, `QUARANTINE`, or `DENY` with composite position and reason.
