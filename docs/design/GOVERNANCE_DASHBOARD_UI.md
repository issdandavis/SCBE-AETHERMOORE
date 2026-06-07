# Governance dashboard UI standard

**Status:** design contract for docs/static and agent-bus surfaces
**Audience:** humans + AI editors — keep future changes from drifting to generic SaaS styling

## Intent

The product should read as **AI safety infrastructure** / **developer operations console**, not a marketing landing page. Reviewers should understand ALLOW / QUARANTINE / ESCALATE / DENY without a long explanation.

## Locked direction

| Element | Rule |
|---------|------|
| Theme | Dark operational dashboard |
| Decision colors | ALLOW green, QUARANTINE yellow, ESCALATE blue, DENY red — same semantics everywhere |
| Logs | Monospace terminal block for live governance decisions and pipeline traces |
| Pipeline | Show the 14-layer path as an **active system**, not static explanatory copy only |
| Tone | Premium, heavy-duty developer tool — restrained neon accents, high contrast |

## Do not

- Flip to light theme by default on ops pages
- Use stock “AI startup” gradients or generic chat bubbles on the governance console
- Hide decision tier colors behind icons-only UI
- Replace the terminal/log region with short toast-only feedback

## Related implementation

- Static docs: `docs/static/polly-sidebar.js`, `docs/agents.html`
- Ingestion math: `src/harmonic/contextBundle.ts` (L1 mouth — intent + identity/temporal/environment on imaginary lift)

## Screenshots

Optional: add `docs/design/screenshots/` when capturing stable builds for KDP or pitch decks — not required for CI.
