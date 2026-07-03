# AetherDesk Overnight Work Queue

Date: 2026-06-27
Mode: local/light/unattended-safe

## Operating rules

- No paid HF/OpenWeights jobs.
- No non-local training runs.
- No publishing npm/PyPI/model artifacts.
- No destructive file moves/deletes.
- No repeated browser/HF polling unless explicitly configured.
- Prefer docs, schemas, small UI patches, local datasets, and task lists.
- If a task would need build/test validation, write the change and mark validation pending instead of running it.

## Current priorities

| ID | Status | Lane | Task | Output |
|---|---|---|---|---|
| AD-001 | done | Browser | Harden malformed URL preview label. | `AetherDesk/react-desktop/src/main.jsx` |
| AD-002 | done | Skills | Make Skills search global when query text exists. | `AetherDesk/react-desktop/src/main.jsx` |
| AD-003 | todo | Skills | Define local skill manifest schema. | `docs/specs/AETHERDESK_SKILL_MANIFEST_SCHEMA.md` |
| AD-004 | todo | Skills | Convert current hard-coded skill catalog into JSON manifest. | `AetherDesk/react-desktop/src/skills/catalog.json` or server route |
| AD-005 | todo | Skills | Add selected-skill detail pane with inputs, outputs, risk, routes, last receipt. | React UI patch |
| AD-006 | todo | Browser | Add browser skill presets that prefill query/mode for audit, deep research, terms scan, SEO, design extraction. | React UI patch |
| AD-007 | todo | Browser | Draft Browser Action Language spec. | `docs/specs/SCBE_BROWSER_ACTION_LANGUAGE_SPEC.md` |
| AD-008 | todo | Browser | Draft browser action JSON schema with no-token/no-polling gates. | `docs/specs/SCBE_BROWSER_ACTION_PACKET_SCHEMA.md` |
| AD-009 | todo | Training | Convert skill manifests into `aetherdesk_skills_catalog_v1.sft.jsonl`. | training-data SFT slice |
| AD-010 | todo | Training | Add browser-action conlang holdout prompts. | holdout JSONL |
| AD-011 | todo | Research | Source manifest for human-authored open-source browser/compiler/tokenizer docs. | source manifest, no ingestion yet |
| AD-012 | todo | Product | Add Agent Training Dashboard spec from current local artifacts. | docs/specs or product note |
| AD-013 | todo | Product | Add Long-Form Workflow spec. | docs/specs/AETHERDESK_LONG_FORM_WORKFLOW.md |
| AD-014 | todo | UI | Add command-palette behavior distinct from Start menu. | React UI patch |
| AD-015 | todo | UI | Add visible "no background polling" status badge for browser/dashboard surfaces. | React UI patch |

## Approval-required tasks

| ID | Blocked reason | Task |
|---|---|---|
| AD-B01 | explicit approval required | Run AetherDesk build/smoke validation. |
| AD-B02 | explicit approval required | Start any new local GPU training run longer than a tiny proof. |
| AD-B03 | explicit approval required | Launch any paid/non-local HF/OpenWeights job. |
| AD-B04 | explicit approval required | Publish npm, PyPI, HF, Vercel, Netlify, or GitHub release artifacts. |
| AD-B05 | explicit approval required | Modify auth/token storage behavior beyond docs/UI scaffolding. |

## Recommended next unattended task

Start with `AD-003`:

```text
Define AetherDesk skill manifest schema.
```

Reason:

- It turns copied skill cards into product architecture.
- It supports training data generation.
- It is local-only and low risk.
- It gives future agents a stable target for UI/server implementation.

## Resume instructions for next agent

1. Read this file.
2. Pick the lowest-numbered `todo` task that does not require approval.
3. Make a small local change.
4. Update the status and append relevant autolog entry.
5. Do not validate with builds/tests unless explicitly asked.
## Checkpoint - specs pass

Done:
- AD-003: Defined the local AetherDesk skill manifest schema in `docs/specs/AETHERDESK_SKILL_MANIFEST_SCHEMA.md`.
- AD-007: Defined the browser action packet and receipt contract in `docs/specs/AETHERDESK_BROWSER_ACTION_PACKET.md`.
- AD-013: Defined the long-form workflow contract in `docs/specs/AETHERDESK_LONG_FORM_WORKFLOW.md`.

Still intentionally not run:
- No build or Playwright validation.
- No training run.
- No paid HF/OpenWeights job.
- No package publishing.
- No repeated polling.

