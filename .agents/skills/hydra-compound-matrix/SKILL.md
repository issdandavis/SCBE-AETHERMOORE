---
name: hydra-compound-matrix
description: Use when SCBE needs a multi-model council to choose, score, and package agentic research/coding/sorting operations with Kaggle-style validation discipline, formation-matrix routing, and HYDRA brain context-vault outputs.
---

# HYDRA Compound Matrix

Use this skill when a task needs multiple AI lanes to decide what to do next without flooding context or trusting unvalidated claims.

## Workflow

1. Refresh formation tuning if the current task shape changed.

```powershell
python scripts/system/tune_formation_matrix.py --grid 7 --top 12
```

2. Build the council packet.

```powershell
python scripts/system/multi_model_compound_matrix.py --top 10
```

3. Read the generated review before calling live models.

```powershell
Get-Content artifacts/agent_context_vault/compound_matrix/full_system_review.md
```

4. Promote only one operation at a time into live execution. Prefer dry packets first.

## Strategy Rules

- Start with the metric and validation gate before optimizing.
- Treat public feedback, visible scores, and repeated probes as overfit risk.
- Use out-of-fold or held-out lane outputs before stacking model council conclusions.
- Add diverse model lanes only when they reduce error correlation.
- Convert successful traces into training rows only after provenance, leakage, and held-out gates pass.
- Document every promoted operation with proof paths, hashes, and rollback notes.

## Default Formations

- `pair`: narrow private work or one-model verification.
- `triad`: stable default for builder, verifier, context roller.
- `quad`: maximum variable mapping without full mesh chatter.
- `hex`: broad research, release, training, and packaging work when coordination cost is acceptable.

## Output Contract

The council writes:

- `artifacts/agent_context_vault/compound_matrix/compound_matrix_packet.json`
- `artifacts/agent_context_vault/compound_matrix/full_system_review.md`

Use those files as the handoff packet for HYDRA brain decisions.
