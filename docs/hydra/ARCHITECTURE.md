---
title: HYDRA Multi-Agent Coordination System - Architecture
status: Reference Architecture (HYDRA)
scope: Multi-agent orchestration layer above SCBE-AETHERMOORE
canonical_kernel_spec: SPEC.md
keywords:
  - HYDRA multi-agent coordination
  - GFSS spectral governance
  - Byzantine fault tolerance quorum
  - Sacred Tongue agent swarm
  - SCBE-AETHERMOORE integration
  - deterministic authorization boundary
  - audit log ledger librarian memory
---

> **Status:** Reference Architecture (HYDRA).  
> **Scope:** Multi-agent orchestration layer that runs *above* SCBE-AETHERMOORE.  
> **Canonical Kernel Spec:** See `SPEC.md` and SCBE Phase-Breath Hyperbolic Governance (Layer 1-14).  
> HYDRA is not the cryptographic kernel; it is the execution/orchestration plane.

# HYDRA Multi-Agent Coordination System – Complete Architecture

This document summarises the HYDRA Multi-Agent Coordination System as documented in the internal Notion page “HYDRA Multi-Agent Coordination System – Complete Architecture”. The goal is to make the core architectural concepts, components, and terminology available within this repository for ease of access and version control.

## Executive summary

HYDRA is a terminal-native multi-agent coordination system designed to act as “armor” for any AI model. It provides the infrastructure to run and orchestrate multiple AI heads simultaneously while enforcing strong safety guarantees through consensus voting and spectral governance. Key features include:

- Multi-tab browser orchestration – a swarm of six phase-modulated agents control parallel browser sessions.
- Cross-session memory – a librarian component stores vector embeddings and builds a knowledge graph for later retrieval.
- Byzantine fault tolerance – the system tolerates one malicious agent (f=1) out of six and originally required a 2f+1 quorum (three matching votes) for approval. Subsequent governance updates introduce risk-tiered quorums and lineage diversity checks, as outlined in the governance specification.
- Graph Fourier anomaly detection – spectral analysis of agent interactions detects collusion or drift.
- Universal AI interface – any AI model (Claude, GPT, Codex, local LLMs) can “wear” HYDRA armor via the Head abstraction.
- Terminal-native operation – a CLI and pipe-compatible interface integrate the system into shell workflows.

The system historically advertised a “518,400× security multiplier” when all six Sacred Tongues were used. Governance corrections clarify that this figure derives from the combinatorial diversity of agent permutations (6!×6!) and should not be interpreted as a cryptographic security factor; the actual weight product of the six agents is approximately 1,051×.

## Layered architecture

HYDRA’s architecture is organised into seven layers, spanning from the user interface down to the core cryptographic engine. The simplified ASCII diagram below captures the layering:

```
┌─────────────────────────────────────────────────────────────┐
│                  LAYER 7: USER INTERFACE                    │
│  Terminal CLI • Browser Tabs • API Endpoints • REPL         │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│             LAYER 6: HYDRA COORDINATION                     │
│  Spine  •  Heads  •  Limbs  •  Librarian                    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│           LAYER 5: SPECTRAL GOVERNANCE                      │
│  Graph Fourier Scan Statistics  •  Byzantine Consensus      │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              LAYER 4: SWARM BROWSER                         │
│  Six Sacred Tongue agents with phase-modulated roles        │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│            LAYER 3: BROWSER BACKENDS                        │
│  Chrome MCP • Playwright • Selenium • CDP                   │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│             LAYER 2: SCBE API GATEWAY                       │
│  Four-tier authentication and SCBE core endpoints           │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│          LAYER 1: SCBE-AETHERMOORE CORE                     │
│  14-layer cryptographic pipeline with harmonic filters      │
└─────────────────────────────────────────────────────────────┘
```

Each layer builds on the one below it: the user interface accepts commands and displays results; the coordination layer orchestrates agents, memory and persistence; the spectral governance layer uses GFSS and quorum voting to enforce safety; the swarm browser provides domain-separated capabilities via six agents; backend layers handle browser drivers, API gateway calls and the cryptographic core.

## Core components

### HYDRA Spine (Coordinator)

The Spine is the central orchestrator. It manages sessions, registers AI heads and execution limbs, and synchronises state across the system. It interacts with the Librarian and Ledger for memory and audit trails. In code it holds dictionaries of heads and limbs and exposes methods like `register_head`, `delegate_task` and `sync_state`.

### HYDRA Heads (Universal AI interface)

A Head wraps a specific AI model (Claude, GPT, Codex, or local LLM) and exposes a universal `process` method. It mediates input prompts through governance (intent validation), executes the prompt on the underlying model, and stores results in the Librarian. Multiple heads can be registered for one session, enabling ensemble reviews or parallel tasks.

### HYDRA Limbs (Execution backends)

Limbs execute real-world actions on behalf of the system. They include browser limbs (driven by Playwright, Selenium or Chrome MCP) for navigation and interaction, API limbs for REST/GraphQL calls, and tool limbs for file I/O or shell commands. A `BrowserLimb` exposes methods such as `navigate`, `click`, and `extract` to interact with web pages.

### HYDRA Librarian (Memory & Knowledge)

The Librarian provides cross-session memory and knowledge graph capabilities. It uses sentence-transformer embeddings and an SQLite database to store textual memories, perform semantic search and build a graph of relationships. Key tables include `memories` (storing content and embeddings) and `knowledge_graph` (edges between memories). The Librarian integrates with SCBE governance to control access to sensitive memories.

### HYDRA Ledger (Persistent state)

