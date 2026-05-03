# Deploy Ready Status - 2026-05-03

This is the current shipping board for SCBE-AETHERMOORE after the May 3 deploy-readiness sweep.

## Current Status

Overall status: packageable, locally signed, and emulator smoke-tested, with account upload steps still required before public store release.

The web, npm, PyPI, harness, and Android package lanes all have working local gates. The mobile lane now builds signed AetherBrowse artifacts with the native package name `com.issdandavis.aetherbrowse` instead of the older AetherCode package identity.

## Green Gates

| Lane | Command | Result |
| --- | --- | --- |
| npm package guard | `npm run publish:check:strict` | PASS: `scbe-aethermoore-4.0.3.tgz`, 1275 entries, clean package contents |
| PyPI build | `npm run publish:pypi:build` | PASS: built `scbe_aethermoore-4.0.3-py3-none-any.whl` and `scbe_aethermoore-4.0.3.tar.gz` |
| PyPI dist guard | `npm run publish:pypi:check` | PASS: upload-safe, with non-blocking warnings for three test-like modules in the wheel |
| docs publish surface | `python scripts/system/verify_docs_publish_surface.py --root docs --require index.html --require support.html --require redteam.html --require-checkout` | PASS |
| harness release readiness | `python scripts/ci/harness_release_readiness.py --json` | PASS: `ready_to_publish=true`, 41/41 files, no drift in the harness release set |
| Play package | `powershell -ExecutionPolicy Bypass -File scripts/system/package_aetherbrowse_appstore.ps1 -Format aab -Store play -SkipInstall` | PASS: signed AAB |
| Kindle package | `powershell -ExecutionPolicy Bypass -File scripts/system/package_aetherbrowse_appstore.ps1 -Format apk -Store kindle -SkipInstall` | PASS: signed APK |
| APK signature verify | `apksigner verify --verbose --print-certs artifacts/releases/aetherbrowse-appstore/20260503T141755Z/aetherbrowse-kindle.apk` | PASS: v1 and v2 signatures verified |
| Emulator install smoke | `adb install -r artifacts/releases/aetherbrowse-appstore/20260503T141755Z/aetherbrowse-kindle.apk` | PASS: installed and launched on `emulator-5554` |

## Built Artifacts

### PyPI

- `artifacts/pypi-dist/scbe_aethermoore-4.0.3-py3-none-any.whl`
- `artifacts/pypi-dist/scbe_aethermoore-4.0.3.tar.gz`

Guard note: the wheel includes these test-like modules:

- `symphonic_cipher/scbe_aethermoore/layer_tests.py`
- `symphonic_cipher/scbe_aethermoore/patent_validation_tests.py`
- `symphonic_cipher/scbe_aethermoore/test_scbe_system.py`

The guard marks these as warnings, not blockers.

### AetherBrowse - Google Play AAB

- Artifact: `artifacts/releases/aetherbrowse-appstore/20260503T141714Z/aetherbrowse-play.aab`
- Manifest: `artifacts/releases/aetherbrowse-appstore/20260503T141714Z/release_manifest.json`
- SHA256: `2353E115A26363849B6D5001F18BF1A74C4852D35AF358A2038F0424EEDB94EA`
- App ID in release manifest: `com.issdandavis.aetherbrowse`
- Signed with local AetherBrowse upload key

### AetherBrowse - Kindle APK

- Artifact: `artifacts/releases/aetherbrowse-appstore/20260503T141755Z/aetherbrowse-kindle.apk`
- Manifest: `artifacts/releases/aetherbrowse-appstore/20260503T141755Z/release_manifest.json`
- SHA256: `766E2B418EFCB14D8579C6BB280A8378AB5A51D85E7CE8D811B5C0E2FBDC9F68`
- Verified with `aapt dump badging`:
  - package: `com.issdandavis.aetherbrowse`
  - label: `AetherBrowse`
  - min SDK: `23`
  - target SDK: `35`
- Verified with `apksigner`:
  - v1 JAR signing: true
  - v2 APK Signature Scheme: true
  - signer SHA-256 certificate digest: `a293e4881b52aafc8a94ff65d3dc7a7fca951765fd1a947e0c80807dc9a49614`

## Fix Landed During Sweep

`kindle-app/android/app/build.gradle` now honors `AETHERCODE_APP_VARIANT=aetherbrowse` at the native Android layer:

- `applicationId` switches to `com.issdandavis.aetherbrowse`
- app label switches to `AetherBrowse`
- package/custom URL strings switch to the AetherBrowse ID

This matters because `capacitor.config.ts` already selected the AetherBrowse variant, but the native Gradle package still built as `com.issdandavis.aethercode`. The APK metadata now matches the intended store identity.

## Signing Key

The AetherBrowse upload key was generated locally with `keytool` and is not stored in Git.

- Keystore path: `C:\Users\issda\.scbe\android-signing\aetherbrowse-upload.jks`
- Alias: `aetherbrowse_upload`
- Certificate SHA-256: `A2:93:E4:88:1B:52:AA:FC:8A:94:FF:65:D3:DC:7A:7F:CA:95:17:65:FD:1A:94:7E:0C:80:80:7D:C9:A4:96:14`
- Validity: 2026-05-03 through 2053-09-18
- Local secret config: `kindle-app/android/signing.local.properties`

The local secret config and `*.jks`/`*.keystore` files are ignored by `kindle-app/android/.gitignore`.

## Emulator Smoke

The signed Kindle APK installed and launched on `SCBE_Pixel_6_API35`.

- Device: `emulator-5554`
- Install result: `Success`
- Package probe: `package:com.issdandavis.aetherbrowse`
- Launch result: `mCurrentFocus=Window{... com.issdandavis.aetherbrowse/com.issdandavis.aethercode.MainActivity}`

The activity class still lives under `com.issdandavis.aethercode.MainActivity`, which is acceptable for this build because the published package identity is `com.issdandavis.aetherbrowse`. A later cleanup can rename the Java package if desired, but it is not required for install or launch.

## Remaining Release Blockers

1. Registry/account publish tokens still need explicit operator approval.

   npm and PyPI package guards are green, but actual publishing should happen only after confirming the intended package names, registry accounts, two-factor/auth flow, and version tag.

2. Mobile store accounts still need upload access.

   The repo has store listing drafts in `kindle-app/store-listing-aetherbrowse.md`, `kindle-app/store-listing-google-play.md`, and `kindle-app/store-listing.md`. Those should be reviewed against the final artifact before upload.

3. Repo-wide dirty tree is still intentionally mixed.

   The harness release set is clean, but the wider worktree still contains training, CLI, hook, package, and generated/mobile packaging changes. Do not make a broad release commit. Stage only the files for the specific release lane being shipped.

## Next Best Actions

1. Commit the native AetherBrowse package-identity and signing-configuration fix with this status note.
2. Decide which lane publishes first:
   - website/Vercel docs surface
   - npm package
   - PyPI package
   - Android Play AAB
   - Kindle APK
