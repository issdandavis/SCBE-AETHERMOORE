# Proton Mail Bridge AI Workflow

Goal: local, secure AI-assisted mail operations for `aethermoregames@pm.me` through Proton Mail Bridge.

## What is already done
- Proton Mail Bridge is installed on this machine.
- Local mail tool created: `scripts/system/proton_mail_ops.py`
- Shell helper created: `scripts/system/proton_bridge_env.ps1`

## One-time human step
1. Open Proton Mail Bridge.
2. Sign into your Proton account.
3. Add the mailbox you want the AI to operate on.
4. In Bridge, copy the local mailbox credentials:
   - username
   - password
   - IMAP port
   - SMTP port

## Load the Bridge credentials into your current PowerShell shell
```powershell
powershell -ExecutionPolicy Bypass -File scripts/system/proton_bridge_env.ps1
```

You will be prompted for the Bridge username and password.

## Check readiness
```powershell
python scripts/system/proton_mail_ops.py doctor --json
```

Expected result when ready:
- `ready: true`
- `imap_reachable: true`
- `smtp_reachable: true`

## List folders
```powershell
python scripts/system/proton_mail_ops.py folders --json
```

## Read inbox summaries without mutating mail
```powershell
python scripts/system/proton_mail_ops.py inbox --folder INBOX --limit 20 --json
```

## Plan deterministic triage without moving anything
```powershell
python scripts/system/proton_mail_ops.py triage --folder INBOX --limit 20 --json
```

## Apply the triage plan
Dry-run behavior is the default. Actual moves require `--execute`.

```powershell
python scripts/system/proton_mail_ops.py apply --folder INBOX --limit 20 --execute --json
```

## Send a mail through Proton Bridge
Dry-run behavior is the default. Actual sending requires `--execute`.

```powershell
python scripts/system/proton_mail_ops.py send --to someone@example.com --subject "Test" --body "Hello" --execute --json
```

## Safety model
- local-only through Proton Bridge on `127.0.0.1`
- no password storage in repo files
- dry-run by default for triage and send
- allowlisted target folders only
- JSONL audit log at `artifacts/mail/proton_mail_ops.jsonl`

## Current deterministic categories
- `Support`
- `Orders`
- `Access Keys`
- `Delivery Failures`
- `Partnerships`
- `Admin`
- fallback: `AI Review`

## Next step after the Bridge login works
- add a supervised AI classification layer on top of the deterministic triage
- add reply drafting
- add guarded auto-send rules for only the lanes you approve