The Ledger logs all actions, decisions and agent states in a SQLite database. Tables include `sessions` (metadata), `events` (actions and governance decisions) and `agent_state` (agent metrics). This immutable audit trail supports compliance and post-hoc analysis.

### HYDRA CLI (Terminal interface)

The CLI provides pipe-friendly commands to start HYDRA, process workflows and interact with agents. Users can pipe JSON tasks into the CLI or run it in REPL mode.

## Swarm browser: the six Sacred Tongues

HYDRA’s swarm browser uses six specialised agents operating at different phase angles to separate concerns and prevent cross-contamination. Their roles and approximate weights (from the original risk model) are:

| Agent | Phase | Role | Key actions | Weight |
| --- | --- | --- | --- | --- |
| KO-SCOUT | 0° | Navigation & coordination | `goto`, `back`, `forward`, `refresh` | 1.00 |
| AV-VISION | 60° | Visual perceptions | `screenshot`, `analyze_layout`, `detect_elements` | 1.38 |
| RU-READER | 120° | Content extraction | `extract_text`, `parse_table`, `get_links` | 2.62 |
| CA-CLICKER | 180° | Interaction | `click`, `hover`, `drag`, `drop` | 6.18 |
| UM-TYPER | 240° | Input & secrets | `type`, `fill_form`, `upload_file` | 4.24 |
| DR-JUDGE | 300° | Verification & validation | `verify_page`, `check_state`, `validate_data` | 11.09 |

The weights roughly capture the risk level of each action; heavier weights correspond to higher risk and therefore stronger governance scrutiny. HYDRA originally required a 3/6 quorum for actions, but the governance system now uses tiered quorums based on risk.

## Spectral governance & consensus

The Spectral Governance layer combines Graph Fourier Scan Statistics (GFSS) with a Byzantine fault-tolerant consensus. GFSS constructs an interaction graph, computes the Laplacian and performs a Fourier transform to detect anomalous energy spikes. Meanwhile, a quorum voting mechanism (originally count >= 3 for six agents) determines approval. Recent corrections replace this flat threshold with a risk-tiered governance class that requires higher quorums (4/6, 5/6, 6/6) and lineage diversity checks for medium, high and critical actions.

## Integration with SCBE-AETHERMOORE

HYDRA sits atop the SCBE-AETHERMOORE cryptographic pipeline. All actions pass through layers such as Hyperbolic Distance, Spectral Coherence, Harmonic Scaling and Risk Decision before being allowed, denied or flagged for review. Critical operations may require multi-signature governance, where multiple Sacred Tongues sign off on actions. For example, basic navigation is Tier 1, form submission with sensitive data is Tier 3, and system-level changes are Tier 6.

## File structure & codebase

The HYDRA codebase is organised as follows:

```
hydra/
├── __init__.py      # Package initialisation
├── base.py          # Base classes and types
├── spine.py         # Coordinator
├── head.py          # Universal AI interface
├── limbs.py         # Execution backends
├── librarian.py     # Memory & knowledge graph
├── ledger.py        # SQLite persistence
├── spectral.py      # Graph Fourier analysis
├── consensus.py     # Voting & governance
└── cli.py           # Terminal interface

agents/
└── swarm_browser.py  # Implementation of the six Sacred Tongues

docs/
└── POLLY_PADS_ARCHITECTURE.md  # “Clone Trooper armour” concept
```

The combined code exceeds 2,800 lines and is accompanied by extensive tests and research notes.

## Performance benchmarks

Benchmarks collected on the Notion page indicate HYDRA can coordinate six parallel browser tabs with an average latency of ~47 ms, while Byzantine consensus adds about 12 ms overhead. Semantic search over 10,000 memories completes in under 50 ms, and vector embeddings take around 23 ms each. CLI throughput can process around 500 commands per second, with end-to-end latency under 200 ms.

## Use cases

- Multi-AI code review – register multiple AI heads to analyse a pull request from different perspectives, delegate tasks and reach a consensus on approval.
- Autonomous web scraping – define a JSON workflow and pipe it into the CLI; agents navigate, extract data and verify results.
- Cross-session knowledge building – store memories in the Librarian, later perform semantic search to recall context and build knowledge graphs across sessions.

## Security features

HYDRA incorporates multiple security controls:

- Byzantine fault tolerance – tolerates one malicious agent and uses quorums to agree on actions.
- Spectral anomaly detection – GFSS catches collusion and drift by analysing the frequency domain of agent interactions.
- SCBE governance – all actions pass through a multilayer pipeline that applies exponential cost scaling and risk decisions.
- Audit trail – every action and decision is logged in the Ledger for compliance and post-mortem analysis.

## Roadmap

Planned enhancements include WebSocket support for real-time coordination, distributed deployments, advanced graph machine learning for anomaly detection, integration with additional AI backends (Gemini, Mistral), WASM compilation for browser-native execution, quantum-resistant key exchange, federated learning, visual dashboards, self-healing swarms, predictive task delegation and natural-language control. An open-source community release is envisioned after these features are stabilised.

## Related documentation

This summary is based on the internal Notion page and related documents. For further details, consult the following pages:

- HYDRA Governance Specification – Mathematical Corrections – describes the risk-tiered governance model, Dilithium3 signatures, execution permits and corrected state computation.
- Master Wiki & Navigation Hub – provides a directory of technical, marketing and world-building pages and explains how the SCBE-AETHERMOORE ecosystem fits together.
- Roundtable Security – details the multi-signature governance requirements and the concept of Sacred Tongues.
- Spectral Anomaly Detection – expands on GFSS and provides proofs and references.

Prepared February 2026. This document captures the state of HYDRA v1.1.0 and includes corrections and clarifications from subsequent governance audits.
