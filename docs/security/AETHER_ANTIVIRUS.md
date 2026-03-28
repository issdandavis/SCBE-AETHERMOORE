# Aether Antivirus

Status: active stack overview

Aether Antivirus is the umbrella name for the defensive scanning and containment layers already present in SCBE-AETHERMOORE.

It is not a separate standalone runtime or a separate exported package today.

## What it includes

### 1. Antivirus Membrane

Purpose:
- deterministic content scan
- prompt-injection signature detection
- malware-like pattern detection
- domain-aware turnstile actions

Code:
- `agents/antivirus_membrane.py`

### 2. SemanticAntivirus

Purpose:
- web content scanning
- prompt-injection and malware pattern checks
- entropy and obfuscation pressure
- Hamiltonian safety score tracking
- governance decision support for web actions

Code:
- `src/symphonic_cipher/scbe_aethermoore/concept_blocks/web_agent/semantic_antivirus.py`

Docs:
- `docs/SCBE_WEB_AGENT_ARCHITECTURE.md`

### 3. Kernel Antivirus Gate

Purpose:
- policy engine for kernel telemetry events
- containment actions such as throttle, quarantine, kill, and honeypot
- bridges event streams into SCBE/HYDRA containment decisions

Code:
- `agents/kernel_antivirus_gate.py`

Docs:
- `docs/KERNEL_ANTIVIRUS_SCBE.md`

### 4. Agentic Antivirus

Purpose:
- repository and corpus triage
- secret and risky-pattern scanning
- artifact reports for operator review

Code:
- `scripts/agentic_antivirus.py`

Docs:
- `docs/SCBE_SYSTEM_CLI.md`
- `docs/SELF_IMPROVEMENT_AGENTS.md`

## Relationship to the rest of the system

- `HYDRA` = orchestration body
- `Hydra Armor` = HYDRA with governance and antivirus protection
- `OctoArmor` = router and connector hub
- `Aether Antivirus` = the scanning and containment stack

## Current naming rule

Use `Aether Antivirus` when talking about the implemented defensive stack as a whole.

Do not describe it as:
- a separate standalone API
- a separate exported class
- a distinct runtime unrelated to the modules above

## Current source anchors

- `agents/antivirus_membrane.py`
- `agents/kernel_antivirus_gate.py`
- `scripts/agentic_antivirus.py`
- `src/symphonic_cipher/scbe_aethermoore/concept_blocks/web_agent/semantic_antivirus.py`
- `docs/KERNEL_ANTIVIRUS_SCBE.md`
- `docs/SCBE_WEB_AGENT_ARCHITECTURE.md`
