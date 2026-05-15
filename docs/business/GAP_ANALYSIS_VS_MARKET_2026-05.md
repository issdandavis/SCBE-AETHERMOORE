# SCBE-AETHERMOORE — Gap Analysis vs. Market
> May 2026 | Based on codebase audit + competitive scan

---

## Summary

SCBE is ahead of the market on mathematical depth (hyperbolic geometry, PQC, BFT), workspace provenance, and adversarial detection. It is behind on operator UX surface, third-party framework integrations, and cloud-hosted onboarding. The gaps are real but buildable — none require core re-architecture.

---

## What We Actually Have (Verified in Codebase)

| Capability | Status | Location |
|-----------|--------|----------|
| 14-layer governance pipeline | **Built** | `src/harmonic/` |
| Post-quantum crypto (ML-KEM-768, ML-DSA-65) | **Built** | `src/crypto/` |
| Workspace audit chain (sha256 chain-of-custody) | **Built** | `packages/agent-bus/`, `packages/agent-bus-py/` |
| Trap-in-good-loops adversarial gate | **Built** | `packages/cli/bin/scbe.js` |
| Multi-agent fleet + agent registry | **Built** | `src/fleet/` (45 files) |
| Polly Pads (specialized agent modes) | **Built** | `src/fleet/polly-pads/` |
| Multi-tenant SaaS routes (tenants/flocks/sheep) | **Built** | `src/api/saas_routes.py` |
| Stripe billing + webhooks | **Built** | `src/api/stripe_billing.py` |
| Self-healing orchestrator | **Built** | `src/selfHealing/` |
| Governance engine + decision envelopes | **Built** | `src/governance/` |
| BFT consensus (HYDRA) | **Built** | `hydra/` (40+ files) |
| Sacred Tongues tokenizer (6D) | **Built** | `packages/sixtongues/`, `src/tokenizer/` |
| Red/Blue adversarial arena | **Built** | `src/security-engine/redblue-arena.ts` |
| Spectral coherence (FFT, L9-10) | **Built** | `src/spectral/` |
| Free LLM governance routes | **Built** | `src/api/free_llm_routes.py` |
| CLI (scbe + scbe-agent-bus) | **Built + Published** | `packages/cli/`, `packages/agent-bus-py/` |
| PyPI packages (2) | **Published** | scbe-aethermoore 4.1.3, scbe-agent-bus 0.3.0 |
| npm packages (4) | **Published** | scbe-aethermoore, scbe-agent-bus, @scbe/kernel, @scbe/sixtongues |
| GeoSeal coder pair system | **Built** | `src/api/geoseal_*.py` |
| In-memory metrics store | **Built (partial)** | `src/api/main.py` MetricsStore |
| MCP server | **Built (minimal)** | `src/mcp_server/` (3 files, semantic_mesh only) |

---

## Gap Analysis by Category

### 1. Operator UX — CRITICAL GAP

**What peers have:**
- LangSmith: Full web dashboard — trace explorer, dataset browser, human annotation queues, time-series charts
- Aurascape: Policy management UI, governance report viewer
- Lakera Guard (Check Point): Dashboard with prompt injection heatmaps and trend lines
- NeMo Guardrails: YAML/Colang config editors with UI preview

**What SCBE has:**
- No `ui/` directory at all
- Governance decisions are JSON over REST — no visual layer
- In-memory `MetricsStore` (not persisted, not exportable)

**Gap:**
- No web dashboard for viewing governance decisions, audit trails, or system health
- No time-series analytics (what % of prompts were DENY this week vs last week?)
- No alert management UI (configure thresholds visually)

**Impact:** Buyers in security/compliance ask for a dashboard in the first demo. Without one, the product looks like a library, not a product.

**Build priority:** High. A read-only Next.js dashboard over the existing REST API would close 80% of this gap.

---

### 2. Observability & Telemetry Export — HIGH GAP

**What peers have:**
- Darktrace: Splunk/SIEM integration, native Prometheus metrics
- CrowdStrike AIDR: Falcon telemetry pipeline, real-time streaming
- LangSmith: OpenTelemetry traces exportable to Datadog/Jaeger
- Azure AI Content Safety: Azure Monitor integration out of the box

