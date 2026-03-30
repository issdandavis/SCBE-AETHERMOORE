# Workflow Governance Audit

- Total workflows: 68
- Total findings: 54
- High: 14
- Medium: 36
- Low: 4

## auto-approve-trusted.yml

- [MEDIUM] line 22: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`

## auto-publish.yml

- [HIGH] line 86: MASKED_ERROR_OR_ECHO (Error masking can hide failures and create false-positive success.)
  - `PREV_TAG=$(git describe --tags --abbrev=0 HEAD^ 2>/dev/null || echo "")`

## auto-resolve-conflicts.yml

- [HIGH] line 40: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `git merge origin/main --no-commit --no-ff 2>/dev/null || true`
- [HIGH] line 45: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `git merge --abort 2>/dev/null || true`

## ci-auto-fix.yml

- [HIGH] line 88: MASKED_ERROR_OR_ECHO (Error masking can hide failures and create false-positive success.)
  - `FCOUNT=$(python3 -c "import json; print(json.load(open('/tmp/failure_report.json')).get('failure_count', 0))" 2>/dev/null || echo 0)`
- [MEDIUM] line 71: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 102: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 108: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`

## ci.yml

- [MEDIUM] line 84: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`

## coherence-gate.yml

- [MEDIUM] line 55: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`

## daily-review.yml

- [MEDIUM] line 32: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 36: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 45: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 50: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 60: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 65: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 71: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`

## daily_ops.yml

- [LOW] line 40: SET_PLUS_E_WITHOUT_EXIT_HANDLING (set +e requires explicit status handling to avoid silent failures.)
  - `set +e`
- [LOW] line 219: SET_PLUS_E_WITHOUT_EXIT_HANDLING (set +e requires explicit status handling to avoid silent failures.)
  - `set +e`

## deploy-aws.yml

- [HIGH] line 132: MASKED_ERROR_OR_ECHO (Error masking can hide failures and create false-positive success.)
  - `--query 'FunctionUrl' --output text 2>/dev/null || echo "")`
- [HIGH] line 286: MASKED_ERROR_OR_ECHO (Error masking can hide failures and create false-positive success.)
  - `curl -s "${API_URL}/v1/health" | jq . || echo "Health check pending..."`

## deploy-eks.yml

- [HIGH] line 75: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `SVC_URL=$(kubectl get svc scbe-aethermoore-service -n scbe-aethermoore -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null) || true`

## deploy-gke.yml

- [HIGH] line 109: MASKED_ERROR_OR_ECHO (Error masking can hide failures and create false-positive success.)
  - `|| echo " - Health check pending (service starting)"`

## eslint.yml

- [MEDIUM] line 60: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`

## interface-pr-ops-runner.yml

- [HIGH] line 56: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `wc -l pr_queue.jsonl || true`

## kindle-build.yml

- [HIGH] line 164: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `ls kindle-app/android/app/build/outputs/bundle/release/*.aab 2>/dev/null && echo "- Release AAB: uploaded (Play Store ready)" >> $GITHUB_STEP_SUMMARY || true`
- [HIGH] line 165: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `ls kindle-app/android/app/build/outputs/apk/release/*.apk 2>/dev/null && echo "- Release APK: uploaded (Amazon ready)" >> $GITHUB_STEP_SUMMARY || true`

## notion-to-dataset.yml

- [MEDIUM] line 94: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`

## npm-publish.yml

- [HIGH] line 72: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `last_tag=$(git describe --tags --abbrev=0 2>/dev/null || true)`

## overnight-pipeline.yml

- [MEDIUM] line 42: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 51: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 107: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 120: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 164: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 177: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 239: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 248: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 255: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 258: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 266: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 273: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 324: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 426: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 434: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`

## pqc-python.yml

- [HIGH] line 45: MASKED_ERROR_OR_TRUE (Error masking can hide failing CI checks.)
  - `ldconfig -p | grep oqs || true`

## release.yml

- [HIGH] line 41: MASKED_ERROR_OR_ECHO (Error masking can hide failures and create false-positive success.)
  - `ls -la packages/ 2>/dev/null || echo "No packages/ directory"`
- [MEDIUM] line 53: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`

## security-checks.yml

- [MEDIUM] line 49: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 57: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 63: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`

## weekly-security-audit.yml

- [MEDIUM] line 124: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [MEDIUM] line 131: CONTINUE_ON_ERROR (Non-failing CI jobs can conceal regressions.)
  - `continue-on-error: true`
- [LOW] line 29: SET_PLUS_E_WITHOUT_EXIT_HANDLING (set +e requires explicit status handling to avoid silent failures.)
  - `set +e`
- [LOW] line 96: SET_PLUS_E_WITHOUT_EXIT_HANDLING (set +e requires explicit status handling to avoid silent failures.)
  - `set +e`

