# Vercel Cost Guard

The Vercel project `scbe-agent-bridge-vercel` is kept as a paid-service test surface, not the primary customer website.

Default customer delivery stays on GitHub Pages at `https://aethermoore.com/`. Vercel should only spend build CPU when a deployment is tied to production, launch validation, or an explicit customer/test branch.

## Branches Allowed To Build

The repository `vercel.json` allows Vercel builds only for:

- `main`
- `launch/*`
- `vercel-test/*`
- `customer/*`
- `fix/launch-*`

All other branches are ignored by Vercel's Ignored Build Step. This intentionally blocks routine automation branches, dependency branches, training branches, and research branches from burning preview build CPU.

## Current Production Project

- Team: `issac-davis-projects`
- Project: `scbe-agent-bridge-vercel`
- Project ID: `prj_9nwqtAmDwlZIOGUKSoIbkdiEttdC`
- Production URL: `https://scbe-agent-bridge-vercel.vercel.app`

## Operator Checks

Use the Vercel CLI with the existing logged-in account:

```powershell
npx --yes vercel@latest whoami
npx --yes vercel@latest project inspect scbe-agent-bridge-vercel --scope issac-davis-projects
npx --yes vercel@latest usage --scope issac-davis-projects --group-by project
npx --yes vercel@latest usage --scope issac-davis-projects --breakdown daily
```

Do not buy credits or enable paid extras unless there is a real customer need.
