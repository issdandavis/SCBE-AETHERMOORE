# AetherDesk Browser Agent

This is the stable browser lane for AI-driven service work.

It uses a real Chrome profile plus Chrome DevTools Protocol (CDP). The user signs
into Google, Hugging Face, Kaggle, GitHub, and other services once in that
profile. After that, agents attach to the same signed-in browser instead of
creating throwaway Playwright browsers that get blocked by login systems.

## What this solves

- One persistent AetherDesk browser profile.
- One stable CDP port.
- AI can open tabs, inspect pages, monitor notebook output, dedupe tabs, and run
  Colab cells through the existing Colab runner.
- Service sign-in is reused from the profile instead of being re-created.

## What this does not do

- It does not bypass Google login security.
- It does not scrape or store passwords.
- It does not hide automation from service risk checks.

The reliability boundary is session reuse: use the same real Chrome profile.

## Commands

Run from repo root:

```powershell
npm run aetherbrowser:agent -- doctor
npm run aetherbrowser:start -- --target colab_training
npm run aetherbrowser:status -- --json
```

Open common service targets:

```powershell
npm run aetherbrowser:agent -- targets
npm run aetherbrowser:agent -- open --target huggingface
npm run aetherbrowser:agent -- open --target kaggle
```

Inspect the current browser:

```powershell
npm run aetherbrowser:agent -- inspect --match colab
```

Open a specific AetherDesk app and force its window to the front:

```powershell
npm run aetherbrowser:agent -- open-app --match 127.0.0.1:5717 --app runcontrol
```

Close duplicate tabs:

```powershell
npm run aetherbrowser:agent -- dedupe --match colab --keep newest
```

Monitor an existing notebook without rerunning it:

```powershell
npm run aetherbrowser:agent -- monitor --match train_qlora --watch-for SCBE_FAST_FULL_DONE --timeout-ms 3600000
```

Run a Colab cell through the existing runner:

```powershell
npm run aetherbrowser:agent -- colab-run `
  --target colab_training `
  --code-file artifacts\colab\scbe_fast_full_cell_one_line.py `
  --watch-for SCBE_FAST_FULL_SPEED `
  --timeout-ms 1800000
```

## Default profile

```text
C:\Users\issda\.aetherdesk\browser-profile
```

If a service needs login, open this browser once and complete login there. The
same profile is reused for later AI runs.

## Artifacts

```text
artifacts/aetherdesk_browser/last_start.json
artifacts/aetherdesk_browser/last_inspect.json
artifacts/aetherdesk_browser/last_monitor.json
artifacts/aetherdesk_browser/inspect_*.png
artifacts/aetherdesk_browser/inspect_*.txt
```
