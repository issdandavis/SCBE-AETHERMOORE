# Kindle App Research + Virtual Upload Path

Date: 2026-03-04
Owner: agent.codex
Status: active

## Current Local State
1. Kindle app wrapper exists in `kindle-app/` (Capacitor + Android project).
2. Asset sync works (`copy-pwa-assets.js` + `npx cap sync android`).
3. Local APK build is currently blocked on missing Java runtime (`java` / `JAVA_HOME`).

## Verified Submission and Testing Path
1. Amazon Appstore submission for Fire OS accepts APK/AAB and runs through Developer Console steps (upload, target, details, review, submit).
2. Fire Tablet supports ADB debugging and APK install workflows for local testing.
3. `adb install <path_to_apk>` is the official install command for connected devices.
4. Amazon Appstore for Android mobile devices was discontinued in 2025, but Fire Tablet/Fire TV Appstore remains supported.

## Kindle Virtual Upload (Sideload) Checklist
1. On Kindle Fire:
- Enable Developer Options and USB debugging.
- Set USB mode to File Transfer (MTP) / Media device.

2. On workstation:
- Install Android platform tools (`adb`).
- Confirm device visibility: `adb devices`.
- Build APK:
  - `powershell -ExecutionPolicy Bypass -File scripts/system/kindle_build_install.ps1 -BuildType debug`
- Install APK:
  - `powershell -ExecutionPolicy Bypass -File scripts/system/kindle_build_install.ps1 -BuildType debug -Install`
  - Or direct: `adb install -r <apk_path>`

3. If multiple devices:
- Use `adb -s <serial> install -r <apk_path>`

## UI Design Notes for Kindle Fire
1. Use larger touch targets (minimum 48dp-equivalent) for tablet interaction distance.
2. Keep primary controls in thumb-safe lower/right zones in landscape.
3. Ensure readable base text at 14-16px minimum with high contrast.
4. Avoid tiny multi-column layouts on 7-inch devices; collapse to single-column action flow.
5. Keep offline banner persistent and obvious since network quality on tablets can vary.
6. Prefer local assets over CDN dependencies in the shell (already fixed in `copy-pwa-assets.js`).

## Support Added in This Repo
1. `scripts/system/kindle_build_install.ps1`
- One-command asset patch + Capacitor sync + APK build + optional ADB install.

2. `scripts/system/monitor_kindle_lane.py`
- Reads cross-talk bus and outputs Kindle-lane status snapshots.

## Immediate Blocker to Resolve
1. Install JDK 17 and set `JAVA_HOME`, then rerun `kindle_build_install.ps1`.

## Sources
1. Amazon App Submission: https://developer.amazon.com/docs/app-submission/submitting-apps-to-amazon-appstore.html
2. Fire Tablet ADB setup: https://developer.amazon.com/docs/fire-tablets/connecting-adb-to-device.html
3. Fire debug APK testing: https://developer.amazon.com/docs/fire-tablets/webapp-use-debug-apk.html
4. Android ADB install docs: https://developer.android.com/guide/developing/tools/adb.html
5. Capacitor install/getting started: https://capacitorjs.com/docs/getting-started
6. Capacitor sync command: https://capacitorjs.com/docs/cli/commands/sync
7. Amazon Appstore Android-device change note (Fire devices unaffected): https://developer.amazon.com/apps-and-games/blogs/2025/02/upcoming-changes-to-amazon-appstore-for-android-devices-and-coins-program
