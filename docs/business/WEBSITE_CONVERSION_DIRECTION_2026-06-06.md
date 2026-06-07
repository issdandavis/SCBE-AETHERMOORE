# Website Conversion Direction - 2026-06-06

## Verdict

The website does not need more checkout plumbing. It already has live Stripe, Ko-fi, Cash App, manual invoice, product pages, and service pages. The conversion problem is focus.

The homepage currently asks a buyer to process too many lanes at once:

- governed AI operating system
- research lab
- books and writing process
- $7 / $29 / $99 / $500 offers
- support/tip paths
- demos, benchmarks, and internal proof language

That is a strong archive, but a weak sales path. A buyer should not have to decode the whole SCBE world before knowing what to buy.

The best conversion direction is:

> Sell one concrete first outcome: an AI workflow governance snapshot with receipts.

Everything else should support that path or move behind secondary pages.

The tighter product direction is now captured as **SCBE Briefing Room** in
`docs/business/ONE_PRODUCT_BRIEFING_ROOM_2026-06-06.md`: one buyer-facing
experience that accepts a messy workflow/research question and returns a professional report,
route receipt, risk checklist, and next actions.

## Primary Money Lane

### Primary offer

**SCBE Briefing Room**

Recommended positioning:

> Send one AI workflow, prompt chain, MCP/tool stack, repo automation, research question, or source pack. Get a professional formatted report, route receipt, risk notes, and next actions.

Current offer fit:

- Existing `workflow_snapshot_starter` at `$99 starter`
- Existing `governance_snapshot` at `$500 fixed scope`
- Existing `governance_heartbeat` at `$99/month`
- Existing `$29` toolkit and training vault as down-sells / self-serve add-ons

Recommended conversion hierarchy:

1. **Briefing Room Snapshot - $500** - primary CTA and serious buyer path.
2. **Briefing Room Starter - $99** - lower-friction entry when buyer is curious but not ready.
3. **Briefing Room Heartbeat - $99/month** - post-snapshot retention, not homepage hero.
4. **$29 Toolkit / Training Vault** - self-serve fallback, not equal-weight hero offers.

Why this is the best lane:

- It turns the abstract SCBE platform into a deliverable.
- It matches the market language: AI governance, agent security, audit trail, runtime controls, receipts.
- It can be fulfilled manually while the platform matures.
- It creates evidence, training data, testimonials, and product requirements from each sale.

## Buyer

Best first buyer:

- small AI teams using agents/tools and worrying about prompt injection, unsafe tool calls, secrets, or workflow drift
- founders shipping AI automation who need a defensible risk read before showing customers
- consultants and proposal writers who need governed research/report workflows
- security-aware teams that cannot buy enterprise platforms yet but still need receipts and decision evidence

Not the first buyer:

- Fortune 500 governance programs needing enterprise procurement, SOC2, support SLAs, or legal guarantees
- consumers who want a chatbot
- readers coming for lore, books, prime math, or space-foundry research

Those other audiences can exist, but they should not control the conversion page.

## Website Shape

### New conversion homepage direction

First viewport should answer four things in under ten seconds:

1. **Who is this for?** Teams using AI agents/tools in real workflows.
2. **What do they get?** A governance snapshot with receipts and three prioritized fixes.
3. **Why now?** AI agents can call tools, leak data, and drift without auditable control.
4. **What is the next action?** Buy/book the snapshot or send intake.

Draft hero:

```text
SCBE Briefing Room

Professional AI workflow and research reports with route receipts.

Send one workflow, toolchain, source pack, or automation path. Get a formatted report, governance notes, risk checklist, and next actions.

[Start a $99 Briefing] [Book the $500 Snapshot]
```

Secondary proof line:

```text
Built from SCBE's governed CLI, agent-bus, GeoSeal gates, route receipts, prompt-injection checks, and deterministic test harnesses.
```

### Page sequence

Use this structure for the conversion page:

1. Hero: one offer, one buyer, one primary CTA.
2. Problem: agentic workflows fail in ways normal websites and SaaS forms do not.
3. Deliverable: exactly what the buyer receives.
4. Proof: repo-backed examples, tests, receipts, screenshots, and short demos.
5. Packages: $99 starter, $500 snapshot, $99/month heartbeat, $29 self-serve fallback.
6. Who it is for / not for.
7. Intake and safety rules: no secrets, no regulated data, redacted examples only.
8. FAQ.
9. Final CTA.

### What to move out of the homepage

Move these behind a clear `Research Lab` or `Proof Library` route:

- prime/number theory research
- space foundry and tether concepts
- sacred tongue / dual lattice deep architecture
- books and lore
- long benchmark narratives
- broad "operating system" philosophy

Do not delete them. They are useful proof and identity. They just should not compete with the buyer's first decision.

## Offer Copy

### $99 starter

Name:

