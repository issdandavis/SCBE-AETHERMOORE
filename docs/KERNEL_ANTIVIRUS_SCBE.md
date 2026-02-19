# Kernel Antivirus Bridge for PHDM/SCBE

Status: active implementation (policy bridge)  
Code: `agents/kernel_antivirus_gate.py`  
Tests: `tests/test_kernel_antivirus_gate.py`

## What this is

`kernel_antivirus_gate` is the SCBE policy engine for kernel telemetry events.
It is designed to sit between:

- event producers (eBPF/Falco, ETW, minifilter, Sysmon),
- and enforcement points (allow, throttle, quarantine, kill, honeypot).

It reuses current SCBE components:

- Threat membrane: `agents.antivirus_membrane.scan_text_for_threats`
- Domain turnstile: `hydra.turnstile.resolve_turnstile`
- Enemy-first thresholds used in extension gating

## Security-as-cells model

The gate applies immune-style state transitions:

- `HEALTHY`: normal flow (`ALLOW`)
- `PRIMED`: elevated monitoring
- `INFLAMED`: friction increase (`THROTTLE`)
- `NECROTIC`: hard containment (`HONEYPOT` + isolation)

State derives from three signals:

- `suspicion` (content + integrity + geometry blend)
- `antibody_load` (time-decayed suspicion memory)
- `membrane_stress` (geometry boundary pressure)

## Event schema

Input (`KernelEvent`) includes:

- process identity (`pid`, `process_name`, `parent_process`)
- operation (`exec`, `module_load`, `process_inject`, etc.)
- target path/resource
- signer/hash integrity (`signer_trusted`, `hash_sha256`)
- optional geometric signal (`geometry_norm`)

Output (`KernelGateResult`) includes:

- SCBE decision (`ALLOW`, `QUARANTINE`, `ESCALATE`, `DENY`)
- immune cell state
- turnstile outcome
- kernel action (`ALLOW`, `THROTTLE`, `QUARANTINE`, `KILL`, `HONEYPOT`)

## Why this fits PHDM/SCBE

- Keeps user friction low for clean workloads.
- Pushes friction and containment to hostile trajectories.
- Maintains continuity with existing turnstile math and domain policy.
- Lets kernel enforcement remain simple while SCBE policy evolves in Python/TS.

## Run tests

```powershell
pytest -q tests/test_kernel_antivirus_gate.py
```

