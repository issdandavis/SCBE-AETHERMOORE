# AI Tooling Landscape, SCBE's Competitive Wedge, and "Governed MCP Rooms"

_2026-06-18. Synthesized from a 108-agent cited research pass + the SCBE codebase. Market-share
figures come from VC/vendor surveys (Menlo Ventures — a disclosed Anthropic investor — and
LangChain), so they are directional, not audited telemetry._

---

## 1. The landscape (one-pager)

The 2025-2026 AI-agent stack has converged into a small number of layers:

| Layer | What won / who matters | Note for SCBE |
|---|---|---|
| **Tool protocol** | **MCP (Model Context Protocol)** is the de-facto standard — Anthropic-created, now Linux-Foundation-governed; even OpenAI's Responses API auto-discovers MCP tools over Streamable HTTP/SSE and ships first-party "Connectors" (Google Workspace, Dropbox, M365). | The integration substrate is **settled**. Build *on* MCP, not a rival protocol. |
| **Models** | **Claude is dominant for coding (~54% by Dec 2025)**; top-3 (Anthropic/OpenAI/Google) ≈ 88%. Coding is the largest enterprise AI spend category (~$4.0B). | Default agent backend ≈ Claude. |
| **Multi-model reality** | **>75% of orgs run multiple models** and route by cost/latency/complexity. | **Directly validates a routing + governance product.** |
| **Coding agents** | Cursor, GitHub Copilot, Claude Code, Amazon Q, Windsurf, Google Antigravity; open/BYOK: OpenCode (MIT, 75+ providers), Cline, Aider. 30+ tools tracked; ranked on Terminal-Bench. | These are the things that *call tools* — i.e., what flows through a governance layer. |
| **Inference runtimes** | Ollama / llama.cpp / LM Studio (local prototyping); **vLLM** for production (≈44× llama.cpp throughput at 64 users). | SCBE's local-first default rides the Ollama/local trend. |
| **Runtime capabilities** | Web search (Tavily, Exa, Brave), sandboxes (E2B, Modal, Daytona), browser (**browser-use ~99k★**), vector DBs (Pinecone, Chroma, pgvector, Qdrant). | These are the **niche tools** a "room" would route to (see §4). |
| **Guardrails / safety** | Lakera Guard, ProtectAI (LLM Guard, DeBERTa injection), Meta Prompt/Llama Guard, NVIDIA NeMo Guardrails. | **Our competitors — but only on point-detection.** |
| **Observability / eval** | LangSmith, Langfuse, Helicone, Arize Phoenix, Braintrust. | They *trace*; they don't *govern*. |

---

## 2. Where SCBE does NOT win (be honest)

**Raw detection recall.** Lakera, ProtectAI, and Prompt Guard win on classifier recall — bigger
training sets, threat feeds, dedicated models. We literally *use* ProtectAI's DeBERTa as our
opt-in tier. **Do not fight on "we detect more attacks."** We'd lose, and it's not believable.

---

## 3. How we beat them — the wedge

Three candidate angles, then the combination that is actually a category:

**A. Forwardable, tamper-evident receipts (evidence-as-product).**
Guardrails return a *verdict*; observability tools return *traces*. Neither makes the **sealed,
forwardable audit record** the primary product. SCBE already issues per-call receipts (receipt no.,
issuer, subject + input SHA-256, decision, plain-language attestation, SHA-256 seal, run seal binding
all of them — `scripts/audit/generate_attestation.py`). For a **regulated/gov buyer the evidence IS
the deliverable.** "We don't just block — we hand you a court-/auditor-forwardable receipt."

**B. Govern the routing / multi-agent layer, not just the prompt.**
Every guardrail vendor is a **point-filter on one prompt or one response.** With >75% of orgs running
multiple models and MCP as the substrate, **nobody is governing the orchestration** — the hops between
agents and tools. That is exactly where SCBE's *routing + governance + receipts* combine.

**C. Local / deterministic / air-gapped / zero-egress default.**
Lakera is a cloud API (your prompts leave your perimeter); ProtectAI needs a model. SCBE's **default
is a deterministic, pure-Python screen + audit** — runs air-gapped, no data egress, no per-call cost.
For the CAGE-code / defense / regulated buyer, **"your data never leaves + deterministic + auditable"**
beats "send your prompts to a vendor cloud."

