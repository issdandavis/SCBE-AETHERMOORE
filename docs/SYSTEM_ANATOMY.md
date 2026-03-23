# SCBE-AETHERMOORE System Anatomy

*The system mapped to a body. Life made it work — we just borrow the patterns.*

---

## The Body Map

```
ORGAN SYSTEM              SCBE MODULE                    FUNCTION
─────────────────────────────────────────────────────────────────────

SKULL (crystal lattice)   src/ai_brain/phdm-core.ts      16-polyhedra cognitive container
                          src/crypto/quasicrystal_lattice Aperiodic lattice = no exploitable patterns
                          PHDM Notion Ch.6               Dual lattice with phason shifts

BRAIN (21D state)         src/ai_brain/unified-state.ts   21D canonical state vector
                          src/ai_brain/cymatic-voxel-net  Neurons at Chladni nodal points
                          src/ai_brain/tri-manifold       3-layer manifold lattice

SPINE (HYDRA)             hydra/spine.py                  Central coordinator
                          hydra/__init__.py               "Many heads, one governed body"
                          hydra/ledger.py                 Action/decision audit trail

NERVOUS SYSTEM            14-layer pipeline               Signals travel L1→L14
  Sensory (L1-L4)         src/harmonic/pipeline14.ts      Context → Poincare embedding
  Processing (L5-L10)     src/harmonic/hyperbolic.ts      Distance, breathing, phase, spectral
  Decision (L11-L13)      src/harmonic/governanceSim.ts   Triadic consensus → ALLOW/DENY
  Motor (L14)             src/harmonic/audioAxis.ts       FFT telemetry output

IMMUNE SYSTEM             src/gateway/COMPUTATIONAL_IMMUNE Threat analysis (physics/chem/bio/math)
                          agents/antivirus_membrane.py     Semantic antivirus turnstile
                          src/ai_brain/immune-response.ts  Immune response gates

CIRCULATORY SYSTEM        src/knowledge/funnel.py          Data flows: Source → Scan → Store → Push
  Arteries (input)        src/knowledge/scrapers/          arXiv, Notion, web, S2 scrapers
  Veins (output)          scripts/push_to_hf.py            Push governed data to HuggingFace
  Heart (pump)            hydra/research.py                Research orchestrator pumps data

SKELETON (structure)      src/harmonic/constants.ts        Phi, scales, thresholds — the fixed frame
                          src/crypto/sacred_tongues.py     6 tongues = 6 bone groups
                          packages/kernel/                 Kernel = the core skeleton

MUSCLES (execution)       agents/browser/main.py           Browser execution
                          hydra/limbs.py                   Browser/Terminal/API limbs
                          src/agentic/execution-district   Sandboxed execution environment

SKIN (boundary)           src/api/main.py                  HTTP boundary (FastAPI)
                          src/browser/hyperlane.ts          Service mesh (GREEN/YELLOW/RED zones)
                          src/network/                      Network-level boundary

EYES (perception)         agents/obsidian_researcher/      Knowledge graph builder
                          src/browser/polly_vision.py       Visual page understanding
                          src/aetherbrowser/page_analyzer    Page content analysis

HANDS (8 arms)            OctoArmor (src/fleet/octo_armor)  8-arm connector hub
  Arm 1                   GitHub connector
  Arm 2                   HuggingFace connector
  Arm 3                   Notion connector
  Arm 4                   Slack connector
  Arm 5                   Discord connector
  Arm 6                   Shopify connector
  Arm 7                   Airtable connector
  Arm 8                   Webhook connector

VOICE                     packages/sixtongues/              Sacred Tongue encoding (speech)
                          src/symphonic_cipher/              Audio-based crypto (harmonic voice)
                          scripts/article_to_video.py        TTS video generation

MEMORY                    hydra/librarian.py                 Long-term memory (SQLite)
                          hydra/ledger.py                    Decision history
                          src/knowledge/tokenizer_graph/     6D DNA memory chain
                          src/storage/                       Multi-surface storage backends

EGGS (reproduction)       src/crypto/sacred_eggs.py          GeoSeal-encrypted payloads
                          Polly Eggs                         NPC/character generation
                          training-data/                     Training data = offspring

FEATHERS (Raven)          agents/obsidian_researcher/        Raven-like reconnaissance
                          hydra/swarm_browser.py             Swarm scouting
                          Polly (the raven NPC)              Sarcastic guide/scout

DNA (encoding)            src/knowledge/tokenizer_graph/memory_chain.py
                          6D coordinates = genetic code
                          Chain hash = parent→child lineage
```

---

## Mermaid System Flow

