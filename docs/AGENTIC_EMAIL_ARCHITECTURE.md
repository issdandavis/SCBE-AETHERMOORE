# Agentic Email Architecture

> Research note: How to build AI-powered email triage with autonomous "agentic employees" — derived from SCBE-AETHERMOORE's Apollo pipeline and multi-agent dispatch spine.

---

## The Problem

A single inbox becomes a bottleneck. Sales inquiries, support tickets, bug reports, partnership requests, spam, and newsletters all arrive in one stream. Manual sorting doesn't scale. Rules-based filters miss nuance. What's needed is **intent-aware routing** where specialized AI agents handle different email types autonomously.

---

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Website Form   │────▶│  /api/contact   │────▶│  Proton SMTP    │
│  or IMAP Inbox  │     │  (FastAPI)      │     │  (issac@...)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                         │
                              ┌────────────────────────┘
                              ▼
                    ┌─────────────────┐
                    │  Apollo Email   │
                    │  Reader (IMAP)  │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  LLM Classifier │◀── Gemini / Claude / Local
                    │  (Intent + Urgency)
                    └─────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌─────────┐    ┌─────────┐    ┌─────────┐
        │  Sales  │    │ Support │    │  Tech   │
        │  Agent  │    │  Agent  │    │  Agent  │
        └─────────┘    └─────────┘    └─────────┘
              │               │               │
              ▼               ▼               ▼
        ┌─────────┐    ┌─────────┐    ┌─────────┐
        │  Draft  │    │  Draft  │    │  Draft  │
        │  Reply  │    │  Reply  │    │  Reply  │
        └─────────┘    └─────────┘    └─────────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                    ┌─────────────────┐
                    │  Human Review   │◀── Gate for sensitive actions
                    │  (Optional)     │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  SMTP Outbound  │
                    │  (Proton)       │
                    └─────────────────┘
```

---

## Component Breakdown

### 1. Ingestion Layer

**Option A: Website Contact Form**
- Static site POSTs to `/api/contact` (FastAPI)
- API sends email via SMTP to owner
- Same email address = same inbox = same triage pipeline

**Option B: Direct IMAP Polling**
- Apollo `email_reader.py` polls Proton/Gmail IMAP
- Classifies by Sacred Tongue (KO/AV/RU/CA/UM/DR)
- Processes last N days, max 50 messages per run

**Option C: Webhook (n8n/Zapier)**
- Form service (Formspree, Basin) triggers webhook
- Webhook hits local n8n bridge or FastAPI endpoint
- Real-time vs. polling tradeoff

**Recommendation:** Use A (direct API) for website forms + B (IMAP polling) for general email. This gives both real-time website notifications and batch processing of all inbound mail.

---

### 2. Classification Layer

**Two-tier approach:**

**Tier 1 — Sacred Tongues (keyword heuristic)**
Fast, deterministic, no API cost. Catches obvious patterns:
- KO: "request", "need", "deadline", "approve"
- AV: "update", "newsletter", "summary"
- RU: "invoice", "contract", "payment"
- CA: "bug", "deploy", "API", "error"
- UM: "password", "security", "breach"
- DR: "unsubscribe", "welcome", "settings"

**Tier 2 — LLM Classifier**
Runs when Tier 1 confidence is low or when `agentic_triage.py` is invoked. Uses Gemini/Claude with a structured prompt:

```
Agentic employees available:
- sales: pricing inquiry, custom project, enterprise scoping
- support: delivery issue, refund request, broken link
- technical: API question, bug report, integration help
- security: vulnerability report, audit request
- content: guest post, interview, speaking engagement
- admin: spam, newsletter, unclear intent

