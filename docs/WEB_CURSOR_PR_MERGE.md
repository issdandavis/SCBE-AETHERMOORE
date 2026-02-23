# Web Cursor PR Merge

Use `scripts/web_cursor_merge_prs.py` to merge pull requests through the GitHub interface side with Playwright.

## Install
```powershell
python -m pip install playwright
playwright install chromium
```

## Approval File
`approvals.json`:
```json
{
  "approvals": [
    {
      "pr": 247,
      "approved": true,
      "approved_by": "issac",
      "expires_at": "2026-03-01T00:00:00Z"
    }
  ]
}
```

## Dry Run (default)
```powershell
python scripts/web_cursor_merge_prs.py --repo issdandavis/SCBE-AETHERMOORE --prs 247 --out artifacts/pr_merge_report.json
```

## Execute Merge Clicks
```powershell
python scripts/web_cursor_merge_prs.py --repo issdandavis/SCBE-AETHERMOORE --prs 247 --approval-file approvals.json --execute --out artifacts/pr_merge_report.json
```

## Queue File
`queue.json`:
```json
{
  "prs": [247, 248, 249]
}
```

Then run:
```powershell
python scripts/web_cursor_merge_prs.py --repo issdandavis/SCBE-AETHERMOORE --queue queue.json --approval-file approvals.json --execute
```

## Notes
- Script uses persistent browser profile at `~/.scbe-playwright-github` unless overridden.
- If login is required, run non-headless and authenticate once in that profile.
- Keep approval gating on for production merges.
- GitHub hosted runners validate/export queue; real interface clicks are intended for trusted sessions.
