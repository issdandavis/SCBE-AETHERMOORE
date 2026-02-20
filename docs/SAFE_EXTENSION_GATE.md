# Safe Extension Gate (Enemy-First)

Status: active design + tested implementation  
Code: `agents/extension_gate.py`  
Tests: `tests/test_extension_gate.py`

## Goal

Enable legitimate user extensions with low friction while pushing security friction
onto hostile payloads.

This gate does not punish users by default. It escalates only when threat signals,
permission risk, or provenance risk cross thresholds.

## Pipeline

1. Threat scan (`agents.antivirus_membrane.scan_text_for_threats`)
- prompt-injection signatures
- malware-like command signatures
- external link pressure

2. Manifest scoring
- permission risk (weighted by capability)
- provenance risk (trusted source domain, sha256 pin, manifest completeness)

3. Combined suspicion
- `suspicion = 0.55*scan + 0.25*permission + 0.20*provenance`

4. Turnstile resolution (`hydra.turnstile.resolve_turnstile`)
- domain aware outcomes:
  - `browser`: ALLOW/HOLD/ISOLATE/HONEYPOT
  - `vehicle`: PIVOT/DEGRADE (no unsafe stall)
  - `fleet`: ISOLATE/DEGRADE with swarm continuity
  - `antivirus`: ISOLATE/HONEYPOT

5. Permission partition
- low suspicion: mostly full enablement, block strongest execution channels
- medium suspicion: reduced allowlist
- high suspicion: zero permission enablement

## Why this matches your objective

- "Gate enemies, not users":
  - clean extensions pass with minimal friction
  - hostile extensions are held, isolated, or honeypotted
- User extensions remain possible and practical.
- Security action becomes adaptive and domain-aware.

## Run tests

```powershell
pytest -q tests/test_extension_gate.py
```
