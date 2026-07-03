# AetherDesk Skill Marketplace Backlog

Date: 2026-06-27
Source: user-provided Kimi skills/plugin inventory
Purpose: convert competitor/product inspiration into AetherDesk modules and training targets.

## Product thesis

AetherDesk should not be "a chat window with tools." It should feel like a local-first operating surface with:

- a command palette
- reusable skills
- agent training/eval dashboard
- browser/research grounding
- docs/slides/sheets workflows
- scheduled tasks
- plugin marketplace
- safe local terminal/browser controls

The useful pattern from Kimi is the skill catalog: small named workflows that users can invoke repeatedly.

## Immediate AetherDesk surfaces to add

| Priority | Surface | Why it matters | First implementation |
|---|---|---|---|
| P0 | Command palette / Ctrl-K | Fast launch surface for humans and agents | `Ctrl+K` opens app/tool/action search across AetherDesk |
| P0 | Skills library | Turns workflows into reusable product units | local skills registry with title, description, category, command/action route |
| P0 | Agent Training Dashboard | Directly matches current model work | show local models, eval results, datasets, pending runs, browser-use holdouts |
| P0 | Browser research mode | Compete with Perplexity | answer composer, source receipts, web audit, no-token-in-browser boundary |
| P1 | Scheduled tasks | Makes AetherDesk useful while idle | local scheduler for safe one-shot tasks, no hidden loops by default |
| P1 | Agent swarm panel | Shows multi-agent work as visible lanes | queue, status, receipts, handoff graph |
| P1 | Docs / Slides / Sheets tools | Productive everyday workflows | launch document/report/table generation from skills |
| P1 | Plugin store / skill marketplace | Upgrade path and moat | install/enable/disable local skill packs with provenance |
| P2 | Shared attachments | Work continuity | file/URL/context tray attached to tasks |
| P2 | Native lore/character grounding | Unique SCBE flavor | character/style packs grounded in local canon and user-authored notes |

## Skill categories to build

### Research and browser

Inspired by:

- Deep Research
- content-research-writer
- seo-audit
- tos-clause-scanner
- scientific-problem-selection
- cross-examine

AetherDesk versions:

- `research-brief`
- `source-receipt`
- `browser-audit`
- `current-recommendation-check`
- `policy-tos-scan`
- `research-problem-selector`
- `plan-cross-examiner`

### Coding, testing, and architecture

Inspired by:

- Kimi Code
- Kimi Claw
- test-suite-architect
- test-driven-dev
- secure-code-review
- deep-module-refactor
- api-shape-explorer
- route-to-openapi
- repo-audit

AetherDesk versions:

- `code-repair`
- `local-code-review`
- `security-review`
- `test-plan-builder`
- `api-shape-lab`
- `module-refactor-map`
- `openapi-generator`
- `repo-risk-audit`

### Product, SaaS, and business

Inspired by:

- pricing-strategy
- saas-metrics-coach
- churn-prevention
- campaign-plan
- ad-creative
- copywriting
- copy-editing
- work-recap-writer
- project-sizing-guide

AetherDesk versions:

- `pricing-lab`
- `saas-metrics`
- `churn-defense`
- `campaign-builder`
- `ad-creative-lab`
- `landing-copy`
- `weekly-recap`
- `project-sizing`

### Data, spreadsheets, and reports

Inspired by:

- Sheets
- sql-insight
- regression-modeler
- weighted-scorer
- stock-signal-analyzer
- value-investing-scorecard
- equity-research
- timeline-builder

AetherDesk versions:

- `sheet-analyzer`
- `sql-insight`
- `regression-report`
- `decision-matrix`
- `technical-indicator-scan`
- `company-scorecard`
- `timeline-report`

### Compliance, legal, and security

Inspired by:

- legal-risk-assessment
- regulatory-audit-generator
- secure-code-review
- tos-clause-scanner
- terraform-deploy-pitfalls

AetherDesk versions:

- `legal-risk-matrix`
- `compliance-checklist`
- `terms-risk-scan`
- `security-code-review`
- `infra-deploy-diagnosis`

Boundary:

These must be framed as operational risk support, not legal advice.

### Documents, presentations, and content

Inspired by:

- Slides
- Docs
- theme-factory
- process-doc
- structured-minutes
- scholarly-writing-refiner
- translation-craft
- localization-toolkit
- domain-glossary

AetherDesk versions:

- `doc-maker`
- `slide-builder`
- `theme-factory`
- `sop-builder`
- `meeting-minutes`
- `academic-polish`
- `translation-workbench`
- `localization-audit`
- `glossary-builder`

### Media and visual QA

Inspired by:

- video-quality-diff
- design-system-builder
- sun-path

AetherDesk versions:

- `video-quality-diff`
- `design-system-extractor`
- `sun-shadow-study`

## Data model

Every skill should be a small manifest:

```json
{
  "id": "browser-audit",
  "name": "Browser Audit",
  "category": "research",
  "description": "Inspect a URL, capture source facts, and produce a receipt.",
  "inputs": ["url", "question"],
  "outputs": ["answer", "sources", "receipt"],
  "routes": ["POST /api/playwright/view", "POST /api/web/audit"],
  "risk": "read-only",
  "local_first": true,
  "secrets_allowed_in_browser": false
}
```

