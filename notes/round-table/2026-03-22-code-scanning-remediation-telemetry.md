# Code Scanning Remediation Telemetry — 2026-03-22

## Objective

Stabilize the GitHub code-scanning lane, harden release-signing workflow handling, close obvious remaining scanner issues in local code, and preserve the remediation path as reusable AI telemetry.

## Why This Run Happened

- GitHub Security Overview reported weak `java-kotlin` CodeQL analysis quality.
- The original CodeQL lane only covered interpreted languages and did not build the Android / Gradle surface.
- The Kindle release workflow held hardcoded signing defaults and was not suitable for durable release identity.
- Local code still had a scanner-visible DOM construction path in [browse.html](C:/Users/issda/SCBE-AETHERMOORE/kindle-app/www/browse.html).
- Workflow status retrieval from this shell was intermittently blocked by outbound socket restrictions, so the audit layer needed an offline inventory mode.

## Exact Steps Taken

1. Reviewed the current CodeQL workflow and confirmed it only scanned `javascript-typescript` and `python`.
2. Inspected the Kindle Android lane and confirmed it is a real Gradle / Capacitor build rooted at [kindle-app/android](C:/Users/issda/SCBE-AETHERMOORE/kindle-app/android).
3. Added [codeql-analysis.yml](C:/Users/issda/SCBE-AETHERMOORE/.github/workflows/codeql-analysis.yml) with a dedicated `java-kotlin` job using Node 20, Java 21, Android SDK, `npm ci`, `npx cap sync android`, and `./gradlew assembleDebug`.
4. Added [codeql-config.yml](C:/Users/issda/SCBE-AETHERMOORE/.github/codeql/codeql-config.yml) to include Android source and ignore generated Android / Gradle output.
5. Added the repo-local code-scanning ops lane under [skills/codex-mirror/scbe-code-scanning-ops](C:/Users/issda/SCBE-AETHERMOORE/skills/codex-mirror/scbe-code-scanning-ops) and the alert summarizer [inspect_code_scanning_alerts.py](C:/Users/issda/SCBE-AETHERMOORE/skills/codex-mirror/scbe-code-scanning-ops/scripts/inspect_code_scanning_alerts.py).
6. Fixed the connector bridge in [connector_bridge.py](C:/Users/issda/SCBE-AETHERMOORE/src/fleet/connector_bridge.py) by adding the missing `automations` connector, explicit event validation, and safe HTTP posting.
7. Hardened the Kindle release workflow in [kindle-build.yml](C:/Users/issda/SCBE-AETHERMOORE/.github/workflows/kindle-build.yml) so release signing is gated on GitHub secrets instead of hardcoded values.
8. Upgraded that release workflow from ephemeral keystore generation to a persistent-keystore model using `AETHERCODE_KEYSTORE_B64`.
9. Generated a persistent Android signing keystore locally, saved a backup at `C:\Users\issda\AppData\Local\SCBE\secrets\AetherCode`, and stored passwords as DPAPI-encrypted files.
10. Set GitHub repository secrets:
    - `AETHERCODE_KEY_ALIAS`
    - `AETHERCODE_KEYSTORE_PASSWORD`
    - `AETHERCODE_KEY_PASSWORD`
    - `AETHERCODE_KEYSTORE_B64`
