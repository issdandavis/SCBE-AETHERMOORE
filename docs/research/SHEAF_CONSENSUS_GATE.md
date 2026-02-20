# Sheaf Consensus Gate

Files:

- Module: `src/harmonic/sheaf_consensus_gate.py`
- CLI: `scripts/sheaf_consensus_gate.py`

## Purpose

Operational lattice-sheaf gate for SCBE pipelines:

- Takes temporal signals (`fast`, `memory`, `governance`)
- Computes Tarski sheaf obstruction/stability
- Produces `ALLOW | QUARANTINE | DENY` via omega gate
- Supports single-shot mode or JSONL batch mode

## Single-shot usage

```bash
python scripts/sheaf_consensus_gate.py \
  --fast 0.12 \
  --memory 0.18 \
  --governance 0.20 \
  --harm-score 0.92 \
  --drift-factor 0.90 \
  --spectral-score 0.88
```

## Batch JSONL usage

Input JSONL rows may include:

- `fast_signal`
- `memory_signal`
- `governance_signal`
- optional gate factors: `pqc_valid`, `harm_score`, `drift_factor`, `spectral_score`

```bash
python scripts/sheaf_consensus_gate.py \
  --input-jsonl training/intake/web_research/sample.jsonl \
  --output-jsonl artifacts/sheaf_gate/sample_out.jsonl
```

Each output row receives:

- `sheaf_gate.decision`
- `sheaf_gate.omega`
- `sheaf_gate.triadic_stable`
- `sheaf_gate.sheaf_obstructions`
- `sheaf_gate.assignment`
- `sheaf_gate.projected`