Next unattended local/light work:
- AD-004: Convert the hardcoded AetherDesk skill cards into a local `skills/catalog.json` manifest file.
- AD-005: Add browser preset handoff so a skill card can open Browser with a mode, query, and stop rules.
- AD-006: Draft concrete manifests for Browser Audit, Deep Research, Secure Code Review, and Long-Form Workflow.

## Checkpoint - catalog extraction

Done:
- AD-004: Draft local app-side skill catalog created at `C:/Users/issda/AetherDesk/react-desktop/src/skills/catalog.json`.

Important boundary:
- The catalog is not wired into React runtime yet. It is a stable data target for the next code pass.

Next unattended local/light work:
- AD-005: Wire SkillsApp to read from `src/skills/catalog.json` instead of the hardcoded `SKILL_CATALOG`.
- AD-006: Make skill card buttons emit browser action packets into Browser state.
- AD-008: Add a local receipt drawer for browser action packets.

## Checkpoint - browser action presets

Done:
- AD-006 prep: Draft browser action presets created at `C:/Users/issda/AetherDesk/react-desktop/src/skills/browserActionPresets.json`.

Important boundary:
- Presets are not runtime-wired yet. They are ready for the next React code pass.

Next unattended local/light work:
- AD-005: Import `skills/catalog.json` into the Skills app.
- AD-006: Import `skills/browserActionPresets.json` and pass selected packets to Browser state.
- AD-008: Render packet receipts in a drawer or side panel.

## Checkpoint - runtime catalog and browser packet wiring

Done:
- AD-005: `C:/Users/issda/AetherDesk/react-desktop/src/main.jsx` now imports `src/skills/catalog.json` and normalizes it into the existing Skills UI card shape.
- AD-006: Browser-facing skills now load draft `aetherdesk.browser.action.v1` packets from `src/skills/browserActionPresets.json` into Browser state.
- Skills with a browser packet now show `Open packet` instead of only opening a generic route.
- Browser "Good skills" buttons now load their packet directly into Aether Browser instead of only opening the Skills app.
- Browser action posts now include the loaded `actionPacket` in the request body so downstream routes can receipt the skill context.

Validation status:
- Not built.
- Not smoke-tested.
- No network actions, paid jobs, training runs, publishing, destructive operations, or repeated polling were triggered.

Next unattended local/light work:
- AD-008: Add a dedicated receipt drawer/side panel for pending action packets and completed browser receipts.
- AD-009: Add local export from browser receipts to SFT JSONL examples.
- AD-010: Draft corpus license/provenance review before release training.
- AD-B01: Build validation remains approval-gated while machine-light mode is active.

## Checkpoint - train-orchestrator morning sync

Source read:
- `C:/dev/train-orchestrator/MORNING_BRIEFING.md`
- `C:/dev/train-orchestrator/OVERNIGHT_PLAN.md`

Captured:
- Train-orchestrator overnight run is complete and has no more scheduled wakes.
- Corpus is locked at 331 rows: 247 human + 84 verified AI = 74.6% human.
- Train split is 298 rows, holdout is 33 rows, FIM occlusion is 233 rows.
- `api.py` has HF device-code OAuth scaffold but waits on `HF_OAUTH_CLIENT_ID`.
- Live dashboard waits on server-side `HF_TOKEN`.
- First real fine-tune remains explicitly approval-gated.

Next unattended local/light work:
- AD-005: Wire `skills/catalog.json` into the Skills app.
- AD-006: Wire browser action presets into pending Browser state.
- AD-008: Add browser receipt drawer.
- AD-009: Add a local export path from browser receipts to SFT JSONL.
- AD-010: Draft corpus license/provenance review before any release training.

Still blocked on Issac:
- `HF_TOKEN` for live dashboard backend.
- `HF_OAUTH_CLIENT_ID` for Hugging Face device-code login.
- Approval for any paid fine-tune or eval.
- Approval for build/test validation if the machine should stay light.

## Checkpoint - Colab lane scaffold

Done:
- Added `C:/dev/train-orchestrator/colab_lane.py`.
- Added backend routes: `/api/colab/manifest`, `/api/colab/notebook`, `/api/colab/package`.
- Added dashboard route `/colab`.
- Added dashboard page `C:/dev/train-orchestrator/dashboard/src/pages/Colab.tsx`.
- Added sidebar navigation item `Colab`.
- Added `C:/dev/train-orchestrator/COLAB_LANE.md`.

Boundary:
- This creates/downloads a notebook and package only.
- It does not upload to Colab.
- It does not start training.
- It does not spend money.

Next:
- Build-validate dashboard when approved.
- Open `/colab` and download package when backend/dashboard are running.
- Add result-ingest route after first manual Colab run.
