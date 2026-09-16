# Vercel cost guard and operator guide

The root Vercel project is an optional host for the agent bridge, Polly HTTP
handlers and billing webhook. The primary static website is served by GitHub
Pages at `https://aethermoore.com/`. Model training has its own compute pipeline.

## Default: deploy deliberately

Root `vercel.json` sets `git.deploymentEnabled` to **false**. Git pushes and pull
requests should not automatically deploy this root project, including pushes to
`main`. A deliberate CLI or dashboard deployment remains possible. The setting
does not delete existing deployments, change the account's plan, cancel running
builds, or cap traffic/usage on an already deployed service.

The old ignored-build script is still present as a secondary path filter, but it
is not a spending limit. It permits `main` unconditionally and permits a build
when metadata lookup fails. The previous documentation overstated its branch
restrictions. Do not rely on that filter to suppress automatic deployments.

This file applies to the root agent-bridge project. A project linked with
`conference-app` or another subdirectory as its Root Directory reads that
directory's configuration. Inventory each linked Vercel project before claiming
account-wide automation is disabled.

See Vercel's [Git configuration](https://vercel.com/docs/project-configuration/git-configuration)
for the supported switch. Restoring automated builds requires an explicit review
of the branches, changed paths, account plan and usage allowance first.

## Historical link and verified account state

- Team slug recorded locally: `issac-davis-projects`
- Project: `scbe-agent-bridge-vercel`
- Project ID: `prj_9nwqtAmDwlZIOGUKSoIbkdiEttdC`
- Previously published URL: `https://scbe-agent-bridge-vercel.vercel.app`

On 2026-09-13 UTC, the signed-in dashboard showed the Hobby plan and no projects.
The account activity log records this project and eight others deleted on
September 6. The published `/api/agent/system` URL returns HTTP 404 with
`X-Vercel-Error: DEPLOYMENT_NOT_FOUND`; the main GitHub Pages website returns
HTTP 200. The local project link above is stale. Do not use it as evidence that
an active deployment exists or silently recreate a deleted service.

The September 6 quota notification specifically reported **Function Storage at
100% of its 10 GB allowance**. At review time, the Usage dashboard showed
deployment storage and function storage at **0 B**, with traffic and function
execution below their displayed allowances. The activity log also shows earlier
deployments from routine automation and dependency branches. Manual deployment
defaults prevent those Git triggers if this root project is deliberately
reintroduced. They do not replace a deployment-retention policy.

Keep the retired bridge's failures visible in smoke reports until its supported
replacement or an explicit disabled-service contract has been verified. Do not
redeploy merely to turn those checks green. These observations describe this
team at review time, not other teams or future usage.

## Read-only account inspection

Use a linked project directory. Check `.vercel/project.json` (one project) or
`.vercel/repo.json` (a linked monorepo) before running project-scoped commands.
Confirm the team before linking or deploying; never print credentials.

Vercel CLI 59.16.0 was checked for this review:

```powershell
npx --yes vercel@59.16.0 whoami
npx --yes vercel@59.16.0 teams ls
npx --yes vercel@59.16.0 project ls --scope issac-davis-projects
npx --yes vercel@59.16.0 project inspect scbe-agent-bridge-vercel --scope issac-davis-projects
npx --yes vercel@59.16.0 list scbe-agent-bridge-vercel --scope issac-davis-projects
npx --yes vercel@59.16.0 usage --scope issac-davis-projects --group-by project
npx --yes vercel@59.16.0 usage --scope issac-davis-projects --breakdown daily
```

If logged out, complete `npx --yes vercel@59.16.0 login` with the account owner.
Reconnecting the Vercel app integration and signing into the CLI are separate
authentication paths; neither is a plan upgrade.

Check the current plan, allowance reset dates, build usage, function usage,
traffic and storage before creating another deployment. See
[CLI usage](https://vercel.com/docs/cli/usage). Historical configuration cannot
establish the current balance or which project caused an earlier alert.

## When Vercel is useful here

- Previewing an explicitly selected web interface before release.
- Serving a small, authenticated HTTP API or receiving a verified webhook.
- Routing a web request to a separately hosted model, with request and token
  limits on the model service as well as platform usage controls.

First validate the existing local routers with
`node scripts/vercel/verify-router.cjs` and the relevant API tests. Review the
exact source, required environment-variable names and intended API routes before
a preview deployment. Keep deployment protection enabled; use `vercel curl`
for authenticated preview checks. Verify real responses before changing public
links or promoting an alias.

The [Hobby plan](https://vercel.com/docs/plans/hobby) is for personal,
non-commercial use. A customer-facing commercial bridge needs a suitable plan;
do not buy one solely to make an unused endpoint's smoke check green. On paid
plans, inspect [spend management](https://vercel.com/docs/spend-management): an
alert alone is not an automatic pause, and the controls do not cover every fixed
fee or third-party charge. Do not enable credits, storage products or other paid
extras without a defined use and budget.
