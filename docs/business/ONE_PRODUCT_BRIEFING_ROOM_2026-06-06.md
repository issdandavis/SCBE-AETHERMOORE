# One Product Direction - SCBE Briefing Room

## Product

**SCBE Briefing Room**

Plain-English promise:

> Turn one messy AI/research/workflow question into a professional, source-aware report with a route receipt, risk notes, and next actions.

The buyer does not buy "SCBE," "GeoSeal," "agent bus," "dual lattice," "toolkit," or "RAG."

The buyer buys a finished work product:

- a professional report
- a governance / route receipt
- a risk and fix checklist
- optional supporting templates or exports

Everything else stays under the hood.

## Why This Is Better Than Many Offers

The current site has real assets, but they are presented as separate things:

- Governance Snapshot
- Workflow Snapshot
- Training Vault
- Toolkit
- Service Credits
- Research system
- CLI / agent bus / GeoSeal
- books / lore / research

That is hard for a buyer.

The product should feel like one application:

```text
Ask -> route -> verify -> format -> deliver
```

The pricing can still have tiers, but the experience is one product.

## Core User Experience

### Step 1: User submits a task

The user sees one intake:

```text
What do you need?

[ ] AI workflow governance snapshot
[ ] Research brief
[ ] Proposal / grant / market memo
[ ] Agent/toolchain risk read
[ ] Technical documentation package

Paste the workflow, links, notes, or documents.
Tell us what decision this report should support.
```

### Step 2: System routes internally

The user does not need to know the machinery, but the internal system can use:

- Compass / intent router
- utterance log and real phrasing corpus
- GeoSeal policy gates
- agent bus execution
- governed RAG / source retrieval
- code governance checks
- prompt-injection checks
- route receipts
- report templates
- toolkit / training vault assets when useful

### Step 3: System produces a professional package

Every job produces:

```text
briefing-report.md / briefing-report.pdf
route-receipt.json
risk-checklist.md
next-actions.md
source-notes.md
```

Optional outputs:

- buyer-ready executive summary
- technical appendix
- implementation checklist
- security review table
- prompt / tool route map
- data/source coverage map

## Product Boundary

This is not a chatbot.

This is not "buy access to all my research."

This is a report-and-receipt machine:

> The user brings a problem. SCBE returns a professionally formatted answer package with evidence and governance notes.

That is a product people can understand.

## Under-The-Hood Map

```text
User task
  -> intake normalizer
  -> scope classifier
  -> source / attachment scrubber
  -> route planner
  -> governance gate
  -> retrieval / research / code checks
  -> report composer
  -> receipt generator
  -> formatted delivery
```

SCBE internals become invisible infrastructure:

| Internal asset | Buyer-facing role |
| --- | --- |
| GeoSeal | "Every report includes a route receipt and safety notes." |
| Agent bus | "Your request is routed through a controlled workflow." |
| Toolkit | "Reusable templates are included when relevant." |
| Training Vault | "Benchmarks and examples support technical reports." |
| Governed RAG | "Claims are grounded in selected sources." |
| Utterance logs | "The router improves from confirmed real tasks." |
| CLI | "Operator console for fulfillment, not the main buyer UI." |

## Pricing As One Product

Use one product with three lanes:

### Briefing Room Starter - $99

For one small task.

Deliver:

- concise memo
- route receipt
- three next actions

This maps to the existing `workflow_snapshot_starter`.

### Briefing Room Snapshot - $500

Primary paid offer.

Deliver:

- professional report
- source / workflow map
- risk and governance notes
- route receipt
- implementation checklist
- one follow-up clarification thread

This maps to the existing `governance_snapshot`.

### Briefing Room Heartbeat - $99/month

Retention offer.

Deliver:

- monthly delta report
- refreshed route receipt
- changed-risk summary
- next action list

This maps to the existing `governance_heartbeat`.

The $29 toolkit and vault become add-ons or self-serve fallback:

```text
Want to do it yourself? Download the toolkit.
Training or evaluating systems? Download the vault.
```

They should not compete with the main product.

## First Public Page

Build one page:

```text
docs/briefing-room.html
```

Hero:

```text
SCBE Briefing Room

Professional AI workflow and research reports with route receipts.

Send one workflow, question, source pack, or automation path. Get a formatted report, governance notes, and next actions.

[Start a $99 Briefing] [Book the $500 Snapshot]
```

Section order:

1. Hero
2. What you can submit
3. What you receive
4. How the route receipt works
5. Pricing
6. Example package preview
7. Safety boundary
8. FAQ
9. Final CTA

## First MVP Implementation

No complex portal first. Use a static page plus fulfillment commands.

### Public side

- `docs/briefing-room.html`
- one intake mailto or simple form
- existing Stripe links
- example report preview
- example receipt preview

### Operator side

Create or reuse one internal command later:

```powershell
scbe briefing create --type governance --intake path\to\intake.json --out artifacts\briefings\<id>
```

Expected output:

```text
artifacts/briefings/<id>/report.md
artifacts/briefings/<id>/report.pdf
artifacts/briefings/<id>/route-receipt.json
artifacts/briefings/<id>/risk-checklist.md
artifacts/briefings/<id>/next-actions.md
```

### Minimum working fulfillment

Even before the command exists, the product can be fulfilled manually:

1. buyer pays / sends intake
2. operator runs existing repo tools and research checks
3. operator writes report in the standard template
4. operator includes route receipt / checklist
5. delivery by email

This keeps revenue possible while automation catches up.

## Website Change

The homepage should point to this one product:

```text
Need a governed AI report or workflow review?
Open the SCBE Briefing Room.
```

Do not show all offers as equal hero choices.

The homepage can keep secondary routes:

- Research Lab
- Proof Library
- Product Manual
- Support

But the buyer path should be:

```text
Home -> Briefing Room -> Intake / Checkout -> Report
```

## Conversion Rule

Every public sentence should support one of these:

- "I understand what this product does."
- "I trust this can produce a professional report."
- "I know what I will receive."
- "I know what to click next."

If copy does not support one of those, move it to the Research Lab or Proof Library.

## Immediate Next Build

1. Build `docs/briefing-room.html`.
2. Add an example package preview.
3. Add the existing $99 and $500 checkout links.
4. Add a homepage CTA to the Briefing Room.
5. Keep the rest of the site as proof, not the primary sales path.
