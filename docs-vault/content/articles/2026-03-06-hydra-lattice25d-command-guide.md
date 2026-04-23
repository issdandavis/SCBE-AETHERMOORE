# HYDRA Lattice25D Command Guide

**Issac Daniel Davis** | SCBE-AETHERMOORE | 2026-03-06

## Why this command matters

The new `hydra lattice25d` command gives the main HYDRA CLI a direct way to map notes into a 2.5D hyperbolic lattice with cyclic phase. This closes the gap between research notes and executable geometry.

## Core workflow

```bash
hydra lattice25d notes --glob "docs/**/*.md" --max-notes 30 --json
```

The command:

- ingests notes from local markdown
- normalizes tags and governance fields
- embeds intent vectors with metric tags
- returns deterministic JSON for n8n or MCP handoff

## Design notes

Lattice25D keeps 2D layout plus cyclic phase for overlap-safe flow. This enables quasi-periodic routing without forcing full volumetric 3D cost.

## References

- `hydra/cli.py`
- `hydra/lattice25d_ops.py`
- `tests/test_hydra_lattice25d_cli.py`
