# AetherBrowse Command Center — Play Store / Kindle Deployment

## Architecture

```
+--------------------------------------------------------------+
|                    PLAY STORE / KINDLE                       |
|                                                              |
|  +--------------------------------------------------------+  |
|  |           TWA (Trusted Web Activity)                   |  |
|  |     Android wrapper around your web app                |  |
|  |     Full-screen, no browser chrome                     |  |
|  |     Launches: https://aetherbrowse.web.app             |  |
|  +------------------------+-------------------------------+  |
+---------------------------+----------------------------------+
                            |
+---------------------------+----------------------------------+
|              FIREBASE HOSTING                                |
|                                                              |
|  React SPA (this command center UI)                          |
|  Privacy policy page                                         |
|  PWA manifest + service worker                               |
|  <-> Firebase Auth (anonymous -> optional email)             |
|  <-> Firestore (mission logs, approvals, user prefs)         |
|  <-> Cloud Functions (webhooks, push notifications)          |
+---------------------------+----------------------------------+
                            | HTTPS API calls
+---------------------------+----------------------------------+
|             CLOUD RUN (your existing backend)                |
|                                                              |
|  FastAPI: agents/browser/main.py                             |
|  Endpoints:                                                  |
|    POST /v1/browse          <- main browsing + governance    |
|    POST /v1/safety-check    <- pre-flight validation         |
|    GET  /v1/containment-stats <- telemetry for Poincare disc |
|    POST /v1/reset-session   <- session management            |
|    GET  /health             <- health check                  |
|                                                              |
|  HYDRA Swarm: hydra/swarm_browser.py                         |
|    6 Sacred Tongue agents (KO/AV/RU/CA/UM/DR)               |
|    Playwright + Chromium                                     |
|    SCBE 14-layer governance on every action                  |
|    Ledger + audit trail                                      |
+--------------------------------------------------------------+
```

## Why TWA Instead of React Native

1. Backend is already FastAPI — app is a client dashboard
2. TWA = web app running full-screen as Android app, no WebView limitations
3. No React Native build chain to maintain
4. One codebase serves web + Play Store + Kindle
5. Updates deploy instantly via Firebase Hosting
6. Chrome rendering engine, not janky WebView

Requirements:
- Digital Asset Links verification (proves domain ownership)
- PWA requirements (manifest.json, service worker, HTTPS)
- Hosted on controlled domain

## Deployment Phases

### Phase 1: Firebase Project Setup
```bash
npm install -g firebase-tools
firebase login
firebase init hosting  # public: dist, SPA: yes
firebase init firestore
```

### Phase 2: Build Web App
```bash
npm create vite@latest aetherbrowse-app -- --template react-ts
cd aetherbrowse-app
npm install firebase zustand
npm run build
```

### Phase 3: PWA Configuration
- manifest.json with icons (192, 512, maskable)
- Service worker for offline support
- Register SW in app entry point

### Phase 4: Deploy to Firebase
```bash
firebase deploy --only hosting
```

### Phase 5: TWA Android Wrapper
Use PWABuilder (https://pwabuilder.com) — fastest path, no Android Studio needed.

### Phase 6: Digital Asset Links
- Get SHA-256 from signing key
- Create `.well-known/assetlinks.json`
- Redeploy Firebase

### Phase 7: Play Store Submission
- Upload AAB, store listing, content rating, privacy policy

### Phase 8: Amazon Appstore / Kindle
- Submit APK or use Amazon Web App Tester for hosted URL

## Cost Estimate

| Service | Free Tier | Monthly |
|---------|-----------|---------|
| Firebase Hosting | 10GB transfer | $0 |
| Firebase Auth | 10K anon/month | $0 |
| Firestore | 1GB, 50K reads/day | $0 |
| Cloud Run | 2M requests | ~$8-15 |
| Play Store | $25 one-time | - |
| Amazon Appstore | Free | $0 |
| **Total** | | **~$8-15/mo** |

## Revenue Model

- v1.0 Free: 5 missions/day, basic research
- v1.1 Freemium: $9.99-29.99/mo tiers
- Enterprise: Self-hosted, custom governance, SLA
