# Triadic Operator Manifold

**Status:** v1 product slice.
**Code:** `src/operator/triadic_manifold.ts` and `packages/agent-bus-py/src/scbe_agent_bus/companions.py`.

## Purpose

The operating surface is not just 2D, 2.5D, or 3D. Those are rendered views.
The real work happens in an N-dimensional shared operating space between:

- the human, who supplies intent, trust, approval, and time pressure;
- the machine, which supplies files, processes, storage, permissions, and real execution;
- the AI, which supplies fast navigation, synthesis, uncertainty, and tool use.

The Triadic Operator Manifold names that shared space so product features can
route through it instead of becoming one-off scripts.

## Rule

Do not replace working tools. Upgrade them.

Scripts become commands. Commands become workflows. Workflows emit receipts.
Receipts become product trust.

## Lightweight install policy

SCBE packages should reference companion packages without forcing heavy
installs. A user who only needs the tokenizer should not be forced to install a
large agent workspace. A user who only needs the Python agent bus should not be
forced to pull a browser, model cache, or full repo.

Companion prompts are advisory:

- npm users can be pointed toward PyPI agent-bus features;
- Python users can be pointed toward npm governance/operator features;
- no package silently installs another ecosystem;
- cloud lanes are opt-in and must honor privacy.

The package map lives at `config/system/triadic_operator_packages.json`.

## Runtime model

```text
Human intent
  x Machine state
  x AI inference
  x constraints
  -> operator plan
  -> governed action
  -> receipts
  -> export, merge, release, or storage handoff
```

The TypeScript API:

```ts
import { createTriadicOperatorPlan } from 'scbe-aethermoore/operator';

const plan = createTriadicOperatorPlan({
  intent: 'run repo verification without straining my laptop',
  privacy: 'remote_ok',
  workload: 'large',
  preferCloud: true,
  features: ['agent-bus', 'workspace'],
});
```

The Python API:

```py
from scbe_agent_bus import recommend_companion_packages

print(recommend_companion_packages(["operator_manifold", "tokenizer"]))
```

## Cloud and compute posture

Default to `local_first`.

Use `cloud_assist` only when:

- privacy is `remote_ok`;
- workload is large or long-running;
- local CPU, memory, disk, or battery pressure is high;
- the user explicitly approves Codespaces, VM, or hosted runner use.

Do not upload secrets, private keys, local-only notes, or unreviewed proprietary
customer files to cloud lanes.

## Receipts

The first receipt markers are:

- `SCBE_OPERATOR_PLAN_READY=1`
- `SCBE_WORKSPACE_READY=1`
- `SCBE_GATE_ALLOW=1`
- `SCBE_STORAGE_EXPORT_READY=1`

These are intentionally small. They let CLI, mobile, npm, PyPI, and GitHub
Actions show positive progress without inventing a new UI for every subsystem.
