# Overseer Control Panel Research (2026-04-30)

## Goal

Design an overseer-facing agentic control panel that keeps execution fast under pressure while preserving governance gates (execution, review, temporal reliance).

## Research Signals Applied

### 1) StarCraft command UX patterns

- **Control groups as fast context switching**: experts bind key unit/building sets and rebind in pressure moments.
- **Alert-first minimap behavior**: bright localized alerts and rapid camera-jump semantics keep operators on highest-impact events.
- **Production queue visibility**: macro control works because queues are always visible and actionable.

Applied to panel:
- lane filters (`execution`, `review`, `temporal`) as control-group analogs.
- persistent alert feed with severity tiers.
- mission queue as production-style list with clear state transitions.

## 2) AI company control-plane patterns (OpenAI + Datadog docs)

- **RBAC + spend/use controls** (OpenAI Enterprise admin controls).
- **Trace-backed investigation loops** (Datadog Bits AI SRE: hypothesis -> evidence -> conclusion).
- **Incident channel ergonomics**: quick summaries, responder-visible status, and explicit next actions.

Applied to panel:
- doctrine switches mapped to execution/review/temporal layers.
- "Battle Board" quick doctrine for escalation/commit rules.
- alert + queue layout that separates triage from action execution.

## 3) SCBE-specific alignment

- The panel is not a replacement for Stage6 or review policy. It is an operator surface over existing gates.
- Commit remains downstream of: generation -> constrained decode -> review -> governance decision.
- Temporal reliance remains explicit for delayed tasks requiring re-anchor checks.

## Implemented Surface

- New app: `scbe-visual-system/components/apps/OverseerControlPanelApp.tsx`
- Desktop launcher integration: `scbe-visual-system/App.tsx` (`Overseer` icon/app)

## Next practical upgrades

- Wire live data from `agent_bus` events JSONL into alert and mission sections.
- Add per-lane policy toggles backed by real manifest/tool contract checks.
- Add "camera jump" equivalent: one-click deep-link into failing job/log/test context.

## Toolchain note (2026-04-30)

`lucide-react` **v1.11.0** (pinned in `scbe-visual-system`) does not export a `Github` icon. The Automator graph node now uses `GitBranch`, which keeps `npm run build` green. When upgrading Lucide, re-check icon renames in [lucide.dev](https://lucide.dev).
