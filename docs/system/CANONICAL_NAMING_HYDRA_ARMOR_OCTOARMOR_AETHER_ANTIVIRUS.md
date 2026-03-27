# Canonical Naming: HYDRA, Hydra Armor, OctoArmor, and Aether Antivirus

Status: active naming reference

This file locks the intended naming so product copy, docs, and code do not drift.

## Core rule

There is no first-class runtime module named `Aether Antivirus` in the repo today.

If the name is used publicly, it should refer to the existing antivirus stack as an umbrella label, not as a separate implementation.

## Canonical mapping

### HYDRA

HYDRA is the orchestration body.

It is the multi-agent coordination system built around heads, limbs, memory, consensus, and terminal/browser execution.

Primary code:
- `hydra/head.py`
- `hydra/spine.py`
- `hydra/limbs.py`
- `hydra/librarian.py`

Primary docs:
- `docs/hydra/ARCHITECTURE.md`
- `docs/HYDRA_COORDINATION.md`

### Hydra Armor

Hydra Armor is the defensive layer wrapped onto HYDRA.

It is a system label, not a separate exported class. Use it to describe HYDRA plus the governance and antivirus layers that protect actions before execution.

Hydra Armor should mean:
- HYDRA coordination
- SCBE governance gating
- antivirus membrane / semantic antivirus
- turnstile containment

Do not describe Hydra Armor as a standalone hook framework unless that framework is actually implemented.

### OctoArmor

OctoArmor is the router and connector hub, not the antivirus itself.

It is the model-selection and lane-routing layer used in AetherBrowser and related surfaces.

Primary code:
- `src/aetherbrowser/router.py`
- `src/aetherbrowser/trilane_router.py`
- `src/aetherbrowser/serve.py`

Primary docs:
- `docs/ISSAC_QUICKSTART.md`
- `docs/SYSTEM_ANATOMY.md`

### Aether Antivirus

If this name is used, it should be treated as the umbrella brand for the antivirus stack already present in the repo.

The current stack is:

1. Antivirus Membrane
- deterministic text/content scanner
- code: `agents/antivirus_membrane.py`

2. SemanticAntivirus
- web-agent content and action scanning layer
- code: `src/symphonic_cipher/scbe_aethermoore/concept_blocks/web_agent/semantic_antivirus.py`
- docs: `docs/SCBE_WEB_AGENT_ARCHITECTURE.md`

3. Kernel Antivirus Gate
- policy engine for kernel telemetry and containment
- code: `agents/kernel_antivirus_gate.py`
- docs: `docs/KERNEL_ANTIVIRUS_SCBE.md`

4. Agentic Antivirus
- repo/code scanning and triage CLI
- code: `scripts/agentic_antivirus.py`
- docs: `docs/SELF_IMPROVEMENT_AGENTS.md`, `docs/SCBE_SYSTEM_CLI.md`

## Recommended product language

Use this wording:

- `HYDRA` = orchestration body
- `Hydra Armor` = HYDRA with governance and antivirus protection
- `OctoArmor` = routing and connector hub
- `Aether Antivirus` = umbrella label for Antivirus Membrane + SemanticAntivirus + Kernel Antivirus Gate + Agentic Antivirus

## Avoid these claims

Do not claim any of the following unless implemented and verified in code:

- a standalone `HydraArmor` runtime class
- a general extension hook registry for Hydra Armor
- a separate product runtime that does not map to the existing HYDRA or antivirus modules

## Current source anchors

- `agents/antivirus_membrane.py`
- `agents/kernel_antivirus_gate.py`
- `scripts/agentic_antivirus.py`
- `src/symphonic_cipher/scbe_aethermoore/concept_blocks/web_agent/semantic_antivirus.py`
- `src/aetherbrowser/router.py`
- `hydra/head.py`
- `hydra/spine.py`
- `docs/KERNEL_ANTIVIRUS_SCBE.md`
- `docs/SCBE_WEB_AGENT_ARCHITECTURE.md`
- `docs/hydra/ARCHITECTURE.md`
- `docs/HYDRA_COORDINATION.md`