> AI Workflow Snapshot Starter

Buyer promise:

> A quick risk read for one AI workflow, repo automation, prompt chain, MCP stack, or agent process.

Deliverables:

- one concise findings memo
- key unsafe tool paths / prompt injection surfaces / observability gaps
- three prioritized fixes
- upgrade credit toward the $500 Governance Snapshot

### $500 primary

Name:

> AI Governance Snapshot

Buyer promise:

> A fixed-scope review that turns one AI workflow into a risk map, evidence checklist, and action plan.

Deliverables:

- 2-5 page findings memo
- workflow map
- governance / security risk list
- decision receipt checklist
- three prioritized fixes
- one follow-up clarification thread

### $99/month retention

Name:

> Governance Heartbeat

Buyer promise:

> Monthly delta report for one workflow so the snapshot does not go stale.

Use after the snapshot, not before it.

### $29 products

Keep these, but position as fallback:

- **Toolkit**: templates and examples for builders who want to do it themselves.
- **Training Vault**: dataset/benchmark starter for people training or evaluating governed AI systems.

## Proof Stack

Use proof that a buyer can understand without reading the whole repo.

Best proof blocks:

- a one-screen "before / after" workflow route
- example governance receipt JSON
- prompt-injection blocked example
- GeoSeal / agent-bus route diagram
- test counts and commands, but only after the buyer understands the outcome
- a short "what we inspect" checklist

Avoid leading with:

- novel theory claims
- massive architecture diagrams
- abstract sacred geometry language
- all product offers at once
- raw benchmark tables without a buyer story

## Competitive Position

The market is already moving toward AI governance, agent security, runtime controls, audit trails, and receipts.

SCBE should not try to out-enterprise enterprise platforms on day one. The wedge is:

> A small, practical governance service and toolkit for teams using AI agents before they are ready for a large platform.

This is closer to "audit/readiness snapshot plus implementation notes" than "buy a full governance platform."

Competitor language is useful, but the site should avoid sounding like an enterprise vendor without enterprise proof. Sell the first useful artifact.

## Researcher-Guided RAG Lane

There is a second strong money lane already preserved in project memory:

> Private, governed research systems that turn verified internal knowledge into client-ready drafts with human approval and full audit trails.

This can become a second landing page after the governance snapshot page is cleaned up.

Best offer shape:

> SCBE Briefing Room - Research Brief mode

Deliverables:

- ingest selected docs / notes / sources
- generate source-grounded research briefs, proposal drafts, grant drafts, market reports, technical memos, or executive summaries
- human approval queue
- audit JSON per output

This is commercially stronger than selling a standalone governance SDK because it delivers immediate paid utility and lets SCBE run as the trust layer underneath.

## First Build Recommendation

Do not rewrite the full `docs/index.html` first. It is large and functions as an archive.

Build or revise one clean buyer page first:

```text
docs/briefing-room.html
```

or, as a temporary fallback if you want to reuse the current live page:

```text
docs/governance-snapshot.html
```

Then add one prominent homepage CTA:

```text
Need a governed AI report or workflow review? Open the SCBE Briefing Room.
```

This keeps the existing site intact while creating a measurable conversion path.

## Measurement

Minimum measurement without new paid tooling:

- count clicks to Stripe links by offer
- count `mailto:` intake starts
- track downloads / exports of toolkit pages
- add URL parameters to each CTA path:
  - `?src=home-hero`
  - `?src=offers`
  - `?src=governance-page`
  - `?src=footer`

Primary metric:

> governance snapshot checkout or intake-start rate.

Secondary metrics:

- $99 starter purchases
- toolkit purchases
- heartbeat follow-up conversions
- research brief inquiries

## Next Action

Make `briefing-room.html` the conversion page:

1. Tighten hero around one result.
2. Move the $99 Starter and $500 Snapshot CTAs above the fold.
3. Keep $99 starter as secondary.
4. Push toolkit/training/book offers lower.
5. Add an example receipt and a "what we inspect" checklist.
6. Add one homepage CTA pointing to the snapshot page.

This is the smallest change that turns the current website from "archive of a complex system" into "buy the first useful result."

## Research Notes

Sources used for current market and conversion direction:

- NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework
- NIST Generative AI Profile: https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf
- OWASP Top 10 for LLM Applications: https://owasp.org/www-project-top-10-for-large-language-model-applications
- OWASP Agentic Skills Top 10: https://owasp.org/www-project-agentic-skills-top-10/
- Protect AI platform positioning: https://protectai.com/
- Credo AI governance platform positioning: https://www.credo.ai/product
- AgentReceipt audit-trail positioning: https://www.agentreceipt.co/
- AgentTraceHQ audit-trail positioning: https://www.agenttracehq.com/
- CXL landing page clarity guidance: https://cxl.com/blog/designing-landing-pages-product-unique/
