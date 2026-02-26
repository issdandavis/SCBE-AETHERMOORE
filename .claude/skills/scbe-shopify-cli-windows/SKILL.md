---
name: scbe-shopify-cli-windows
description: Bootstrap and operate Shopify CLI on Windows for theme and app development, then bridge Shopify credentials into SCBE connector registration. Use when asked to install Shopify CLI, validate Node/npm/Git prerequisites, run theme/app workflows, troubleshoot CLI issues, or wire Shopify Admin token flows into SCBE automation.
---

# SCBE Shopify CLI Windows

Use this skill for deterministic Windows PowerShell execution.

## Prerequisites

1. Node.js `20.10+`
2. npm available in PATH
3. Git available in PATH
4. Modern browser for auth

## Install + Verify

```powershell
node -v
npm -v
git --version
npm install -g @shopify/cli@latest
shopify version
shopify help
```

## Auth

```powershell
shopify auth login --store your-store.myshopify.com
```

If auth command differs by CLI release, run a dev command with `--store` and complete browser login prompt.

## Theme Workflow

```powershell
shopify theme init
cd .\<theme-dir>
shopify theme dev --store your-store.myshopify.com
shopify theme pull --store your-store.myshopify.com
shopify theme push --unpublished --store your-store.myshopify.com
shopify theme publish --store your-store.myshopify.com
shopify theme check
```

## App Workflow

```powershell
npm init @shopify/app@latest
cd .\<app-dir>
shopify app dev --store your-dev-store.myshopify.com
shopify app generate extension
shopify app deploy
```

## Bridge To SCBE Connector

After obtaining Admin API token from Shopify custom app:

1. Register `kind=shopify` connector via `/mobile/connectors`.
2. Use header auth `X-Shopify-Access-Token`.
3. Keep default runs in read-safe mode first.

## Troubleshooting

1. `shopify` not recognized -> reopen shell and verify `%APPDATA%\npm` in PATH.
2. Node version error -> upgrade Node to `20.10+`.
3. Auth loop/login failure -> `shopify auth logout`, then login again.
4. Webhook/proxy local issues -> use tunnel mode instead of localhost-only assumptions.

## Output Contract

Return:

1. Installed CLI version.
2. Auth status + target store.
3. Selected path (`theme` or `app`) and exact next commands.
4. If requested, SCBE connector payload with redacted token placeholder.
