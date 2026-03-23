## SCBE-inspired workflow references

### 1) Governance envelope audit
- Treat `detectPolicyObstruction` outcomes as canonical governance state.
- Persist the result as auditable envelope payloads with nonce, timestamp, and integrity check.
- Prefer one-line summary output before storing raw payload artifacts.

### 2) Interoperability parity guard
- Verify cross-language KDF and serialization points before merge.
- Flag fixed-length field assumptions (for example byte-level length prefixes) whenever they can drift between languages.
- Keep canonical test vectors near the boundary case that historically regressed.

### 3) CI-to-code triage loop
- Start from failed workflow IDs, then map back to source files and language-level modules.
- Run minimal edits to restore workflow shape before touching core protocol logic.
- Re-run the focused CI/validation target after each fix instead of full-suite repetition.