11. Corrected the PKCS12 password behavior so the key password matches the store password.
12. Removed dynamic string-built DOM rendering from [browse.html](C:/Users/issda/SCBE-AETHERMOORE/kindle-app/www/browse.html) and replaced it with `document.createElement(...)` construction for quick links, recents, and tabs.
13. Added regression coverage in [test_code_scanning_batch5.py](C:/Users/issda/SCBE-AETHERMOORE/tests/test_code_scanning_batch5.py) for the Kindle browse rendering path.
14. Extended [github_workflow_audit.py](C:/Users/issda/SCBE-AETHERMOORE/scripts/system/github_workflow_audit.py) so it falls back to a categorized local workflow inventory when live GitHub API access is blocked.
15. Added regression coverage in [test_github_workflow_audit.py](C:/Users/issda/SCBE-AETHERMOORE/tests/test_github_workflow_audit.py).
16. Committed the first workflow/security batch on branch `fix/workflow-security-hardening`, pushed it, and opened [PR #608](https://github.com/issdandavis/SCBE-AETHERMOORE/pull/608).

## Proof / Evidence

- PR: [#608](https://github.com/issdandavis/SCBE-AETHERMOORE/pull/608)
- Branch: `fix/workflow-security-hardening`
- Backup directory: `C:\Users\issda\AppData\Local\SCBE\secrets\AetherCode`
- Verified GitHub secrets present via `gh secret list -R issdandavis/SCBE-AETHERMOORE`
- Local workflow inventory written to [workflow_audit.json](C:/Users/issda/SCBE-AETHERMOORE/artifacts/system-audit/workflow_audit.json)

## Test Evidence

- `python -m pytest tests/test_github_workflow_audit.py tests/test_notebooklm_connector_bridge.py tests/test_inspect_code_scanning_alerts.py tests/test_system_script_security.py tests/test_sensitive_output_redaction.py tests/test_code_scanning_batch5.py tests/test_browser_toolkit.py tests/test_hydra_command_center.py tests/aetherbrowser/test_page_analyzer.py -q`
  - `114 passed`
- `python -m pytest tests/test_code_scanning_batch5.py tests/test_browser_toolkit.py tests/aetherbrowser/test_page_analyzer.py tests/test_notebooklm_connector_bridge.py -q`
  - `82 passed`
- YAML validation:
  - [codeql-analysis.yml](C:/Users/issda/SCBE-AETHERMOORE/.github/workflows/codeql-analysis.yml)
  - [codeql-config.yml](C:/Users/issda/SCBE-AETHERMOORE/.github/codeql/codeql-config.yml)
  - [kindle-build.yml](C:/Users/issda/SCBE-AETHERMOORE/.github/workflows/kindle-build.yml)

## Workflow Surface Snapshot

Local workflow audit currently groups the GitHub Actions surface into:

- `20` CI workflows
- `13` automation workflows
- `10` deploy workflows
- `8` security workflows
- `6` training workflows

This snapshot exists to support the next cleanup pass: consolidation of overlapping deploy, nightly, and training lanes.

## Residual Notes

- GitHub cannot manually `workflow_dispatch` the new `codeql-analysis.yml` by name until that workflow exists on the default branch. The PR lane is therefore the correct rescan path for now.
- The code-scanning warnings on GitHub will remain open until the new workflow runs and uploads fresh results.
- The signing keystore is now durable, but the long-term release path should eventually move from a repo-secret base64 blob to a more formal secret-storage or signing service lane.

## Follow-Up Batch - Remaining Scanner Alerts

This follow-up batch targeted the remaining selected alerts after PR `#608` was already open:

- `#2228` clear-text storage in [scripts/scbe-system-cli.py](C:/Users/issda/SCBE-AETHERMOORE/scripts/scbe-system-cli.py)
- `#2248`, `#2247`, `#2068`, `#2067` information exposure through exception in [scbe_n8n_bridge.py](C:/Users/issda/SCBE-AETHERMOORE/workflows/n8n/scbe_n8n_bridge.py)
- `#2246` overly permissive regex in [secret_store.py](C:/Users/issda/SCBE-AETHERMOORE/src/security/secret_store.py)
- `#2263` missing workflow permissions in [security-checks.yml](C:/Users/issda/SCBE-AETHERMOORE/.github/workflows/security-checks.yml)
- stale test-lane logging hits `#500` and `#501` in [test_harmonic_scaling_integration.py](C:/Users/issda/SCBE-AETHERMOORE/tests/test_harmonic_scaling_integration.py)

### Exact Follow-Up Steps

1. Traced the stale `scbe-system-cli.py` line reference to the current Colab bridge lane and confirmed the sensitive path was the bridge setter carrying tokens through process arguments and registry-like persistence surfaces.
2. Added token-safe bridge preparation in [scripts/scbe-system-cli.py](C:/Users/issda/SCBE-AETHERMOORE/scripts/scbe-system-cli.py) so `bridge-set` strips `?token=...` from backend URLs, moves the token into `SCBE_COLAB_BRIDGE_TOKEN`, and passes only `--token-env` to the helper script.
3. Hardened `_save_agent_registry(...)` in that same file so accidental secret-like keys are removed before registry JSON is written to disk while preserving safe `api_key_env` references.
4. Patched [colab_n8n_bridge.py](C:/Users/issda/SCBE-AETHERMOORE/external/codex-skills-live/scbe-n8n-colab-bridge/scripts/colab_n8n_bridge.py) to support `--token-env`, stop storing `backend_url_raw`, and stop reflecting token-bearing probe URLs in output.
5. Tightened [secret_store.py](C:/Users/issda/SCBE-AETHERMOORE/src/security/secret_store.py) by narrowing the Shopify token regex and adding optional `tongue` compatibility for the bridge helper.
6. Added public-error sanitization helpers in [scbe_n8n_bridge.py](C:/Users/issda/SCBE-AETHERMOORE/workflows/n8n/scbe_n8n_bridge.py) and converted kernel-runner, browser-service, provider-dispatch, tongue-encoding, Zapier, and HF-upload failure paths to stable error codes instead of raw exception text or upstream bodies.
7. Added explicit least-privilege permissions and normalized formatting in [security-checks.yml](C:/Users/issda/SCBE-AETHERMOORE/.github/workflows/security-checks.yml).
8. Reduced the stale harmonic test log surface in [test_harmonic_scaling_integration.py](C:/Users/issda/SCBE-AETHERMOORE/tests/test_harmonic_scaling_integration.py) so the selected lines no longer print raw index/distance values.
9. Added deterministic regressions in [test_scbe_n8n_bridge_security.py](C:/Users/issda/SCBE-AETHERMOORE/tests/test_scbe_n8n_bridge_security.py), [test_sensitive_output_redaction.py](C:/Users/issda/SCBE-AETHERMOORE/tests/test_sensitive_output_redaction.py), and [test_system_script_security.py](C:/Users/issda/SCBE-AETHERMOORE/tests/test_system_script_security.py).

### Follow-Up Test Evidence

- `python -m pytest tests/test_scbe_n8n_bridge_security.py tests/test_sensitive_output_redaction.py tests/test_harmonic_scaling_integration.py -q`
  - `29 passed`
- `python -m pytest tests/test_system_script_security.py tests/test_scbe_system_cli_operator.py tests/test_github_workflow_audit.py tests/test_code_scanning_batch5.py -q`
  - `26 passed`
- `python -c "import py_compile; ..."`
  - `py_compile ok` for the touched Python files
- `python -c "import yaml, pathlib; ..."`
  - `yaml ok` for [security-checks.yml](C:/Users/issda/SCBE-AETHERMOORE/.github/workflows/security-checks.yml)

## Follow-Up Batch 2 - Final PR #608 Alert Sweep

This batch targeted the remaining live PR alerts after the previous rescan reduced the backlog to a smaller set:

- `#2276` clear-text logging in [colab_n8n_bridge.py](C:/Users/issda/SCBE-AETHERMOORE/external/codex-skills-live/scbe-n8n-colab-bridge/scripts/colab_n8n_bridge.py)
- `#2275` clear-text storage in [secret_store.py](C:/Users/issda/SCBE-AETHERMOORE/src/security/secret_store.py)
- `#2274`, `#2273`, `#2272` Hydra browser sanitization issues in [hydra_terminal_browse.mjs](C:/Users/issda/SCBE-AETHERMOORE/external/codex-skills-live/hydra-node-terminal-browsing/scripts/hydra_terminal_browse.mjs)
- older biased-randomness findings still open on [watermark.ts](C:/Users/issda/SCBE-AETHERMOORE/src/video/watermark.ts) and [aetherlex-seed.ts](C:/Users/issda/SCBE-AETHERMOORE/src/crypto/aetherlex-seed.ts)

### Exact Follow-Up Steps

1. Pulled the live PR `#608` code-scanning alerts from GitHub and reduced the remaining worklist to the bridge, secret-store, Hydra sanitizer, and older RNG findings.
2. Reworked [secret_store.py](C:/Users/issda/SCBE-AETHERMOORE/src/security/secret_store.py) so `set_secret(...)` no longer writes plaintext values to `.secrets.json`.
3. Added encrypted-at-rest secret persistence using:
   - `Fernet` when `SCBE_SECRET_STORE_KEY` is set
   - Windows DPAPI fallback on this machine when no portable key is provided
   - process-only fallback metadata when neither encrypted persistence path is available
4. Kept the existing `get_secret(...)` / `set_secret(...)` interface intact so bridge, router, and workflow callers did not need a second secret API.
5. Hardened [colab_n8n_bridge.py](C:/Users/issda/SCBE-AETHERMOORE/external/codex-skills-live/scbe-n8n-colab-bridge/scripts/colab_n8n_bridge.py) again so `--env` emits resolver commands that fetch secrets at execution time instead of printing the token into stdout.
6. Reduced bridge probe output to a public payload only (`ok`, `status`, `api_root`, `error`) and removed preview/body text from the success path.
7. Replaced the brittle blocked-tag regex lane in [hydra_terminal_browse.mjs](C:/Users/issda/SCBE-AETHERMOORE/external/codex-skills-live/hydra-node-terminal-browsing/scripts/hydra_terminal_browse.mjs) with a small parser-style scanner for `script`, `style`, and `noscript` blocks.
8. Reordered HTML entity decoding so ampersands are decoded last, eliminating the double-unescape path.
9. Extended link filtering in that same Hydra script to reject `javascript:`, `data:`, and `vbscript:` schemes.
10. Exported the Hydra helper functions and guarded CLI execution behind a direct-entry check so the sanitizer lane can be tested as a module.
11. Replaced the remaining custom bounded-random math in [watermark.ts](C:/Users/issda/SCBE-AETHERMOORE/src/video/watermark.ts) with `crypto.randomInt(...)`.
12. Replaced the remaining custom bounded-random/global-index sampling in [aetherlex-seed.ts](C:/Users/issda/SCBE-AETHERMOORE/src/crypto/aetherlex-seed.ts) with `randomInt(...)` and bit-split global-index decoding.
13. Added regression coverage in:
   - [test_colab_n8n_bridge_security.py](C:/Users/issda/SCBE-AETHERMOORE/tests/test_colab_n8n_bridge_security.py)
   - [hydra-terminal-browse.test.ts](C:/Users/issda/SCBE-AETHERMOORE/tests/hydra-terminal-browse.test.ts)
   - [aetherlexSeed.test.ts](C:/Users/issda/SCBE-AETHERMOORE/tests/crypto/aetherlexSeed.test.ts)
   - [generator.test.ts](C:/Users/issda/SCBE-AETHERMOORE/tests/video/generator.test.ts)
14. Installed local Node dev dependencies with `npm ci` because the worktree did not have `vitest` / `tsc` available, then reran the targeted TS validation slice.

### Follow-Up Batch 2 Test Evidence

- `python -m pytest tests/test_colab_n8n_bridge_security.py tests/test_sensitive_output_redaction.py tests/test_system_script_security.py -q`
  - `23 passed`
- `npm test -- --run tests/hydra-terminal-browse.test.ts tests/crypto/aetherlexSeed.test.ts tests/video/generator.test.ts`
  - `3 files passed`
  - `92 tests passed`
- `npm run typecheck -- --pretty false`
  - `passed`
- `node --check external/codex-skills-live/hydra-node-terminal-browsing/scripts/hydra_terminal_browse.mjs`
  - `passed`
- `python -m py_compile src/security/secret_store.py external/codex-skills-live/scbe-n8n-colab-bridge/scripts/colab_n8n_bridge.py`
  - `passed`
