# AetherCode Phone Emulator Research

Date: 2026-03-15

## Problem

The current phone lane is trying to be too many things at once:

- webtoon reader
- AI operator surface
- mobile browser
- website test harness

That produces the exact failure mode you called out: one page that is technically alive but operationally useless.

## Repo Reality

The repo already has most of the pieces needed for a better design:

- Capacitor Android shell with a single `WebView` container in [kindle-app/android/app/src/main/res/layout/activity_main.xml](C:/Users/issda/SCBE-AETHERMOORE/kindle-app/android/app/src/main/res/layout/activity_main.xml)
- Capacitor bridge activity in [kindle-app/android/app/src/main/java/com/issdandavis/aethercode/MainActivity.java](C:/Users/issda/SCBE-AETHERMOORE/kindle-app/android/app/src/main/java/com/issdandavis/aethercode/MainActivity.java)
- phone mode launcher in [scripts/system/start_aether_phone_mode.ps1](C:/Users/issda/SCBE-AETHERMOORE/scripts/system/start_aether_phone_mode.ps1)
- native stack launcher with gateway, runtime, and Playwright worker in [scripts/system/start_aether_native_stack.ps1](C:/Users/issda/SCBE-AETHERMOORE/scripts/system/start_aether_native_stack.ps1)
- current mobile lane shell in [kindle-app/www/polly-pad.html](C:/Users/issda/SCBE-AETHERMOORE/kindle-app/www/polly-pad.html)
- current chat front door in [kindle-app/www/chat.html](C:/Users/issda/SCBE-AETHERMOORE/kindle-app/www/chat.html)
- webtoon QA preview in [kindle-app/www/manhwa/ch01/index.html](C:/Users/issda/SCBE-AETHERMOORE/kindle-app/www/manhwa/ch01/index.html)
- existing mobile goal and connector product spec in [docs/ide/MVP_SPEC.md](C:/Users/issda/SCBE-AETHERMOORE/docs/ide/MVP_SPEC.md)

The core architectural issue is not missing technology. It is missing lane separation.

## External Findings

### 1. Desktop mobile emulation is not enough

Chrome DevTools Device Mode is explicitly a first-order approximation, not a real mobile device. Chrome’s own docs say it does not actually run your code on a mobile device and recommend remote debugging on a real mobile runtime when accuracy matters.

Playwright’s standard emulation path is useful for viewport, user agent, and touch behavior, but it is still emulation. It should be treated as a fast check, not the final truth.

### 2. Real Android browser automation already exists

Playwright has experimental Android automation support for Chrome for Android and Android WebView. That is the right lane when you want AI to actually drive pages in an Android runtime instead of pretending a desktop browser is a phone.

Appium remains useful for hybrid apps because it can switch between `NATIVE_APP` and `WEBVIEW_*` contexts. That matters if the app has native navigation chrome around WebView content, or if you want AI to test both app shell and site content in one session.

### 3. WebView can be debugged properly

Android’s current WebView docs recommend enabling `setWebContentsDebuggingEnabled(...)` in development builds and using Chrome DevTools over `chrome://inspect` for real WebView inspection. That gives you DOM, console, network, and runtime inspection inside the actual emulator app.

### 4. Android app layout should adapt instead of pretending all screens are the same

Current Android guidance is to build responsive/adaptive layouts using `ConstraintLayout`, window size classes, and alternate layouts for different screen widths and orientations. On phones you should prefer a single-pane or bottom-nav model. On larger tablets you can promote to two-pane.

### 5. Emulator networking is stable enough for local lanes

Android’s emulator networking docs still define `10.0.2.2` as the special alias for the host loopback interface. That means local bridge and runtime flows are fine, but the shell should treat them as infrastructure, not as the entire product.

## What A Good Phone Emulator Should Be

Not one page.

It should be a compact mobile workspace with three distinct lanes:

1. Reader lane
2. Browse lane
3. Test lane

Everything else should be subordinate to those lanes.

## Recommended Product Architecture

### Lane 1: Reader

Purpose:
- read the webtoon comfortably
- scroll chapter previews
- save position
- review pacing, gaps, and balloon density

This lane should be optimized for:

- full-height vertical reading
- large tap targets
- low chrome
- remembered chapter and scroll position
- instant switch between text-overlay and image-only versions
- optional brightness / text-scale controls
- offline caching of the current chapter pack

This should not share UI with the automation controls.

Recommended entry points:

- `Reader`
- `Chapter selector`
- `Notes`

The existing Chapter 1 preview belongs here. Polly Pad should link into it, not try to render it as a sub-feature of an ops dashboard.

### Lane 2: Browse

Purpose:
- normal human browsing on the emulator
- signed-in site inspection
- quick navigation to docs, GitHub, Notion, storefronts, etc.

This lane should be a real tabbed browser surface, not a disguised launcher page.

Minimum features:

- tabs
- back / forward / reload
- address bar
- open in external Chrome
- per-tab persistence
- screenshot capture
- share current URL into AI lane

