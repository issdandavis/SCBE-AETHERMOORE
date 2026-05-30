# SCBE Polly Pad

`scbe-polly-pad` is the small Python interface for Polly Pads: personal and squad workspaces for AI agents. It exposes the Polly Pad runtime without shipping the full SCBE monorepo.

## Install

```bash
pip install scbe-polly-pad
```

## CLI

```bash
scbe-polly-pad modes
scbe-polly-pad decide --d-star 0.4 --coherence 0.9 --h-eff 12
scbe-polly-pad namespace --unit-id polly-1 --mode ENGINEERING --lang CA --epoch 1
scbe-polly-pad trace --state 0.1,0.2,0.0,0.0,0.0,0.0 --d-star 0.2
scbe-polly-pad audit append --actor human --action task.add --subject youtube --payload-json "{\"step\":\"title\"}"
scbe-polly-pad audit verify
scbe-polly-pad audit export
```

## Python

```python
from scbe_polly_pad import PollyPad, SquadSpace, UnitState

pad = PollyPad(unit_id="polly-1", mode="ENGINEERING")
state = UnitState(unit_id="polly-1", x=0, y=0, z=0, coherence=0.9, d_star=0.2, h_eff=5)
squad = SquadSpace(squad_id="demo", units={"polly-1": state})

print(pad.assist("code review", state, squad))
```

This package is intentionally runtime-only. Patent workbench files, training corpora, private notes, generated artifacts, and repository-local automation are not included in the wheel.

## Audit Receipts

Polly Pad audit ledgers are append-only JSONL files under `.polly/audit.jsonl` by default. Each event stores a canonical SHA-256 hash and the previous event hash, so edits to old receipts are detected by `scbe-polly-pad audit verify`.
