# n8n Multi-Agent Routing Playbook with Lattice25D

**Issac Daniel Davis** | SCBE-AETHERMOORE | 2026-03-06

## Objective

Route research and execution jobs across multiple model lanes while preventing lane collisions and preserving auditability.

## Practical strategy

- Use `all_paths` branch exploration when discovery quality matters.
- Use `first_match` for low-latency operational loops.
- Use lattice neighbor distance as a tie-breaker for route arbitration.
- Gate cross-lane transitions with separator token logic.

## Operator checklist

1. Ingest notes from repo + Notion.
2. Query nearest bundles for task context.
3. Select lane by governance score and phase distance.
4. Persist route evidence in artifacts.
5. Export a daily JSONL snapshot for training.

## Suggested metrics

- median branch score
- coverage percentage
- cross-lane transition count
- separator authorization failure rate

## References

- `workflows/n8n/choicescript_branching_engine.py`
- `workflows/n8n/scbe_n8n_bridge.py`
- `hydra/lattice25d_ops.py`