## UI model

Add a Skills app/window in AetherDesk:

```text
left rail: categories
center: skill cards
right rail: selected skill details, inputs, risk, routes, last receipts
top: Ctrl-K search
bottom: run history
```

Each skill card should show:

- skill name
- one-line value
- required inputs
- risk tier
- local/cloud label
- last run status
- install/enable state

## Training implications

Each skill can generate training pairs:

```text
skill instruction
  -> required inputs
  -> safe route plan
  -> expected output schema
  -> verifier gates
```

Keep slices separate:

- `aetherdesk_browser_use_v1`
- `aetherdesk_skills_catalog_v1`
- `aetherdesk_docs_slides_sheets_v1`
- `aetherdesk_security_compliance_v1`
- `aetherdesk_business_ops_v1`

Always prefer human-written open-source guides when license-compatible.

## Next build tasks

| ID | Status | Task | Output |
|---|---|---|---|
| SK-001 | todo | Define AetherDesk skill manifest schema. | `docs/specs/AETHERDESK_SKILL_MANIFEST_SCHEMA.md` |
| SK-002 | done | Add Skills app/window to AetherDesk React desktop. | `AetherDesk/react-desktop/src/main.jsx`, `styles.css` |
| SK-003 | todo | Add Ctrl-K command palette for apps/actions/skills. | Keyboard searchable launcher |
| SK-004 | todo | Convert existing AetherDesk actions into skill manifests. | local `skills.json` or server route |
| SK-005 | todo | Add Agent Training Dashboard skill card. | model/eval/dataset dashboard entry |
| SK-006 | done | Add Browser Audit skill card. | copied into local Skills catalog |
| SK-007 | done | Add Docs/Slides/Sheets placeholder cards. | docs/slides/sheets-adjacent workflow cards copied |
| SK-008 | todo | Add security/compliance skill cards with non-legal-advice boundary. | risk-support workflows |
| SK-009 | todo | Create `aetherdesk_skills_catalog_v1.sft.jsonl`. | training data from skill manifests |
| SK-010 | todo | Add install/enable/disable model for local skill packs. | plugin marketplace foundation |
| SK-011 | done | Copy high-value Kimi-style skills into AetherDesk local catalog. | research, code, docs, data, business, compliance, design |
| SK-012 | done | Add Long-Form Workflow skill. | plan, research, draft, revise, package, publish |
| SK-013 | done | Harden malformed browser URL label and make Skills search global. | `AetherDesk/react-desktop/src/main.jsx` |
| SK-014 | done | Create unattended-safe AetherDesk overnight work queue. | `docs/product/AETHERDESK_OVERNIGHT_WORK_QUEUE_2026-06-27.md` |

## Product rule

Do not add skills as fake buttons. A skill must have at least one of:

- real local route
- documented schema and pending route
- training/eval target
- plugin/install target

Otherwise it stays in backlog.
## Implementation checkpoint - schema/action/workflow

Added the product contracts needed to turn copied Kimi-style cards into real AetherDesk skills:

- `docs/specs/AETHERDESK_SKILL_MANIFEST_SCHEMA.md` defines the skill card and execution manifest.
- `docs/specs/AETHERDESK_BROWSER_ACTION_PACKET.md` defines the browser action, approval, terminal, network, and receipt packet.
- `docs/specs/AETHERDESK_LONG_FORM_WORKFLOW.md` defines the overnight/long-form work loop and handoff contract.

Backlog status update:

- SK-014: done. Overnight work queue exists and now has concrete resume checkpoints.
- SK-015: new. Convert `SKILL_CATALOG` from hardcoded React data into a local manifest JSON file.
- SK-016: new. Make skill cards emit browser action packets instead of only opening apps.
- SK-017: new. Add a receipt drawer that renders `aetherdesk.browser.receipt.v1`.

## Implementation checkpoint - catalog draft

- SK-015: partially done. A local draft catalog now exists at `C:/Users/issda/AetherDesk/react-desktop/src/skills/catalog.json`.
- Remaining SK-015 work: wire `SkillsApp` to import the catalog instead of using hardcoded card data.
- Keep the hardcoded UI in place until a build-approved pass can validate the import path and JSON shape.

## Implementation checkpoint - browser presets

- SK-016: prep done. Browser action packet presets now exist at `C:/Users/issda/AetherDesk/react-desktop/src/skills/browserActionPresets.json`.
- Remaining SK-016 work: wire skill card clicks to create a pending browser action packet and open the Browser app in the preset mode.

## Implementation checkpoint - runtime wiring

- SK-015: runtime wiring applied. `SkillsApp` now uses `src/skills/catalog.json` through the normalized catalog path in `main.jsx`.
- SK-016: runtime wiring applied. Browser-facing skill cards now create pending browser action packets from `src/skills/browserActionPresets.json` and open Aether Browser.
- SK-017: still open. A dedicated receipt drawer is not implemented yet; the packet currently appears in the existing Browser receipt area.

Validation status:

- Not build-validated in this pass.
- Not Playwright-smoked in this pass.
- Treat as code-changed/unverified until build approval.