**What SCBE has:**
- `MetricsStore` in `main.py` is in-memory, no persistence, no export
- No `/metrics` Prometheus endpoint
- No OpenTelemetry SDK wired up
- No Splunk/SIEM integration

**Gap:**
- Enterprise buyers already have Splunk, Datadog, or ELK. They expect governance decisions to flow there automatically.
- No way to set alerts on DENY rate spikes without building custom polling

**Build priority:** Medium-High. Adding a `/metrics` (Prometheus format) endpoint to main.py is a day of work and opens every enterprise door.

---

### 3. Framework Integrations — HIGH GAP

**What peers have:**
- NeMo Guardrails: Native LangChain integration, CrewAI support, AutoGen adapter
- Guardrails AI: `pip install guardrails-ai` + validators for Pydantic models; LangChain LCEL integration
- Rebuff: Drop-in middleware for LangChain chains
- Arize Phoenix: LangChain/LlamaIndex tracing callbacks

**What SCBE has:**
- REST API only — no native LangChain `Tool`, no CrewAI plugin, no AutoGen integration
- No LlamaIndex integration for RAG governance
- No LangGraph node type

**Gap:**
- The three most common agentic frameworks (LangChain, CrewAI, AutoGen) have no SCBE adapter
- Developers must write REST wrapper code to integrate — high friction
- No "install and use in 5 lines" story

**Build priority:** High. A `scbe-langchain` and `scbe-autogen` adapter package (thin REST wrappers) would close this entirely. Two packages, ~500 lines each.

---

### 4. Agent-to-Agent Protocol Compliance — MEDIUM GAP

**What peers have:**
- Google A2A protocol (agent-to-agent): growing ecosystem; agents advertise capabilities via Agent Cards
- Anthropic MCP: Tool exposure standard; Claude Code, Cursor, Windsurf all use it
- OpenAI Assistants API function calling schema

**What SCBE has:**
- MCP server exists (`src/mcp_server/semantic_mesh.py`) but is minimal (3 files, no tool registration)
- No Google A2A adapter or Agent Card publisher
- No standardized tool schema for external agents to discover SCBE governance tools

**Gap:**
- SCBE can't be discovered or auto-wired by Claude Code, Cursor, or any A2A-compatible orchestrator
- The MCP server exposes `semantic_mesh` only — governance tools (trap_dispatch, workspace_new, governance_check) are not exposed as MCP tools

**Build priority:** Medium. Expanding the MCP server to expose trap_dispatch and workspace_new as MCP tools would let Claude Code use SCBE governance natively. ~1 day of work.

---

### 5. Structured Output Validation (Rails Pattern) — MEDIUM GAP

**What peers have:**
- Guardrails AI: "Guardrails" schema — define validators (format, length, toxicity, PII) on LLM outputs; re-prompt on failure
- NeMo Guardrails: Output rails — validate structured JSON, detect hallucinated fields, enforce schema
- LangSmith: Dataset-based evaluation of structured output quality

**What SCBE has:**
- Governs input prompts (trap gate) and agent actions (workspace audit)
- `stage6_constrained_decoding.py` does constrained generation for Sacred Tongues coding — not general structured output validation
- No schema-validator-on-output pattern

**Gap:**
- SCBE prevents bad inputs from reaching models but does not validate that model outputs conform to declared schema
- This is a distinct attack surface: models can be manipulated to output malformed JSON that downstream code parses incorrectly

**Build priority:** Medium. Could be built as a `scbe-output-guard` module using existing governance primitives.

---

### 6. Content Moderation (Categories) — MEDIUM GAP

**What peers have:**
- Azure AI Content Safety: Hate, violence, sexual, self-harm categories with severity levels
- Perspective API (Google): Toxicity, severe toxicity, insult, threat, identity attack
- Amazon Comprehend Toxicity: 7 categories with confidence scores
- OpenAI Moderation API: Free, covers most content categories

**What SCBE has:**
- Adversarial/governance detection (SCONE-tagged prompts, hyperbolic distance scoring)
- DENY decision for recognized attack patterns
- No built-in hate/violence/CSAM category classifiers