Implementation options:

- short term: keep the existing WebView shell, but build an actual tab model around it
- medium term: promote the current AetherBrowse runtime + worker stack and use the phone app as a governed mobile client
- if full browser parity matters: route page execution through Chrome on the emulator and treat the in-app shell as orchestration, not rendering

### Lane 3: Test

Purpose:
- let AI test real websites from a phone-like runtime
- collect evidence
- reproduce failures

This lane should not be a human reading UI with extra buttons.

It should expose:

- target URL
- task prompt
- run mode:
  - `emulated-fast`
  - `android-chrome`
  - `android-webview`
- artifact capture:
  - screenshot
  - console
  - network
  - DOM snapshot
  - trace

Recommended execution stack:

- `emulated-fast`: desktop Playwright mobile emulation for cheap first-pass checks
- `android-chrome`: Playwright Android support for Chrome on the emulator
- `android-webview`: Appium or Chrome DevTools inspection when validating the in-app WebView itself

This is the important split:

- browsing is for humans
- testing is for AI + evidence

Trying to make one page do both makes both bad.

## Recommended Navigation Model

For phone-width surfaces:

- bottom navigation with `Read`, `Browse`, `Test`, `Ops`
- single-pane content
- AI controls in a bottom sheet, not a permanent giant dashboard

For tablet / roomy emulator widths:

- nav rail or two-pane layout
- left side for lane navigation or chapter list
- right side for content / actions

This aligns with current Android adaptive guidance around responsive layouts, window size classes, and two-pane promotion on larger displays.

## What To Keep Out Of The Phone Front Door

Do not put these on the first screen:

- nine-seat arena
- dense provider matrix
- bridge diagnostics as the main event
- giant ops copy blocks
- multi-column layouts on phone

Those are operator tools, not mobile-first content.

The front door should be:

- `Continue reading`
- `Open browser`
- `Run site test`
- `Recent tasks`

## Best Technical Stack For This Repo

### Short-term

Keep the current Capacitor shell, but change the app structure:

- `chat.html` becomes `ops`
- `polly-pad.html` becomes a real launcher
- add a real `reader.html`
- add a real `browse.html`
- add a real `test.html`

The existing `index.html` arena should no longer be the default mobile entry.

### Medium-term

Use the repo’s existing native stack:

- gateway on `8400`
- AetherBrowse runtime on `8401`
- Playwright worker connected to runtime

Then make the mobile app a client for that stack rather than a standalone fake browser.

That lets the phone app:

- send test jobs
- receive artifacts
- open human browsing tabs
- hand URLs or DOM state into AI tasks

### Debugging and Inspection

For dev builds:

- enable WebView debugging
- inspect the emulator app via `chrome://inspect`
- keep WebView debugging off in production builds

That is the right way to make the emulator useful for AI-assisted website debugging without inventing a fake inspector.

## Concrete Recommendation

Build this as a three-tier testing pyramid:

1. Desktop fast check
- Playwright mobile emulation
- cheap and fast

2. Android emulator browser check
- Playwright Android driving Chrome on the emulator
- validates real Android browser behavior

3. In-app WebView check
- Chrome DevTools or Appium context switching against the Capacitor app
- validates the actual shipped mobile shell

This is better than forcing every task through the in-app WebView.

## Minimum Slice To Build Next

1. Create `reader.html`
- chapter list
- chapter viewer
- saved scroll position
- notes jump target

2. Create `browse.html`
- tab strip
- URL entry
- simple bookmarks / recent
- open current page in external Chrome

3. Create `test.html`
- target URL
- test prompt
- run mode selector
- artifact viewer

4. Make `polly-pad.html` a thin home surface
- only launches lanes
- does not try to be the lanes

5. Add dev-only WebView debugging in Android
- only for debug builds

## Why This Will Make The Emulator Useful

Because the emulator will stop being “one useless tab” and become:

- a readable webtoon device
- a usable mobile browser
- a real AI website testing client

Those are three different jobs. The product needs to admit that.

## External Sources

- Android Emulator networking:
  - https://developer.android.com/studio/run/emulator-networking
- Android responsive/adaptive views:
  - https://developer.android.com/develop/ui/views/layout/responsive-adaptive-design-with-views
- Android two-pane layouts:
  - https://developer.android.com/develop/ui/views/layout/twopane
- Android WebView debugging with Chrome DevTools:
  - https://developer.android.com/develop/ui/views/layout/webapps/debug-chrome-devtools
- Android WebView API reference:
  - https://developer.android.com/reference/android/webkit/WebView
- Chrome DevTools Device Mode:
  - https://developer.chrome.com/docs/devtools/device-mode
- ChromeDriver mobile emulation guidance:
  - https://developer.chrome.com/docs/chromedriver/mobile-emulation
- Playwright Android automation:
  - https://playwright.dev/docs/api/class-android
- Appium hybrid app automation:
  - https://appium.github.io/appium.io/docs/en/writing-running-appium/web/hybrid/
