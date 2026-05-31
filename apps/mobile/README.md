# Aethermoor Bus — mobile app

Mobile shell that surfaces SCBE-AETHERMOORE agents and the agent-bus event
stream. Ships as a Trusted Web Activity (TWA) wrapper around a PWA, so the
codebase is plain React + TypeScript and we deliver an AAB to Google Play
without maintaining a separate native codebase.

## Architecture

```
[ Phone Play Store install ]
          │
          ▼
[ Android Trusted Web Activity (Chrome custom tab) ]   ← thin native shell
          │  loads
          ▼
[ PWA at https://bus.aethermoor.io (or your host) ]    ← React + TS + Vite
          │  HTTPS calls
          ▼
[ Your backend ]
   - workflows/n8n/scbe_n8n_bridge.py   (FastAPI, /v1/agent/task etc.)
   - src/api/main.py                    (gateway)
   - npm scbe-agent-bus                 (event envelope)
```

Update flow: deploying the PWA updates the app immediately. Only the TWA
shell goes through Play Store review, and that ships once.

## Layout

| Path | Role |
|------|------|
| `pwa/` | React+TypeScript PWA. Vite build. Manifest + service worker. |
| `pwa/src/` | Components, API clients, agent-bus subscriber. |
| `pwa/public/` | Icons (reuses `artifacts/branding/scbe_dev_logo_512.png`), manifest. |
| `twa/` | Bubblewrap config + signing key wrapper. |
| `twa/twa-manifest.json` | Bubblewrap input. |

## Deploy steps (one-time setup)

### 1. Build + deploy the PWA

```powershell
cd apps/mobile/pwa
npm install
npm run build
# pick a host; example with HF Spaces (free, you already have HF Pro):
hf upload-folder dist <your-hf-space>
# or Vercel: vercel deploy --prod
# or Cloudflare Pages: wrangler pages deploy dist
```

Note the public HTTPS URL of the deployed PWA.

### 2. Wrap with Bubblewrap → AAB

```powershell
cd apps/mobile/twa
npx -y @bubblewrap/cli init --manifest=https://<your-pwa-host>/manifest.webmanifest
# Bubblewrap asks for app name, package name, signing key etc.
# Use:
#   App name:     Aethermoor Bus
#   Package:      io.aethermoor.bus
#   Display:      standalone
# The first build creates a signing keystore at android.keystore.
# BACK THIS UP — losing it means losing the ability to ship updates.

npx @bubblewrap/cli build
# Output: app-release-bundle.aab
```

### 3. Upload to Play Console

The `app-release-bundle.aab` is what you drop into the Internal Testing
release page. Play App Signing takes over from there.

## What the v0.1 PWA does

- Sign in by pasting an HF token (stored only in IndexedDB, never sent
  outside the SCBE backend you configure).
- Agents tab — lists the active agents the bus knows about, last-seen
  governance verdict per agent.
- Bus tab — live feed of agent-bus events (envelope schema:
  `scbe-agentbus-pipe-result-v1`).
- Trigger — minimal form to fire an agent task and watch its verdict.

That's the MVP. Push notifications, multimodal media uploads, deeper agent
control come in v0.2+.

## Why not React Native or Flutter?

- React Native: solid native experience but doubles the codebase. Your
  whole stack (npm `scbe-aethermoore`, `scbe-agent-bus`, the 14-layer
  pipeline TS) already runs in browsers. RN would mean reimplementing
  bridges and dealing with the Android+iOS toolchain split.
- Flutter: Dart. SCBE's TS code would have to be ported or wrapped in
  HTTP. Same downside as RN with extra language friction.
- TWA is what Twitter, Trivago, AliExpress etc. ship to Play Store. Google
  itself recommends it for content-driven apps that already have a strong
  web presence. Yours qualifies.

If/when v1.0 needs native features (background services, deep OS
integrations, push notifications without FCM-on-the-web), we can layer
those into a Capacitor or React Native shell while keeping the PWA as the
authoritative codebase.

## Hosting choices (all $0 to start)

| Host | URL pattern | Notes |
|------|-------------|-------|
| HF Spaces (Static) | `https://<user>-<space>.hf.space/` | You already have HF Pro. Easy. |
| Vercel | `https://<project>.vercel.app/` | Free hobby tier, Edge Network |
| Cloudflare Pages | `https://<project>.pages.dev/` | Free tier, Workers integration |
| GitHub Pages | `https://<user>.github.io/<repo>/` | Already set up via `pages-deploy.yml` |

The TWA only needs an HTTPS-reachable manifest and reasonable uptime. Pick
the host you already operate.
