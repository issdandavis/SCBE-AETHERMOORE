# Browser Fallback

Use browser proof only when the command line cannot establish the answer cleanly.

Recommended surfaces:
- branches page
- pulls page
- branch protection settings

Commands:

```powershell
python C:\Users\issda\SCBE-AETHERMOORE\scripts\system\browser_chain_dispatcher.py --domain github.com --task navigate --engine playwriter
python C:\Users\issda\SCBE-AETHERMOORE\scripts\system\playwriter_lane_runner.py --session 1 --url https://github.com/<owner>/<repo>/branches --task navigate
python C:\Users\issda\SCBE-AETHERMOORE\scripts\system\playwriter_lane_runner.py --session 1 --url https://github.com/<owner>/<repo>/pulls --task snapshot
```

Use the browser to confirm:
- what GitHub shows as protected or default
- whether a branch is still tied to visible PR state
- whether the cleanup plan matches the UI before remote deletion
