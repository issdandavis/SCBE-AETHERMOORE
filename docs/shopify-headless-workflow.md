# Shopify Both-Sides Headless Workflow

This workflow gives you:

- A headless smoke test for both Shopify surfaces:
  - Admin side (`/admin/...`)
  - Storefront side (`/collections/...` or home page)
  - App side (`admin/apps/...` or your embedded app URL)
- A one-command storefront bootstrap that pushes your local theme and can publish it.

## 1) Both-sides browser test (Playwright)

Script: `scripts/shopify_both_side_test.py`

### First run (recommended if login session is missing)

```powershell
python scripts/shopify_both_side_test.py `
  --store-domain your-store.myshopify.com `
  --headed `
  --keep-open
```

Sign in once in the opened browser window, then press Enter to close.

### Normal headless run

```powershell
python scripts/shopify_both_side_test.py `
  --store-domain your-store.myshopify.com `
  --headless `
  --strict
```

### Headless run with app-side validation

```powershell
python scripts/shopify_both_side_test.py `
  --store-domain your-store.myshopify.com `
  --app-url "https://admin.shopify.com/store/YOUR_STORE_HANDLE/apps/YOUR_APP_HANDLE" `
  --headless `
  --strict
```

Outputs:

- `artifacts/shopify-both-side/<timestamp>-admin.png`
- `artifacts/shopify-both-side/<timestamp>-storefront.png`
- `artifacts/shopify-both-side/<timestamp>-app.png` (when `--app-url` is set)
- `artifacts/shopify-both-side/<timestamp>-report.json`

## 2) Bootstrap storefront theme (Shopify CLI)

Script: `scripts/shopify_storefront_bootstrap.ps1`

Note: the script now rejects placeholder store values like `your-store.myshopify.com`.

Push unpublished theme:

```powershell
pwsh -File scripts/shopify_storefront_bootstrap.ps1 `
  -Store your-store.myshopify.com
```

Push and publish live theme:

```powershell
pwsh -File scripts/shopify_storefront_bootstrap.ps1 `
  -Store your-store.myshopify.com `
  -Publish
```

Outputs:

- `artifacts/shopify-bootstrap/<timestamp>-bootstrap.log`
- `artifacts/shopify-bootstrap/<timestamp>-summary.json`

The summary includes `preview_url` and `editor_url` when Shopify returns JSON payload details.

If bootstrap fails with auth error (401), run:

```powershell
shopify auth logout
shopify auth login
shopify theme list --store your-real-store.myshopify.com --json
```
