# AetherBrowse Packaging Update (Build + Store Path)

Today we pushed AetherBrowse closer to store release from local files.

## What Improved

- Added an AetherBrowse app variant in Capacitor config:
  - app id: `com.issdandavis.aetherbrowse`
  - app name: `AetherBrowse`
- Added dedicated build commands for:
  - Play Store AAB
  - Amazon APK
- Hardened asset copy so local packaging does not crash when `src/aethercode` is missing.
- Added one-command release packager that emits:
  - build artifact
  - SHA256 hash
  - release manifest JSON

## Why This Matters

This turns packaging into a repeatable lane instead of a manual sequence of brittle steps.

## Current Blocker

Packaging machine needs JDK configured:
- `JAVA_HOME` must point to a valid Java installation.

## Next Command

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/package_aetherbrowse_appstore.ps1 -Format aab -Store play -SkipInstall
```

## Short Social Post

Built a real release lane for AetherBrowse from local repo files:
- AetherBrowse app variant (`com.issdandavis.aetherbrowse`)
- one-command Play/Amazon packaging
- hashed release manifest
- fewer brittle build assumptions

Next step: set `JAVA_HOME`, produce signed AAB, move to Play internal testing.
