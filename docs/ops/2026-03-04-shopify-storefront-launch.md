# Shopify Storefront Launch (Aethermore Code)

## Current state
- Custom domain `https://aethermoore.com` resolves to `/password`.
- Admin side is reachable at `https://admin.shopify.com/store/aethermore-code/products`.
- Storefront lock prevents product discovery and sales.

## Immediate unblock
1. In Shopify Admin open `Online Store -> Preferences`.
2. In **Password protection**, uncheck `Restrict access to visitors with the password`.
3. Save changes and verify:
   - `https://aethermoore.com/`
   - `https://aethermoore.com/collections/all`

## Launch pack commands
Generate standardized product media + catalog evaluation + both-side smoke report:

```powershell
Set-Location C:\Users\issda\SCBE-AETHERMOORE
powershell -ExecutionPolicy Bypass -File scripts/system/run_shopify_store_launch_pack.ps1 -Store aethermore-code.myshopify.com -RunBothSideTest -EmitCrosstalk
```

Optional live publish (requires `SHOPIFY_ACCESS_TOKEN` or `SHOPIFY_ADMIN_TOKEN`):

```powershell
Set-Location C:\Users\issda\SCBE-AETHERMOORE
powershell -ExecutionPolicy Bypass -File scripts/system/run_shopify_store_launch_pack.ps1 -Store aethermore-code.myshopify.com -RunBothSideTest -PublishLive -EmitCrosstalk
```

## Theme deploy
Push current theme and create preview:

```powershell
Set-Location C:\Users\issda\SCBE-AETHERMOORE
pwsh -File scripts/shopify_storefront_bootstrap.ps1 -Store aethermore-code.myshopify.com
```

Publish theme live when preview is approved:

```powershell
Set-Location C:\Users\issda\SCBE-AETHERMOORE
pwsh -File scripts/shopify_storefront_bootstrap.ps1 -Store aethermore-code.myshopify.com -Publish
```

## Quality targets before ads
- Product card image ratio standardized (1:1, 1600x1600).
- Minimum 250 characters of clear value proposition on each product.
- Explicit deliverables list (`what buyer gets`) in product description.
- Price ladder coherence across entry/mid/pro tiers.

