# SYSTEM BUILD GUIDE (SCBE-AETHERMOORE)
Version: 1.0
Last Updated: 2026-01-18

This document consolidates the build, install, test, and publish steps for the
SCBE-AETHERMOORE system. It replaces the need to jump between multiple files by
covering the full setup flow and the known issues we have encountered.

## Scope
- Node.js TypeScript package (npm publish flow)
- Python RWP v3.0 + Sacred Tongues + SCBE layers
- Test and validation steps (Vitest + Pytest)
- Common failures and how to avoid them

## Prerequisites
- Node.js 20+ and npm
- Python 3.11+ (tested with Python 3.14)
- Git

Optional (only if using PQC features):
- liboqs-python (requires a working liboqs build on your platform)

## Repository Setup
From the repo root:

```bash
git status
```

Confirm you are in:
`C:\Users\issda\Downloads\SCBE_Production_Pack`

## Install Dependencies

### Node.js (TypeScript package)
```bash
npm install
```

### Python (RWP v3.0 + SCBE)
Create and activate a virtual environment (recommended):

PowerShell:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Git Bash:
```bash
python -m venv .venv
source .venv/Scripts/activate
```

Install requirements:
```bash
pip install -r requirements.txt
```

Optional PQC:
```bash
pip install liboqs-python
```

## Build Steps

### TypeScript build (npm package)
```bash
npm run build
```

Expected output:
- `dist/` populated
- Type declarations generated

### Python demo validation
```bash
python examples/rwp_v3_demo.py
```

Expected output includes:
`All Demos Complete!`

## Run Tests

### Full test suite (Node + Python)
```bash
npm run test:all
```

Note: This runs `vitest run` followed by `pytest tests/ -v`.

### Node-only tests
```bash
npm test
```

### Python-only tests
```bash
pytest tests/ -v
```

## Known Test Issues and How to Avoid Them

1. Pytest failure: `tests/test_scbe_comprehensive.py::TestEdgeCasesAndFaults::test_98_timing_consistency`
   - Symptom: Assertion comparing std deviation to 50 percent of mean.
   - Cause: Timing variance on busy machines or aggressive CPU scaling.
    - Mitigation:
      - Close background CPU-heavy apps.
      - Re-run the test on an idle machine.
      - Consider pinning CPU performance mode before running tests.
   - Override: Set `SCBE_TIMING_STDDEV_RATIO=0.75` (or higher) to relax the
     consistency threshold in variable environments.

2. Pytest XPASS in `tests/test_known_limitations.py`
   - Symptom: Tests marked XFAIL unexpectedly pass.
   - Note: This indicates the implementation is stronger than the limitation
     assumptions. It is not a failure, but it is reported in the summary.

3. Vitest warning: `package.json` export `types` condition order
   - Symptom: Warning that `types` is never used because it appears after
     `import` and `require`.
   - Mitigation: Optional cleanup by reordering conditions (not required for
     the build).

## NPM Publish Flow (If Releasing the Package)
```bash
npm pack
npm publish scbe-aethermoore-3.0.0.tgz --access public
```

See `NPM_PUBLISH_NOW.md` for full release checklist and troubleshooting.

## System Components (Build Targets)
This build covers:
- RWP v3.0 protocol (Argon2id + XChaCha20-Poly1305 + Sacred Tongues)
- SCBE Layer 1-14 governance
- Thin Membrane Manifold extension (boundary layer governance)
- Topological Linearization CFI integration

Detailed references:
- `RWP_V3_QUICKSTART.md`
- `RWP_V3_INTEGRATION_COMPLETE.md`
- `DIMENSIONAL_THEORY_COMPLETE.md`
- `SACRED_TONGUE_QUICK_REFERENCE.md`
- `SCBE_AETHERMOORE_TOPOLOGICAL_CFI_UNIFIED_STRATEGY.md`

## Troubleshooting (Environment)

### Git Bash .bashrc encoding
If Git Bash fails to load `.bashrc` or shows encoding garbage:
- Ensure `.bashrc` is UTF-8 without BOM.
- Convert to Unix line endings.

### Python import errors
- `ImportError: No module named 'argon2'` -> `pip install argon2-cffi`
- `ImportError: No module named 'Crypto'` -> `pip install pycryptodome`
- `ImportError: No module named 'oqs'` -> `pip install liboqs-python` (optional)

### AEAD failures
`ValueError: AEAD authentication failed` typically indicates:
- Wrong password
- Tampered envelope

## Post-Build Validation Checklist
- `python examples/rwp_v3_demo.py` completes with all demos passing
- `npm test` completes without failures
- `pytest tests/ -v` completes without failures (or only expected xfail/skip)
- `dist/` contains generated JS and `.d.ts`

## Support
- GitHub: https://github.com/issdandavis/scbe-aethermoore-demo
- Live Demo: https://replit.com/@issdandavis/AI-Workflow-Architect
