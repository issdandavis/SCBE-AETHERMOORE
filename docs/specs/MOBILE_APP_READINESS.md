# Mobile App Packaging Readiness

Status: audit
Date: 2026-03-31
Scope: what's ready vs what's needed to ship SCBE tools as mobile apps

## Android (Google Play via TWA)

### What's Ready
- PWA manifest (in AetherBrowse deployment kit)
- Service worker (caching, offline support)
- Firebase hosting config
- Digital Asset Links template
- All demos run in browser (no native dependencies)

### What's Needed
- Lighthouse score >= 80 (audit and fix)
- Bubblewrap or PWABuilder packaging
- Play Store developer account ($25 one-time)
- Privacy policy page
- App icon set (512x512 + adaptive)

### Effort: 1-2 days

## iOS (App Store)

### What's Ready
- Same PWA as Android
- Core logic runs in browser

### What's Needed
- React Native (Expo) wrapper (Apple rejects pure PWAs)
- At least one native feature:
  - Option A: Push notifications via APNs
  - Option B: On-device inference via Core ML (lightweight pump kernel)
  - Option C: Biometric auth (Face ID/Touch ID for governance gate)
- Apple Developer account ($99/year)
- App Review compliance (Guideline 4.2 requires "substantial native functionality")

### Effort: 1-2 weeks (mostly the Expo wrapper + App Review cycle)

### Risk: Apple rejection
Each rejection-resubmission takes days to weeks.
Best strategy: include Core ML inference (even lightweight) to clearly satisfy 4.2.

## What to Ship First

1. **Android PWA** (via TWA) -- lowest effort, fastest to market
2. **Polly Chat app** -- pump-oriented chatbot with tongue profiling
3. **AI Arena mobile** -- 9-model debate in your pocket
4. **iOS version** -- after Android validates demand

## Mobile-Specific Pump Considerations

- CycleBudget: reduce from 15s to 5s for mobile (users expect faster)
- Aquifer: ship a compressed 100-bundle subset (not full 1000)
- Tongue profiler: runs client-side, no API calls needed
- UndercoverFilter: critical on mobile (no internal state in screenshots)
