# AetherCode Kindle App — Design Document

**Date:** 2026-03-04
**Author:** Claude (agent.claude)
**Lane:** kindle-app-packaging
**Status:** Building

## Problem

AetherCode exists as a PWA (Progressive Web App) served from a local FastAPI
gateway. To reach the Amazon Appstore (Kindle Fire tablets), we need a native
Android APK that wraps the PWA with offline-first behavior.

## Decision

Use **Capacitor** (by Ionic) to wrap the AetherCode PWA as an Android APK.

### Why Capacitor over alternatives?

| Approach | Verdict | Reason |
|----------|---------|--------|
| Capacitor | **Chosen** | Real APK, offline support, plugin ecosystem, Kindle-compatible |
| TWA (Bubblewrap) | Rejected | Kindle uses Silk browser, not Chrome — TWA may not work |
| Amazon WebApp SDK | Rejected | Deprecated since 2023 |
| React Native | Rejected | Would require rewriting the entire UI |

## Architecture

```
kindle-app/
├── package.json            # Capacitor dependencies
├── capacitor.config.ts     # Android + Kindle Fire config
├── scripts/
│   └── copy-pwa-assets.js  # Copies + patches src/aethercode/ → www/
├── www/                    # Patched PWA assets (generated)
│   ├── index.html          # Patched app.html (API → GCP VM)
│   ├── manifest.json       # Patched paths (relative)
│   ├── sw.js               # Patched service worker
│   └── static/icons/       # App icons
├── android/                # Capacitor Android project (generated)
└── store-listing.md        # Amazon Appstore metadata

.github/workflows/
└── kindle-build.yml        # CI: builds APK on push to kindle-app/
```

## Data Flow

```
User opens AetherCode on Kindle
  → Capacitor WebView loads www/index.html
  → Service worker caches shell for offline
  → API calls go to GCP VM (34.134.99.90:8001)
  → If offline: cached UI shows, "Offline" status
  → If online: full AI features (chat, code, research, browse)
```

## Asset Pipeline

The `copy-pwa-assets.js` script:
1. Copies `src/aethercode/app.html` → `www/index.html`
2. Patches `window.location.origin` → GCP VM URL
3. Fixes all paths from absolute (`/sw.js`) to relative (`./sw.js`)
4. Adds Capacitor bridge + online/offline event handlers
5. Copies manifest.json, sw.js, icons

## Build Pipeline

### CI (GitHub Actions)
- Triggers on push to `kindle-app/**` or `src/aethercode/**`
- Ubuntu runner with JDK 17 + Android SDK
- Outputs debug APK as artifact

### Local (when Android SDK installed)
```bash
cd kindle-app
npm install
npm run build
npx cap add android
npx cap sync
cd android && ./gradlew assembleDebug
adb install app/build/outputs/apk/debug/app-debug.apk
```

## Kindle Fire Targeting

- **Min SDK:** 22 (Fire OS 5, Kindle Fire 7th gen 2017+)
- **Target SDK:** 34 (Android 14)
- **WebView:** Amazon WebView (Chromium-based, similar to Chrome)
- **Screen sizes:** 7" (1024x600), 8" (1280x800), 10" (1920x1200), 11" (2000x1200)

## Offline Behavior

| Feature | Online | Offline |
|---------|--------|---------|
| UI Shell | Yes | Yes (cached) |
| Chat | Yes | No (shows offline) |
| Code | Yes | No |
| Research | Yes | No |
| Browse | Yes | No |
| Settings/Keys | Yes | Yes (local storage) |

## Store Submission

See `kindle-app/store-listing.md` for full Amazon Appstore metadata.

**Submission steps:**
1. Register at developer.amazon.com
2. Create new app → Android/Kindle Fire
3. Upload APK
4. Fill in listing from store-listing.md
5. Submit for review

## Dependencies

- AetherCode PWA: `src/aethercode/` (app.html, manifest.json, sw.js)
- GCP VM: `34.134.99.90:8001` (backend API)
- Capacitor: `@capacitor/core`, `@capacitor/android`, `@capacitor/cli`
- Build: JDK 17+, Android SDK (CI or local)