**Gap:**
- SCBE is strong at detecting _adversarial AI agent actions_ (jailbreaks, treasury drains, ownership exploits)
- It is not a content moderation layer for hate speech, toxicity, or CSAM in general text
- Enterprise deployments often need both: governance (what SCBE does) AND content safety (what Azure/Perspective do)

**Build priority:** Low for core product. Frame this as a composability story: "use Azure AI Content Safety for content categories, SCBE for agent governance." Position them as complementary, not competing. Add an integration adapter if customers ask.

---

### 7. RAG-Specific Attack Surface — MEDIUM GAP

**What peers have:**
- Lakera Guard: RAG poisoning detection, indirect prompt injection via retrieved documents
- Rebuff: Canary token injection in retrieved context to detect exfiltration attempts
- LlamaGuard 3: Meta's model fine-tuned for RAG safety evaluation

**What SCBE has:**
- `search_enrichment.py` and `search_routes.py` exist but are search tooling, not RAG security
- Trap gate catches adversarial prompts before dispatch but doesn't inspect retrieved document context
- No canary token injection for retrieved context

**Gap:**
- If SCBE is placed in front of a RAG agent, it governs the query but not the poison in the retrieved documents
- Indirect prompt injection through document retrieval is currently undetected

**Build priority:** Medium. Add document context inspection to trap_dispatch flow — flag documents containing SCONE-tagged adversarial patterns.

---

### 8. Real-Time Push Alerts — LOW-MEDIUM GAP

**What peers have:**
- LangSmith: Slack/email alerts on eval regressions, threshold crossings
- Aurascape: PagerDuty integration for governance policy violations
- CrowdStrike AIDR: Falcon Fusion SOAR for automated response workflows

**What SCBE has:**
- Stripe webhook handler (inbound) — not outbound governance alerts
- Governance decisions are synchronous responses — callers poll or handle in-request
- No `/webhooks` endpoint for SCBE to push DENY/ESCALATE events outward

**Gap:**
- No way for a security team to get paged when DENY rate spikes
- No Slack notification when an adversarial prompt hits the trap gate

**Build priority:** Low-Medium. Add an outbound webhook config (URL + secret) that fires on DENY/ESCALATE decisions. ~1 day.

---

### 9. Self-Serve Cloud Onboarding — HIGH GAP (Business)

**What peers have:**
- Every SaaS competitor has a cloud sign-up flow: enter email, get API key, call the API
- LangSmith: Free tier, instant access
- Lakera Guard: Self-serve developer tier
- Guardrails AI Hub: Cloud-hosted validator registry

**What SCBE has:**
- Stripe billing routes built (`stripe_billing.py`, `saas_routes.py`)
- Multi-tenant architecture exists in code
- No deployed cloud endpoint that customers can actually sign up for

**Gap:**
- The backend plumbing for SaaS exists. There is no `cloud.aethermoore.com` where someone can sign up and get an API key in 2 minutes.
- This is the biggest business gap — not a technical gap.

**Build priority:** Critical for revenue. Deploy the existing FastAPI app behind a public domain with Stripe Checkout wired to API key provisioning. The code is there. It needs a deployment.

---

### 10. Longitudinal Behavioral Baseline — MEDIUM GAP

**What peers have:**
- Darktrace: Builds a behavioral fingerprint per entity over time; anomalies relative to that baseline
- Arize Phoenix: Drift detection on model inputs/outputs over time
- Whylogs/WhyLabs: Statistical profiling of LLM I/O distributions

**What SCBE has:**
- Workspace lineage: audit chain of what happened in a workspace session
- No cross-workspace, cross-tenant longitudinal baseline
- No drift detection on governance score distributions over time

**Gap:**
- Can detect adversarial intent at request time but cannot flag when a user's behavior pattern is shifting toward adversarial (e.g., probing over many sessions)
- No "this user normally gets 2% DENY rate; today it's 40%" signal

**Build priority:** Medium-Low. Needs a time-series store (postgres or even SQLite) and a cron job to compute per-tenant decision distributions.

---

### 11. Multimodal Governance — LOW GAP (Now)

**What peers have:**
- Azure AI Content Safety: Image safety analysis
- Amazon Rekognition: Image/video content moderation
- Google Vertex AI Safety: Multimodal input safety filters

