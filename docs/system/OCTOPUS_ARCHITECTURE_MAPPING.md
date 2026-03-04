# Octopus Biology → SCBE Architecture Mapping

> Real science, real numbers, bolted onto real code.

## Why Octopus?

The octopus nervous system is the closest biological analog to a distributed AI agent fleet:
- 500M neurons, 70% in the arms (not the brain)
- Each arm makes decisions autonomously — severed arms work for ~1 hour
- Arms coordinate via a neural ring that **bypasses the brain**
- RNA editing rewrites proteins at runtime without changing DNA
- 168 protocadherin genes (3x mammals) for short-range dense wiring

Papers on octopus-inspired AI/robotics grew 54% from 2021→2024. We're not metaphoring — we're engineering.

---

## The Numbers

| Octopus | Value | SCBE Analog | Code Location |
|---------|-------|-------------|---------------|
| Total neurons | 500M | Total agent capacity across fleet | `src/fleet/octo_armor.py` |
| Brain neurons (30%) | 150M | Central governance hub | `workflows/n8n/scbe_n8n_bridge.py` |
| Arm neurons (70%) | 350M (8 arms) | 8 tentacle providers (semi-autonomous) | `src/fleet/octo_armor.py` → 20 tentacles |
| Neurons per arm | ~40-44M | Capacity per tentacle | Individual provider (Groq, Claude, etc.) |
| Neural ring (brain bypass) | Arm↔arm direct | Cross-talk JSONL bus | `artifacts/agent_comm/github_lanes/cross_talk.jsonl` |
| Suckers per arm | ~240 | Tool slots per tentacle | Endpoints/capabilities per provider |
| Neurons per sucker | ~10,000 | Processing per tool invocation | Token budget per API call |
| Protocadherins (168) | Local wiring specificity | Sacred Tongue encoding (6 tongues) | `src/symphonic_cipher/` |
| Zinc-finger TFs (~1,800) | Config space for circuits | 14-layer dressing configurations | `src/geoseed/dressing_geometric.py` |
| RNA editing (60%+ transcripts) | Runtime protein rewrite | Hot-swap model/prompt without retrain | OctoArmor provider switching |
| Chromatophore speed (<300ms) | Instant output adaptation | Sub-second response routing | `scripts/system/browser_chain_dispatcher.py` |
| 3 hearts | Separate pump circuits | Separate inference vs dispatch vs telemetry | Bridge(8001) + Webhook(8002) + AetherNet(8300) |
| Blue blood (hemocyanin) | Efficient at low O2 | Efficient at low token budgets | Rate-limited API structuring |
| Arms: 6 forage + 2 locomotion | Functional specialization | 6 Sacred Tongue tentacles + 2 infrastructure | KO/AV/RU/CA/UM/DR + n8n + SCBE Bridge |

---

## Architecture Layers (Biology → Code)

### Layer 1: Central Brain (30%) → Governance Hub
- **Bio**: Supraesophageal + subesophageal ganglia, donut-shaped around esophagus
- **Code**: SCBE 14-layer pipeline makes ALLOW/DENY/QUARANTINE decisions
- **Principle**: Sets priorities, doesn't micromanage execution

### Layer 2: Arm Ganglia (40M neurons each) → Tentacle Providers
- **Bio**: Each arm has a full neurochemical toolkit (dopamine, serotonin, GABA, glutamate, ACh, octopamine, peptides)
- **Code**: Each OctoArmor tentacle is a complete LLM provider with its own auth, rate limits, model selection
- **Principle**: Semi-autonomous — can complete tasks without central brain

### Layer 3: Neural Ring → Cross-Talk Bus
- **Bio**: Mechanostimulation of one arm generates spiking in other arms WITHOUT going through brain
- **Code**: `cross_talk.jsonl` — tentacles write packets that other tentacles read directly
- **Principle**: Peer-to-peer signaling bypasses central governance for speed

### Layer 4: Suckerotopy → Indexed Capability Registry
- **Bio**: Each sucker has a topographic address within its arm segment
- **Code**: `config/web_access_map.json` — each service has indexed capabilities per tentacle
- **Principle**: Spatial addressing, not flat lists

### Layer 5: Arm Recruitment (Nearest-Neighbor) → Load Balancing
- **Bio**: When grabbing objects, octopus recruits nearest arm first (44% of cases)
- **Code**: `browser_chain_dispatcher.py` scoring: domain match +10, idle +3, adjacent tentacle preferred
- **Principle**: Local-first routing before escalation

### Layer 6: Severed Arm Behavior → Fault Isolation
- **Bio**: Severed arms complete current task autonomously for ~1 hour
- **Code**: If a tentacle's API goes down, in-flight requests complete locally, then tentacle drops
- **Principle**: Graceful degradation, not cascade failure

