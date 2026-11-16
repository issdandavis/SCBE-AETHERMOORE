# conference-app/

"Vibe Coder Conference": a demo-day web app where project submissions pass an SCBE governance gate and investors sign an NDA before seeing sensitive material.

- `src/api/` — Express server. Routes: auth, projects, NDAs, conferences, funding, orgs. `store.ts` is an **in-memory store** and `middleware/auth.ts` uses the user ID as a bearer token; both are marked MVP-only in their own headers.
- `src/api/services/` — WebSocket live events, multi-tenant "Conferences-as-a-Service", Zoom Meeting SDK integration.
- `src/frontend/` — React pages, components, and hooks.
- `src/shared/governance/scbeGate.ts` — the governance gate used to score submissions.

```bash
cd conference-app && npm install && npm run dev
```

Deploys to Vercel via `vercel.json`. Tests are in `tests/conference/`.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/conference-app.md`](../docs/file-index/conference-app.md).