> **The wedge = B + A + C: the governance + audit *control plane* for multi-agent MCP.**
> Not a better classifier — the layer that sits at the routing boundary, governs every hop, and emits
> forwardable receipts, locally. The point-detection vendors don't occupy it; the observability vendors
> don't *govern*; the MCP gateways route but don't govern or receipt. That empty quadrant is the category.

---

## 4. "Governed MCP Rooms" — the tool-call-as-chat-room design

**The idea (yours):** a tool call shouldn't be a flat one-shot function. It should open a **topic-scoped
room** — a shared space for the topic being worked — that **routes the niche sub-aspects to specialist
tools.**

**Why MCP needs it.** MCP today is *flat*: a server exposes a flat list of tools; the client picks one;
the call is stateless and one-shot. Two real pains follow: **(1) tool sprawl** — agents get dozens or
hundreds of tools in-context, which bloats context and degrades selection; **(2) no shared state** — no
place for several agents/tools to collaborate on one topic across turns, and **no governance or receipt
spanning the interaction.**

**The room upgrade:**

```
        agent ──"work on <topic>"──▶  ROOM (topic-scoped MCP surface)
                                       │   shared, governed context (a channel for the topic)
                                       ▼
                                  COORDINATOR  ── classifies each sub-aspect ──┐
                                       │                                        │ routes to the
            ┌──────────────┬───────────┼───────────────┬──────────────┐        │ niche specialist
            ▼              ▼           ▼                ▼              ▼        │
        niche tool A   niche tool B  niche tool C   niche tool D   niche tool E ◀┘
        (MCP sub-server) (MCP sub-server) ...
                                       │
                          every inbound msg GATED · every route LOGGED · room emits a RECEIPT transcript
```

- A **room** = a topic-scoped MCP surface. The agent talks to *the topic* (one coarse entry), not to 50
  flat tools — **killing tool sprawl** and improving selection.
- A **coordinator** routes each sub-aspect to the right **niche tool** (specialist sub-MCP-servers) — a
  switchboard for the topic.
- The room holds **shared state** (the transcript/context) so multiple agents + tools collaborate across
  turns instead of one-shot calls.
- The room is the **governance + audit boundary**: every inbound message is scored (ALLOW/QUARANTINE/
  ESCALATE/DENY), every route is logged, and the room emits a **receipt transcript** — the audit trail
  for the *whole* multi-tool interaction, not a single call.

**Why SCBE is the right builder (it maps onto assets we already have):**

| Room component | SCBE asset |
|---|---|
| Route sub-aspect → niche tool | the swarm router / geometry (place the topic on the tongue-weighted manifold; route to the nearest specialist) |
| Govern every room message | the L13 gate (`scbe_aethermoore.scan`) |
| Audit the whole interaction | the receipt system (per-hop receipts + a room transcript, sealed) |
| MCP plumbing | a **"room server"** = an MCP gateway/proxy that fronts N niche sub-servers, maintains room state via MCP resources + notifications, and forwards (MCP-to-MCP) |

**MVP (buildable on what exists):** an MCP **router/room server** that (1) registers N niche MCP
sub-servers under a topic, (2) exposes a single `ask_<topic>` tool + a room resource, (3) classifies each
call's sub-aspect and forwards to the right sub-server, (4) **gates + receipts every hop**, (5) returns
the result + a receipt id. Start the routing as a simple embedding/classifier; the geometry is a later
optimization, **not** a launch dependency.

**This unifies §3 and the room idea:** "Governed MCP Rooms" *is* the wedge made concrete — route +
govern + receipt **on top of MCP**. Guardrails filter a prompt; SCBE governs the room. Observability
tools trace; SCBE governs + receipts. MCP gateways (Docker MCP, mcp-router) route; SCBE routes **and**
governs **and** receipts.

---

## 5. Honest caveats & what it needs

- A real **MCP gateway/proxy + room state** is genuine engineering, not a weekend; the MVP above is the
  scoped first slice.
- The wedge needs a **design partner**: one regulated/gov buyer with a multi-agent or MCP deployment, to
  validate that the *receipt* and the *room governance* are what they'll pay for.
- **Don't overclaim the geometry.** Routing can be a plain classifier first. The differentiator is the
  control-plane *position* (govern + receipt at the room boundary), not the math.
- Market-share numbers are VC/vendor surveys (Menlo is an Anthropic investor); treat as directional.
- We still **lose on raw recall** — so the pitch leads with *provable governance of the orchestration*,
  and uses ProtectAI/PromptGuard-class models as the recall tier *inside* the room, not as the headline.