### Layer 7: RNA Editing → Runtime Adaptation
- **Bio**: ADAR enzyme converts A→I in RNA, changing protein function without DNA mutation
- **Code**: Hot-swap model weights, prompt templates, provider routing without redeploying
- **Principle**: Adapt the runtime, preserve the genome (codebase)

### Layer 8: Protocadherins (168) → Sacred Tongue Encoding
- **Bio**: 10x more than other invertebrates, enable short-range dense local wiring
- **Code**: 6 Sacred Tongues (KO/AV/RU/CA/UM/DR) with phi-weighted 16x16 token grids
- **Principle**: Complexity through local specificity, not long-range broadcast

### Layer 9: Chromatophore 3-Layer System → Output Routing
- **Bio**: Chromatophores (fast/neural), Iridophores (medium/hormonal), Leucophores (constant/structural)
- **Code**: Edge response (sub-second) → Mesh routing (seconds) → Base governance (persistent)
- **Principle**: Speed tiers for different output types

### Layer 10: LACE (Skin Photoreceptors) → Edge Sensing
- **Bio**: Skin responds to light WITHOUT eyes or brain — local sense-and-act
- **Code**: Browser tentacles do local DOM parsing before escalating to governance scan
- **Principle**: Sense at the edge, not everything goes through central

---

## OctoTree Fan-Out (Sacred Geometry Mapping)

```
                    CENTRAL BRAIN (Governance Hub)
                           |
            ┌──────────────┼──────────────┐
            │         NEURAL RING          │  ← peer-to-peer bypass
            │     (cross_talk.jsonl)        │
     ┌──────┼──────┬──────┬──────┬────────┤
     KO     AV     RU     CA     UM       DR    ← 6 Sacred Tongue roots
     │      │      │      │      │        │
   ┌─┼─┐  ┌─┼─┐ ┌─┼─┐  ┌─┼─┐ ┌─┼─┐   ┌─┼─┐  ← 6 children each (36 total)
   S S S  S S S S S S  S S S S S S   S S S     ← suckers (tool slots)
```

- **Depth 0**: 1 governance hub
- **Depth 1**: 6 tongue roots (fan-out 6)
- **Depth 2**: 36 sub-nodes (6x6)
- **Depth 3**: 216 leaf workers (6x6x6)
- **Max concurrent**: 216 (configurable via AcceleratorConfig)

At depth 3, if each worker handles 10 URLs at ~300ms each:
- Sequential: 2,160 URLs × 300ms = 648 seconds
- OctoTree: 2,160 URLs / 216 workers × 300ms = **3 seconds**

That's **216x speedup**. Even at conservative depth 2 (36 workers): **36x speedup**.

---

## Key Papers (Cited)

1. Nature 2015 — Octopus genome (33K genes, 168 protocadherins, 1800 zinc-fingers)
2. Cell 2023 — Temperature-dependent RNA editing (13K+ codons recoded)
3. Current Biology 2024 — 3D molecular atlas of arm nerve cord (suckerotopy)
4. Current Biology 2023 — Neural ring bypasses brain for arm-to-arm signaling
5. PNAS 2024 — Arm topology as computational substrate (embodied computation)
6. Science Robotics 2025 — Hierarchical suction intelligence (two-tier distributed control)
7. CyberOctopus 2024 — $7.5M MURI project for octopus-inspired distributed AI
8. Science 1992 — Observational learning (first invertebrate)
9. Current Biology 2009 — Tool use (coconut shell carrying)

---

## File Map

| Component | File | Octopus Analog |
|-----------|------|----------------|
| Central governance | `workflows/n8n/scbe_n8n_bridge.py` | Central brain |
| Tentacle fleet | `src/fleet/octo_armor.py` | 8 arms |
| Cross-talk bus | `artifacts/agent_comm/github_lanes/cross_talk.jsonl` | Neural ring |
| Browser tentacles | `scripts/system/browser_chain_dispatcher.py` | Arm ganglia |
| OctoTree accelerator | `src/browser/octotree_accelerator.py` | Fan-out motor program |
| Web access map | `config/web_access_map.json` | Suckerotopy |
| Webhook receiver | `scripts/system/github_webhook_server.py` | Chromatophore input |
| IDE mesh router | `scripts/system/github_ide_mesh_router.py` | Arm specialization |
| Sacred Tongue encoding | `src/symphonic_cipher/` | Protocadherins |
| 14-layer pipeline | `src/harmonic/pipeline14.ts` | RNA editing layers |
| Repo sectioning | `scripts/system/github_repo_sectioning.py` | Camouflage (what to show/hide) |
| Dual-tentacle lanes | `scripts/system/github_dual_tentacle_router.py` | Arm coordination |
