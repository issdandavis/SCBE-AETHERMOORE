---
name: aetherbrowse-dev
description: Architecture knowledge for AetherBrowse — the SCBE-governed AI browser. Covers the agent loop (OBSERVE→EMBED→GOVERN→EXECUTE), module locations, extending the planner/perceiver/worker, Hydra bridge, and how BitSpin/ChiralityCoupling feed into browser governance decisions. Use when developing AetherBrowse features, adding new browser backends, extending the agent loop, or understanding how vision embeddings flow through the Poincaré containment pipeline.
---

# AetherBrowse Developer Guide

Use this skill when building, extending, or debugging AetherBrowse internals.

## Architecture: "Browser Inside the AI"

AetherBrowse inverts the typical AI-browser relationship. The AI doesn't "use" the browser — it **perceives through** the browser as a sensory organ. Vision is native, not bolted on.

```
Edge model:    Browser → AI sidebar (AI can see some things, sometimes)
Aether model:  AI Core → Browser as sensory organ (AI sees EVERYTHING by default)
```

## Agent Loop: OBSERVE → EMBED → GOVERN → EXECUTE

| Phase    | Layer      | Component              | File                              |
|----------|------------|------------------------|-----------------------------------|
| OBSERVE  | L1-2       | DOM snapshot + page ctx | `agents/browser/dom_snapshot.py`  |
| EMBED    | L3-5       | CLIP → 16D Poincaré    | `agents/browser/vision_embedding.py` |
| GOVERN   | L5,8,12,13 | PHDM + Bounds + Swarm  | `agents/browser/action_validator.py` |
| EXECUTE  | L14        | Browser backend action  | `agents/browsers/base.py`         |

## Module Map

### Core Runtime
| File                                   | Purpose                                          |
|----------------------------------------|--------------------------------------------------|
| `agents/browser/main.py`              | FastAPI server (port 8001), `/v1/browse` endpoint |
| `agents/browser/session_manager.py`   | AetherbrowseSession — backend + validator wrapper |
| `agents/browser/action_validator.py`  | Merges PHDM + BoundsChecker decisions            |
| `agents/browser/phdm_brain.py`        | Poincaré ball safety containment (safe_radius=0.92) |
| `agents/browser/bounds_checker.py`    | 6 geometric constraint sets (B_intent..B_gfss)   |
| `agents/browser/vision_embedding.py`  | CLIP → QR projection → Poincaré exponential map  |
| `agents/browser/dom_snapshot.py`      | Compact page representation (text, links, forms)  |

### Browser Backends
| File                              | Backend    | Notes                           |
|-----------------------------------|------------|----------------------------------|
| `agents/browsers/base.py`        | Abstract   | Interface: navigate/click/type/screenshot |
| `agents/browsers/cdp_backend.py` | CDP        | Chrome DevTools Protocol (fastest) |
| `agents/browsers/playwright_backend.py` | Playwright | Multi-browser, smart waits     |
| `agents/browsers/selenium_backend.py`  | Selenium  | Legacy compatibility            |
| `agents/browsers/chrome_mcp.py`       | Chrome MCP | Model Context Protocol          |

### Multi-Agent (Swarm)
| File                          | Purpose                                    |
|-------------------------------|--------------------------------------------|
| `agents/swarm_browser.py`    | 6 Sacred Tongue agents, Byzantine consensus |
| `agents/browser_agent.py`    | SCBE governance client + escalation         |
| `agents/antivirus_membrane.py` | Threat scanning + turnstile actions        |
| `agents/extension_gate.py`   | Enemy-first extension onboarding            |

### Governance Fields (TypeScript Canonical)
| File                                    | Purpose                               |
|-----------------------------------------|---------------------------------------|
| `src/harmonic/bitSpin.ts`              | P-bit stochastic operators (Ising)    |
| `src/harmonic/chiralityCoupling.ts`    | Global handedness constraints         |
| `src/harmonic/governanceGaugeField.ts` | Unified gauge field + phase locking   |
| `src/fleet/browser-pool.ts`           | Memory-aware browser pooling          |

## Swarm Agents (Sacred Tongues)

| Tongue | Role    | Class         | Responsibilities                     |
|--------|---------|---------------|--------------------------------------|
| KO     | Scout   | `ScoutAgent`  | URL navigation, domain risk scoring  |
| AV     | Vision  | `VisionAgent` | Visual analysis, element detection   |
| RU     | Reader  | `ReaderAgent` | Text extraction, injection detection |
| CA     | Clicker | `ClickerAgent`| Click execution, interaction         |
| UM     | Typer   | `TyperAgent`  | Form filling, sensitive fields       |
| DR     | Judge   | `JudgeAgent`  | Final decision, Byzantine quorum     |

Consensus: 4/6 ALLOW required. 2 DENY → DENY. 2+ ESCALATE → ESCALATE.

## How to Add a New Browser Backend

1. Create `agents/browsers/my_backend.py`
2. Extend `BrowserBackend` from `agents/browsers/base.py`
3. Implement: `initialize()`, `navigate()`, `click()`, `type_text()`, `screenshot()`, `execute_script()`, `get_page_content()`, `get_current_url()`, `scroll()`, `close()`
4. Register in `agents/browser/session_manager.py` `_create_backend()`
5. Add CLI option in `agents/aetherbrowse_cli.py`

## How to Extend the Governance Pipeline

1. Add constraint to `agents/browser/bounds_checker.py` `_check_all_bounds()`
2. Or wire BitSpin/ChiralityCoupling fields into `action_validator.py`
3. The spin field provides anomaly detection; chirality provides transport asymmetry
4. Both feed into the GovernanceGaugeField Lagrangian → risk decision

## Vision Pipeline

```
Screenshot (bytes)
  → CLIP ViT-B/32 (512D)
  → QR-decomposed projection (512D → 16D)
  → Poincaré exponential map: tanh(||v||/2) * v/||v||
  → SimplePHDM.check_containment()
  → SafetyDecision {ALLOW | QUARANTINE | ESCALATE | DENY}
```

## Key Formulas

- **Hyperbolic distance:** `d_H(u,v) = arcosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))`
- **Harmonic wall:** `H(d) = R^(d²)` where R=1.5 (exponential risk amplification)
- **Risk score:** `0.4 * radius_risk + 0.6 * amplified_risk` (clamped [0,1])
- **Safe radius:** 0.92 (Poincaré ball boundary)

## API Endpoints

| Endpoint               | Method | Purpose                              |
|------------------------|--------|--------------------------------------|
| `/v1/browse`           | POST   | Execute actions with containment     |
| `/v1/safety-check`     | POST   | Pre-validate without executing       |
| `/v1/containment-stats`| GET    | Aggregate safety metrics             |
| `/v1/reset-session`    | POST   | Clear browser + history              |
| `/health`              | GET    | Component status                     |
