# Local Run Guide (No Docker)

This guide sets up both SCBE repos to run end-to-end on Windows without Docker.

Last updated: 2026-01-26

---

## 1) SCBE-AETHERMOORE (Python core + tests)

Repo:

```powershell
cd C:\Users\issda\source\repos\SCBE-AETHERMOORE
```

Pull latest:

```powershell
git pull origin main
```

Install deps:

```powershell
pip install numpy scipy pytest pytest-cov fastapi uvicorn pydantic
```

Run the API (only if `api/` exists in this repo):

```powershell
cd api
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open docs:

- http://localhost:8000/docs

Run full test suite:

```powershell
cd C:\Users\issda\source\repos\SCBE-AETHERMOORE
python -m pytest -v
```

If local run scripts are present, you can use:

```powershell
cd C:\Users\issda\source\repos\SCBE-AETHERMOORE
.\scripts\run-local.ps1
```

On Linux/macOS: `./scripts/run-local.sh`
On cmd.exe: `scripts\run-local.bat`

---

## 2) scbe-aethermoore-demo (Gateway + 14-layer pipeline + TS tests)

Repo:

```powershell
cd C:\Users\issda\source\repos\scbe-aethermoore-demo
```

If you want the feature branch (RWP envelope wiring):

```powershell
git pull origin claude/add-rwp-envelope-tests-1ByAu
```

Otherwise use main:

```powershell
git pull origin main
```

Install API deps:

```powershell
pip install fastapi uvicorn pydantic
```

Run the API:

```powershell
$env:SCBE_API_KEY="your-key"
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Open docs:

- http://localhost:8000/docs

Run Node deps + tests:

```powershell
npm install
npm test
```

Run only RWP tests:

```powershell
npm test -- --run tests/spiralverse/rwp.test.ts
npm test -- --run tests/spiralverse/rwp.envelope.test.ts
```

---

## 3) One-command local runners (if present)

Core repo:

```powershell
cd C:\Users\issda\source\repos\SCBE-AETHERMOORE
.\scripts\run-local.ps1
```

If you later add a similar script to the demo repo:

```powershell
cd C:\Users\issda\source\repos\scbe-aethermoore-demo
.\scripts\run-local.ps1
```

---

## 4) Quick sanity flow (full system check)

Start demo API:

```powershell
cd C:\Users\issda\source\repos\scbe-aethermoore-demo
pip install fastapi uvicorn pydantic
$env:SCBE_API_KEY="your-key"
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Hit docs:

- http://localhost:8000/docs

Run an authorization call:

```powershell
curl -X POST http://localhost:8000/v1/authorize `
  -H "Content-Type: application/json" `
  -H "X-API-Key: your-key" `
  -d '{"agent_id":"fraud-detector-001","action":"READ","target":"customer_transactions","context":{"department":"security","sensitivity":"high"}}'
```

Expected decision bands (per pipeline config):

- ALLOW > 0.5
- QUARANTINE 0.3 - 0.5
- DENY < 0.3

---

## Notes

- This guide is Windows-first and avoids Docker.
- If you are space-constrained on C:, move Docker Desktop data to D: and/or prune unused images.
