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

## Linux adapter (Falco/eBPF) - implemented

Bridge module:

- `agents/linux_kernel_event_bridge.py`

CLI monitor:

- `scripts/linux_kernel_antivirus_monitor.py`

Adapter responsibilities:

- parse Falco JSON (`output_fields`) into normalized `KernelEvent`
- map `evt.type` to SCBE operation classes (`exec`, `open`, `write`, `network_connect`, etc.)
- carry antibody load per process key (`host:pid:process`) across events
- emit SCBE containment decisions in JSONL

Run:

```powershell
# from live stdin feed
falco -o json_output=true | python scripts/linux_kernel_antivirus_monitor.py --input - --alerts-only

# from replay file
python scripts/linux_kernel_antivirus_monitor.py --input artifacts/falco_events.jsonl --pretty
```

## Linux enforcement hooks (auto-response) - implemented

Hook module:

- `agents/linux_enforcement_hooks.py`

Additional tests:

- `tests/test_linux_enforcement_hooks.py`

Behavior:

- maps `kernel_action` into Linux command emitters (`renice`, `kill`, quarantine copy/chmod)
- keeps per-process cooldown to avoid duplicate rapid enforcement
- supports dry-run emission or optional command execution

Run with command emitters only (safe default):

```powershell
falco -o json_output=true | python scripts/linux_kernel_antivirus_monitor.py --input - --alerts-only --emit-enforcement
```

Run with execution enabled (requires host permissions):

```powershell
falco -o json_output=true | python scripts/linux_kernel_antivirus_monitor.py --input - --alerts-only --apply-enforcement --quarantine-dir /var/quarantine/scbe
```

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
pytest -q tests/test_linux_kernel_event_bridge.py
pytest -q tests/test_linux_enforcement_hooks.py
pytest -q tests/test_antivirus_membrane.py tests/test_hydra_turnstile.py tests/test_extension_gate.py
```
