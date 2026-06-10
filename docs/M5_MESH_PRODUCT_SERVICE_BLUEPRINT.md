# M5 Mesh Foundry — Product & Service Blueprint

Last updated: 2026-05-10
Status: **operational** — paying offers live, end-to-end pipeline shipped

## 1) What M5 is

M5 Mesh Foundry is the productized, governance-aware data-and-intelligence
layer that sits in front of the SCBE 14-layer pipeline and turns one workflow
at a time into a delivered, audited artifact.

It is the **revenue surface** for SCBE-AETHERMOORE. Where M6 (see
`M6_SEED_MULTI_NODAL_NETWORK_SPEC.md`) is the research substrate, M5 is what
customers actually buy.

Three properties define M5:

1. **Single-workflow scope.** Every offer maps to exactly one workflow, one
   delivery, one report. No open-ended consulting.
2. **Governed by default.** Every record that flows through M5 passes through
   the same harmonic-wall + axiom-mesh pipeline used internally; nothing
   leaves without a governance stamp.
3. **Capture-on-delivery.** Every governed delivery emits a structured record
   into the training capture lane so M6 research benefits from M5 production.

## 2) Buyer problem

Teams are adopting AI tools faster than they can document, audit, and govern
them. Their common gaps are:

- no durable record of prompts, outputs, decisions, and follow-up actions
- no clean separation between local/private work and cloud/provider work
- no repeatable evidence packet for internal review, clients, or regulators
- no clear way to turn operational traces into training/evaluation data

M5 sells the read, not the platform.

## 3) Live offers (canonical: `docs/offers.json`)

The offer catalog is data-driven. The file `docs/offers.json` is the single
source of truth. As of 2026-05-10:

| ID | Name | Price | Type | Role in M5 |
|---|---|---|---|---|
| `service_credits` | SCBE Service Credits | $5+ pay-as-you-go | usage_credit | Usage-billed tier (2-5% coordination fee on provider passthrough) |
| `tip_jar` | Tip Jar | $5 one time | one_time | Lowest-friction support |
| `supporter_monthly` | AetherMoore Supporter | $20/mo | subscription | Recurring patron tier |
| `governance_snapshot` | **Governance Snapshot** | **$500 fixed scope** | service | **Flagship M5 deliverable** |
| `governance_heartbeat` | **Governance Heartbeat** | **$99/mo** | subscription | **Continuity tier; upsells from Snapshot** |
| `toolkit` | SCBE Toolkit | $29 | digital_download | Self-serve tooling |
| `training_vault` | Training Vault | $29 | digital_download | Self-serve dataset access |

### 3.1) Governance Snapshot (the flagship)

**What the buyer gets, fixed scope:**

- One AI workflow scanned through the SCBE 14-layer pipeline
- One short written report (delta vs. baseline, risks, recommendations)
- One axiom-compliance summary (which of the 5 axioms held, where they bent)
- One recommended action list
- 5-business-day delivery, refund any time before delivery

**Why it sells:** every other governance vendor sells a platform. M5 sells one
finished read for a fixed price — the buyer is not committing to integration,
they are buying clarity.

### 3.2) Governance Heartbeat (the continuity)

**What the buyer gets, monthly:**

- Monthly scan of one workflow
- Short report (delta vs. last month)
- One risk / change summary
- One recommended action list
- Optional dataset / training capture
- Cancel any time

**Why it sells:** Snapshot proves the read; Heartbeat keeps it. First report
within 14 days of subscription start.

## 4) The pipeline (what actually runs)

```
Visitor on /hire or /governance-snapshot
        │
        │ funnel beacons (docs/static/polly-funnel.js)
        ▼
HF dataset: polly-funnel/  (event-prefixed)
        │
        │ /v1/polly/lead   (form intake)
        │ /v1/polly/funnel (event endpoint)
        ▼
HF dataset: polly-leads/   +   polly-chat-live/
        │
        │ Stripe Payment Link → checkout.session.completed
        ▼
api/billing/stripe_webhook.js
   ├─ HMAC-SHA256 verify (constant-time)
   ├─ Snapshot detection: payment_link match OR (mode=payment, $500 USD)
   └─ Heartbeat detection: payment_link match OR (mode=subscription, $99 USD)
        │
        ├─ repository_dispatch: polly_snapshot_paid
        │       └─ .github/workflows/polly-snapshot-paid.yml
        │             ├─ files tracking issue (idempotent on session_id)
        │             └─ SMTP intake email (1-business-day SLA)
        │
        └─ repository_dispatch: polly_heartbeat_started
                └─ .github/workflows/polly-heartbeat-started.yml
                      ├─ files heartbeat-started issue
                      └─ SMTP onboarding email (14-day first report SLA)
        │
        ▼
Operator dashboard: docs/polly-stats.html
   ├─ 7-day per-event funnel breakdown
   └─ funnel_events column (per-event counts)
        │
        ▼
scripts/polly/consolidate_to_sft.py --include-leads
        └─ HF dataset: SFT training pairs (chat + leads) — feeds M6
```

Every box in that diagram exists in the repo today. Nothing in this section
is aspirational.

## 5) Sellable packaging tiers

Beyond the catalog above, M5 packages into three sellable bundles for direct
outreach:

### Launch Pack

- One Governance Snapshot delivery
- First governed dataset published to the buyer's HuggingFace org (or to ours
  with a license grant back)