```mermaid
graph TB
    subgraph SKULL["SKULL: Crystal Lattice Brain"]
        PHDM[PHDM 16-Polyhedra<br/>Quasicrystal Lattice]
        BRAIN[21D Unified State<br/>Cymatic Voxel Net]
        PHDM --> BRAIN
    end

    subgraph SPINE["SPINE: HYDRA Orchestration"]
        HYDRA_SPINE[HydraSpine<br/>Central Coordinator]
        HEADS[HydraHeads<br/>Claude/Codex/GPT/Local]
        LEDGER[Ledger<br/>Audit Trail]
        LIBRARIAN[Librarian<br/>Long-term Memory]
        HYDRA_SPINE --> HEADS
        HYDRA_SPINE --> LEDGER
        HYDRA_SPINE --> LIBRARIAN
    end

    subgraph NERVOUS["NERVOUS: 14-Layer Pipeline"]
        L1_4[L1-L4: Sensory<br/>Context → Poincare]
        L5_7[L5-L7: Processing<br/>Distance + Breathing + Phase]
        L8[L8: Multi-Well<br/>Hamiltonian Realms]
        L9_10[L9-L10: Spectral<br/>FFT Coherence + Spin]
        L11[L11: Triadic<br/>Temporal Consensus]
        L12[L12: Harmonic Wall<br/>H = π^φd*]
        L13[L13: Decision<br/>ALLOW/QUARANTINE/DENY]
        L14[L14: Motor<br/>Audio Axis + PQC]
        L1_4 --> L5_7 --> L8 --> L9_10 --> L11 --> L12 --> L13 --> L14
    end

    subgraph IMMUNE["IMMUNE: Defense Systems"]
        CIS[Computational<br/>Immune System]
        AVM[Antivirus<br/>Membrane]
        TURNSTILE[Turnstile<br/>Gate]
        CIS --> AVM --> TURNSTILE
    end

    subgraph CIRCULATORY["CIRCULATORY: Data Flow"]
        SCRAPERS[Scrapers<br/>arXiv/Notion/Web/S2]
        FUNNEL[Knowledge<br/>Funnel]
        BASIN[Basin<br/>Data Lake]
        GRAPH[Tokenizer<br/>Graph 6D]
        HF[HuggingFace<br/>Push]
        SCRAPERS --> FUNNEL --> BASIN --> GRAPH --> HF
    end

    subgraph SKELETON["SKELETON: Structure"]
        TONGUES[6 Sacred Tongues<br/>KO AV RU CA UM DR]
        PHI[φ-Weights<br/>1.0 → 11.09]
        CRYPTO[PQC Primitives<br/>ML-KEM + ML-DSA]
        TONGUES --> PHI
        TONGUES --> CRYPTO
    end

    subgraph HANDS["HANDS: OctoArmor 8-Arm Hub"]
        GH[GitHub]
        HF2[HuggingFace]
        NOTION[Notion]
        SLACK[Slack]
        DISCORD[Discord]
        SHOPIFY[Shopify]
        AIRTABLE[Airtable]
        WEBHOOK[Webhooks]
    end

    subgraph MUSCLES["MUSCLES: Execution"]
        BROWSER[Browser Agent]
        LIMBS[HYDRA Limbs]
        SANDBOX[Execution<br/>District]
    end

    subgraph SKIN["SKIN: Boundaries"]
        API[FastAPI<br/>Endpoints]
        HYPERLANE[HyperLane<br/>Service Mesh]
        NETWORK[SpaceTor<br/>Network]
    end

    subgraph STORAGE["MEMORY: Multi-Surface Storage"]
        OCTREE[HyperbolicOctree<br/>3D Spatial]
        LATTICE[Lattice25D<br/>2.5D Cyclic]
        QC[QuasiCrystal<br/>6D Tensor]
        CONE[CymaticCone<br/>Octree+Chladni]
        SSC[SemiSphereCone<br/>Adaptive Density]
        LIGHTNING[Lightning<br/>Query Engine]
        TICTAC[TicTac Grid<br/>Pattern Encoding]
    end

    subgraph EGGS["EGGS: Reproduction"]
        SACRED_EGGS[Sacred Eggs<br/>Sealed Payloads]
        POLLY_EGGS[Polly Eggs<br/>NPC Generation]
        TRAINING[Training Data<br/>SFT/DPO]
    end

    %% Connections between organ systems
    SKULL --> NERVOUS
    BRAIN --> L8
    SPINE --> NERVOUS
    HYDRA_SPINE --> MUSCLES
    NERVOUS --> IMMUNE
    L13 --> IMMUNE
    IMMUNE --> SKIN
    CIRCULATORY --> STORAGE
    SKELETON --> NERVOUS
    TONGUES --> L1_4
    HANDS --> SKIN
    MUSCLES --> SKIN
    STORAGE --> CIRCULATORY
    EGGS --> CIRCULATORY
    LIGHTNING --> STORAGE

    %% Feedback loops
    L14 -->|Telemetry| L1_4
    LEDGER -->|Audit| L13
    GRAPH -->|Memory| BRAIN
```

