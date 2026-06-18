# AetherMoore Book Studio Mobile Release Runbook

This is the annoying part turned into a checklist.

Goal: ship AetherMoore Book Studio as a web/PWA first, then wrap it for Google Play and the Apple App Store only after the web version proves people use it.

Current product surface:

- Web app: `docs/bookforge-writing-studio.html`
- Privacy policy: `docs/legal/privacy.html`
- KDP checklist: `docs/downloads/kdp-bookforge-checklist.md`
- Package page: `docs/packages/scbe-bookforge.html`

## Release Rule

Do not start with app stores. Start with the web app.

App stores require icons, screenshots, privacy answers, account paperwork, review, testing tracks, and repeated metadata fields. The web app can go live from the existing site first. Native wrappers come after there is a reason.

## Phase 1: Web/PWA Release

- [ ] Keep the app as a static web tool first.
- [ ] Add the page to the site navigation from `docs/guides.html` and `docs/packages.html`.
- [ ] Verify mobile layout with Playwright.
- [ ] Run the phone launcher: `python scripts/release/bookforge_phone_launch.py`
- [ ] Open the printed Phone URL on the phone.
- [ ] Use Add to Home Screen / Install app.
- [ ] Link the privacy policy: `https://aethermoore.com/SCBE-AETHERMOORE/legal/privacy.html`
- [ ] Link the KDP checklist download.
- [ ] Link the $7 Writing Process Pack checkout.
- [ ] Add source links inside the app for KDP requirements.
- [ ] Publish through the normal site deployment path.
- [ ] Post one short launch note with the direct URL.

Minimum launch copy:

> AetherMoore Book Studio is a free mobile-friendly workbench for writers: scene packet, KDP checklist, cover/spine math, and book-derived cover prompt waves. Use it before fighting KDP upload.

## Phase 2: PWA Readiness

- [ ] Add `manifest.webmanifest`.
- [ ] Add app icon set: 192x192, 512x512, maskable icon.
- [ ] Add theme color and app name metadata.
- [ ] Add offline-safe shell only if it does not create stale KDP guidance.
- [ ] Confirm install prompt works on Android Chrome / Edge.
- [ ] Keep all generated book/manuscript content local unless the user explicitly submits it.

Suggested app metadata:

- App name: `AetherMoore Book Studio`
- Short name: `Book Studio`
- Category: `Productivity` or `Books & Reference`
- Tagline: `Write scenes, prep KDP, and build cover briefs.`

## Phase 3: Google Play Wrapper

Only do this after the web app is useful.

- [ ] Pick wrapper path: Capacitor is the likely route because the app is already web-first.
- [ ] Create Android package name, for example `com.aethermoore.bookforge`.
- [ ] Prepare app icon, feature graphic, and screenshots.
- [ ] Create a signed Android App Bundle (`.aab`).
- [ ] Create app in Play Console.
- [ ] Complete app content declarations.
- [ ] Complete Google Play Data safety form.
- [ ] Add privacy policy URL.
- [ ] Set content rating.
- [ ] Set target audience.
- [ ] Use internal testing first.
- [ ] If Google requires closed testing for the account type, set up closed testing before production.
- [ ] Submit production release only after test track is clean.

Official sources:

- Play testing tracks: <https://support.google.com/googleplay/android-developer/answer/9845334>
- Google Play Data safety: <https://support.google.com/googleplay/android-developer/answer/10787469>
- Google Play policies: <https://play.google/developer-content-policy/>

## Phase 4: Apple App Store Wrapper

Only do this after the web/PWA release is working and there are screenshots worth showing.

- [ ] Pick wrapper path: Capacitor or a minimal native shell.
- [ ] Create bundle ID, for example `com.aethermoore.bookforge`.
- [ ] Create app record in App Store Connect.
- [ ] Prepare app name, subtitle, description, keywords, support URL, marketing URL, and privacy policy URL.
- [ ] Prepare iPhone screenshots. Add iPad screenshots if supporting iPad.
- [ ] Fill App Privacy details in App Store Connect.
- [ ] Check third-party SDK/privacy manifest requirements if wrapper libraries add SDKs.
- [ ] Submit through TestFlight first.
- [ ] Submit for App Review after TestFlight smoke is clean.

Official sources:

- App submission overview: <https://developer.apple.com/app-store/submitting/>
- App privacy details: <https://developer.apple.com/app-store/app-privacy-details/>
- Manage app privacy in App Store Connect: <https://developer.apple.com/help/app-store-connect/manage-app-information/manage-app-privacy/>
- Screenshots and previews: <https://developer.apple.com/help/app-store-connect/manage-app-information/upload-app-previews-and-screenshots/>
- App Review Guidelines: <https://developer.apple.com/app-store/review/guidelines/>

## Store Privacy Draft For AetherMoore Book Studio

Use this only if the app remains local/static and does not add accounts, analytics, cloud storage, ads, or remote AI calls.

Plain-English position:

> AetherMoore Book Studio is a local-first writing and publishing helper powered by the Bookforge engine. The app lets users enter book setup details, scene notes, and cover brief notes in their browser. The basic app does not require an account and does not intentionally upload manuscript text, scene notes, or cover prompts to AetherMoore servers.

Data safety draft:

- Account creation: No
- Login required: No
- Ads: No
- In-app purchases: No for the free app shell; external website checkout exists for separate digital products
- User-generated content sharing: No public sharing inside the app
- Sensitive permissions: None expected
- Data collection: None intentionally collected by the static app itself
- Third-party processors: Website host and payment processors if the user follows external checkout links

Re-check this if the app later adds:

- accounts
- cloud manuscript save
- hosted image generation
- analytics
- push notifications
- payment inside the app
- AI provider API calls

## Screenshots To Capture

- [ ] Hero screen with `Write the scene. Check the book. Build the files.`
- [ ] Book Setup showing spine width and cover dimensions.
- [ ] Scene Packet output.
- [ ] Cover Lab rough/prompt waves.
- [ ] KDP Upload Checklist.
- [ ] Source Links section.

Screenshot captions:

- `Plan your KDP upload before the previewer rejects it.`
- `Calculate spine width from page count and paper type.`
- `Turn a scene goal into a usable writing packet.`
- `Build cover art in waves from the book itself.`

## Human Loop

When you are tired, do only the next physical step:

1. Open the web app.
2. Take screenshots.
3. Fill one metadata field.
4. Stop.

The app stores are not intellectually hard. They are just a pile of small forms. Treat them as a checklist, not a judgment of whether you are good at this.
