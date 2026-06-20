# agents/

Root-level agent implementations. **This tree is live code, not an empty shim** —
~8,400 LOC of working, imported modules that other parts of the repo depend on
(`src/api`, the gates, the n8n bridge). An earlier note claimed this directory had
been extracted to a separate `scbe-agents` repo and emptied; that is **out of date**.
The full standalone HYDRA *agent runtime* does live separately, but the modules
below remain here and are tested.

## What's here (and tested)

| Module | Purpose |
|--------|---------|
| `antivirus_membrane.py` | Prompt-injection + malware regex scanner → `ThreatScan` (the shared primitive every gate uses) |
| `kernel_antivirus_gate.py` | Policy engine mapping kernel telemetry → ALLOW/THROTTLE/QUARANTINE/KILL/HONEYPOT |
| `extension_gate.py` | Browser-extension onboarding gate (content scan + permission/provenance scoring) |
| `linux_kernel_event_bridge.py` | Parses Falco/eBPF-style JSON events into `KernelEvent` objects |
| `agent_bus*.py` (13 files) | Free-tier task router: search → scrape → free LLM → governed output, with cost meter, signing, ledger, replay |
| `swarm_browser.py` | Six Sacred-Tongue agents doing BFT-consensus browser automation (survives 2/6 compromised) |
| `browser/` (13 files) | FastAPI governed browser fleet with PHDM geometric containment |
| `browsers/` | Pluggable backends (Playwright / Selenium / CDP / Chrome MCP) |
| `aetherbrowse_cli.py`, `research_agent.py`, `web_scraper.py`, `browser_agent.py` | Single-agent browsing/research surface |
| `obsidian_researcher/` | Knowledge-graph researcher (selftest: 9/9 pass) |
| `multi_model_modal_matrix.py` | N-model × K-modality reliability-weighted decision reducer |
| `hyperbolic_scanner.py`, `pqc_key_auditor.py` | Poincaré boundary scoring; post-quantum key audit |

## Gate stack

The governance spine composes left-to-right and is exercised by passing tests:

```
antivirus_membrane → hyperbolic_scanner → hydra.turnstile → kernel_antivirus_gate / extension_gate
```

## Run / test

```bash
PYTHONPATH=. python -m pytest tests/agents/ tests/test_swarm_judge_veto.py tests/test_openclaw_swarm.py -v
python agents/obsidian_researcher/selftest.py
python -m agents.agent_bus_cli run "..." --mode swarm
```

The full pre-split monolith state is still tagged `v-monolith-final`.
