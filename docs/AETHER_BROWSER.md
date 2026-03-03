# Aether Browser (HYDRA Layer 4)

Aether Browser is the swarm browser execution plane within HYDRA, providing
SCBE-governed multi-agent web automation via six Sacred Tongue agents.

## Invocation

```bash
# Launch swarm browser with all six tongue agents
python -m hydra.swarm_browser --tongues=KO,AV,RU,CA,UM,DR --backend=playwright

# Launch with specific backend
python -m hydra.swarm_browser --backend=selenium

# CLI swarm mode
python -m hydra.cli_swarm
```

## Architecture

Aether Browser sits at HYDRA Layer 4 (Swarm Browser) and Layer 3 (Browser Backends):

```
HYDRA Spine (orchestrator)
  |
  +-- Spectral Governance (anomaly detection)
  |
  +-- Swarm Browser (6 tongue agents)
  |     |
  |     +-- KO-SCOUT (0deg)   -- Navigate
  |     +-- AV-VISION (60deg)  -- Screenshot / capture
  |     +-- RU-READER (120deg) -- Extract / parse
  |     +-- CA-CLICKER (180deg)-- Interact
  |     +-- UM-TYPER (240deg)  -- Input
  |     +-- DR-JUDGE (300deg)  -- Verify / validate
  |
  +-- Browser Backends
        +-- Playwright (default)
        +-- Selenium
        +-- Chrome DevTools Protocol (CDP)
```

## Security Model

Every browser action passes through the SCBE governance pipeline:

1. **L13 Decision Gate**: Every screenshot/extract/interact operation is evaluated
   through the 14-layer pipeline. DENY blocks the action, QUARANTINE flags for
   review, ALLOW permits execution.

2. **G6 Phase-Lock Gate**: When agents operate in ENTANGLED mode, phase angles
   must be sufficiently synchronized (lock score >= 0.8) for joint actions.
   Desynchronized agents degrade to observe-only mode.

3. **Quorum Consensus (G5)**: High-risk browser actions (form submission,
   payment flows, credential entry) require 4/6 agent quorum before execution.

4. **Ledger Audit**: Every voxel commit from browser operations is recorded
   in the append-only ledger with idempotency keys and quorum proofs.

5. **Antivirus Membrane**: The `agents/antivirus_membrane.py` threat scanner
   evaluates page content before extraction, blocking prompt injection and
   malicious payloads.

## Threat Model

| Threat | Mitigation |
|--------|------------|
| Prompt injection in scraped content | Antivirus membrane scans all extracted text |
| Malicious redirects | Navigation restricted to allowed domains per task |
| Credential exfiltration | ENCRYPT_TRANSPORT required for sensitive data; COLLAPSED agents cannot encrypt |
| Swarm desynchronization | Phase-lock gate degrades unlocked agents to observe-only |
| Single compromised agent | Byzantine quorum (f=1) tolerates one faulty agent |

## Key Files

| File | Purpose |
|------|---------|
| `hydra/swarm_browser.py` | Six-agent browser execution plane |
| `hydra/browsers.py` | Browser backend adapters |
| `hydra/swarm_governance.py` | SCBE decision integration for browser actions |
| `hydra/switchboard.py` | Task routing and dispatch |
| `agents/antivirus_membrane.py` | Threat scanning + turnstile |
| `agents/browser_agent.py` | SCBE-governed browser automation |
| `docs/AETHERBROWSE_BLUEPRINT.md` | Original blueprint |
| `docs/AETHERBROWSE_GOVERNANCE.md` | Governance integration details |
