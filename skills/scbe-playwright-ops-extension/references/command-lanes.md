# Command Lanes

Objective: Run extension packet quickly
Lane: [CHAT]
Command:
```powershell
python skills/scbe-playwright-ops-extension/scripts/playwright_extension_runner.py --url "https://example.com" --task-id "PWX-DEMO" --summary "Playwright extension demo" --emit-notion-payload
```
Success signal: `run_report.json` prints with `"status": "OK"` or `"PARTIAL"`.

Objective: Verify report status
Lane: [OPS]
Command:
```powershell
python -c "import json, pathlib; p=pathlib.Path('artifacts/playwright_extension/run_report.json'); print(json.loads(p.read_text(encoding='utf-8'))['status'])"
```
Success signal: prints `OK`.

Objective: Check pending cross-talk messages for recipient
Lane: [OPS]
Command:
```powershell
python scripts/system/crosstalk_relay.py pending --agent agent.claude
```
Success signal: JSON array of pending packets appears.
