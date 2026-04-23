# CLI Research Stack Patterns for Multi-Model Swarms

**Issac Daniel Davis** | SCBE-AETHERMOORE | 2026-03-06

## Pattern 1: Fast pulse check

Use light mode for broad recall:

```bash
hydra research "topic" --mode httpx --max-subtasks 2 --discovery 3
```

This keeps latency low while building enough evidence for next-step branching.

## Pattern 2: Geometry-first storage

Immediately push outputs into lattice workflow for spatial memory and drift checks.

## Pattern 3: Publish loop

Use article templates under `content/articles/`, then run:

```bash
python scripts/publish/post_all.py --dry-run
```

Capture evidence from `artifacts/publish_browser/` before claiming success.

## Pattern 4: Cross-lane continuity

Treat each route result as a packet that can be replayed by other agents without re-running expensive discovery.

## References

- `hydra/cli.py`
- `hydra/research.py`
- `scripts/publish/post_all.py`
