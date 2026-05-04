# Play Store Readiness - AetherBrowse / AetherCode

Date: 2026-05-03

## Build Evidence

Command run:

```powershell
cd C:\Users\issda\SCBE-AETHERMOORE\kindle-app
npm run build:aab:aetherbrowse
```

Result: PASS.

Release artifact:

- `kindle-app/android/app/build/outputs/bundle/release/app-release.aab`
- Size: `67,471,067` bytes
- SHA-256: `2353e115a26363849b6d5001f18bf1a74c4852d35af358a2038f0424eedb94ea`

Staged Play upload copy:

- `artifacts/releases/aetherbrowse-appstore/20260504T013958Z/aetherbrowse-play.aab`
- SHA-256: `2353E115A26363849B6D5001F18BF1A74C4852D35AF358A2038F0424EEDB94EA`
- Manifest: `artifacts/releases/aetherbrowse-appstore/20260504T013958Z/release_manifest.json`

Gradle result:

- `:app:bundleRelease` completed successfully.
- `:app:signReleaseBundle` completed successfully.
- Release signing report exists for the release variant.
- Release certificate is valid through 2053.

## Current App Shape

Capacitor project:

- Root: `kindle-app`
- Android project: `kindle-app/android`
- Web assets: `kindle-app/www`
- App bundle command: `npm run build:aab:aetherbrowse`

Current variant command builds the AetherBrowse package variant from the AetherCode Capacitor shell.

Store listing draft:

- `kindle-app/store-listing-google-play.md`

Current listing fields include title, short description, full description, category, privacy/support URLs, screenshot plan, feature graphic plan, package details, and content rating notes.

## Important Boundaries

- The local signing properties file exists and is ignored by Git.
- Do not commit signing files, keystores, passwords, or generated bundle outputs.
- The generated `app-release.aab` is a local release artifact, not a source file.

## Blockers Before Upload

1. Confirm the Play Console app identity.
   - Decide whether the Play Store package is `com.issdandavis.aetherbrowse` or `com.issdandavis.aethercode`.
   - The current AAB command uses the AetherBrowse variant.

2. Verify the built app on emulator or physical device.
   - The phone-lane status currently recommends `check-adb-or-recover`.
   - Local ports `127.0.0.1:8088` and `127.0.0.1:8400` were not live during this pass.

3. Review store claims against the actual packaged UI.
   - The current listing promises multi-model round table behavior and bring-your-own-key storage.
   - Before public upload, verify those flows in the built app or soften the listing language.

4. Create screenshots and feature graphic.
   - Required phone screenshots are not yet captured from the release build.
   - Tablet screenshots are still planned, not captured.

5. Privacy policy.
   - Current draft points to `https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/PRIVACY.md`.
   - `PRIVACY.md` was added in this pass.
   - Before public upload, review it once against the final packaged app behavior.

## Next Exact Step

Run the release readiness gate, then run the emulator lane, install the release build or a release APK build, and capture screenshots:

```powershell
npm run publish:play:check
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/start_polly_pad_emulator.ps1 -SkipEmulatorLaunch
cd kindle-app
npm run build:apk:aetherbrowse
```

Then install the generated release APK with `adb install` if the emulator is visible.

If Play Console upload is the next milestone, upload the AAB only after the screenshot and privacy checks pass.