**What SCBE has:**
- Text-only governance pipeline
- `src/video/` directory exists (video processing) but no governance integration
- No image or audio input modality in the trap gate

**Gap:**
- As agentic systems use vision models (GPT-4o, Gemini, Claude with vision), inputs include images
- SCBE's trap gate only governs text prompts today

**Build priority:** Low for 2026. Flag this as roadmap. Becomes critical when vision-capable agent deployments are the norm (2027+).

---

## Capability Matrix vs. Direct Competitors

| Capability | SCBE | Guardrails AI | NeMo Guardrails | LangSmith | Lakera Guard | Aurascape |
|-----------|------|--------------|----------------|-----------|-------------|----------|
| Hyperbolic cost escalation | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Post-quantum crypto | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Workspace audit chain | ✅ | ❌ | ❌ | Partial | ❌ | Partial |
| Multi-agent BFT governance | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Adversarial trap gate | ✅ | Partial | ✅ | ❌ | ✅ | ❌ |
| Multi-tenant SaaS architecture | ✅ (code) | ✅ | ❌ | ✅ | ✅ | ✅ |
| Stripe billing | ✅ (code) | ✅ | ❌ | ✅ | ✅ | ✅ |
| **Web dashboard** | ❌ | Partial | ❌ | ✅ | ✅ | ✅ |
| **Cloud-hosted onboarding** | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |
| **LangChain/AutoGen integration** | ❌ | ✅ | ✅ | ✅ | Partial | ❌ |
| **Prometheus/OTel metrics** | ❌ | Partial | ❌ | ✅ | Partial | Partial |
| **Outbound webhook alerts** | ❌ | Partial | ❌ | ✅ | ✅ | ✅ |
| **Structured output validation** | ❌ | ✅ | ✅ | Partial | ❌ | Partial |
| **Full MCP server** | Partial | ❌ | ❌ | ❌ | ❌ | ❌ |
| **RAG attack detection** | ❌ | Partial | Partial | ❌ | ✅ | ❌ |
| Behavioral baseline / drift | ❌ | ❌ | ❌ | ✅ | Partial | Partial |
| Self-serve API key signup | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ |

---

## Priority Order

| Priority | Gap | Effort | Revenue Impact |
|----------|-----|--------|---------------|
| 1 | Deploy cloud onboarding (existing code → hosted endpoint) | Medium | Direct: unblocks every sales conversation |
| 2 | LangChain + AutoGen adapters | Low (500 LOC each) | High: removes integration friction for 80% of prospects |
| 3 | Prometheus `/metrics` endpoint | Low (1 day) | Medium: enterprise prerequisite |
| 4 | Web dashboard (read-only) | Medium-High | High: demo credibility |
| 5 | Expand MCP server (expose trap_dispatch, workspace_new) | Low (1 day) | Medium: Claude Code + Cursor ecosystem |
| 6 | Outbound webhooks (DENY/ESCALATE events) | Low (1 day) | Medium: SecOps integration |
| 7 | RAG document context inspection in trap gate | Medium | Medium: next-gen agent use cases |
| 8 | Structured output validation module | Medium | Medium: Guardrails AI overlap |
| 9 | Behavioral baseline / drift detection | High | Low-Medium: differentiator at enterprise scale |
| 10 | Multimodal governance | High | Low (2026), High (2027+) |

---

## What We Have That Nobody Else Does

These are genuine moats. Don't trade them away for speed:

1. **Hyperbolic geometry cost escalation** — mathematically proven, patent-protected. 117,000x adversarial cost. Nobody else has this.
2. **Post-quantum crypto in a governance pipeline** — PQC vendors do crypto. Security vendors do governance. SCBE does both, integrated.
3. **Sacred Tongues cryptolinguistic audit trail** — unique domain separation with phi-weighted spectral fingerprints.
4. **Workspace audit chain with sha256 chain-of-custody** — provenance at the action level, not just the request level.
5. **BFT multi-agent consensus** — no single agent can approve its own risky action.
6. **Free-only dispatch enforcement** — hard-coded at the parser level; can't accidentally bill users.

---

_Last updated: 2026-05-14_