Classify this email. Respond with JSON:
{
  "agent": "<key>",
  "confidence": 0.0-1.0,
  "summary": "...",
  "urgency": "low|normal|high|critical",
  "action": "recommended next step",
  "draft_reply": "1-paragraph response"
}
```

**Cost optimization:**
- Run heuristic first (free)
- Only call LLM if heuristic confidence < 0.7
- Cache classifications by sender+subject hash
- Use Gemini Flash ($0.075/1M tokens) or local Ollama

---

### 3. Agentic Employees (Dispatch)

Each agent is a **capability + prompt template**, not a separate process.

| Employee | Role | Capability | Prompt Anchor |
|---|---|---|---|
| **Ava** (Sales) | `agent.sales` | `email.sales` | "You are Ava, SCBE sales. Be concise, outcome-focused. Never invent pricing." |
| **Sam** (Support) | `agent.support` | `email.support` | "You are Sam, SCBE support. Be patient, solution-oriented. Escalate refunds." |
| **Tao** (Technical) | `agent.technical` | `email.technical` | "You are Tao, SCBE engineer. Be precise, reference docs, provide code." |
| **Sage** (Security) | `agent.security` | `email.security` | "You are Sage, SCBE security. Be serious, thorough, follow disclosure policy." |
| **Cara** (Content) | `agent.content` | `email.content` | "You are Cara, SCBE content. Be warm, calendar-aware, story-oriented." |
| **Alex** (Admin) | `agent.admin` | `email.admin` | "You are Alex, SCBE admin. Be neutral, efficient, archive when appropriate." |

**Dispatch mechanism:**
1. Classification outputs `agent` key
2. Task is inserted into `dispatch.db` (SQLite) with `owner_role = agent.role`
3. Agent picks up tasks where `status = 'queued' AND owner_role = 'agent.X'`
4. Agent generates draft reply using its prompt template + email context
5. Draft goes to human review queue (or auto-send if confidence > 0.9 and low risk)

---

### 4. Response Generation

**Draft reply flow:**
```python
agent = AGENTIC_EMPLOYEES[classification["agent"]]
prompt = f"""{agent['tone']}

Original email:
From: {email.sender}
Subject: {email.subject}
Body: {email.body}

Draft a response. Rules:
- Only mention real products/prices from catalog
- If unsure, say "I'll check with the team and get back to you"
- Include relevant links from: {links_for_agent(agent)}
- Sign as {agent['name']}
"""
```

**Human-in-the-loop gates:**
| Action | Auto-send? | Gate |
|---|---|---|
| Informational reply (pricing, links) | Yes, if confidence > 0.9 | Log only |
| Refund processing | No | Human approval required |
| Custom quote | No | Human approval required |
| Security report acknowledgment | Yes | Log + alert human |
| Spam/unsubscribe | Yes | No review |

---

### 5. Storage & Audit

**SQLite schema (dispatch spine):**
```sql
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    title TEXT,
    goal TEXT,
    capability TEXT,        -- email.sales, email.support, etc.
    priority INTEGER,       -- 40 (low) to 95 (critical)
    status TEXT,            -- queued, running, completed, failed
    owner_role TEXT,        -- agent.sales, agent.support, etc.
    requested_by TEXT,      -- sender email
    payload TEXT,           -- JSON: full email + classification
    route TEXT,             -- JSON: queue + action
    notes TEXT,
    created_at TEXT,
    updated_at TEXT,
    result_summary TEXT     -- draft reply or action taken
);
```

**Audit trail:**
- Every classification logged with confidence score
- Every draft reply stored before sending
- Every auto-send flagged for retroactive review
- Monthly report: classification accuracy, response times, escalation rate

---

## Implementation Roadmap

### Phase 1: Basic Triage (Done)
- ✅ SMTP outbound (`email_service.py`)
- ✅ Contact API endpoint (`/api/contact`)
- ✅ Heuristic classifier (`agentic_email_triage.py`)
- ✅ Dispatch to SQLite (`advanced_ai_dispatch.py`)

### Phase 2: LLM Enhancement (Next)
- [ ] Add Gemini API key to `.env.connector.oauth`
- [ ] Enable LLM fallback in `agentic_email_triage.py`
- [ ] Add response generation to each agent
- [ ] Build human review UI (simple HTML page or CLI)

### Phase 3: Automation (Future)
- [ ] Auto-send high-confidence replies
- [ ] Calendar integration for booking calls
- [ ] Stripe integration for refund processing
- [ ] Knowledge base retrieval for technical answers
- [ ] Feedback loop: human corrections improve classifier

### Phase 4: Scale (Future)
- [ ] Separate agent processes (not just SQLite rows)
- [ ] Vector DB for email history + RAG
- [ ] Multi-language support
- [ ] SLA monitoring and alerting

---

## Security Considerations

1. **Secret scrubbing** — Apollo already scrubs API keys, tokens, card numbers before any email touches training data or logs
2. **SMTP token isolation** — Stored in `.env.connector.oauth`, never committed
3. **Reply gates** — Financial and security actions require human approval
4. **Rate limiting** — Contact API should limit to 5 submissions/IP/hour
5. **Spam filtering** — reCAPTCHA on contact form + honeypot field

---

## Cost Estimate

| Component | Monthly Cost |
|---|---|
| Proton Mail Business | $12.99/mo (already paid) |
| Gemini Flash API | ~$0.50-2.00/mo (light usage) |
| Cloudflare Tunnel | Free |
| SQLite storage | Negligible |
| **Total** | **~$1-3/mo incremental** |

---

## References

- SCBE `scripts/apollo/email_reader.py` — IMAP ingestion + tongue classification
- SCBE `scripts/apollo/apollo_core.py` — Interactive search + teaching loops
- SCBE `scripts/system/advanced_ai_dispatch.py` — Lease-based task dispatch
- SCBE `scripts/system/email_service.py` — SMTP outbound
- This doc: `docs/AGENTIC_EMAIL_ARCHITECTURE.md`
