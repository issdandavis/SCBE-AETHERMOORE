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
