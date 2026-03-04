# AetherBrowse Multi-Profile + Connector Ops

## What Was Added

- Persistent browser profiles with storage state:
  - `aetherbrowse/profiles/<profile_id>/storage_state.json`
- Worker actions:
  - `switch_profile`
  - `list_profiles`
  - `autofill_login`
- Planner shortcuts:
  - `open google colab`
  - `open ai studio`
  - `open shopify`
  - `switch profile to <id>`
  - `list profiles`
  - `autofill login for <domain> [submit]`
- Runtime env alias expansion now includes:
  - `GOOGLE_AI_API_KEY`/`GOOGLE_API_KEY`/`GEMINI_API_KEY`
  - `SHOPIFY_ADMIN_TOKEN` aliases
  - Secret-store fallback lookup for aliases

## Import Google Password Export (Safe Mode)

This path stores credentials in local secret store and writes only references:

```powershell
python scripts/system/import_google_password_export.py `
  --csv "C:\path\to\Google Passwords.csv" `
  --profile-id creator-main
```

Output index path:

```text
external/credentials/browser_profiles/creator-main/credentials_index.json
```

No raw passwords are written to this index file.

## Command Examples

From runtime command lane:

- `switch profile to creator-main`
- `list profiles`
- `open google colab`
- `open ai studio`
- `open shopify`
- `autofill login for github.com submit`

## Notes

- `autofill_login` works when page has detectable username/password selectors.
- Keep `credentials_index.json` local/private.
- Rotate any keys previously pasted in chat.
