# SCBE Repo Manager — GitHub App

Automated repository management for **SCBE-AETHERMOORE**, built on the [Probot](https://probot.github.io/) framework.

## What It Does

| Event | Action |
|-------|--------|
| **Issue opened** | Detects component (crypto, harmonic, tongues, game, API, CI, testing, docs), adds labels, classifies type (bug/enhancement/question/security), flags priority |
| **PR opened** | Generates a review checklist (test coverage, changelog, layer tags, lint, crypto review flag), adds size label (S/M/L/XL), lists changed files |
| **Push to main** | Parses conventional commits, categorizes them, appends entries to `CHANGELOG.md` under `[Unreleased]` |
| **Check suite passed** | Adds `ready-to-merge` label when all CI checks pass on a PR; removes it on failure |
| **Scheduled (daily)** | Marks issues/PRs inactive for 30+ days as stale, closes after 7 more days of inactivity, creates dependency update reminder issues |

## Setup

### 1. Register the GitHub App

1. Go to **https://github.com/settings/apps/new**
2. Fill in the form using `app.yml` as reference:
   - **Name**: `SCBE Repo Manager`
   - **Webhook URL**: Your server URL (or a [smee.io](https://smee.io/new) proxy for local dev)
   - **Webhook Secret**: Generate one (`openssl rand -hex 20`)
3. Set permissions:
   - Issues: **Read & write**
   - Pull requests: **Read & write**
   - Contents: **Read & write**
   - Checks: **Read-only**
   - Metadata: **Read-only**
4. Subscribe to events: **Issues**, **Pull request**, **Push**, **Check suite**
5. Click **Create GitHub App**
6. Note the **App ID** from the app settings page
7. Generate a **Private Key** (`.pem` file) and download it

### 2. Install on Repository

1. Go to your app's settings page
2. Click **Install App** in the sidebar
3. Select the **issdandavis** account
4. Choose **Only select repositories** and pick `SCBE-AETHERMOORE`
5. Click **Install**

### 3. Configure Environment

```bash
cd apps/scbe-github-app
cp .env.example .env
```

Edit `.env` and fill in:
- `APP_ID` — from step 1.6
- `PRIVATE_KEY_PATH` — path to the `.pem` file from step 1.7
- `WEBHOOK_SECRET` — the secret you generated in step 1.2

### 4. Install Dependencies

```bash
npm install
```

### 5. Run

**Development** (with smee.io webhook proxy):
```bash
# Set WEBHOOK_PROXY_URL in .env first
npm run dev
```

**Production**:
```bash
npm start
```

## Scheduled Maintenance

The daily stale-cleanup runs via `repository_dispatch`. Add this GitHub Actions workflow to trigger it:

```yaml
# .github/workflows/scheduled-maintenance.yml
name: Scheduled Maintenance
on:
  schedule:
    - cron: '0 8 * * *'  # Daily at 08:00 UTC
  workflow_dispatch: {}

jobs:
  dispatch:
    runs-on: ubuntu-latest
    steps:
      - uses: peter-evans/repository-dispatch@v3
        with:
          event-type: scheduled-maintenance
```

## Component Detection

The triage engine recognizes these SCBE components from issue/PR text:

| Component | Example Keywords |
|-----------|-----------------|
| `component:crypto` | crypto, pqc, kyber, dilithium, ml-kem, spiral-seal, envelope, nonce |
| `component:harmonic` | harmonic, pipeline, 14-layer, poincare, hyperbolic, hamiltonian, mobius |
| `component:tongues` | tongue, langues, sacred tongue, KO, AV, RU, CA, UM, DR, tokenizer |
| `component:game` | game, spiralverse, everweave, cstm, story, lore, choicescript |
| `component:api` | api, fastapi, express, gateway, endpoint, router, middleware |
| `component:ci` | ci, workflow, github action, docker, release, deploy |
| `component:testing` | test, vitest, pytest, coverage, benchmark, mock |
| `component:docs` | doc, readme, changelog, spec, architecture, guide |

## Commit Classification

Conventional commits (`feat:`, `fix:`, `docs:`, etc.) are parsed automatically. Non-conventional messages use keyword heuristics to classify into: Added, Fixed, Changed, Security, Performance, Documentation, Testing, CI/CD, Build, Style, Maintenance.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ID` | — | GitHub App ID (required) |
| `PRIVATE_KEY_PATH` | `./private-key.pem` | Path to app private key (required) |
| `WEBHOOK_SECRET` | — | Webhook verification secret (required) |
| `LOG_LEVEL` | `info` | Probot log level |
| `STALE_DAYS` | `30` | Days before marking issues/PRs as stale |
| `ENABLE_SCHEDULED_TASKS` | `true` | Enable/disable scheduled maintenance |

## Architecture

```
apps/scbe-github-app/
  index.js          Main Probot app (all event handlers)
  package.json      Dependencies and scripts
  app.yml           GitHub App manifest (permissions + events)
  .env.example      Environment variable template
  README.md         This file
```

The app is a single `index.js` module exporting the Probot handler function. It uses:
- **Probot** for webhook routing, authentication, and event context
- **@octokit/rest** for GitHub API calls (provided via `context.octokit`)

## Deployment Options

1. **Local + smee.io** — Best for development
2. **GitHub Actions** — Use `@probot/adapter-github-actions` (zero infrastructure)
3. **Docker** — Add to the main SCBE Docker Compose stack
4. **Hetzner VPS** — Deploy alongside the existing SCBE API server
5. **Vercel / Railway / Render** — Serverless deployment with webhook URL