---

## Health Status (Pass 2 — 2026-03-22)

```
TOTAL: 3856 passed, 39 failed, 11 collection errors = 99.0% pass rate
```

```mermaid
graph TB
    subgraph HEALTHY["HEALTHY (100% pass)"]
        style HEALTHY fill:#0a5,stroke:#0a5
        SK[SKELETON<br/>71 tests<br/>pi^phi, HKDF]
        NV[NERVOUS L13<br/>7 tests<br/>quorum, hash]
        MEM[MEMORY<br/>177 tests<br/>6 surfaces]
        DNA2[DNA<br/>43 tests<br/>spin, dispersal]
        CIRC[CIRCULATORY<br/>27 tests<br/>lightning, membrane]
        IMM[IMMUNE<br/>29 tests pass<br/>28.6% detection]
        FUS[FUSIONS<br/>13 tests<br/>3 combos]
    end

    subgraph NEEDS_WORK["NEEDS WORK (39 failures)"]
        style NEEDS_WORK fill:#a50,stroke:#a50
        QCV[QC Voxel Drive<br/>6 xfail spec features]
        GEO[Geoseed M6<br/>~8 failures<br/>spec drift]
        DYN[Dynosphere<br/>~5 failures<br/>API changed]
        BV[Braided Voxel<br/>~4 failures<br/>encoding change]
        WT[Webtoon<br/>~4 failures<br/>quality gate]
        MISC[Misc<br/>~18 failures<br/>import paths]
    end

    subgraph ISOLATED["ISOLATED (collection errors)"]
        style ISOLATED fill:#555,stroke:#555
        AE[test_aethermoore<br/>scipy missing]
        EDE[test_ede<br/>dep missing]
        PQC[test_pqc<br/>liboqs missing]
        N8N[test_n8n_bridge<br/>dep missing]
    end

    subgraph FIX_PLAN["FIX PLAN"]
        T1[Tier 1: Update imports<br/>30 min each, low risk]
        T2[Tier 2: Implement features<br/>1-2 hr each, medium risk]
        T3[Tier 3: Mark xfail<br/>5 min each, zero risk]
    end

    NEEDS_WORK --> T1
    QCV --> T2
    ISOLATED --> T3

    subgraph IMMUNE_DETAIL["IMMUNE SYSTEM GAPS"]
        ML[Multilingual: 0%<br/>NEEDS: semantic encoding]
        SD[Spin Drift: 0%<br/>NEEDS: cumulative tracker]
        AS[Adaptive Seq: 9%<br/>NEEDS: sequence detection]
        DO[Direct Override: 30%<br/>NEEDS: threshold tuning]
    end
```

## What's Left and Why

| Gap | Why it exists | Best fix | Worst fix |
|-----|---------------|----------|-----------|
| Multilingual 0% | Text metrics are language-blind | Token-level semantic encoding across tongues | Keyword blocklist (brittle) |
| Spin drift 0% | Cost rises 7x but per-message, not cumulative | Sliding window cost tracker across conversation | Lower threshold (more false positives) |
| QC float→int | `int(abs(c)*10)` loses precision | Native float gate vectors | Wider acceptance radius (loses security) |
| 11 collection errors | Module moves during rapid dev | Update import paths | Delete the test files (loses coverage) |
| 39 test failures | Spec changes not reflected in tests | Rewrite tests to match code | Rewrite code to match tests (risky) |

---

## Quick Reference: What Goes Where

| Question | Organ | Module |
|----------|-------|--------|
| "Where does thinking happen?" | Brain | `src/ai_brain/unified-state.ts` |
| "Where do decisions get made?" | Nervous L13 | `src/harmonic/governanceSim.ts` |
| "Where is data stored?" | Memory | `src/storage/` (6 surfaces) |
| "How do we talk to the outside?" | Skin | `src/api/main.py` |
| "How do we connect to services?" | Hands | `src/fleet/octo_armor.py` |
| "How do we defend against attacks?" | Immune | `agents/antivirus_membrane.py` |
| "How does data flow in?" | Circulatory | `src/knowledge/funnel.py` |
| "How do we coordinate agents?" | Spine | `hydra/spine.py` |
| "What holds it all together?" | Skeleton | `packages/kernel/` + Sacred Tongues |
| "How do we reproduce/train?" | Eggs | `src/crypto/sacred_eggs.py` + training-data/ |
| "How do we see the web?" | Eyes | `agents/obsidian_researcher/` |
| "How do we act in the world?" | Muscles | `agents/browser/main.py` |
