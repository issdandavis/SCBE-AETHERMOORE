# Autonomous Web AI Agent: HuggingFace Ecosystem Research Report

**Project**: SCBE-AETHERMOORE
**Author**: Research compiled for Issac Davis
**Date**: 2026-02-21
**Scope**: Models, tools, and deployment strategies for building a deployable autonomous web AI agent integrated with the SCBE 14-layer governance pipeline

---

## Table of Contents

1. [Small-to-Medium LLMs for Fine-Tuning](#1-small-to-medium-llms-for-fine-tuning)
2. [Sentence Transformers / Embedding Models](#2-sentence-transformers--embedding-models)
3. [Web Navigation / Browser Agent Models](#3-web-navigation--browser-agent-models)
4. [Deployment Options](#4-deployment-options)
5. [Semantic Antivirus Integration](#5-semantic-antivirus-integration)
6. [Long-Running Web Agent Resilience](#6-long-running-web-agent-resilience)
7. [Mapping to Existing HuggingFace Repos](#7-mapping-to-existing-huggingface-repos)
8. [Recommended Architecture](#8-recommended-architecture)

---

## 1. Small-to-Medium LLMs for Fine-Tuning

### 1.1 Model Comparison Matrix

| Model | Params | License | LoRA Support | DPO/RLHF | VRAM (QLoRA 4-bit) | Best For |
|-------|--------|---------|-------------|-----------|---------------------|----------|
| **Qwen3-8B** | 8B | Apache-2.0 | Excellent (Unsloth, TRL) | DPO + GRPO native | ~6.5 GB | Best all-around; thinking/non-thinking modes; 131K context with YaRN |
| **Qwen2.5-7B** | 7B | Apache-2.0 | Excellent | DPO via TRL | ~6 GB | Proven, stable; strong multilingual and code |
| **Llama 3.1-8B** | 8B | Llama 3.1 Community | Excellent | DPO via TRL | ~6 GB | Large ecosystem; strong Q&A and reasoning |
| **Phi-3.5-mini** | 3.8B | MIT | Good (Torchtune, Unsloth) | DPO via TRL | ~3.5 GB | Ultra-efficient; textbook-quality training; runs on 4 GB VRAM |
| **Phi-4** | 14B | MIT | Good | DPO via TRL | ~10 GB | Strong reasoning; MIT license |
| **Mistral Small 3 (24B)** | 24B | Apache-2.0 | Good | DPO via TRL | ~16 GB | Function calling; fast conversational agent |
| **SmolLM2-1.7B** | 1.7B | Apache-2.0 | Excellent | DPO via TRL | ~2 GB | On-device; beats Qwen2.5-1.5B and Llama 3.2-1B |
| **DeepSeek-R1-Distill-Qwen3-8B** | 8B | MIT | Excellent (Unsloth) | GRPO / DPO | ~6.5 GB | Chain-of-thought reasoning distilled from 671B |
| **Fara-7B** (Microsoft) | 7B | MIT | TBD | N/A (pre-trained CUA) | ~6 GB | Computer-use agent; 73.5% WebVoyager; MIT license |

### 1.2 Top Recommendation: Qwen3-8B

Qwen3 was released April 29, 2025, with dense models ranging from 0.6B to 32B and MoE models up to 235B-A22B. The 8B variant is the sweet spot for SCBE-AETHERMOORE because:

- **Thinking/Non-Thinking Mode**: Seamlessly switches between deep reasoning (complex safety evaluations) and fast dialogue (web navigation decisions) within a single model. This maps directly to the Polly/Quasi/Demi flux states in the Polly Pad architecture.
- **Apache-2.0 License**: Fully permissive for commercial use and patent-compatible.
- **LoRA + DPO + GRPO**: Native support via Unsloth and TRL. Unsloth reports 2x faster training with 70% less VRAM.
- **131K Context**: With YaRN, supports long web browsing sessions without losing context.
- **Consumer GPU Friendly**: QLoRA 4-bit fits in ~6.5 GB VRAM (RTX 3060+).

### 1.3 Fine-Tuning Pipeline for CSTM Nursery Integration

The CSTM (Concept Story Training Module) nursery system produces preference data naturally: agents make choices in story graphs, and their outcomes generate implicit preference pairs (chosen path vs. rejected alternatives). This is a direct fit for DPO training.

**Recommended Pipeline**:

1. **Stage 1 -- SFT (Supervised Fine-Tuning)**: Fine-tune the base model on curated CSTM playthroughs using Unsloth + TRL SFTTrainer with LoRA (r=16, alpha=32). Data format: scene description + choice label pairs from `StoryEngine` outputs.

2. **Stage 2 -- DPO (Direct Preference Optimization)**: Convert CSTM nursery graduation data into preference pairs. Each `PlaythroughRecord` contains the chosen path and metadata about alternatives. Build `(prompt, chosen, rejected)` triples where:
   - `prompt` = scene text + personality context
   - `chosen` = action that led to graduation
   - `rejected` = action that led to failure or suboptimal outcome

3. **Stage 3 -- GRPO (Optional)**: For reasoning-heavy tasks, Qwen3 supports GRPO (Group Relative Policy Optimization) which can further align the model's thinking-mode outputs with SCBE safety axioms.

**LoRA Hyperparameters (Starting Point)**:
- Rank: r=16 (increase to 32 for complex tasks)
- Alpha: 32
- Dropout: 0.05
- Target modules: q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
- Learning rate: 2e-4 (SFT), 5e-6 (DPO)
- Batch size: 4 with gradient accumulation of 4

**Framework**: [Unsloth](https://github.com/unslothai/unsloth) is the clear winner for single-GPU LoRA fine-tuning. It is up to 2.7x faster and uses up to 74% less memory compared to standard implementations. It natively supports Qwen3, Llama 3.x, Phi-3/4, and DeepSeek models.

### 1.4 License Summary

| License | Models | Patent Compatible | Commercial Use |
|---------|--------|-------------------|----------------|
| **Apache-2.0** | Qwen2.5, Qwen3, SmolLM2, Mistral | Yes | Yes |
| **MIT** | Phi-3/4, Fara-7B, DeepSeek-R1-Distill | Yes | Yes |
| **Llama 3.1 Community** | Llama 3.1 | Conditional (700M MAU limit) | Yes with restrictions |

**Recommendation**: Prefer Apache-2.0 and MIT models for full USPTO patent compatibility with #63/961,403.

---

## 2. Sentence Transformers / Embedding Models

### 2.1 Model Comparison for SCBE Use Cases

The SCBE system needs embeddings for three distinct purposes:
1. **Scene text encoding** (CSTM story content)
2. **Choice label encoding** (decision options in story graphs)
3. **21D personality vector integration** (mapping to/from PHDM brain state dimensions)

| Model | Dims | Params | Speed (CPU) | Quality (MTEB) | Best For |
|-------|------|--------|-------------|-----------------|----------|
| **all-MiniLM-L6-v2** | 384 | 22M | 5-14K sent/sec | Good | Ultra-fast local inference; SCBE antivirus baseline |
| **all-mpnet-base-v2** | 768 | 109M | 2-3K sent/sec | Best (ST classic) | High-quality semantic search; scene encoding |
| **BGE-base-en-v1.5** | 768 | 109M | ~2K sent/sec | Excellent (MTEB top) | Retrieval tasks; RAG integration |
| **EmbeddingGemma-300M** | 768 (truncatable to 128-512) | 300M | <15ms on EdgeTPU | Excellent | On-device; Matryoshka dims; works with Ollama |
| **static-retrieval-mrl-en-v1** | variable | <5M | 100K+ sent/sec | Good for retrieval | Extreme speed; no GPU needed |
| **nomic-embed-text-v1.5** | 768 (truncatable) | 137M | ~2K sent/sec | Excellent | Matryoshka; good for RAG + clustering |

### 2.2 Top Recommendation: Dual-Model Strategy

**Primary (Quality)**: `all-mpnet-base-v2` or `BGE-base-en-v1.5` at 768D for scene text and choice label encoding. These provide the semantic resolution needed for CSTM story content analysis.

**Secondary (Speed)**: `all-MiniLM-L6-v2` at 384D for real-time antivirus scanning and safety filtering. At 5-14K sentences/sec on CPU, it can process web page content in real-time without GPU.

**On-Device Option**: `EmbeddingGemma-300M` supports Matryoshka representation learning, meaning you can use full 768D for quality or truncate to 256D/128D for speed, all from the same model weights. This is ideal for Polly Pad drones that may have varying compute budgets.

### 2.3 Integration with 21D Personality Vector System

The existing `PersonalityVector` in `player_agent.py` uses 21 named dimensions across 7 categories (Cognitive, Ethical, Social, Executive, Motivational, Emotional, Meta). To bridge sentence embeddings (384D/768D) with the 21D personality space:

**Approach 1 -- Learned Projection**:
Train a small projection head (768D -> 21D or 384D -> 21D) using the CSTM nursery data. Each playthrough provides a (scene_embedding, personality_update) pair. The projection head learns which semantic features of scene content most activate each personality dimension.

```
scene_text -> Embedding Model (768D) -> Linear(768, 128) -> ReLU -> Linear(128, 21) -> personality_delta
```

**Approach 2 -- Cosine Alignment**:
Pre-compute 21 "anchor embeddings" by embedding the canonical description of each personality dimension (e.g., "reasoning and logical deduction", "harm avoidance and safety consideration"). Then compute cosine similarity between a scene embedding and each anchor to produce a 21D alignment vector.

**Approach 3 -- Hybrid (Recommended)**:
Use Approach 2 for initialization and cold-start, then refine with Approach 1 as training data accumulates from the CSTM nursery. The `phdm-21d-embedding` model on HuggingFace can serve as the anchor embedding source.

### 2.4 Static Embeddings for Extreme Throughput

HuggingFace's recent `static-retrieval-mrl-en-v1` and `static-similarity-mrl-multilingual-v1` models eliminate the encoder bottleneck entirely, using pre-computed token embeddings with mean pooling. They achieve 100K+ sentences/sec, making them suitable for batch processing of large web crawl datasets during training runs.

---

## 3. Web Navigation / Browser Agent Models

### 3.1 Existing Models and Frameworks

| Model/Framework | Type | Size | Benchmark | License | HF Available |
|----------------|------|------|-----------|---------|--------------|
| **Fara-7B** (Microsoft) | CUA Model | 7B | 73.5% WebVoyager | MIT | Yes |
| **UI-TARS-1.5-7B** (ByteDance) | GUI Agent | 7B | 66.4% WebVoyager | Apache-2.0 | Yes |
| **UI-TARS-2** (ByteDance) | GUI Agent | 7B/72B | SOTA on OSWorld | Apache-2.0 | Yes |
| **OpenWebVoyager-IL** | Web Agent | 8B (idefics2-8b) | Based on GPT-4o trajectories | Apache-2.0 | Yes |
| **Mind2Web flan-t5** | Action Prediction | 250M-3B | Mind2Web benchmark | Apache-2.0 | Yes |
| **browser-use** | Python Framework | N/A (uses external LLM) | 89.1% WebVoyager | MIT | N/A (pip) |

### 3.2 Top Recommendation: Fara-7B + browser-use

**Fara-7B** is the standout choice for the SCBE-AETHERMOORE web agent because:

- **MIT License**: Fully compatible with USPTO patent #63/961,403.
- **73.5% WebVoyager**: Outperforms GPT-4o (65.1%) at computer-use tasks.
- **7B Parameters**: Runs on consumer GPUs (RTX 3060+).
- **Screenshot-Based**: Takes screenshots as input and predicts actions with grounded coordinates. This maps directly to the RECON drone class (CT-7567 "REX") loadout of `browser-use, playwright, vision`.
- **Step Efficiency**: Completes tasks in ~16 steps vs. ~41 steps for UI-TARS-1.5-7B.
- **Built-in Safety Refusals**: Refuses tasks involving personal info entry, purchases, emails, and account sign-ins, which aligns with SCBE governance principles.

**browser-use** as the orchestration layer because:

- Python-native, wraps Playwright in an LLM-driven control loop.
- DOM restructuring optimized for LLM consumption (strips irrelevant elements, labels interactive components).
- Supports local models via Ollama, enabling fully offline operation.
- 89.1% on WebVoyager when paired with strong LLMs.
- Active development with 21K+ GitHub stars.

### 3.3 Headless Browser Options

| Browser | Language | Speed vs Chrome | Memory vs Chrome | Playwright Compatible | Maturity |
|---------|----------|-----------------|------------------|-----------------------|----------|
| **Lightpanda** | Zig | 11x faster | 9x less | Yes (via CDP) | Beta (2025-2026) |
| **Playwright (Chromium)** | Node/Python | Baseline | Baseline | Native | Production |
| **Puppeteer (Chrome)** | Node | Baseline | Baseline | N/A (own API) | Production |
| **Steel Browser** | Cloud API | N/A | N/A (hosted) | Yes | Production |

**Recommendation**: Use Playwright as the production default (battle-tested, full API support), with Lightpanda as an experimental fast path for high-volume scraping tasks. Lightpanda's CDP compatibility means existing Playwright scripts work with minimal changes by swapping the browser endpoint.

### 3.4 Integration Architecture for SCBE RECON Drones

```
                    +-----------------------+
                    |    MOTHER SHIP        |
                    |  Fleet Registry       |
                    |  SCBE Gateway         |
                    +-----------+-----------+
                                |
                    SCBE Secure Channel
                    H(d,R) = R^(d^2)
                                |
                    +-----------+-----------+
                    |   POLLY PAD (RECON)   |
                    |   CT-7567 "REX"       |
                    |                       |
                    |  +------------------+ |
                    |  | Fara-7B / Qwen3  | |  <-- Vision + Reasoning LLM
                    |  +--------+---------+ |
                    |           |            |
                    |  +--------+---------+ |
                    |  | browser-use      | |  <-- Orchestration Loop
                    |  +--------+---------+ |
                    |           |            |
                    |  +--------+---------+ |
                    |  | Playwright /     | |  <-- Browser Engine
                    |  | Lightpanda       | |
                    |  +------------------+ |
                    |                       |
                    |  Trust: 0.95 (KO)     |
                    +-----------------------+
```

### 3.5 Datasets for Training/Evaluation

| Dataset | Size | Description | HF Link |
|---------|------|-------------|---------|
| **Mind2Web** | 2,000+ tasks, 137 websites, 31 domains | Generalist web agent tasks | `osunlp/Mind2Web` |
| **Mind2Web-2** | Extended with long-horizon search | Agent-as-a-Judge evaluation | `osunlp/Mind2Web-2` |
| **Online-Mind2Web** | 300 tasks, 136 websites | Live website evaluation | `osunlp/Online-Mind2Web` |
| **WebVoyager** | 643 tasks, 15 websites | End-to-end web task benchmark | `agentorg/webvoyager` |

---

## 4. Deployment Options

### 4.1 Serving Framework Comparison

| Framework | Throughput | Concurrent Users | Setup Complexity | Best For | Cost |
|-----------|------------|-------------------|-----------------|----------|------|
| **vLLM** | 793 TPS | Scales well | Medium | Production API serving | Open source |
| **TGI** (HF) | ~500 TPS | Good | Medium | HF ecosystem integration | Open source |
| **Ollama** | 41 TPS | Limited (default) | Very Low | Dev/prototyping, local | Open source |
| **llama.cpp** | Variable | Single user | Low | CPU inference, edge | Open source |
| **TensorRT-LLM** | Highest | Enterprise | High | Maximum throughput (NVIDIA) | Open source |

**Key Insight**: vLLM achieves 793 TPS vs Ollama's 41 TPS at equivalent configurations. Ollama's performance remains flat under concurrency, quickly hitting its maximum capacity. Use Ollama for development, vLLM for production.

### 4.2 HuggingFace Inference Endpoints Pricing

| Instance | GPU | VRAM | Price/Hour | Best For |
|----------|-----|------|------------|----------|
| GPU Small | NVIDIA T4 | 16 GB | ~$0.60/hr | SmolLM2, Phi-3.5-mini |
| GPU Medium | NVIDIA A10G | 24 GB | ~$1.00/hr | Qwen3-8B, Llama 3.1-8B, Fara-7B |
| GPU Large | NVIDIA A100 | 40 GB | ~$4.00/hr | Qwen3-32B, larger models |
| GPU XL | NVIDIA A100 | 80 GB | ~$8.00/hr | 70B models, high throughput |

**Billing**: Charged per minute while the endpoint is in "running" state. Endpoints can be set to scale-to-zero for cost savings.

**Monthly Cost Estimates** (24/7 operation):
- Qwen3-8B on A10G: ~$720/month
- SmolLM2-1.7B on T4: ~$432/month
- Scale-to-zero with ~4hr/day usage: ~$120/month (A10G)

### 4.3 Self-Hosted Options

**Option A -- Single GPU Server (RTX 4090)**:
- Hardware: ~$2,000 one-time (or ~$0.40/hr cloud rental)
- Run: Qwen3-8B (QLoRA 4-bit) + all-MiniLM-L6-v2 simultaneously
- Serving: vLLM for LLM, FastAPI for embeddings
- Throughput: ~50-100 requests/min for chat, unlimited for embeddings

**Option B -- Cloud GPU (Lambda Labs / RunPod)**:
- A10G: ~$0.40-0.75/hr
- A100 (40GB): ~$1.10-2.00/hr
- H100: ~$2.50-4.00/hr
- Good for burst workloads; pair with scale-to-zero

**Option C -- Hybrid (Recommended)**:
- Local RTX 4090 for development and embedding inference
- HF Inference Endpoints (scale-to-zero) for production LLM serving
- Ollama locally for rapid iteration during fine-tuning cycles

### 4.4 FastAPI Wrapper Pattern

The recommended production pattern for wrapping LLM inference:

**Architecture**:
```
Client -> FastAPI (async) -> vLLM OpenAI-compatible server -> GPU
                          -> Embedding model (in-process) -> CPU
                          -> SCBE governance pipeline -> CPU
```

**Key Patterns**:
- Load models during application startup; maintain in memory throughout lifecycle
- Use `async def` for I/O-bound operations (API calls, browser automation)
- Offload CPU-bound LLM inference to `ProcessPoolExecutor` or separate microservice
- Implement rate limiting to prevent compute resource exhaustion
- Input validation and sanitization before prompt construction
- Streaming token output via SSE (Server-Sent Events) for real-time responses
- Health check endpoints for Polly Pad fleet monitoring

**Security Considerations**:
- Prompt injection defense via SCBE Layer 12 (Harmonic Scaling) -- adversarial prompts incur exponential cost
- Rate limiting per client using token bucket algorithm
- Input length limits and character restrictions
- Pattern detection for known injection vectors

### 4.5 3rd-Party Service Pattern

For offering SCBE-governed inference as a service to third parties:

```
Third Party -> API Gateway (rate limit, auth)
            -> FastAPI (SCBE pre-processing: Layers 1-7)
            -> LLM Inference (vLLM/TGI)
            -> FastAPI (SCBE post-processing: Layers 8-14)
            -> Response with governance metadata
```

Each response includes:
- Trust radius (from Poincare ball computation)
- Governance score (14-layer pipeline result)
- Harmonic cost (H(d,R) = R^(d^2) computation)
- SpiralSeal signature (post-quantum envelope)

---

## 5. Semantic Antivirus Integration

### 5.1 Embedding Similarity as Content Safety Filter

The SCBE "Semantic Antivirus" concept can be implemented using embedding similarity as the core detection mechanism:

**How It Works**:
1. Pre-compute embedding vectors for known-harmful content categories (hate speech patterns, manipulation tactics, deception markers, etc.)
2. Embed incoming content (web page text, LLM prompts, agent outputs) using `all-MiniLM-L6-v2` (fast) or `all-mpnet-base-v2` (accurate)
3. Compute cosine similarity against the harmful content embeddings
4. If similarity exceeds threshold (e.g., 0.85), flag for governance review
5. The similarity score feeds into the SCBE Layer 5 (Hyperbolic Risk Assessment) as an additional risk signal

**Advantages over keyword filtering**:
- Catches semantic paraphrases and euphemisms
- Language-agnostic with multilingual embedding models
- Continuously improvable by adding new harmful embeddings
- Quantifiable risk score (cosine similarity) rather than binary flag

### 5.2 Guardrails Libraries

| Library | Approach | Integration | Best For |
|---------|----------|-------------|----------|
| **NeMo Guardrails** (NVIDIA) | Colang 2.0 DSL + LLM + embedding similarity | Standalone or middleware | Programmable safety rails; K-NN semantic matching; jailbreak detection |
| **LlamaGuard 3** (Meta) | Fine-tuned Llama-3.1-8B classifier | HF Transformers / Ollama | Input/output classification; MLCommons hazard taxonomy; 8 languages |
| **LlamaGuard 4** (Meta) | Multimodal (text + image) | HF Transformers | Combines text + vision safety; Llama 4 ecosystem |
| **Guardrails AI** | Pydantic-based validators | Python decorators | Structured output validation; schema enforcement |
| **Llama-3.1-Nemotron-Safety-Guard-8B-v3** (NVIDIA) | Safety classifier | HF Transformers | 23 safety categories; multilingual; real-time PII detection |

### 5.3 Recommended Stack: SCBE 14-Layer + NeMo + LlamaGuard

**Layer Mapping**:

| SCBE Layer | Function | Guardrail Integration |
|------------|----------|----------------------|
| L1-L4 (Input Processing) | Tokenization, Sacred Tongues, Spectral Identity | NeMo input rails: topic detection, PII filtering |
| L5-L7 (Hyperbolic Assessment) | Poincare ball risk scoring, cost amplification | Embedding similarity scores feed as risk signals |
| L8 (PHDM) | Polyhedral Hamiltonian Defense Manifold | LlamaGuard classification as additional defense vertex |
| L9-L11 (Governance) | Grand Unified governance, consensus | NeMo Colang flows for governance rule enforcement |
| L12 (Harmonic Scaling) | H(d,R) = R^(d^2) cost wall | Cost amplification of flagged content |
| L13 (Hive Integration) | Fleet consensus | Multi-agent guardrail aggregation |
| L14 (Audio Axis) | Telemetry and monitoring | Guardrail violation logging and alerting |

**Implementation Pattern**:
```
Input -> NeMo Input Rails (topic check, PII scan)
      -> Embedding Similarity Check (semantic antivirus)
      -> SCBE Layers 1-7 (hyperbolic risk assessment)
      -> LlamaGuard Classification (MLCommons hazard check)
      -> SCBE Layers 8-12 (governance + cost scaling)
      -> LLM Inference (if all checks pass)
      -> SCBE Layers 13-14 (output governance)
      -> NeMo Output Rails (factuality check, toxicity filter)
      -> Response
```

### 5.4 NeMo Guardrails Specifics

NeMo Guardrails uses `sentence-transformers/all-MiniLM-L6-v2` for semantic matching by default, embedding inputs into a dense vector space and performing K-Nearest Neighbor searches to find the most semantically similar patterns. This aligns perfectly with the SCBE antivirus concept.

**Key Capabilities**:
- **Colang 2.0 DSL**: Define safety rules in a human-readable domain-specific language
- **Topical Rails**: Restrict conversation to approved topics
- **Jailbreak Detection**: Detect prompt injection and jailbreak attempts via embedding similarity
- **Hallucination Prevention**: Cross-reference outputs against known facts
- **PII Protection**: Detect and redact personally identifiable information
- **Moderation**: Integration with external moderation APIs

---

## 6. Long-Running Web Agent Resilience

### 6.1 Preventing Agents from Getting Stuck

**Self-Reflection Loop (Primary Strategy)**:
After each browser action, the agent checks the page for the expected change. If the expected outcome is not observed, the agent revises its plan or tries an alternative. This maps directly to the Polly Pad "field repair" capability.

**Memory-Based Loop Detection**:
Agents maintain a history of past actions and page states (stored as embedding vectors). Before taking an action, the agent checks if the resulting state would be too similar to a previously visited state. If cosine similarity > 0.95, the agent is likely stuck in a loop and should try a fundamentally different approach.

**VIGIL-Style External Supervisor**:
Separate the self-healing task from the primary agent entirely. An external out-of-band supervisor monitors the agent's progress and intervenes when:
- No meaningful state change detected for N steps
- Agent is repeating the same action sequence
- Page load times exceed threshold
- Error states detected (404, 500, CAPTCHA)

**Timeout and Retry Strategy**:
```
Action Timeout: 30 seconds per browser action
Page Load Timeout: 60 seconds
Max Retries per Step: 3 (with exponential backoff: 2s, 4s, 8s)
Max Steps per Task: 50 (configurable per task complexity)
Total Task Timeout: 15 minutes (default), 60 minutes (extended)
```

### 6.2 Session Management and State Persistence

**Browser Session State**:
- Cookies and localStorage persisted across page navigations
- Session rotation: Same IP for 5-20 minutes or N pageviews, then rotate
- Cookie jars isolated per task to prevent cross-contamination
- Browser profiles stored in SQLite (matching Polly Pad Store pattern)

**Agent State Persistence**:
- Action history serialized to JSON after each step
- Page state snapshots stored as embeddings (for loop detection)
- Checkpoint/restore capability for long-running tasks
- SQLite-backed state store (matching existing `PollyPadStore` pattern in `hydra/polly_pad.py`)

**State Schema (extends existing Polly Pad schema)**:
```
web_agent_sessions:
  session_id TEXT PRIMARY KEY
  pad_id TEXT REFERENCES pads(pad_id)
  task_description TEXT
  current_url TEXT
  action_history_json TEXT
  page_state_embeddings BLOB
  cookies_json TEXT
  status TEXT (active|paused|completed|failed|stuck)
  created_at INTEGER
  updated_at INTEGER
  retry_count INTEGER DEFAULT 0
```

### 6.3 Anti-Bot Detection Evasion (Ethical Approach)

The goal is not to break terms of service, but to present the agent as a legitimate automated tool that behaves within acceptable parameters. All evasion techniques should be documented and disclosed where required.

**Network Layer**:
- Rotate user agents from a realistic distribution (Chrome 120+, Firefox 130+, Safari 18+)
- Maintain consistent TLS fingerprint per session (JA3/JA4 hash consistency)
- Use residential proxies for tasks requiring geographic specificity
- HTTP/2 with realistic header ordering

**Browser Layer**:
- Playwright stealth mode (`playwright-extra` with stealth plugin)
- Disable `navigator.webdriver` flag
- Realistic viewport sizes (1920x1080, 1440x900, 1366x768)
- Canvas and WebGL fingerprint spoofing (consistent per session)
- Device memory and hardware concurrency matching

**Behavioral Layer**:
- **Realistic timing**: Random delays between actions (800ms-3s for clicks, 50-150ms between keystrokes)
- **Mouse movement**: Smooth Bezier curves with acceleration/deceleration, not instant teleportation
- **Scroll behavior**: Variable velocity with realistic deceleration and occasional "bounce back"
- **Page interaction pattern**: Brief pause before first interaction (1-3s), natural reading time proportional to content length
- **Session patterns**: Realistic session duration (5-30 minutes), natural page visit sequences

**Detection Vectors to Address**:
| Detection Method | Countermeasure | Library |
|-----------------|----------------|---------|
| TLS fingerprinting | curl-impersonate or custom TLS config | `playwright-extra` |
| WebGL/Canvas fingerprint | Consistent spoofing per session | `puppeteer-extra-plugin-stealth` |
| navigator.webdriver | Patch to undefined | Built into stealth plugins |
| Behavioral analytics | Realistic timing + mouse curves | Custom implementation |
| Font enumeration | Match OS-realistic font lists | Anti-detect profile |
| IP reputation | Residential proxies | Third-party proxy service |

### 6.4 Polly Pad Actuator Mapping to Web Navigation Recovery

The existing Polly Pad architecture already contains the conceptual framework for web agent resilience. Here is how the concepts map:

| Polly Pad Concept | Web Agent Implementation |
|-------------------|--------------------------|
| **Flux States** (Polly/Quasi/Demi/Collapsed) | Agent confidence levels: Polly=executing normally, Quasi=retrying with modified approach, Demi=falling back to simpler strategy, Collapsed=requesting human intervention |
| **Field Repairs** | Self-healing loop: detect stuck state, modify strategy, retry |
| **Capability Store** (hot-swappable modules) | Swappable navigation strategies: DOM-based, vision-based, accessibility-tree-based |
| **Squad Synchronization** | Multiple drones collaborating on complex multi-tab tasks |
| **Cousin Takeover Lineage** (in PollyPadStore) | When an agent session fails, a new drone inherits the task context and continues from the last successful checkpoint |
| **Harmonic Depth Scaling** | Retry cost increases exponentially: first retry is cheap, but 5th retry triggers escalation to supervisor |
| **SCBE Secure Channel** | All browser sessions communicate back to Mother Ship via SCBE-validated channel |
| **Trust Radius** | Agent's accumulated trust score from successful task completions; low-trust agents get simpler tasks |

**Recovery Flow**:
```
Agent Action -> Check Result
  |
  +-- Expected outcome? -> Continue
  |
  +-- Unexpected but recoverable? -> Quasi state
  |     |
  |     +-- Retry with modified approach (max 3)
  |     +-- Try alternative navigation strategy
  |     +-- Clear cookies/cache and retry
  |
  +-- Stuck/looping detected? -> Demi state
  |     |
  |     +-- Fall back to simpler strategy
  |     +-- Request help from RESEARCH drone
  |     +-- Try completely different approach
  |
  +-- Unrecoverable error? -> Collapsed state
        |
        +-- Log full state for debugging
        +-- Trigger cousin takeover
        +-- Alert Mother Ship
```

---

## 7. Mapping to Existing HuggingFace Repos

### 7.1 issdandavis/phdm-21d-embedding

**Current State**: Feature extraction model for PHDM 21D Embedding (Hyperbolic AI Safety Embeddings). HF Space in "Sleeping" status.

**Role in Web Agent Architecture**:
- **Personality Vector Encoding**: This model encodes the 21D personality vectors used by CSTM PlayerAgents. Each dimension (reasoning, fairness, empathy, etc.) maps to a specific axis in the PHDM (Polyhedral Hamiltonian Defense Manifold).
- **Scene-to-Personality Bridge**: Acts as the projection layer between high-dimensional sentence embeddings (384D/768D) and the 21D personality space.
- **Safety Scoring Input**: The 21D embedding feeds into the SCBE safety score computation: `H(d,pd) = 1/(1+d+2*pd)`, where `d` is hyperbolic distance and `pd` is personality drift.

**Enhancement Roadmap**:
1. Fine-tune on CSTM nursery playthrough data to improve personality-to-scene alignment
2. Add Matryoshka support for variable-dimension output (21D, 64D, 128D) depending on compute budget
3. Publish benchmark results on personality prediction tasks

### 7.2 issdandavis/spiralverse-ai-federated-v1

**Current State**: Reinforcement Learning model for federated learning.

**Role in Web Agent Architecture**:
- **Federated Fine-Tuning**: Enables distributed fine-tuning across multiple Polly Pad drones without centralizing training data. Each drone contributes local gradient updates from its web browsing experiences.
- **Privacy-Preserving Learning**: Web agent observations (screenshots, page content) may contain sensitive information. Federated learning ensures raw data never leaves the drone; only model updates are shared.
- **Fleet-Wide Improvement**: As the RECON fleet (CT-7567 class drones) browses the web, their collective experience improves the shared navigation model without exposing individual browsing histories.

**Enhancement Roadmap**:
1. Implement differential privacy for gradient updates
2. Add secure aggregation using SCBE's post-quantum cryptography (ML-KEM-768)
3. Build LoRA adapter federation: each drone fine-tunes a local LoRA adapter, and adapters are merged on the Mother Ship using weighted averaging

### 7.3 issdandavis/UltraData-Math

**Current State**: 181MB reasoning training dataset with 124 downloads.

**Role in Web Agent Architecture**:
- **Reasoning Enhancement**: Math and logic training data improves the base model's chain-of-thought reasoning, which is critical for complex multi-step web navigation tasks.
- **SCBE Axiom Validation**: Mathematical reasoning is used internally by SCBE for validating axiom consistency (e.g., verifying that `H(d,R) = R^(d^2)` computations are correct).
- **DPO Training Supplement**: Math reasoning pairs can be converted to preference data: correct reasoning chains as "chosen", incorrect ones as "rejected".

**Enhancement Roadmap**:
1. Convert to DPO-format preference pairs for alignment training
2. Add web-navigation reasoning problems (e.g., "Given this DOM structure, what is the optimal click sequence to reach the checkout page?")
3. Integrate with CSTM story graphs that require mathematical reasoning (resource allocation, scheduling)

### 7.4 issdandavis/SCBE

**Current State**: Core framework repository.

**Role in Web Agent Architecture**:
- **Governance Engine**: The 14-layer pipeline is the central governance system that validates all agent actions before execution.
- **Trust Computation**: Provides the trust radius computation that determines what actions a drone is permitted to take.
- **Cryptographic Envelope**: SpiralSeal signatures ensure that agent-to-Mother-Ship communication is tamper-proof and post-quantum secure.

**Enhancement Roadmap**:
1. Publish the governance pipeline as a standalone HF model card with benchmarks
2. Create a "SCBE-Guard" model that combines the 14-layer pipeline with LlamaGuard classification
3. Build an SCBE-scored dataset for the HF leaderboard (safety-oriented benchmark)

### 7.5 Additional HF Repos (Recommended New)

| Repo Name | Purpose | Contents |
|-----------|---------|----------|
| `issdandavis/scbe-web-agent-lora` | Fine-tuned LoRA adapters | Qwen3-8B LoRA weights trained on CSTM + web navigation data |
| `issdandavis/scbe-safety-embeddings` | Safety filter embeddings | Pre-computed embedding vectors for harmful content categories |
| `issdandavis/scbe-web-navigation-dataset` | Training data | Mind2Web-style task data with SCBE governance annotations |
| `issdandavis/aethermoor-rag-training-data` | (Existing) RAG data | Expand with web-extracted knowledge for agent grounding |
| `issdandavis/scbe-aethermoore-datasets` | (Existing) Combined | Add CSTM preference pairs and web agent trajectories |

---

## 8. Recommended Architecture

### 8.1 Full Stack Overview

```
+============================================================================+
|                           MOTHER SHIP                                       |
|  +------------------+  +------------------+  +------------------+          |
|  | Fleet Registry   |  | SCBE Gateway     |  | Training Server  |          |
|  | (FastAPI)        |  | (14-Layer Pipe)  |  | (Unsloth + TRL)  |          |
|  +------------------+  +------------------+  +------------------+          |
|  +------------------+  +------------------+  +------------------+          |
|  | Embedding Server |  | NeMo Guardrails  |  | LlamaGuard 3     |          |
|  | (all-MiniLM)     |  | (Colang 2.0)     |  | (Safety Classify) |         |
|  +------------------+  +------------------+  +------------------+          |
|  +------------------+                                                       |
|  | vLLM Server      |  <-- Qwen3-8B (production inference)                 |
|  | (OpenAI compat)  |                                                       |
|  +------------------+                                                       |
+====================================|=======================================+
                                     |
                          SCBE Secure Channel
                       H(d,R) = R^(d^2) Validation
                       ML-KEM-768 + ML-DSA-65
                                     |
         +---------------------------+---------------------------+
         |                           |                           |
+--------+--------+       +---------+--------+       +---------+--------+
| POLLY PAD       |       | POLLY PAD        |       | POLLY PAD        |
| RECON (REX)     |       | RESEARCH (ARC)   |       | GUARD (OMEGA)    |
|                 |       |                  |       |                  |
| Fara-7B (local) |       | Qwen3-8B (API)  |       | LlamaGuard (API) |
| browser-use     |       | web-search       |       | scbe-validator   |
| Playwright      |       | arxiv-scraper    |       | audit-logger     |
|                 |       |                  |       |                  |
| Trust: 0.95     |       | Trust: 0.88      |       | Trust: 0.99      |
+-----------------+       +------------------+       +------------------+
```

### 8.2 Technology Stack Summary

| Component | Technology | Why |
|-----------|-----------|-----|
| **Core LLM** | Qwen3-8B | Apache-2.0; thinking/non-thinking modes; 131K context; excellent LoRA/DPO support |
| **Web Agent Model** | Fara-7B | MIT; 73.5% WebVoyager; screenshot-based; 7B runs locally |
| **Embeddings (Quality)** | all-mpnet-base-v2 (768D) | Best sentence-transformers quality; semantic search |
| **Embeddings (Speed)** | all-MiniLM-L6-v2 (384D) | 14K sent/sec on CPU; real-time antivirus |
| **Personality Embeddings** | phdm-21d-embedding | Custom 21D SCBE personality space |
| **Browser Engine** | Playwright (primary) / Lightpanda (experimental) | Production-grade; stealth plugins available |
| **Orchestration** | browser-use (Python) | 89.1% WebVoyager; Playwright wrapper; Ollama support |
| **Serving (Production)** | vLLM + FastAPI | 793 TPS; OpenAI-compatible API; async |
| **Serving (Development)** | Ollama | Zero-config; fast iteration |
| **Fine-Tuning** | Unsloth + TRL | 2.7x faster; 74% less VRAM; DPO native |
| **Safety (Input)** | NeMo Guardrails | Colang 2.0; semantic K-NN matching; jailbreak detection |
| **Safety (Classification)** | LlamaGuard 3/4 | MLCommons taxonomy; 8+ languages; 1B-8B sizes |
| **Safety (Governance)** | SCBE 14-Layer Pipeline | H(d,R) = R^(d^2) cost scaling; patent-protected |
| **State Persistence** | SQLite (WAL mode) | Matching existing PollyPadStore pattern |
| **Federated Learning** | spiralverse-ai-federated-v1 | Privacy-preserving fleet improvement |
| **Training Data** | UltraData-Math + CSTM nursery | Reasoning + preference pairs |

### 8.3 Phase Roadmap

**Phase 1 -- Foundation (Weeks 1-4)**:
- Set up Ollama locally with Qwen3-8B and Fara-7B
- Deploy all-MiniLM-L6-v2 for embedding inference
- Build FastAPI wrapper with SCBE pre/post-processing hooks
- Integrate browser-use with Playwright for basic web navigation
- Implement session state persistence using SQLite

**Phase 2 -- Safety Integration (Weeks 5-8)**:
- Deploy NeMo Guardrails with Colang 2.0 safety rules
- Integrate LlamaGuard 3-1B as lightweight safety classifier
- Build embedding-based semantic antivirus using pre-computed harmful content vectors
- Wire SCBE 14-layer pipeline as middleware in FastAPI
- Implement stealth browser configuration (user agent rotation, realistic timing)

**Phase 3 -- Fine-Tuning (Weeks 9-12)**:
- Collect CSTM nursery playthrough data
- Convert to SFT format and run Stage 1 fine-tuning with Unsloth
- Build DPO preference pairs from graduation/failure outcomes
- Run Stage 2 DPO training
- Evaluate on Mind2Web and WebVoyager benchmarks
- Publish LoRA adapters to HuggingFace

**Phase 4 -- Fleet Deployment (Weeks 13-16)**:
- Deploy Polly Pad fleet with RECON, RESEARCH, and GUARD drone classes
- Implement federated learning across fleet
- Set up vLLM production serving with scale-to-zero
- Implement cousin takeover and self-healing recovery loops
- Build monitoring dashboard (extending existing `scbe-visual-system`)
- Production hardening: rate limiting, circuit breakers, alerting

### 8.4 Estimated Costs (Monthly, Production)

| Component | Self-Hosted (RTX 4090) | Cloud (HF Endpoints) | Hybrid |
|-----------|----------------------|----------------------|--------|
| LLM Inference | $0 (hardware owned) | $720/mo (A10G 24/7) | $120/mo (scale-to-zero) |
| Embedding Inference | $0 (CPU) | $0 (CPU on same instance) | $0 (local CPU) |
| Safety Models | $0 (local) | $432/mo (T4 for LlamaGuard) | $0 (local) |
| Browser Infrastructure | $0 (local Playwright) | $50-200/mo (cloud browsers) | $0 (local) |
| Proxy Service | $50-200/mo | $50-200/mo | $50-200/mo |
| **Total** | **$50-200/mo** | **$1,252-1,552/mo** | **$170-320/mo** |

**Recommendation**: Start with self-hosted (RTX 4090 or equivalent) for development and small-scale production. Migrate to hybrid (local + HF Endpoints with scale-to-zero) as traffic grows.

---

## Sources

### Small Language Models and Fine-Tuning
- [Top 15 Small Language Models for 2026 | DataCamp](https://www.datacamp.com/blog/top-small-language-models)
- [Best Open Source LLMs in 2025 | Koyeb](https://www.koyeb.com/blog/best-open-source-llms-in-2025)
- [10 Best Open-Source LLM Models | HuggingFace Blog](https://huggingface.co/blog/daya-shankar/open-source-llms)
- [The Best Open-Source Small Language Models in 2026 | BentoML](https://www.bentoml.com/blog/the-best-open-source-small-language-models)
- [15 Best Open Source LLMs with GPU Sizing Guide | AceCloud](https://acecloud.ai/blog/best-open-source-llms/)
- [Qwen3 Technical Report](https://arxiv.org/pdf/2505.09388)
- [Qwen3: Run and Fine-tune | Unsloth](https://unsloth.ai/docs/models/qwen3-how-to-run-and-fine-tune)
- [Fine-Tuning Qwen3 | DataCamp](https://www.datacamp.com/tutorial/fine-tuning-qwen3)

### DPO, RLHF, and LoRA Fine-Tuning
- [Fine-tune Llama 2 with DPO | HuggingFace Blog](https://huggingface.co/blog/dpo-trl)
- [DPO Trainer | HuggingFace TRL](https://huggingface.co/docs/trl/main/en/dpo_trainer)
- [Make LLM Fine-tuning 2x faster with Unsloth and TRL](https://huggingface.co/blog/unsloth-trl)
- [LoRA Fine-tuning Hyperparameters Guide | Unsloth](https://unsloth.ai/docs/get-started/fine-tuning-llms-guide/lora-hyperparameters-guide)
- [Post-training methods for language models | Red Hat](https://developers.redhat.com/articles/2025/11/04/post-training-methods-language-models)
- [Unsloth GitHub](https://github.com/unslothai/unsloth)

### Embedding Models
- [Sentence Transformers | HuggingFace](https://huggingface.co/sentence-transformers)
- [all-MiniLM-L6-v2 | HuggingFace](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [Pretrained Models | SBERT](https://www.sbert.net/docs/sentence_transformer/pretrained_models.html)
- [Train 400x faster Static Embedding Models | HuggingFace Blog](https://huggingface.co/blog/static-embeddings)
- [Introducing EmbeddingGemma | Google Developers Blog](https://developers.googleblog.com/en/introducing-embeddinggemma/)
- [Best Open-Source Embedding Models Benchmarked](https://supermemory.ai/blog/best-open-source-embedding-models-benchmarked-and-ranked/)
- [The Best Open-Source Embedding Models in 2026 | BentoML](https://www.bentoml.com/blog/a-guide-to-open-source-embedding-models)

### Web Agent Models and Browser Automation
- [Fara-7B | HuggingFace](https://huggingface.co/microsoft/Fara-7B)
- [Fara-7B | Microsoft Research](https://www.microsoft.com/en-us/research/blog/fara-7b-an-efficient-agentic-model-for-computer-use/)
- [Fara-7B rivals GPT-4o | VentureBeat](https://venturebeat.com/ai/microsofts-fara-7b-is-a-computer-use-ai-agent-that-rivals-gpt-4o-and-works)
- [UI-TARS-1.5-7B | HuggingFace](https://huggingface.co/ByteDance-Seed/UI-TARS-1.5-7B)
- [UI-TARS GitHub | ByteDance](https://github.com/bytedance/UI-TARS)
- [Mind2Web | HuggingFace Datasets](https://huggingface.co/datasets/osunlp/Mind2Web)
- [Mind2Web-2 | HuggingFace Datasets](https://huggingface.co/datasets/osunlp/Mind2Web-2)
- [browser-use GitHub](https://github.com/browser-use/browser-use)
- [Browser-Use | InfoWorld](https://www.infoworld.com/article/3812644/browser-use-an-open-source-ai-agent-to-automate-web-based-tasks.html)
- [Best 30+ Open Source Web Agents in 2026 | AIMultiple](https://aimultiple.com/open-source-web-agents)
- [OpenWebVoyager-IL | HuggingFace](https://huggingface.co/OpenWebVoyager/OpenWebVoyager-IL)

### Headless Browsers
- [Lightpanda GitHub](https://github.com/lightpanda-io/browser)
- [Lightpanda.io](https://lightpanda.io)
- [CDP vs Playwright vs Puppeteer | Lightpanda Blog](https://lightpanda.io/blog/posts/cdp-vs-playwright-vs-puppeteer-is-this-the-wrong-question)
- [Top 10 Remote Browsers for AI Agents | O-Mega](https://o-mega.ai/articles/top-10-remote-browsers-for-ai-agents-full-2025-review)

### Deployment and Serving
- [vLLM vs Ollama vs llama.cpp vs TGI | ITECS](https://itecsonline.com/post/vllm-vs-ollama-vs-llama.cpp-vs-tgi-vs-tensort)
- [Ollama vs vLLM Performance Benchmarking | Red Hat](https://developers.redhat.com/articles/2025/08/08/ollama-vs-vllm-deep-dive-performance-benchmarking)
- [HuggingFace Inference Endpoints Pricing](https://huggingface.co/docs/inference-endpoints/en/pricing)
- [HuggingFace Pricing 2026 | MetaCTO](https://www.metacto.com/blogs/the-true-cost-of-hugging-face-a-guide-to-pricing-and-integration)
- [FastAPI + LLMs | Medium](https://medium.com/@kaushalsinh73/fastapi-llms-building-ai-powered-apis-the-easy-way-e14bf75e8786)
- [Building LLM Applications with HF Endpoints and FastAPI | MLMastery](https://machinelearningmastery.com/building-llm-applications-with-hugging-face-endpoints-and-fastapi/)
- [vLLM Production Deployment | Introl](https://introl.com/blog/vllm-production-deployment-inference-serving-architecture)

### Safety and Guardrails
- [NeMo Guardrails GitHub](https://github.com/NVIDIA-NeMo/Guardrails)
- [NeMo Guardrails Overview | NVIDIA](https://docs.nvidia.com/nemo/guardrails/latest/about/overview.html)
- [Content Moderation with NeMo Guardrails | NVIDIA Blog](https://developer.nvidia.com/blog/content-moderation-and-safety-checks-with-nvidia-nemo-guardrails/)
- [LlamaGuard 3-8B | HuggingFace](https://huggingface.co/meta-llama/Llama-Guard-3-8B)
- [LlamaGuard 3-1B | HuggingFace](https://huggingface.co/meta-llama/Llama-Guard-3-1B)
- [LlamaGuard 4-12B | HuggingFace](https://huggingface.co/meta-llama/Llama-Guard-4-12B)
- [Guardrails AI + NeMo Integration](https://www.guardrailsai.com/blog/nemoguardrails-integration)
- [Embedding Guardrails | Portkey](https://portkey.ai/docs/product/guardrails/embedding-guardrails)

### Agent Resilience and Anti-Bot
- [State-of-the-Art Autonomous Web Agents 2024-2025 | Medium](https://medium.com/@learning_37638/state-of-the-art-autonomous-web-agents-2024-2025-3d9d93a5dde2)
- [AI That Fixes Itself: Resilient Agent Architectures | Medium](https://medium.com/@muhammad.awais.professional/ai-that-fixes-itself-inside-the-new-architectures-for-resilient-agents-9d12449da7a8)
- [Stealth AI Browser Agents: Ultimate 2026 Guide | O-Mega](https://o-mega.ai/articles/stealth-for-ai-browser-agents-the-ultimate-2026-guide)
- [Browser Fingerprint Strategy | ScrapingAnt](https://scrapingant.com/blog/browser-fingerprint-strategy-designing-identities-not-just)
- [Proxy Strategy 2025 | ScrapingAnt](https://scrapingant.com/blog/proxy-strategy-in-2025-beating-anti-bot-systems-without)
- [Self-Healing Software Systems | arXiv](https://arxiv.org/pdf/2504.20093)
