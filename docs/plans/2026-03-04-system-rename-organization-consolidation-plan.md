# System-Wide Renaming, Organization, and Consolidation Plan

Date: 2026-03-04
Owner: issdandavis
Scope: Local workstation + SCBE repos + connector/auth paths

## 1) Verified Current State

- Multi-model API auth from this shell:
  - Anthropic: `ok` (`/v1/models` returned models)
  - xAI/Grok: `ok` (`https://api.x.ai/v1/models` returned models)
  - Groq: `ok` (`/openai/v1/models` returned models)
- GitHub Actions secret for Hugging Face:
  - Repo: `issdandavis/SCBE-AETHERMOORE`
  - Secret: `HF_TOKEN` present (`updated 2026-02-28`)
- Local Hugging Face auth:
  - `hf auth whoami` => authenticated user `issdandavis`
  - Repo connector health check => `huggingface: ok`

## 2) Drift and Fragmentation Findings

### Repo variants (local)
- `C:\Users\issda\SCBE-AETHERMOORE`
- `C:\Users\issda\SCBE-AETHERMOORE-working`
- `C:\Users\issda\SCBE-AETHERMOORE-cleanpush`
- `C:\Users\issda\SCBE-AETHERMOORE.2`

### Entropic/EDE knowledge split across locations
- Canonical runtime repo references EDE (`ALIASES.md`, `CONCEPTS.md`, `docs/gateway/ENTROPIC_DUAL_QUANTUM_SYSTEM.md`)
- Additional architecture docs in vault path:
  - `C:\Users\issda\Documents\Avalon Files\SCBE Research\Architecture\14-Layer Architecture.md`
- Additional private repo:
  - `issdandavis/Entropicdefenseengineproposal` (active, private)

### Key doc mismatch detected
- In vault doc, legacy paths referenced but missing in canonical repo:
  - Missing: `ede/`, `flock_shepherd.py`
  - Existing canonical: `src/scbe_14layer_reference.py`, `src/ai_brain/entropic-layer.ts`

## 3) High-Value Unimplemented Items (Implement First)

1. Runtime security hardening
- `src/cloud/multi_cloud_agents.py:434`
- Finding: `Rate limiting not implemented`
- Action: implement token-bucket or sliding-window limiter + tests.

2. Gateway crypto/signature placeholders
- `src/gateway/unified-api.ts:409`
- `src/gateway/unified-api.ts:564`
- Finding: placeholder Kyber keygen + placeholder tongue signing.
- Action: wire real ML-KEM/ML-DSA signing path (or clearly gate as non-prod).

3. Demo crypto marked as non-production
- `src/gateway/DNA_MULTI_LAYER_ENCODING_TEST.py:263`
- Finding: XOR placeholder where AEAD is required.
- Action: replace with AES-256-GCM test path or isolate to demo-only package.

4. AI orchestration execution stubs
- `src/ai_orchestration/agents.py:572`
- `src/ai_orchestration/agents.py:585`
- Finding: local LLM call/test execution placeholders.
- Action: route to production provider abstraction + real test executor.

5. Model matrix local provider stub
- `src/fleet/model_matrix.py:378`
- Finding: local model loader is placeholder.
- Action: implement GGUF/ONNX loader path and health probe.

6. Decision envelope signature placeholders
- `src/fleet/polly-pads/decision-envelope.ts:122`
- `src/fleet/polly-pads/decision-envelope.ts:545`
- Finding: sha256 placeholder where ML-DSA signing is expected.
- Action: implement proper signature provider + verification tests.

## 4) Rename + Organization Policy (Target Standard)

### Canonical repos
- Keep writable canonical:
  - `SCBE-AETHERMOORE`
- Convert other local variants to archive snapshots:
  - `SCBE-AETHERMOORE-working` -> `archive/SCBE-AETHERMOORE-working-YYYYMMDD`
  - `SCBE-AETHERMOORE-cleanpush` -> `archive/SCBE-AETHERMOORE-cleanpush-YYYYMMDD`
  - `SCBE-AETHERMOORE.2` -> `archive/SCBE-AETHERMOORE.2-YYYYMMDD`

### Name normalization rules
- Repos/folders: `kebab-case` with consistent prefix (`scbe-`, `aether-`, `hydra-`).
- Docs: `docs/{domain}/{YYYY-MM-DD}-{topic}.md`.
- Ops reports: `docs/ops/{YYYY-MM-DD}-{topic}.md`.
- Plans: `docs/plans/{YYYY-MM-DD}-{topic}.md`.

### Secret/env normalization rules
- Primary env keys:
  - `XAI_API_KEY` (alias allowed: `GROK_API_KEY`)
  - `ANTHROPIC_API_KEY`
  - `HF_TOKEN`
  - `OPENAI_API_KEY`
- Keep alias map but standardize scripts to read primary key first.

## 5) Consolidation Execution Phases

### Phase A (same day)
1. Freeze canonical repo decision in docs.
2. Move variant repos to dated archive folder.
3. Add `docs/system/CANONICAL_SOURCES.md` with source-of-truth map.

### Phase B (48 hours)
1. Merge unique EDE docs from `Entropicdefenseengineproposal` into canonical `docs/gateway/`.
2. Update vault architecture notes to canonical file paths.
3. Remove stale path references (`ede/`, `flock_shepherd.py`) from active docs.

### Phase C (week)
1. Implement top 3 placeholder/security gaps (rate limit + signing + test crypto).
2. Add CI gate: fail on new `placeholder` in `src/` (except allowlist).
3. Add nightly `aetherpath_audit.py` job to produce drift report.

## 6) Repeatable Audit Pipeline

Run from `SCBE-AETHERMOORE`:

```powershell
python scripts/system/aetherpath_audit.py --cap 250
```

Outputs:
- `artifacts/system_audit/aetherpath_audit.json`
- `docs/ops/aetherpath_audit_latest.md`

## 7) Monetization Link

Do not start broad launches until Phase A+B are done and top placeholders in Section 3 are closed. This avoids selling on unstable foundations and reduces post-sale failure risk.
