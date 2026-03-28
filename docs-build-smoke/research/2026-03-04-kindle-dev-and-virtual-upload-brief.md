# Kindle App Development + Virtual Upload Brief

Date: 2026-03-04
Owner: agent.codex

## What matters right now
1. Build path: Capacitor is already the right wrapper for turning your web app into a Kindle-compatible Android APK.
2. Fast test path: use ADB install (USB or wireless) for virtual upload to your Kindle device.
3. Store path: publish via Amazon Appstore Developer Console once APK is stable.

## Confirmed constraints and guidance
1. Fire OS 14 maps to Android API level 34 (Android 14), so target modern SDK for compatibility and publishing.
2. Amazon testing docs show ADB-based install flow for Fire devices (`adb install <apk>`), which is the fastest iteration loop.
3. Capacitor Android setup supports setting app id, app name, and syncing a native Android shell for APK builds.
4. Amazon Appstore publishing flow is supported through Appstore Developer Console (“Publish” path from app listing docs).
5. Amazon Appstore quality guidance emphasizes testing across form factors and device profiles.

## Virtual upload options to Kindle
1. USB ADB sideload (most reliable):
- Enable developer options + ADB on Kindle.
- Connect device to machine.
- Run `adb devices` then `adb install -r app-debug.apk`.

2. Wireless ADB (faster repeat loop after initial pairing):
- Pair/enable ADB-over-network.
- Use `adb connect <kindle-ip>:5555`.
- Reinstall with `adb install -r app-debug.apk`.

3. CI artifact to local install:
- Build APK in GitHub Actions.
- Download artifact locally.
- Push to device using `adb install -r`.

## UI design direction for Kindle (tablet-first)
1. Design for 7–11 inch tablets with two breakpoints minimum:
- Compact tablet (`~1024x600` class)
- Large tablet (`~1920x1200+` class)

2. Navigation:
- Keep primary actions in a bottom or side rail that stays visible.
- Avoid deeply nested menus for frequent actions.

3. Touch targets:
- Minimum 44px touch targets for all primary controls.
- Keep spacing generous in toolbars and cards.

4. Layout:
- Two-column layout on large tablet.
- Single-column with sticky action bar on smaller tablet.

5. Offline and latency UX:
- Always show connection state.
- Cache shell and last known view.
- Use explicit retry buttons for network actions.

## Next execution steps
1. Run ADB smoke on current `kindle-app` build and confirm install/open.
2. Execute UI pass for tablet breakpoints in `kindle-app/www/index.html`.
3. Prepare Appstore submission checklist and metadata from `kindle-app/store-listing.md`.
4. Use AI2AI workflow payload in `workflows/n8n/kindle_app_research_payload.sample.json` for iterative design/release debate.

## Sources
1. Amazon Fire OS device filtering and API levels: https://developer.amazon.com/docs/fire-tablets/ft-device-and-feature-specifications.html
2. Amazon test app on Fire tablets (ADB install): https://developer.amazon.com/docs/fire-tablets/ft-install-app-overview.html
3. Capacitor Android getting started: https://capacitorjs.com/docs/android
4. Amazon Appstore publishing resources: https://developer.amazon.com/docs/app-submission/understanding-submission.html
5. Amazon Appstore quality recommendations: https://developer.amazon.com/docs/app-submission/appstore-quality-guidelines.html
