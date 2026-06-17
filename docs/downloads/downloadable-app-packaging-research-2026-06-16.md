# Downloadable App Packaging Research

Date: 2026-06-16
Status: decision memo

## Decision

Ship a downloadable **SCBE Workcell** in two steps:

1. **Fast product:** packaged CLI download.
   - Buyer gets `scbe` / `geoseal` as a local tool they can run without cloning the repo.
   - Use the existing `packages/cli` surface first.
   - Publish via GitHub Releases, npm, and the existing $1 lifetime link.

2. **Next product:** desktop shell that wraps the CLI/backend.
   - Use `apps/aether-desktop/shell` as the existing UI base.
   - Package with Electron Builder first, because it fits the current React/Vite/Node repo with the least rewrite.
   - Revisit Tauri after the first downloadable app works and the Rust side is stable.

Do not start with mobile app stores. App stores add signing, review, in-app purchase rules, and support load before the product is proven.

## What People Download

### Product A: SCBE Workcell CLI

Positioning: "A governed command-line workcell for AI operators."

What it gives:

- natural-language command routing over existing legal SCBE verbs
- GeoSeal command gate and receipts
- Mechanical ELIZA support/router layer
- Code Prism safe-subset translation
- local audit trails and deterministic workcell records

Packaging:

- npm package: already aligned through `packages/cli/package.json`
- GitHub Release ZIP/TAR: include `packages/cli`, README, examples, and starter scripts
- optional single executable later with Node single executable application support

Why first:

- fastest to ship
- no GUI bugs
- no native signing blocker
- customers who need clearance/custom AI work are more likely to tolerate CLI tools

### Product B: SCBE Workcell Desktop

Positioning: "A desktop control panel for governed AI workflows."

What it gives:

- chat/support window
- tool console
- local workspace state
- buttons that call the same governed CLI/backend
- installable Windows/macOS/Linux app

Repo base:

- `apps/aether-desktop/shell`
- `scripts/aetherbrowser/api_server.py`
- `src/api/geoseal_service.py`
- `packages/cli`

Recommended packaging:

- Electron Builder for v1 installers
- Windows: NSIS installer or portable `.exe`
- macOS: `.dmg` / `.zip`
- Linux: AppImage first, `.deb` later

Why Electron first:

- current shell is React/Vite/TypeScript
- current CLI is Node-based
- easiest route to call local Node/Python services
- larger app size is acceptable for v1; getting a download into users' hands matters more

## Packaging Stack Comparison

| Stack | Best For | Pros | Cons | SCBE Fit |
|---|---|---|---|---|
| npm package | CLI users | already present, fastest, public distribution | requires Node | immediate |
| GitHub Release ZIP | direct buyers | no store, no review, easy download link | manual trust/signing issue | immediate |
| Node SEA | single-file CLI | no Node install for user | still maturing, one-script constraint | good later |
| PyInstaller | Python CLI/tools | bundles Python runtime, known path | must build per OS; Python dependency edge cases | useful for Python-only tools |
| Briefcase | native Python apps | native installers, mobile options | more structure/rewrite | not first |
| Electron Builder | desktop app | installer formats across OSes, fits React/Node | big binaries | best desktop v1 |
| Tauri 2 | small desktop/mobile app | smaller, Rust backend, app-store path | more setup, WebView dependencies, Rust integration | good v2 |
| MSIX | Windows enterprise install | clean install/uninstall, identity, updates | Windows-specific, cert/signing ceremony | enterprise later |

## Minimum Shippable Download

The smallest real thing to sell:

```text
SCBE Workcell v0.1
+-- scbe / geoseal CLI
+-- starter commands
+-- Mechanical ELIZA support router
+-- Code Prism translator
+-- local receipts folder
+-- one-page buyer guide
```

Release path:

1. Build `packages/cli` with `npm pack`.
2. Create a GitHub Release with:
   - `.tgz` npm package
   - `SCBE-Workcell-Windows.zip`
   - `SCBE-Workcell-README.pdf` or `.md`
3. Add a public download page under `docs/downloads`.
4. Wire the $1 Stripe link to "SCBE Workcell lifetime download."
5. After payment, buyer gets download link plus install instructions.

## First Desktop Release Path

Use Electron Builder unless a blocker appears.

Steps:

1. Add Electron main/preload files under `apps/aether-desktop/shell`.
2. Keep the existing Vite app as renderer.
3. Add an IPC bridge that calls allowlisted CLI commands only.
4. Add `electron-builder` config:
   - Windows: `nsis`, `portable`
   - macOS: `dmg`, `zip`
   - Linux: `AppImage`
5. Add GitHub Actions matrix builds on Windows, macOS, Linux.
6. Upload artifacts to GitHub Releases.

## Safety Boundary

The downloadable app must not be "an agent that can run anything." It should be a governed workcell:

- allowlisted commands only
- explain-before-run
- local receipt for each action
- API keys stay in environment or OS keychain later
- no cloud model call unless user configures a provider key or chooses a free/local route

This is a sellable difference: "downloadable AI tooling that does not silently take over your machine."

## Recommendation

Start with the CLI product this week. It is already closest to real.

Then wrap it in desktop. The desktop app is the sales surface; the CLI is the engine. This keeps the build honest and lets users download something before the full app-store path exists.

## Sources

- Tauri distribution docs: https://v2.tauri.app/distribute/
- Tauri Windows installer docs: https://v2.tauri.app/distribute/windows-installer/
- Electron Forge packaging docs: https://www.electronforge.io/
- Electron Forge makers docs: https://www.electronforge.io/config/makers
- Electron Builder docs: https://www.electron.build/docs/
- Node.js single executable application docs: https://nodejs.org/api/single-executable-applications.html
- PyInstaller manual: https://www.pyinstaller.org/
- BeeWare Briefcase project page: https://pypi.org/project/briefcase/
- Microsoft MSIX docs: https://learn.microsoft.com/en-us/windows/msix/
- GitHub Actions artifact docs: https://docs.github.com/en/actions/tutorials/store-and-share-data