- One Heartbeat month included
- Price: $500 + $99 = $599 first month

### Monthly Ops

- Heartbeat baseline ($99/mo)
- Plus N additional Snapshot deliveries per month at $500 each
- Plus optional service credits for hosted runs (2-5% on passthrough)
- Price: $99 + per-snapshot

### Enterprise License (negotiated)

- Dedicated deployment of the SCBE pipeline behind the customer's auth
- Optional blockchain notarization of governance stamps (the MMCCL credit
  ledger primitives in
  `src/symphonic_cipher/.../context_credit_ledger/`)
- Custom axiom-mesh tuning
- SLA + indemnification language
- Price: by contract

## 6) Minimal delivery loop

1. Buyer purchases (Stripe Payment Link) or requests via `/v1/polly/lead`.
2. Stripe webhook fires `polly_snapshot_paid` (or `polly_heartbeat_started`).
3. GitHub Actions opens an idempotent tracking issue and emails the intake
   checklist within one business day.
4. Buyer returns workflow / artifacts via the intake link.
5. SCBE creates a workspace formation under
   `.aethermoor-bus/workspaces/<workspace-id>/` and records inputs.
6. Governance checks run over the supplied workflow (axiom-mesh + harmonic
   wall + lexicon drift gate).
7. Buyer receives the short report with findings, fixes, next steps —
   5-business-day SLA for Snapshot, 14-day first report for Heartbeat.
8. Approved traces get added to training/evaluation data via
   `scripts/polly/consolidate_to_sft.py`.

## 7) Operational state

| Surface | State | Notes |
|---|---|---|
| `docs/offers.json` | LIVE | 7 offers, all `status: live` |
| Stripe webhook | LIVE | `/v1/billing/stripe-webhook` deployed on Vercel |
| Snapshot Payment Link | LIVE | `buy.stripe.com/eVqeVeaWu79ZgJi11Ydby0j` |
| Heartbeat Payment Link | **PENDING** | currently mailto; **needs Stripe link + `STRIPE_HEARTBEAT_PAYMENT_LINK_ID` env** |
| Snapshot intake email automation | LIVE | `polly-snapshot-paid.yml`, gated on `livemode=true` |
| Heartbeat onboarding email automation | LIVE | `polly-heartbeat-started.yml` |
| Funnel beacons on /hire and /governance-snapshot | LIVE | `docs/static/polly-funnel.js` |
| /hire-b A/B variant (Snapshot-led hero) | LIVE | separate funnel bucket, isolated for hero comparison |
| Operator stats dashboard | LIVE | `docs/polly-stats.html`, per-event 7-day breakdown |
| Lead → SFT consolidation | LIVE | `scripts/polly/consolidate_to_sft.py --include-leads` |

## 8) Key files

| Concern | File |
|---|---|
| Offer catalog | `docs/offers.json` |
| Snapshot landing | `docs/governance-snapshot.html` |
| Hire page (control) | `docs/hire.html` |
| Hire page (variant) | `docs/hire-b.html` |
| Stripe webhook | `api/billing/stripe_webhook.js` |
| Snapshot paid action | `.github/workflows/polly-snapshot-paid.yml` |
| Heartbeat started action | `.github/workflows/polly-heartbeat-started.yml` |
| Funnel client | `docs/static/polly-funnel.js` |
| Funnel HF upload | `api/_polly_hf_upload.js` |
| Stats endpoint | `api/polly/stats.js` |
| Stats dashboard | `docs/polly-stats.html` |
| Lead routing | `api/polly/commerce.js` |
| Lead → SFT | `scripts/polly/consolidate_to_sft.py` |
| n8n bridge | `workflows/n8n/scbe_n8n_bridge.py` |

## 9) What's missing to scale

Not "what to build next" — what is **already designed and missing only
operator clicks** to ship more revenue:

1. **Heartbeat Payment Link.** Create $99/mo Payment Link in Stripe Dashboard,
   paste into `docs/offers.json`, set `STRIPE_HEARTBEAT_PAYMENT_LINK_ID` in
   Vercel env. ~10 minutes.
2. **Traffic.** All engineering is upstream of a problem that is no longer
   engineering.
3. **One delivered Snapshot reference.** First paid delivery becomes the proof
   asset for everything else.

## 10) Gates and guardrails

Every M5 delivery must clear:

- Axiom-mesh check (5 axioms, see `docs/CORE_AXIOMS_CANONICAL_INDEX.md`)
- Harmonic wall in (0,1] (see `src/harmonic/harmonicScaling.ts`)
- Sacred Tongues lexicon drift gate
- Idempotent Stripe processing (`session.id` is the dedup key)

If any gate fails, the delivery does not ship and the operator is paged via
GitHub issue, not email.

## 11) Boundaries

M5 is not a promise to replace a buyer's compliance team, legal counsel, or
security program. It is a workflow evidence and governance package that makes
AI usage easier to inspect, improve, and operationalize.

## 12) See also

- `docs/M6_SEED_MULTI_NODAL_NETWORK_SPEC.md` — research substrate
- `docs/governance-snapshot.html` — buyer-facing landing
- `docs/SCBE_SYSTEM_OVERVIEW.md` — pipeline architecture
- `docs/CORE_AXIOMS_CANONICAL_INDEX.md` — axiom reference
- `docs/LAYER_INDEX.md` — 14-layer reference
